"""Pagina «Oggi»: esercizi a livello con punteggio Elo, ripasso, livello 4, varianti e prova settimanale."""

import json
import random
import re
import time
import uuid

from .curriculum import ALGO, CURRICULUM
from .quick import QUICK_SEEDS, QUICK_TOPICS, TIERS, TIER_DESC, patterns_for, tier_rating
from .config import DATA, LANGNAME, LLMError, LangDir, Preempted, load_json, log_event, save_json
from .llm import current_model, llm_json
from .esecuzione import norm_code, run_program
from .generazione import ARR, STR, SYS_GEN, error_hint, generate_exercise, lang_rules_program
from .percorsi import WORKER, _PLOCK, progress, progress_save, streak, today


# ---------------------------------------------------------------- pagina «Oggi»: esercizi a livello, punteggio tipo Elo
QUICK = LangDir("quick")
QUICK_FOCUS = {"lang": None, "variant": None}
QUICK_WANT = 4
ELO_START = 800
PLAN_SCORE = {"first": 1.0, "free": 1.0, "partial": 0.7, "retry": 0.6, "shown": 0.2, "none": 0.5}
LEVEL_WEIGHT = {1: 0.75, 2: 0.9, 3: 1.0, 4: 1.0}
QUICK_SCHEMA = {"type": "object", "properties": {
    "titolo": STR, "problema": STR, "piano_domanda": STR, "opzioni": ARR, "corretta": {"type": "integer"}, "perche": STR, "passi": ARR,
    "blocchi": {"type": "array", "items": {"type": "object", "properties": {"codice": STR, "cosa_fa": STR, "perche": STR},
                                           "required": ["codice", "cosa_fa", "perche"]}}},
    "required": ["titolo", "problema", "piano_domanda", "opzioni", "corretta", "perche", "passi", "blocchi"]}


def tier_of(r):
    return max(1, min(5, round((r - 650) / 150)))


def elo_state(p, lang):
    return p.setdefault("elo", {}).setdefault(lang, {"r": ELO_START, "n": 0, "hist": []})


# ---- la home segue il percorso: le unità che si possono eseguire, poi gli algoritmi, una dopo l'altra
HOME_STEP = 30      # punti Elo per passare all'argomento successivo
HOME_FROM = 725     # punteggio da cui parte la prima unità

HOME_SKIP = {"python": {"u14", "u18", "u19", "u20"}, "java": {"u16"}}   # file, test, database e HTTP: non diventano algoritmi


def home_units(lang):
    out = []
    for i, u in enumerate(CURRICULUM.get(lang, [])):
        if u.get("exec") in ("output", "tests", "sql") and not u.get("requires") and u["id"] not in HOME_SKIP.get(lang, ()):
            out.append({"label": f"Unità {i + 1} · {u['title']}", "title": u["title"], "concepts": u["concepts"], "notes": u.get("notes", "")})
    if lang in ("python", "java"):
        for i, u in enumerate(ALGO):
            out.append({"label": f"Algoritmi {i + 1} · {u['title']}", "title": u["title"], "concepts": u["concepts"], "notes": ""})
    return out


