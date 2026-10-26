"""Logica e colloquio: viste, giudizio delle risposte, simulazione e report."""

import time
import uuid

from .curriculum import INTERVIEW_LEVEL_NAMES, LEVELS, LOGIC, LOGIC_LEVEL_NAMES
from .config import DATA, LANGNAME, load_json, log_event, save_json
from .llm import llm_json
from .generazione import ARR, STR, SYS_GEN
from .percorsi import FOCUS, INTERVIEW_ALL, INTERVIEW_BY, WORKER, pool_load, progress, streak


# ---------------------------------------------------------------- logica e colloquio: viste
def levels_view(prefix, names, p):
    out = []
    for l in LEVELS:
        key = f"{prefix}/{l['id']}"
        st = p["levels"].get(key, {})
        items = pool_load(key)
        out.append({"id": l["id"], "name": names[l["id"]], "key": key, "stars": st.get("stars", 0), "best": st.get("best", 0),
                    "runs": st.get("runs", 0), "ready": len([e for e in items if e["id"] not in p["seen"]]),
                    "done": len([e for e in items if e["id"] in p["seen"]])})
    return out


def logic_view():
    p = progress()
    return {"cats": [{"id": c["id"], "title": c["title"], "desc": c["desc"], "lang": c["lang"], "code": c["mode"] in ("tests", "sql"),
                      "levels": levels_view(f"logica/{c['id']}", LOGIC_LEVEL_NAMES, p)} for c in LOGIC],
            "xp": p["xp"], "streak": streak(p["days"]), "worker": dict(WORKER, focus=FOCUS["key"])}


def interview_view():
    p = progress()
    reports = []
    for f in sorted(INTERVIEWS.glob("*.json"), reverse=True)[:12]:
        r = load_json(f, None)
        if r:
            reports.append({"id": r["id"], "track": r.get("trackTitle"), "level": r.get("levelName"), "score": r.get("report", {}).get("voto"),
                            "date": r.get("date")})
    return {"tracks": [{"id": t["id"], "title": t["title"], "lang": t["lang"], "algo": t["algo"], "en": t["en"],
                        "levels": levels_view(f"colloquio/{t['id']}", INTERVIEW_LEVEL_NAMES, p),
                        "live": levels_view(f"logica/{t['algo']}", LOGIC_LEVEL_NAMES, p)} for t in INTERVIEW_ALL],
            "levelNames": INTERVIEW_LEVEL_NAMES, "reports": reports, "worker": dict(WORKER, focus=FOCUS["key"])}


ANSWER_SCHEMA = {"type": "object", "properties": {
    "voto": {"type": "integer"}, "coperti": ARR, "mancanti": ARR, "commento": STR}, "required": ["voto", "coperti", "mancanti", "commento"]}


def judge_answer(question, points, model, answer, en=False):
    prompt = ("Sei un selezionatore tecnico che valuta la risposta scritta di un candidato junior.\n"
              f"Domanda: {question}\nPunti chiave attesi:\n" + "\n".join("- " + x for x in points) +
              f"\nRisposta di riferimento: {model}\n\nRisposta del candidato: «{answer}»\n\n"
              "Valuta il contenuto, non la forma. \"voto\": da 1 (sbagliata o vuota) a 5 (completa e precisa). "
              "\"coperti\": i punti chiave che il candidato ha toccato (riformulati brevemente). \"mancanti\": quelli che mancano o sono sbagliati. "
              "\"commento\": 1-3 frasi rivolte al candidato (dagli del tu): cosa va bene e cosa aggiungere, come farebbe un selezionatore gentile ma esigente.")
    schema = ANSWER_SCHEMA
    if en:
        prompt += ("\nIl colloquio è in inglese: scrivi \"commento\", \"coperti\" e \"mancanti\" in inglese semplice. "
                   "In \"lingua\" (in italiano) indica 1-3 correzioni dell'inglese del candidato nella forma «frase sbagliata → frase corretta», "
                   "più un consiglio breve; se l'inglese è buono scrivilo. Non abbassare il voto per l'inglese: il voto riguarda il contenuto.")
        schema = {"type": "object", "properties": dict(ANSWER_SCHEMA["properties"], lingua=STR), "required": ANSWER_SCHEMA["required"] + ["lingua"]}
    d = llm_json([{"role": "system", "content": SYS_GEN}, {"role": "user", "content": prompt}], schema, temperature=0.1)
    try:
        v = max(1, min(5, int(d.get("voto"))))
    except Exception:
        v = 3
    return {"score": v, "covered": [str(x) for x in d.get("coperti") or []][:6], "missing": [str(x) for x in d.get("mancanti") or []][:6],
            "comment": str(d.get("commento") or ""), "language": str(d.get("lingua") or "") if en else ""}


