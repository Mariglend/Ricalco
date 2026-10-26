"""Progressi nel percorso: lezione riscritta, scheda di teoria, vista del percorso, risultati e livelli, riepilogo della home."""

import json
import time

from .curriculum import LEVELS, PATHS, SEEDS, SESSION_SIZE
from .config import LESSONS, load_json, save_json
from .llm import llm_json
from .esecuzione import norm_code, run_program
from .generazione import ARR, STR, SYS_GEN, error_hint, norm_out, program_rule
from .percorsi import (
    FOCUS, THEORY, WORKER, _PLOCK, key_info, path_desc, pool_load, pool_path, progress, progress_save, streak, today,
    unit_available, unit_lesson_id, unit_lesson_path, unit_mode, unit_of, unit_state, units, unlocked, unseen, xl)
from .lezioni import LESSON_JOBS
from .oggi import elo_state, elo_view, patterns_view, weekly_view


def rewrite_card(title, explain, code, lang, path, src):
    """Un blocco di codice da riscrivere a memoria nei giorni successivi (mazzo «ricalco»)."""
    from .flashcard import card_add
    real = [ln for ln in code.split("\n") if ln.strip() and not ln.strip().startswith(("#", "//", "--"))]
    if len(real) < 2:
        return False
    return card_add("ricalco", f"{title}\n\n{explain or 'Riscrivi il codice a memoria.'}", code, src,
                    extra={"kind": "rewrite", "lang": lang, "path": path, "due": time.time() + 20 * 3600})


def home_view():
    from .flashcard import cards_load
    p = progress()
    now = time.time()
    cards = cards_load()
    paths = []
    for pid, P in PATHS.items():
        us = units(pid)
        fixed = [u for u in us if unit_state(pid, u["id"], p).get("mastered")]
        cur = next((u for u in us if unit_available(pid, u["id"], p) and not unit_state(pid, u["id"], p).get("mastered")), None)
        st = unit_state(pid, cur["id"], p) if cur else {}
        started = any(unit_state(pid, u["id"], p) for u in us)
        paths.append({"id": pid, "name": P["name"], "goal": P["goal"], "lang": P["lang"], "algo": bool(P.get("algo")),
                      "units": len(us), "fixed": len(fixed), "started": started,
                      "unit": {"id": cur["id"], "n": us.index(cur) + 1, "title": cur["title"],
                               "step": 1 if not st.get("learned") else 2} if cur else None,
                      "due": len([c for c in cards if c.get("kind") == "rewrite" and (c.get("path") or c.get("lang")) == pid and c["due"] <= now])})
    return {"paths": paths, "reviewDue": len([c for c in cards if c.get("kind") == "rewrite" and c["due"] <= now]),
            "cardsDue": len([c for c in cards if c["due"] <= now]), "xp": p["xp"], "streak": streak(p["days"]),
            "today": today() in p["days"], "quick": p.get("quickStats", {"n": 0}).get("n", 0),
            "elo": {lg: elo_view(elo_state(p, lg), lg) for lg in ("python", "java", "sql")},
            "patterns": {lg: patterns_view(p, lg) for lg in ("python", "java", "sql")},
            "weekly": {lg: weekly_view(lg) for lg in ("python", "java", "sql")},
            "reviewByKind": {k: len([c for c in cards if c.get("kind") == k and c["due"] <= now]) for k in ("quick", "rewrite")},
            "plan": today_plan(p, now),
            "worker": dict(WORKER, focus=FOCUS["key"])}


def today_plan(p, now):
    """I suggerimenti del piano di oggi: un algoritmo del catalogo per linguaggio e le domande del colloquio da ripassare."""
    from .catalogo import catalog_items
    seen = p.get("quickSeen", {})
    nxt = {}
    for lg in ("python", "java"):
        todo = sorted([c for c in catalog_items(lg) if c["id"] not in seen], key=lambda c: c["tier"])
        nxt[lg] = {"id": todo[0]["id"], "title": todo[0]["title"], "tier": todo[0]["tier"]} if todo else None
    bank = p.get("bank", {})
    return {"algo": nxt, "bankDue": len([v for v in bank.values() if v.get("due", 0) <= now]), "bankDone": len(bank)}


MASTERY_ACC = 85
MASTERY_HINTS = 2