def home_index(lang, r):
    n = len(home_units(lang))
    return max(0, min(n - 1, int((r - HOME_FROM) // HOME_STEP))) if n else 0


def home_labels(lang, r):
    hu = home_units(lang)
    i = home_index(lang, r)
    return {hu[j]["label"] for j in (i, i + 1) if j < len(hu)}


def home_topic(lang, idx):
    hu = home_units(lang)
    u = hu[idx]
    before = ", ".join(x["title"] for x in hu[max(0, idx - 4):idx])
    after = ", ".join(x["title"] for x in hu[idx + 1:idx + 3])
    t = (f"{u['label']} del percorso: {u['concepts']}. Trasformalo in un piccolo problema ALGORITMICO (dati in ingresso → risultato) "
         f"che si risolve proprio con questi concetti.")
    if before:
        t += f" Puoi usare anche quello che lo studente ha già visto ({before})."
    if after:
        t += f" Non usare argomenti che vengono dopo ({after})."
    if u.get("notes"):
        t += " " + u["notes"]
    return u, t


def elo_view(e, lang=None):
    r, t = e["r"], tier_of(e["r"])
    lo, hi = tier_rating(t) - 75, tier_rating(t) + 75
    out = {"r": round(r), "n": e["n"], "tier": t, "tierName": TIERS[t], "pct": max(0, min(100, round((r - lo) / (hi - lo) * 100))),
           "nextName": TIERS.get(t + 1), "nextAt": tier_rating(t + 1) - 75 if t < 5 else None, "hist": e.get("hist", [])[-12:]}
    if lang and home_units(lang):
        hu = home_units(lang)
        i = home_index(lang, r)
        out.update(unit=hu[i]["label"], unitNext=hu[i + 1]["label"] if i + 1 < len(hu) else None,
                   unitNextAt=HOME_FROM + HOME_STEP * (i + 1) if i + 1 < len(hu) else None)
    return out


def norm_quick(q, lang):
    q = dict(q)
    q.setdefault("lang", lang)
    q["tier"] = q.get("tier") or 2
    q.setdefault("problem", "")
    q.setdefault("steps", [])
    q.setdefault("plan", None)
    if q.get("pattern") not in patterns_for(lang):
        q["pattern"] = next(iter(patterns_for(lang)))
    q["blocks"] = [dict(b, what=b.get("what") or "", explain=b.get("explain") or "") for b in q.get("blocks", [])]
    return q


def quick_items(lang):
    gen = [norm_quick(q, lang) for q in load_json(QUICK / f"{lang}.json", [])]
    from .catalogo import catalog_items
    seeds = [norm_quick(dict(q, id=f"q{lang[0]}s{i}", seed=True, verified=True), lang) for i, q in enumerate(QUICK_SEEDS.get(lang, []))]
    seeds += [norm_quick(q, lang) for q in catalog_items(lang)]
    return gen, seeds


def quick_item(lang, item_id):
    gen, seeds = quick_items(lang)
    return next((q for q in gen + seeds if q["id"] == item_id), None)


def item_rating(p, q):
    return p.get("qd", {}).get(q["id"], tier_rating(q["tier"]))


def start_level(r, d, help_level=1):
    """Livello di aiuto con cui parte l'esercizio: quello che hai raggiunto (sale dopo un esercizio pulito),
    o più alto se l'esercizio è molto sotto il tuo punteggio."""
    by_gap = 3 if r - d > 260 else 2 if r - d > 110 else 1
    return max(by_gap, help_level)


def quick_pick(lang, skip=(), pattern=None):
    """Sceglie il prossimo esercizio seguendo solo l'Elo.
    Il bersaglio è un esercizio con difficoltà poco sotto il tuo punteggio (circa 55-65% di probabilità attesa di farlo bene),
    con un po' di varietà. Sali di livello perché il tuo punteggio sale. Se l'esercizio nuovo più vicino è troppo sopra di te
    (oltre 100 punti), ne riprendi uno già fatto mentre Qwen ne prepara altri al tuo livello."""
    p = progress()
    e = elo_state(p, lang)
    r = e["r"]
    seen = p.get("quickSeen", {})
    gen, seeds = quick_items(lang)
    allq = gen + seeds
    recent = p.get("quickRecent", {}).get(lang, [])
    fresh = [q for q in allq if q["id"] not in seen and q["id"] not in skip and item_rating(p, q) <= r + 100]
    if pattern and any(q["pattern"] == pattern for q in fresh):
        fresh = [q for q in fresh if q["pattern"] == pattern]
    target = r - 50 + random.uniform(-60, 60)
    repeat_reason = None
    labels = home_labels(lang, r) if home_units(lang) else set()

    def off_path(q):
        # prima gli esercizi dell'argomento del percorso a cui sei arrivato
        if not labels:
            return 0
        return 0 if q.get("unit") in labels else 60 if not q.get("unit") else 110

    if fresh:
        item = min(fresh, key=lambda q: abs(item_rating(p, q) - target) + off_path(q) + (90 if (q.get("topic") or q["title"]) in recent else 0) + random.random() * 25)
    else:
        pool = [q for q in allq if q["id"] not in skip and item_rating(p, q) <= r + 100] or [q for q in allq if q["id"] not in skip] or allq
        item = min(pool, key=lambda q: (seen.get(q["id"], 0), abs(item_rating(p, q) - target))) if pool else None
        repeat_reason = "Al tuo punteggio non ci sono ancora esercizi nuovi: ne riprendi uno già fatto mentre Qwen ne prepara altri."
    near = len([q for q in allq if q["id"] not in seen and abs(item_rating(p, q) - r) <= 150])
    return {"item": item, "startLevel": start_level(r, item_rating(p, item), e.get("help", 1)) if item else 1, "elo": elo_view(e, lang),
            "itemRating": round(item_rating(p, item)) if item else None, "fresh": near, "repeat": bool(item and item["id"] in seen),
            "repeatReason": repeat_reason if item and item["id"] in seen else None,
            "blockHist": p.get("qblocks", {}).get(item["id"]) if item else None}


def quick_prompt(lang, tier, topic, avoid):
    av = ("\nNon ripetere questi esercizi già presenti: " + "; ".join(avoid[-15:]) + ".") if avoid else ""
    return f"""Prepara un esercizio di «ricalco»: lo studente prima ragiona su come risolvere il problema, poi riscrive il codice blocco per blocco.
Argomento: {topic}. Linguaggio: {LANGNAME[lang]}. Difficoltà {tier} su 5, {TIER_DESC[tier]}.{av}

{lang_rules_program(lang)}
- "titolo": massimo 5 parole.
- "problema": cosa deve fare il programma in 1-3 frasi, con un esempio di input e risultato. NON dire come risolverlo.
- "piano_domanda": una domanda sul METODO per risolverlo (es. «Come eviti di provare tutte le coppie?», «Quale struttura dati ti serve?»).
- "opzioni": 4 metodi brevi, uno solo giusto, gli altri plausibili ma sbagliati o inefficienti. "corretta": indice 0-3, non sempre lo stesso.
- "perche": 1-2 frasi sul perché quel metodo funziona{"" if lang == "sql" else ", con la complessità O-grande"}.
- "passi": 2-5 passi logici della soluzione, in parole, senza codice.
- "blocchi": da 2 a 5 blocchi CONSECUTIVI: concatenandoli in ordine si ottiene il programma completo con l'indentazione corretta. Per ognuno:
  "codice": le righe del blocco; "cosa_fa": UNA frase su cosa fa il blocco (es. «Scorre la lista e conta le vocali»);
  "perche": 1-3 frasi sul perché è scritto così, l'errore tipico da evitare{"" if lang == "sql" else " o la complessità"}.
L'ultimo blocco prova il codice su 2-3 casi, compreso un caso limite, e stampa i risultati."""


def generate_quick(lang, tier, topic, avoid):
    pats = patterns_for(lang)
    schema = {"type": "object", "properties": dict(QUICK_SCHEMA["properties"], schema={"type": "string", "enum": list(pats)}),
              "required": QUICK_SCHEMA["required"] + ["schema"]}
    prompt = quick_prompt(lang, tier, topic, avoid) + "\n- \"schema\": lo schema principale usato, uno tra: " + ", ".join(f"{k} ({v})" for k, v in pats.items()) + "."
    msgs = [{"role": "system", "content": SYS_GEN}, {"role": "user", "content": prompt}]
    for attempt in range(3):
        d = llm_json(msgs, schema, temperature=0.45 if attempt == 0 else 0.25)
        blocks = [{"code": norm_code(b.get("codice")), "what": str(b.get("cosa_fa") or ""), "explain": str(b.get("perche") or "")}
                  for b in (d.get("blocchi") or []) if isinstance(b, dict) and str(b.get("codice") or "").strip()]
        opts = [str(o).strip() for o in (d.get("opzioni") or []) if str(o).strip()]
        c = d.get("corretta")
        if len(blocks) < 2:
            problem = "Servono da 2 a 5 blocchi con codice."
        elif len(opts) < 3 or not isinstance(c, int) or not 0 <= c < len(opts):
            problem = "Servono 4 opzioni nel piano e l'indice di quella corretta."
        else:
            run = run_program(lang, "\n".join(b["code"] for b in blocks))
            if run["ok"]:
                return {"id": "q" + uuid.uuid4().hex[:10], "title": str(d.get("titolo") or topic[:40])[:60], "topic": topic, "lang": lang, "tier": tier,
                        "kind": "query" if lang == "sql" else "algoritmo", "verified": True, "output": run["stdout"][:2000],
                        "pattern": d.get("schema") if d.get("schema") in pats else next(iter(pats)),
                        "problem": str(d.get("problema") or ""), "steps": [str(x) for x in (d.get("passi") or [])][:6],
                        "plan": {"q": str(d.get("piano_domanda") or "Come lo risolveresti?"), "options": opts, "correct": c, "why": str(d.get("perche") or "")},
                        "blocks": blocks, "genAttempts": attempt + 1}
            problem = ("Eseguendo il programma ottenuto concatenando i blocchi c'è questo errore:\n" + (run["error"] or "")[:1200] + error_hint(run["error"])
                       + "\nCorreggi il codice (attenzione all'indentazione tra un blocco e l'altro).")
        msgs = msgs[:2] + [{"role": "assistant", "content": json.dumps(d, ensure_ascii=False)},
                           {"role": "user", "content": problem + " Restituisci di nuovo tutto il JSON."}]
    raise LLMError("Il modello non è riuscito a preparare un esercizio che funzioni.")


def quick_job(fails):
    """In sottofondo: prepara esercizi al tuo livello (e uno al livello sopra), verificati eseguendoli."""
    lang = QUICK_FOCUS["lang"]
    if not lang or not current_model():
        return False
    v = QUICK_FOCUS.get("variant")
    if v and not variant_get(*v) and fails.get("variant:" + v[1], 0) < 2:
        WORKER["job"] = "variante da zero"
        WORKER["since"] = time.time()
        try:
            t0 = time.time()
            variant_make(*v)
            log_event("gen", what="variante", lang=v[0], secs=round(time.time() - t0, 1))
        except Preempted:
            raise
        except Exception as e:
            fails["variant:" + v[1]] = fails.get("variant:" + v[1], 0) + 1
            WORKER["error"] = str(e)[:200]
        return True
    if weekly_due(lang) and not weekly_pending(lang) and fails.get("weekly", 0) < 2:
        WORKER["job"] = "prova settimanale"
        WORKER["since"] = time.time()
        try:
            t0 = time.time()
            weekly_make(lang)
            log_event("gen", what="prova settimanale", lang=lang, secs=round(time.time() - t0, 1))
        except Preempted:
            raise
        except Exception as e:
            fails["weekly"] = fails.get("weekly", 0) + 1
            WORKER["error"] = str(e)[:200]
        return True
    if fails.get("quick", 0) >= 3:
        # dopo 3 errori di fila una pausa di 5 minuti, poi si riprova (prima si fermava fino al riavvio)
        if time.time() - fails.get("quick_t", 0) < 300:
            return False
        fails["quick"] = 0
    p = progress()
    seen = p.get("quickSeen", {})
    t = tier_of(elo_state(p, lang)["r"])
    gen, seeds = quick_items(lang)
    fresh = [q for q in gen + seeds if q["id"] not in seen]
    hu = home_units(lang)
    if hu:
        # servono esercizi nuovi sull'argomento del percorso a cui sei arrivato (o il successivo)
        labels = home_labels(lang, elo_state(p, lang)["r"])
        fu = [q for q in fresh if q.get("unit") in labels]
        if len(fu) >= 3:
            return False
        tier = t + 1 if t < 5 and len(fu) >= 2 and not any(q["tier"] == t + 1 for q in fu) else t
    else:
        want = [(t, QUICK_WANT)] + ([(t + 1, 1)] if t < 5 else [])
        tier = next((tt for tt, n in want if len([q for q in fresh if q["tier"] == tt]) < n), None)
        if not tier:
            return False
    unit = None
    if hu:
        # l'argomento segue il percorso: quello del tuo punteggio (o il successivo, per l'esercizio «sopra»)
        idx = home_index(lang, elo_state(p, lang)["r"]) + (1 if tier > t else 0)
        idx = min(idx, len(hu) - 1)
        cand = [i for i in (idx, idx + 1) if i < len(hu)]
        idx = min(cand, key=lambda i: len([q for q in fresh if q.get("unit") == hu[i]["label"]]))
        unit, topic_text = home_topic(lang, idx)
        topic = unit["label"]
    else:
        used = {q.get("topic") for q in gen}
        topics = [x for x in QUICK_TOPICS[lang][tier] if x not in used] or QUICK_TOPICS[lang][tier]
        topic = topic_text = random.choice(topics)
    WORKER["job"] = f"esercizio di oggi · {TIERS[tier]} · {topic}"
    WORKER["since"] = time.time()
    try:
        t0 = time.time()
        item = generate_quick(lang, tier, topic_text, [q["title"] for q in gen])
        item["topic"] = topic
        if unit:
            item["unit"] = unit["label"]
        log_event("gen", what="oggi", lang=lang, tier=tier, topic=topic, secs=round(time.time() - t0, 1), attempts=item.get("genAttempts", 1))
        with _PLOCK:
            items = load_json(QUICK / f"{lang}.json", [])
            items.append(item)
            save_json(QUICK / f"{lang}.json", items[-300:])
        fails["quick"] = 0
    except Preempted:
        raise
    except Exception as e:
        log_event("gen_fail", what="oggi", lang=lang, tier=tier, err=str(e)[:200])
        fails["quick"] = fails.get("quick", 0) + 1
        fails["quick_t"] = time.time()
        WORKER["error"] = str(e)[:200]
    return True


def code_words(blocks):
    """Quante «parole» ha il codice (quelle che «Mostra parola» può rivelare), commenti esclusi."""
    n = 0
    for b in blocks:
        for ln in b["code"].split("\n"):
            ln = re.split(r"\s(#|//|--)\s", " " + ln + " ")[0]
            if not ln.strip().startswith(("#", "//", "--")):
                n += len(ln.split())
    return max(1, n)


def quick_score(plan, level, acc, hints, words=40, levels=None):
    """Piano 40%, codice 60%. Gli aiuti pesano in proporzione alla lunghezza del codice:
    farsi mostrare 1 parola su 10 toglie il 15% del punteggio del codice.
    Con livelli diversi per blocco, il peso del livello è la media dei blocchi."""
    revealed = min(1.0, hints / max(1, words))
    weight = sum(LEVEL_WEIGHT.get(l, 0.55) for l in levels) / len(levels) if levels else LEVEL_WEIGHT.get(level, 0.55)
    code = weight * min(1.0, acc / 100) * max(0.0, 1 - 1.5 * revealed)
    return round(0.4 * PLAN_SCORE.get(plan, 0.5) + 0.6 * code, 3)


def pattern_update(p, lang, pattern, s=None, variant=None):
    st = p.setdefault("patterns", {}).setdefault(lang, {}).setdefault(pattern, {"n": 0, "avg": 0.0, "vn": 0, "vok": 0})
    if s is not None:
        st["avg"] = s if st["n"] == 0 else round(0.7 * st["avg"] + 0.3 * s, 3)
        st["n"] += 1
    if variant is not None:
        st["vn"] += 1
        st["vok"] += bool(variant)


def patterns_view(p, lang):
    pats = patterns_for(lang)
    st = p.get("patterns", {}).get(lang, {})
    out = [{"id": k, "name": v, "n": st.get(k, {}).get("n", 0), "avg": round(st.get(k, {}).get("avg", 0) * 100),
            "vn": st.get(k, {}).get("vn", 0), "vok": st.get(k, {}).get("vok", 0)} for k, v in pats.items()]
    return sorted([x for x in out if x["n"] or x["vn"]], key=lambda x: x["avg"])


def _norm_out(t):
    return "\n".join(ln.rstrip() for ln in str(t or "").strip().splitlines() if ln.strip())


def quick_free_run(lang, item_id, code):
    """Livello 4 «Scrivi tu»: esegue il tuo programma e lo confronta con l'output della soluzione di riferimento."""
    q = quick_item(lang, item_id)
    if not q:
        raise ValueError("esercizio non trovato")
    if not code.strip():
        raise ValueError("Scrivi prima il tuo programma.")
    expected = q.get("output")
    if not expected:
        expected = run_program(lang, "\n".join(b["code"] for b in q["blocks"])).get("stdout", "")
    run = run_program(lang, code)
    match = bool(run["ok"]) and _norm_out(run["stdout"]) == _norm_out(expected)
    log_event("quick_free", id=item_id, ok=run["ok"], match=match)
    return {"ok": run["ok"], "stdout": run["stdout"], "error": run.get("error"), "expected": expected, "match": match}


def quick_done(lang, item_id, level, acc, hints, plan, mode="new", card_id=None, blocks=None):
    """Fine di un esercizio di «Oggi»: punteggio, aggiornamento Elo (solo la prima volta) e programmazione del ripasso."""
    from .flashcard import card_add, grade_card
    q = quick_item(lang, item_id)
    if not q:
        raise ValueError("esercizio non trovato")
    words = code_words(q["blocks"])
    blocks = [b for b in (blocks or []) if isinstance(b, dict)][:len(q["blocks"])]
    levels = [int(b.get("lvl") or level) for b in blocks] if len(blocks) == len(q["blocks"]) else None
    s = quick_score(plan, level, acc, hints, words, levels)
    g = 2 if s >= 0.85 else 1 if s >= 0.6 else 0
    out = {"s": s, "grade": g, "delta": 0, "revealed": round(min(1.0, hints / words) * 100), "words": words}
    with _PLOCK:
        p = progress()
        e = elo_state(p, lang)
        seen = p.setdefault("quickSeen", {})
        best = p.setdefault("qbest", {})
        first = mode == "new" and item_id not in seen
        # rifatto: conta anche lui, a metà peso e solo se fai meglio dell'ultima volta (così non si «farma» lo stesso esercizio)
        again = mode in ("new", "repeat") and item_id in seen and s > best.get(item_id, 0) + 0.02
        if first or again:
            d = item_rating(p, q)
            exp = 1 / (1 + 10 ** ((d - e["r"]) / 400))
            k = 64 if e["n"] < 10 else 32  # i primi 10 esercizi calibrano in fretta
            if again:
                k /= 2
            delta = k * (s - exp)
            e["r"] = max(400, e["r"] + delta)
            e["n"] += 1
            e.setdefault("hist", []).append({"t": int(time.time()), "id": item_id, "title": q["title"], "s": s, "d": round(delta, 1), "r": round(e["r"])})
            e["hist"] = e["hist"][-60:]
            if first:
                p.setdefault("qd", {})[item_id] = d - 16 * (s - exp)
            out["delta"] = round(delta)
            # livello di aiuto di partenza: sale di uno dopo un esercizio pulito, scende dopo uno andato male
            clean = acc >= 90 and out["revealed"] <= 5 and plan in ("first", "free", "retry")
            bad = acc < 75 or out["revealed"] >= 20
            lv_used = round(sum(levels) / len(levels)) if levels else level
            h = e.get("help", 1)
            if clean and lv_used >= h:
                e["help"] = min(3, lv_used + 1)
            elif bad:
                e["help"] = max(1, min(h, lv_used) - 1) if lv_used <= h else h
            out["help"] = e.get("help", 1)
            rec = p.setdefault("quickRecent", {}).setdefault(lang, [])
            rec.append(q.get("topic") or q["title"])
            p["quickRecent"][lang] = rec[-4:]
        seen[item_id] = int(time.time())
        best[item_id] = max(best.get(item_id, 0), s)
        if blocks:
            p.setdefault("qblocks", {})[item_id] = [{"err": int(b.get("err") or 0), "hints": int(b.get("hints") or 0), "lvl": int(b.get("lvl") or level)} for b in blocks]
        if mode in ("new", "review"):
            pattern_update(p, lang, q["pattern"], s)
        qs = p.setdefault("quickStats", {"n": 0})
        qs["n"] = qs.get("n", 0) + 1
        gain = {1: 4, 2: 6, 3: 10}.get(level, 4) + (4 if mode == "review" else 0)
        p["xp"] += gain
        if today() not in p["days"]:
            p["days"].append(today())
        progress_save(p)
        out.update(gain=gain, xp=p["xp"], elo=elo_view(e, lang), streak=streak(p["days"]))
    # ripasso: l'esercizio torna come flashcard (piano + riscrittura a memoria)
    if mode == "review" and card_id:
        grade_card(card_id, g)
    elif mode == "new":
        front = f"«{q['title']}»\n\n{q.get('problem') or ''}"
        card_add("ricalco", front, "\n".join(b["code"] for b in q["blocks"]), item_id,
                 extra={"kind": "quick", "item": item_id, "lang": lang, "path": lang, "box": 1 if g < 2 else 2,
                        "due": time.time() + (4 * 3600 if g == 0 else 20 * 3600 if g == 1 else 3 * 86400 - 3600)})
    return out


# ---- variante da zero: stesso schema, problema diverso, test veri
def variant_path(lang):
    return QUICK / f"var_{lang}.json"


def variant_get(lang, item_id):
    return load_json(variant_path(lang), {}).get(item_id)


def variant_make(lang, item_id):
    q = quick_item(lang, item_id)
    if not q:
        raise ValueError("esercizio non trovato")
    diff = "facile" if q["tier"] <= 2 else "medio" if q["tier"] == 3 else "difficile"
    topic = (f"VARIANTE dell'esercizio «{q['title']}». Problema originale: {q.get('problem')}. Lo studente ha appena riscritto questa soluzione:\n"
             + "\n".join(b["code"] for b in q["blocks"]) +
             f"\nCrea un problema GEMELLO: stesso schema ({patterns_for(lang)[q['pattern']]}; passi: {' '.join(q.get('steps') or [])}) "
             "ma con un obiettivo diverso (per esempio: il minimo invece del massimo, contare invece di cercare, restituire la posizione, "
             "un vincolo in più). Non deve bastare copiare la soluzione originale: va adattata. Nomi di funzioni e variabili diversi.")
    ex = generate_exercise("zero", lang, diff, topic, [q["title"]], "tests", attempts=3)
    ex.pop("state", None)
    ex.update(variantOf=item_id, pattern=q["pattern"])
    with _PLOCK:
        d = load_json(variant_path(lang), {})
        d[item_id] = ex
        save_json(variant_path(lang), d)
    return ex


def variant_done(lang, item_id, result, secs):
    q = quick_item(lang, item_id)
    with _PLOCK:
        p = progress()
        ok = result in ("first", "retry")
        if q:
            pattern_update(p, lang, q["pattern"], variant=ok)
        gain = {"first": 15, "retry": 8}.get(result, 0)
        p["xp"] += gain
        vs = p.setdefault("variants", [])
        vs.append({"t": int(time.time()), "lang": lang, "item": item_id, "result": result, "secs": int(secs or 0)})
        p["variants"] = vs[-300:]
        progress_save(p)
        return {"gain": gain, "xp": p["xp"], "patterns": patterns_view(p, lang)}


# ---- prova settimanale: un problema mai visto, da zero, senza aiuti, con il tempo
WEEK = 7 * 86400
WEEKLY_MIN = {1: 15, 2: 20, 3: 25, 4: 35, 5: 45}


def weekly_hist(p, lang):
    return p.get("weekly", {}).get(lang, [])


def weekly_due(lang, p=None):
    h = weekly_hist(p or progress(), lang)
    return not h or time.time() - h[-1]["t"] >= WEEK - 3600


def weekly_pending(lang):
    return load_json(QUICK / f"weekly_{lang}.json", None)


def weekly_make(lang):
    p = progress()
    t = tier_of(elo_state(p, lang)["r"])
    diff = "facile" if t <= 2 else "medio" if t == 3 else "difficile"
    done = [w.get("title") for w in weekly_hist(p, lang)]
    topic = (random.choice(QUICK_TOPICS[lang][t]) + ". È la PROVA SETTIMANALE: un problema nuovo da risolvere da zero, "
             "senza aiuti, come a un colloquio. Consegna chiara con un esempio.")
    ex = generate_exercise("zero", lang, diff, topic, done, "tests", attempts=3)
    ex.pop("state", None)
    ex.update(tier=t, minutes=WEEKLY_MIN[t])
    save_json(QUICK / f"weekly_{lang}.json", ex)
    return ex


def weekly_view(lang):
    p = progress()
    h = weekly_hist(p, lang)
    nxt = 0 if weekly_due(lang, p) else int((h[-1]["t"] + WEEK - 3600 - time.time()) // 86400) + 1
    return {"due": weekly_due(lang, p), "ready": bool(weekly_pending(lang)), "nextDays": nxt, "hist": h[-12:]}


def weekly_done(lang, ok, secs, tries, revealed):
    ex = weekly_pending(lang)
    with _PLOCK:
        p = progress()
        rec = {"t": int(time.time()), "title": ex.get("title") if ex else "", "ok": bool(ok) and not revealed, "secs": int(secs or 0),
               "tries": int(tries or 0), "tier": (ex or {}).get("tier"), "minutes": (ex or {}).get("minutes")}
        p.setdefault("weekly", {}).setdefault(lang, []).append(rec)
        if rec["ok"]:
            p["xp"] += 40
        progress_save(p)
    try:
        (QUICK / f"weekly_{lang}.json").unlink()
    except OSError:
        pass
    return weekly_view(lang)
