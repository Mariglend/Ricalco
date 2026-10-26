"""Colloquio approfondito: banca di domande con domande a catena, system design, code review e domande comportamentali.

I contenuti sono scritti e controllati a mano (cartella dati/), non generati: Qwen serve solo a valutare le risposte.
I progressi stanno in progress.json sotto "bank": per ogni domanda quanto in fondo alla catena sei arrivato e quando ripassarla."""

import json
import random
import time
from pathlib import Path

from .config import app_lang, log_event
from .llm import llm_json
from .generazione import ARR, STR, SYS_GEN
from .percorsi import _PLOCK, progress, progress_save

DATI = Path(__file__).resolve().parent / "dati"
AREE = {"java": "Java", "spring": "Spring Boot", "sql": "SQL e database", "web": "Web, HTTP e strumenti",
        "python": "Python", "fondamenti": "Fondamenti e OOP"}
LIVELLI = {1: "Junior", 2: "Junior forte", 3: "Verso mid"}
GIORNO = 86400
# dopo quanti giorni torna una domanda, in base a quanto in fondo alla catena sei arrivato (0 = ti sei fermato alla prima)
RIPASSO = [1, 3, 7, 16, 35]

_CACHE = {}


def _dati(nome):
    if nome not in _CACHE:
        f = DATI / f"{nome}.json"
        _CACHE[nome] = json.loads(f.read_text(encoding="utf-8")) if f.exists() else []
    return _CACHE[nome]


def banca():
    return _dati("colloquio_domande")


def domanda(qid):
    d = next((q for q in banca() if q["id"] == qid), None)
    if not d:
        raise ValueError("domanda sconosciuta")
    return d


def _stato(p):
    return p.setdefault("bank", {})


# ---------------------------------------------------------------- banca: viste e scelta
def banca_view():
    p = progress()
    st = _stato(p)
    now = time.time()
    aree = []
    for a, nome in AREE.items():
        qs = [q for q in banca() if q["area"] == a]
        if not qs:
            continue
        fatte = [q for q in qs if q["id"] in st]
        livelli = []
        for lv, ln in LIVELLI.items():
            ql = [q for q in qs if q["livello"] == lv]
            livelli.append({"id": lv, "name": ln, "n": len(ql), "fatte": len([q for q in ql if q["id"] in st]),
                            "piene": len([q for q in ql if st.get(q["id"], {}).get("best", -1) >= len(q.get("approfondimenti", []))])})
        aree.append({"id": a, "name": nome, "n": len(qs), "fatte": len(fatte),
                     "due": len([q for q in fatte if st[q["id"]].get("due", 0) <= now]),
                     "media": round(sum(st[q["id"]].get("score", 0) for q in fatte) / len(fatte), 1) if fatte else None,
                     "livelli": livelli})
    deboli = sorted([(v.get("score", 0), k) for k, v in st.items() if v.get("score", 5) < 3.5], key=lambda x: x[0])[:12]
    return {"aree": aree, "totale": len(banca()), "fatte": len(st),
            "deboli": [{"id": k, "q": domanda(k)["q"], "area": AREE.get(domanda(k)["area"]), "score": s} for s, k in deboli if _esiste(k)]}


def _esiste(qid):
    return any(q["id"] == qid for q in banca())


def banca_next(area=None, livello=None, skip=(), qid=None):
    """La prossima domanda: prima quelle da ripassare (le più deboli), poi quelle nuove del livello scelto.
    Con qid si riprende proprio quella domanda (dall'elenco «Dove ti fermi presto»)."""
    p = progress()
    st = _stato(p)
    now = time.time()
    if qid:
        q = domanda(qid)
        return {"id": q["id"], "area": AREE.get(q["area"]), "livello": LIVELLI.get(q["livello"]), "argomento": q.get("argomento", ""),
                "q": q["q"], "catena": len(q.get("approfondimenti", [])), "motivo": "ripasso", "prima": st.get(q["id"])}
    qs = [q for q in banca() if (not area or q["area"] == area) and (not livello or q["livello"] == int(livello)) and q["id"] not in skip]
    if not qs:
        raise ValueError("Nessuna domanda con questi filtri.")
    due = sorted([q for q in qs if q["id"] in st and st[q["id"]].get("due", 0) <= now], key=lambda q: st[q["id"]].get("score", 0))
    nuove = [q for q in qs if q["id"] not in st]
    if due and (not nuove or random.random() < 0.6):
        q, motivo = due[0], "ripasso"
    elif nuove:
        lv = min(q["livello"] for q in nuove)
        q, motivo = random.choice([x for x in nuove if x["livello"] == lv]), "nuova"
    else:
        q, motivo = min(qs, key=lambda q: st[q["id"]].get("due", 0)), "ripasso anticipato"
    return {"id": q["id"], "area": AREE.get(q["area"]), "livello": LIVELLI.get(q["livello"]), "argomento": q.get("argomento", ""),
            "q": q["q"], "catena": len(q.get("approfondimenti", [])), "motivo": motivo, "prima": st.get(q["id"])}