FOLLOW_SCHEMA = {"type": "object", "properties": {"domanda": STR, "punti_chiave": ARR, "risposta_modello": STR},
                 "required": ["domanda", "punti_chiave", "risposta_modello"]}


def followup(lang, statement, code, en=False):
    prompt = (f"Sei un selezionatore in un colloquio di live coding ({LANGNAME[lang]}). Il candidato ha appena risolto questo problema:\n{statement}\n\n"
              f"Il suo codice (supera i test):\n{code}\n\nFagli UNA domanda di approfondimento sul SUO codice: complessità temporale e spaziale, "
              "un caso limite, oppure come lo renderebbe più efficiente. \"punti_chiave\": 2-4 punti della risposta giusta, riferiti al suo codice. "
              "\"risposta_modello\": la risposta ideale in 40-100 parole."
              + (" Il colloquio è in INGLESE: scrivi domanda, punti chiave e risposta modello in inglese." if en else ""))
    d = llm_json([{"role": "system", "content": SYS_GEN}, {"role": "user", "content": prompt}], FOLLOW_SCHEMA, temperature=0.2)
    return {"question": str(d.get("domanda") or ""), "points": [str(x) for x in d.get("punti_chiave") or []][:5],
            "model": str(d.get("risposta_modello") or "")}


INTERVIEWS = DATA / "interviews"


def interviewer_system(track, level):
    t = INTERVIEW_BY[track]
    if t.get("en"):
        return (f"You are a technical interviewer at an international company, interviewing a candidate for a «{t['title'].replace(' · English', '')}» "
                f"position, level {INTERVIEW_LEVEL_NAMES[level]}. Topics: {t['topic']}.\n"
                "Rules: ask ONE question at a time and wait for the answer. Mix theory questions, reasoning questions (\"how would you…\") "
                "and one small coding problem to explain in words or a few lines. After each answer react in one sentence (without giving the full "
                "solution) and ask a follow-up or move to another topic. Be friendly but demanding, like a real interview. The candidate is not a native "
                "English speaker: speak clear, simple English and do not correct their grammar during the interview. Keep messages short. "
                "The interview lasts about 8 questions: after the eighth, or if the candidate writes END or FINE, thank them and say the interview is over, without grades.")
    return (f"Sei un selezionatore tecnico italiano e stai facendo un colloquio per una posizione «{t['title']}», "
            f"livello {INTERVIEW_LEVEL_NAMES[level]}. Argomenti: {t['topic']}.\n"
            "Regole: fai UNA domanda alla volta e aspetta la risposta. Alterna domande di teoria, domande di ragionamento "
            "(«come faresti a…») e un piccolo problema di codice da spiegare a parole o con poche righe. Dopo ogni risposta reagisci "
            "in una frase (senza dare la soluzione completa) e fai una domanda di approfondimento oppure passa a un altro argomento. "
            "Sii cordiale ma esigente, come in un colloquio vero. Dai del tu. Messaggi brevi. Il colloquio dura circa 8 domande: "
            "dopo l'ottava, o se il candidato scrive FINE, ringrazia e dì che il colloquio è concluso, senza dare voti.")


REPORT_SCHEMA = {"type": "object", "properties": {
    "voto": {"type": "integer"}, "esito": STR,
    "aree": {"type": "array", "items": {"type": "object", "properties": {"area": STR, "voto": {"type": "integer"}, "commento": STR},
                                        "required": ["area", "voto", "commento"]}},
    "punti_forti": ARR, "da_migliorare": ARR, "prossimi_passi": ARR},
    "required": ["voto", "esito", "aree", "punti_forti", "da_migliorare", "prossimi_passi"]}