def lesson_done(lesson_id, level, acc, hints):
    """Lezione finita: aggiorna l'unità (impara/fissa) e crea le carte di ripasso da riscrivere."""
    from .flashcard import card_add
    L = load_json(LESSONS / f"{lesson_id}.json", None)
    if not L:
        raise ValueError("lezione non trovata")
    out = {"learned": True, "mastered": False, "newlyMastered": False, "cards": 0}
    for k, b in enumerate(L.get("blocks", [])):
        real = [ln for ln in b["code"].split("\n") if ln.strip() and not ln.strip().startswith(("#", "//"))]
        if len(real) < 2:
            continue
        front = f"«{L['title']}» · blocco {k + 1}\n\n{b.get('explain') or 'Riscrivi il blocco a memoria.'}"
        if card_add("ricalco", front, b["code"], lesson_id,
                    extra={"kind": "rewrite", "lang": L["lang"], "path": (L.get("unitKey") or L["lang"]).split("/")[0],
                           "due": time.time() + 20 * 3600, "lesson": lesson_id, "block": k}):
            out["cards"] += 1
    if L.get("unitKey"):
        with _PLOCK:
            p = progress()
            st = p.setdefault("units", {}).setdefault(L["unitKey"], {})
            was = st.get("mastered", False)
            st["learned"] = True
            st["bestLevel"] = max(st.get("bestLevel", 0), level)
            if level == 3:
                st["bestL3"] = max(st.get("bestL3", 0), acc)
                if acc >= MASTERY_ACC and hints <= MASTERY_HINTS:
                    st["mastered"] = True
            if today() not in p["days"]:
                p["days"].append(today())
            p["xp"] += 20 if level == 3 else 10
            progress_save(p)
            out.update(mastered=st.get("mastered", False), newlyMastered=st.get("mastered", False) and not was,
                       bestL3=st.get("bestL3", 0))
    return out


THEORY_SCHEMA = {"type": "object", "properties": {
    "spiegazione": STR, "esempio": STR, "punti_chiave": ARR, "errore_tipico": STR},
    "required": ["spiegazione", "esempio", "punti_chiave", "errore_tipico"]}


def get_theory(lang, uid):
    path = THEORY / f"{lang}_{uid}.json"
    cached = load_json(path, None)
    if cached:
        return cached
    i, u = unit_of(lang, uid)
    before = [x["title"] for x in units(lang)[:i]]
    prompt = (f"Scrivi la scheda di teoria dell'unità {i + 1} del percorso {path_desc(lang)}: «{u['title']}». "
              f"Concetti da spiegare: {u['concepts']}. Lo studente conosce già: {', '.join(before) or 'nulla'}.\n"
              + (f"Indicazioni tecniche: {u['notes']}\n" if u.get("notes") else "") +
              "\"spiegazione\": 150-250 parole in italiano, chiare, per chi inizia, dando del tu. Usa paragrafi brevi separati da una riga vuota "
              "e metti i pezzi di codice tra backtick.\n"
              + (f"\"esempio\": un {program_rule(xl(lang))} di 6-22 righe che mostra i concetti, con print e commenti brevi in italiano.\n"
                 if unit_mode(lang, u) not in ("review", "spring") else
                 "\"esempio\": un esempio di codice realistico (12-35 righe, con import e annotazioni) che mostra i concetti, con commenti brevi in italiano.\n") +
              "\"punti_chiave\": 3-5 frasi brevi da ricordare.\n"
              "\"errore_tipico\": l'errore più comune di chi inizia su questo argomento e come evitarlo, in 1-2 frasi.")
    msgs = [{"role": "system", "content": SYS_GEN}, {"role": "user", "content": prompt}]
    last = None
    for attempt in range(3):
        d = llm_json(msgs, THEORY_SCHEMA, temperature=0.3)
        code = norm_code(d.get("esempio"))
        if unit_mode(lang, u) in ("review", "spring") and code:
            run = {"ok": True, "stdout": "", "error": None, "skipped": True}
        else:
            run = run_program(xl(lang), code) if code else {"ok": False, "error": "esempio vuoto", "stdout": ""}
        last = (d, code, run)
        if run["ok"]:
            break
        msgs = msgs[:2] + [{"role": "assistant", "content": json.dumps(d, ensure_ascii=False)},
                           {"role": "user", "content": "L'esempio non funziona:\n" + (run.get("error") or "")[:800] + error_hint(run.get("error")) + "\nCorreggilo e restituisci tutto il JSON."}]
    d, code, run = last
    out = {"lang": xl(lang), "path": lang, "unit": uid, "title": u["title"], "text": str(d.get("spiegazione") or ""), "example": code,
           "output": norm_out(run.get("stdout")) if run["ok"] else "", "verified": run["ok"] and not run.get("skipped"),
           "runnable": not run.get("skipped"),
           "points": [str(x) for x in (d.get("punti_chiave") or [])][:6], "pitfall": str(d.get("errore_tipico") or "")}
    if run["ok"]:
        save_json(path, out)
    return out