def banca_answer(qid, step, answer, en=False):
    """Valuta la risposta a un passo della catena (0 = domanda principale, poi gli approfondimenti).
    Se la risposta regge (voto ≥ 3) il selezionatore scava con l'approfondimento successivo; altrimenti la catena si ferma lì."""
    from .colloquio import judge_answer
    q = domanda(qid)
    chain = [{"q": q["q"], "punti": q["punti"], "modello": q["modello"]}] + list(q.get("approfondimenti", []))
    step = max(0, min(int(step), len(chain) - 1))
    cur = chain[step]
    if not answer.strip():
        r = {"score": 1, "covered": [], "missing": cur["punti"], "comment": "Nessuna risposta: guarda quella modello.", "language": ""}
    else:
        r = judge_answer(cur["q"], cur["punti"], cur["modello"], answer[:4000], en)
    r["model"] = cur["modello"]
    r["points"] = cur["punti"]
    r["trap"] = q.get("trappola", "") if step == 0 else ""
    go_on = r["score"] >= 3 and step + 1 < len(chain)
    r["next"] = {"step": step + 1, "q": chain[step + 1]["q"]} if go_on else None
    r["end"] = not go_on
    if r["end"]:
        reached = step + 1 if r["score"] >= 3 else step      # quanti livelli della catena hai retto
        r["reached"], r["total"] = reached, len(chain)
        _salva(qid, reached, len(chain), r["score"])
    log_event("bank_answer", id=qid, step=step, score=r["score"], end=r["end"])
    return r


def _salva(qid, reached, total, score):
    with _PLOCK:
        from .config import load_json, save_json
        from .percorsi import PROGRESS_FILE
        p = load_json(PROGRESS_FILE, {})
        st = p.setdefault("bank", {})
        old = st.get(qid, {})
        # punteggio della domanda: quanto in fondo sei arrivato (0-5), media mobile con le volte precedenti
        val = round(5 * reached / total, 1)
        sc = round(val if "score" not in old else 0.5 * old["score"] + 0.5 * val, 1)
        st[qid] = {"n": old.get("n", 0) + 1, "best": max(old.get("best", 0), reached - 1), "reached": reached, "total": total,
                   "score": sc, "last": time.time(), "due": time.time() + RIPASSO[min(reached, len(RIPASSO) - 1)] * GIORNO}
        save_json(PROGRESS_FILE, p)


# ---------------------------------------------------------------- system design
def design_list():
    p = progress()
    st = p.get("design", {})
    return [{"id": d["id"], "titolo": d["titolo"], "livello": LIVELLI.get(d["livello"]), "brief": d["brief"],
             "voto": st.get(d["id"], {}).get("voto")} for d in _dati("colloquio_design")]


def design_get(did):
    d = next((x for x in _dati("colloquio_design") if x["id"] == did), None)
    if not d:
        raise ValueError("scenario sconosciuto")
    return {k: d[k] for k in ("id", "titolo", "livello", "brief", "requisiti", "sezioni")} | {"livelloName": LIVELLI.get(d["livello"])}


DESIGN_SCHEMA = {"type": "object", "properties": {
    "criteri": {"type": "array", "items": {"type": "object", "properties": {"criterio": STR, "voto": {"type": "integer"}, "commento": STR},
                                            "required": ["criterio", "voto", "commento"]}},
    "forti": ARR, "mancanze": ARR, "commento": STR}, "required": ["criteri", "forti", "mancanze", "commento"]}