def interview_save_question(question, track, model=""):
    """Salva una domanda del colloquio come flashcard. Se non c'è la risposta modello, la scrive Qwen."""
    from .flashcard import card_add
    question = question.strip()
    if not question:
        raise ValueError("domanda vuota")
    if not model:
        t = INTERVIEW_BY.get(track, {})
        S = {"type": "string"}
        d = llm_json([{"role": "system", "content": SYS_GEN}, {"role": "user", "content":
                       f"Domanda di un colloquio tecnico per «{t.get('title', 'sviluppatore junior')}»:\n{question[:1500]}\n\n"
                       "\"risposta\": la risposta che darebbe un candidato junior preparato, 60-140 parole, con i termini tecnici giusti e "
                       "frammenti di codice tra backtick. \"punti\": i 3-5 punti chiave in una riga ciascuno, separati da «; »."}],
                     {"type": "object", "properties": {"risposta": S, "punti": S}, "required": ["risposta", "punti"]}, temperature=0.2)
        model = str(d.get("risposta") or "") + ("\n\nPunti chiave: " + str(d.get("punti")) if d.get("punti") else "")
    ok = card_add("colloquio-salvate", question[:1500], model[:3000], track or "colloquio")
    log_event("interview_save", track=track, ok=bool(ok))
    return {"ok": True, "added": bool(ok)}


def interview_drill(point, track):
    """«Allenati su questo»: un piccolo mazzo di domande mirate su un punto da migliorare del report."""
    from .flashcard import generate_cards
    t = INTERVIEW_BY.get(track, {})
    topic = (f"un punto debole emerso in un colloquio per «{t.get('title', 'sviluppatore junior')}»: «{point[:400]}». "
             "Fai domande brevi e mirate che allenino proprio questo punto (definizioni, differenze, «cosa succede se», piccoli frammenti di codice)")
    added = generate_cards("punti-deboli", 5, topic)
    log_event("interview_drill", track=track, added=added)
    return {"added": added, "deck": "punti-deboli"}


def interview_report(track, level, history, leaves=0):
    t = INTERVIEW_BY[track]
    tr = "\n".join(("SELEZIONATORE: " if m["role"] == "assistant" else "CANDIDATO: ") + m["content"] for m in history)
    prompt = (f"Questa è la trascrizione di un colloquio tecnico per «{t['title']}», livello {INTERVIEW_LEVEL_NAMES[level]}:\n\n{tr[:14000]}\n\n"
              "Scrivi la valutazione del candidato, onesta e concreta, basata SOLO su quello che ha risposto. "
              "\"voto\": da 1 a 10. \"esito\": una frase (es. «Pronto per un colloquio junior», «Serve ancora pratica su…»). "
              "\"aree\": 3-6 aree toccate nel colloquio, ciascuna con voto da 1 a 10 e un commento breve. "
              "\"punti_forti\" e \"da_migliorare\": 2-4 punti ciascuno, specifici. \"prossimi_passi\": 3 cose concrete da studiare o esercitare."
              + (" Il colloquio era in INGLESE: scrivi la valutazione in italiano e includi un'area «Comunicazione in inglese» con voto e, nel commento, "
                 "2-3 frasi del candidato corrette (frase sbagliata → frase corretta)." if t.get("en") else ""))
    d = llm_json([{"role": "system", "content": SYS_GEN}, {"role": "user", "content": prompt}], REPORT_SCHEMA, temperature=0.2, num_ctx=8192)
    rid = "c" + uuid.uuid4().hex[:10]
    rec = {"id": rid, "track": track, "trackTitle": t["title"], "level": level, "levelName": INTERVIEW_LEVEL_NAMES[level],
           "date": time.strftime("%Y-%m-%d %H:%M"), "history": history, "report": d, "leaves": int(leaves or 0)}
    save_json(INTERVIEWS / f"{rid}.json", rec)
    return rec