def curriculum_view(lang):
    from .flashcard import cards_load
    p = progress()
    out = []
    current = None
    cur_unit = None
    for i, u in enumerate(units(lang)):
        ust = unit_state(lang, u["id"], p)
        avail = unit_available(lang, u["id"], p)
        if avail and not ust.get("mastered") and not cur_unit:
            cur_unit = u["id"]
        lv = []
        for l in LEVELS:
            key = f"{lang}/{u['id']}/{l['id']}"
            st = p["levels"].get(key, {})
            ok = unlocked(key, p)
            if ok and not st.get("stars") and not current and cur_unit == u["id"]:
                current = key
            lv.append({"id": l["id"], "name": l["name"], "key": key, "stars": st.get("stars", 0), "best": st.get("best", 0),
                       "runs": st.get("runs", 0), "unlocked": ok,
                       "ready": len(unseen(key, p)) if pool_path(key).exists() or SEEDS.get(key) else 0})
        mode = unit_mode(lang, u)
        out.append({"id": u["id"], "n": i + 1, "title": u["title"], "concepts": u["concepts"], "mode": mode,
                    "springSetup": u.get("exec") == "spring" and mode == "review",
                    "missing": u.get("requires") if (u.get("exec") == "tests" and mode == "review") else None,
                    "theory": (THEORY / f"{lang}_{u['id']}.json").exists(), "levels": lv,
                    "available": avail, "learned": ust.get("learned", False), "mastered": ust.get("mastered", False),
                    "bestLevel": ust.get("bestLevel", 0), "bestL3": ust.get("bestL3", 0),
                    "lessonId": unit_lesson_id(lang, u["id"]), "lessonReady": unit_lesson_path(lang, u["id"]).exists(),
                    "lessonJob": (LESSON_JOBS.get(f"{lang}/{u['id']}") or {}).get("state")})
    mistakes = [m for m in p["mistakes"] if m["key"].startswith(lang + "/")]
    now = time.time()
    review_due = len([c for c in cards_load() if c.get("kind") == "rewrite" and (c.get("path") or c.get("lang")) == lang and c["due"] <= now])
    if cur_unit and not current:
        current = f"{lang}/{cur_unit}/base"
    return {"lang": lang, "path": lang, "exec": xl(lang), "name": PATHS[lang]["name"], "goal": PATHS[lang]["goal"],
            "units": out, "current": current, "curUnit": cur_unit, "sessionSize": SESSION_SIZE,
            "reviewDue": review_due, "mastery": {"acc": MASTERY_ACC, "hints": MASTERY_HINTS},
            "xp": p["xp"], "streak": streak(p["days"]), "today": today() in p["days"], "free": p["free"],
            "mistakes": len(mistakes), "worker": dict(WORKER, focus=FOCUS["key"])}


def record_result(key, ex_id, result, review=False):
    from .flashcard import cards_from_result
    with _PLOCK:
        p = progress()
        p["seen"][ex_id] = int(time.time())
        gain = {"first": 10, "retry": 5}.get(result, 0)
        p["xp"] += gain
        if today() not in p["days"]:
            p["days"].append(today())
            p["days"] = p["days"][-400:]
        e = next((x for x in pool_load(key) if x["id"] == ex_id), None)
        if e and key_info(key)["kind"] == "path":
            st = p.setdefault("typestats", {}).setdefault(f"{key.split('/')[0]}:{e['type']}", {"n": 0, "first": 0})
            st["n"] += 1
            st["first"] += result == "first"
        ms = [m for m in p["mistakes"] if not (m["id"] == ex_id)]
        if result in ("miss", "retry") and not (review and result == "retry"):
            ms.append({"key": key, "id": ex_id, "t": int(time.time())})
        p["mistakes"] = ms[-200:]
        progress_save(p)
        out = {"xp": p["xp"], "gain": gain, "streak": streak(p["days"])}
    try:
        cards_from_result(key, ex_id)
    except Exception:
        pass
    return out


def record_level(key, first, total):
    with _PLOCK:
        p = progress()
        ratio = first / max(1, total)
        stars = 3 if ratio >= 0.85 else 2 if ratio >= 0.6 else 1 if ratio >= 0.45 else 0
        st = p["levels"].setdefault(key, {})
        before = st.get("stars", 0)
        st["stars"] = max(before, stars)
        st["best"] = max(st.get("best", 0), first)
        st["runs"] = st.get("runs", 0) + 1
        bonus = 15 if stars else 0
        p["xp"] += bonus
        progress_save(p)
        seq = key_info(key)["seq"]
        i = seq.index(key)
        nxt = seq[i + 1] if i + 1 < len(seq) else None
        return {"stars": stars, "bestStars": st["stars"], "bonus": bonus, "xp": p["xp"],
                "next": nxt, "nextUnlocked": bool(nxt and unlocked(nxt, p)), "newlyUnlocked": bool(nxt and stars and not before)}