def design_judge(did, text):
    d = next((x for x in _dati("colloquio_design") if x["id"] == did), None)
    if not d:
        raise ValueError("scenario sconosciuto")
    griglia = "\n".join(f"- {g['criterio']} (peso {g['peso']}): {g['atteso']}" for g in d["griglia"])
    prompt = (f"Sei un selezionatore che valuta un esercizio di system design per una posizione junior.\nRichiesta: {d['brief']}\n"
              "Requisiti:\n" + "\n".join("- " + r for r in d["requisiti"]) + f"\n\nGriglia di valutazione:\n{griglia}\n\n"
              f"Soluzione di riferimento (non è l'unica giusta):\n{d['soluzione']}\n\nProposta del candidato:\n«{text[:6000]}»\n\n"
              "Per OGNI criterio della griglia, nello stesso ordine: \"voto\" da 0 (assente o sbagliato) a 3 (completo e motivato), \"commento\" in 1-2 frasi "
              "con cosa manca o cosa va bene. Premia le scelte motivate anche se diverse dalla soluzione di riferimento. "
              "\"forti\": 1-3 punti forti. \"mancanze\": 1-4 cose importanti da aggiungere. \"commento\": 2-3 frasi finali rivolte al candidato (dagli del tu).")
    r = llm_json([{"role": "system", "content": SYS_GEN}, {"role": "user", "content": prompt}], DESIGN_SCHEMA, temperature=0.1)
    crit = []
    for i, g in enumerate(d["griglia"]):
        c = (r.get("criteri") or [])[i] if i < len(r.get("criteri") or []) else {}
        try:
            v = max(0, min(3, int(c.get("voto"))))
        except Exception:
            v = 0
        crit.append({"criterio": g["criterio"], "peso": g["peso"], "voto": v, "commento": str(c.get("commento") or ""), "atteso": g["atteso"]})
    tot = sum(c["peso"] * 3 for c in crit) or 1
    voto = round(10 * sum(c["peso"] * c["voto"] for c in crit) / tot, 1)
    with _PLOCK:
        from .config import load_json, save_json
        from .percorsi import PROGRESS_FILE
        p = load_json(PROGRESS_FILE, {})
        old = p.setdefault("design", {}).get(did, {})
        p["design"][did] = {"voto": max(voto, old.get("voto", 0)), "ultimo": voto, "t": time.time()}
        save_json(PROGRESS_FILE, p)
    log_event("design_judge", id=did, voto=voto)
    return {"voto": voto, "criteri": crit, "forti": [str(x) for x in r.get("forti") or []][:4], "mancanze": [str(x) for x in r.get("mancanze") or []][:5],
            "commento": str(r.get("commento") or ""), "soluzione": d["soluzione"], "approfondimenti": d.get("approfondimenti", [])}


def design_followup(did, question, answer, en=False):
    from .colloquio import judge_answer
    d = next((x for x in _dati("colloquio_design") if x["id"] == did), None)
    if not d:
        raise ValueError("scenario sconosciuto")
    pts = ["risposta concreta riferita a questo sistema", "considera i casi limite", "motiva la scelta e cita un compromesso"]
    return judge_answer(f"{question} (contesto: {d['brief']})", pts, d["soluzione"], answer[:3000], en)


# ---------------------------------------------------------------- code review
def review_list():
    st = progress().get("review", {})
    return [{"id": r["id"], "titolo": r["titolo"], "lang": r["lang"], "livello": LIVELLI.get(r["livello"]), "contesto": r["contesto"],
             "n": len(r["problemi"]), "trovati": st.get(r["id"], {}).get("trovati")} for r in _dati("colloquio_review")]


def review_get(rid):
    r = next((x for x in _dati("colloquio_review") if x["id"] == rid), None)
    if not r:
        raise ValueError("esercizio sconosciuto")
    return {k: r[k] for k in ("id", "titolo", "lang", "livello", "contesto", "codice")} | {"n": len(r["problemi"]), "livelloName": LIVELLI.get(r["livello"])}


REVIEW_SCHEMA = {"type": "object", "properties": {
    "trovati": {"type": "array", "items": {"type": "integer"}},
    "extra": {"type": "array", "items": {"type": "object", "properties": {"osservazione": STR, "valida": {"type": "boolean"}, "commento": STR},
                                          "required": ["osservazione", "valida", "commento"]}},
    "commento": STR}, "required": ["trovati", "extra", "commento"]}


def review_judge(rid, text):
    r = next((x for x in _dati("colloquio_review") if x["id"] == rid), None)
    if not r:
        raise ValueError("esercizio sconosciuto")
    lista = "\n".join(f"{i}. riga {p['riga']} [{p['tipo']}, {p['gravita']}]: {p['problema']}" for i, p in enumerate(r["problemi"]))
    numerato = "\n".join(f"{i + 1:3d}  {l}" for i, l in enumerate(r["codice"].split("\n")))
    prompt = (f"Sei un selezionatore che corregge una code review fatta da un candidato junior.\nContesto: {r['contesto']}\nCodice:\n{numerato}\n\n"
              f"Problemi noti (numerati da 0):\n{lista}\n\nReview del candidato:\n«{text[:5000]}»\n\n"
              "\"trovati\": gli indici dei problemi noti che il candidato ha individuato davvero (anche con parole sue o senza il numero di riga; "
              "non contare un problema solo nominato di sfuggita senza dire cosa non va). "
              "\"extra\": le osservazioni del candidato che NON corrispondono a nessun problema noto, con \"valida\" true se è comunque un'osservazione giusta. "
              "\"commento\": 2-3 frasi rivolte al candidato (dagli del tu) su come ha fatto la review.")
    j = llm_json([{"role": "system", "content": SYS_GEN}, {"role": "user", "content": prompt}], REVIEW_SCHEMA, temperature=0.1)
    found = sorted({i for i in (j.get("trovati") or []) if isinstance(i, int) and 0 <= i < len(r["problemi"])})
    probs = [dict(p, trovato=i in found) for i, p in enumerate(r["problemi"])]
    with _PLOCK:
        from .config import load_json, save_json
        from .percorsi import PROGRESS_FILE
        p = load_json(PROGRESS_FILE, {})
        old = p.setdefault("review", {}).get(rid, {})
        p["review"][rid] = {"trovati": max(len(found), old.get("trovati", 0)), "n": len(probs), "t": time.time()}
        save_json(PROGRESS_FILE, p)
    log_event("review_judge", id=rid, found=len(found), n=len(probs))
    return {"problemi": probs, "trovati": len(found), "n": len(probs),
            "extra": [x for x in (j.get("extra") or []) if isinstance(x, dict)][:6], "commento": str(j.get("commento") or ""),
            "domanda_finale": r.get("domanda_finale", "")}


# ---------------------------------------------------------------- domande comportamentali
def soft_list():
    st = progress().get("soft", {})
    en = app_lang() == "en"
    return [{"id": s["id"], "q": s["q_en"] if en else s["q_it"], "q_it": s["q_it"], "q_en": s["q_en"], "voto": st.get(s["id"], {}).get("voto")}
            for s in _dati("colloquio_comportamentali")]


SOFT_SCHEMA = {"type": "object", "properties": {
    "voto": {"type": "integer"}, "situazione": {"type": "boolean"}, "compito": {"type": "boolean"}, "azione": {"type": "boolean"},
    "risultato": {"type": "boolean"}, "forti": ARR, "migliorare": ARR, "commento": STR, "lingua": STR},
    "required": ["voto", "situazione", "compito", "azione", "risultato", "forti", "migliorare", "commento", "lingua"]}


def soft_judge(sid, answer, en=False):
    s = next((x for x in _dati("colloquio_comportamentali") if x["id"] == sid), None)
    if not s:
        raise ValueError("domanda sconosciuta")
    q = s["q_en"] if en else s["q_it"]
    prompt = (f"Sei un selezionatore che valuta la risposta a una domanda comportamentale in un colloquio per sviluppatore junior.\n"
              f"Domanda: {q}\nCosa vuole capire il selezionatore: " + "; ".join(s["cosa_cerca"]) + f"\n\nRisposta del candidato: «{answer[:4000]}»\n\n"
              "Valuta con il metodo STAR: indica se ci sono situazione, compito, azione (cosa ha fatto LUI) e risultato (meglio se misurabile o con una lezione imparata). "
              "\"voto\" da 1 a 5 su quanto convince un selezionatore. \"forti\": 1-3 punti forti. \"migliorare\": 1-3 cose concrete da cambiare. "
              "\"commento\": 2-3 frasi rivolte al candidato (dagli del tu). "
              + ("La risposta è in inglese: in \"lingua\" (in italiano) indica 1-3 correzioni dell'inglese nella forma «frase sbagliata → frase corretta» e un consiglio; "
                 "non abbassare il voto per l'inglese." if en else "\"lingua\": stringa vuota."))
    r = llm_json([{"role": "system", "content": SYS_GEN}, {"role": "user", "content": prompt}], SOFT_SCHEMA, temperature=0.1)
    try:
        v = max(1, min(5, int(r.get("voto"))))
    except Exception:
        v = 3
    with _PLOCK:
        from .config import load_json, save_json
        from .percorsi import PROGRESS_FILE
        p = load_json(PROGRESS_FILE, {})
        old = p.setdefault("soft", {}).get(sid, {})
        p["soft"][sid] = {"voto": max(v, old.get("voto", 0)), "t": time.time()}
        save_json(PROGRESS_FILE, p)
    log_event("soft_judge", id=sid, voto=v, en=en)
    return {"voto": v, "star": {k: bool(r.get(k)) for k in ("situazione", "compito", "azione", "risultato")},
            "forti": [str(x) for x in r.get("forti") or []][:3], "migliorare": [str(x) for x in r.get("migliorare") or []][:3],
            "commento": str(r.get("commento") or ""), "lingua": str(r.get("lingua") or "") if en else "",
            "consigli": s["consigli"], "esempio": s["esempio"]}
