"""Flashcard con ripetizione dilazionata (sistema Leitner)."""

import time
import uuid

from .curriculum import PATHS
from .config import DATA, load_json, save_json
from .llm import llm_json
from .generazione import STR, SYS_GEN
from .percorsi import INTERVIEW_ALL, INTERVIEW_BY, _PLOCK, key_info, path_desc, pool_load, unit_of, units


# ---------------------------------------------------------------- flashcard (ripetizione dilazionata, sistema Leitner)
CARDS_FILE = DATA / "cards.json"
BOX_DAYS = [0, 1, 3, 7, 16, 35, 80]


def cards_load():
    return load_json(CARDS_FILE, [])


def cards_save(cards):
    save_json(CARDS_FILE, cards)


def card_add(deck, front, back, src=None, extra=None):
    with _PLOCK:
        cards = cards_load()
        if any(c["deck"] == deck and c["front"] == front for c in cards):
            return False
        c = {"id": "k" + uuid.uuid4().hex[:10], "deck": deck, "front": front, "back": back, "box": 0,
             "due": time.time(), "src": src, "reviews": 0, "lapses": 0}
        c.update(extra or {})
        cards.append(c)
        cards_save(cards)
        return True


def deck_title(deck):
    if deck == "logica":
        return "Logica"
    if deck == "ricalco":
        return "Ricalco · riscrivi a memoria"
    if deck == "spiega":
        return "Spiegalo con parole tue"
    if deck == "colloquio":
        return "Colloquio"
    if deck == "colloquio-salvate":
        return "Colloquio · domande salvate"
    if deck == "punti-deboli":
        return "Colloquio · punti da migliorare"
    if deck.startswith("colloquio/") and deck.split("/")[1] in INTERVIEW_BY:
        return "Colloquio · " + INTERVIEW_BY[deck.split("/")[1]]["title"]
    if "/" in deck:
        lang, uid = deck.split("/", 1)
        try:
            return f"{PATHS[lang]['name']} · {unit_of(lang, uid)[1]['title']}"
        except Exception:
            pass
    return deck


def decks_view():
    now = time.time()
    by = {}
    for c in cards_load():
        d = by.setdefault(c["deck"], {"id": c["deck"], "title": deck_title(c["deck"]), "total": 0, "due": 0, "learned": 0})
        d["total"] += 1
        d["due"] += c["due"] <= now
        d["learned"] += c["box"] >= 3
    gens = [{"id": "logica", "title": "Logica: strategie di ragionamento"}]
    gens += [{"id": f"colloquio/{t['id']}", "title": f"Colloquio · {t['title']}"} for t in INTERVIEW_ALL]
    for lang in PATHS:
        gens += [{"id": f"{lang}/{u['id']}", "title": f"{PATHS[lang]['name']} · {i + 1}. {u['title']}"} for i, u in enumerate(units(lang))]
    return {"decks": sorted(by.values(), key=lambda d: (-d["due"], d["title"])), "generators": gens}


def grade_card(cid, grade):
    with _PLOCK:
        cards = cards_load()
        c = next((x for x in cards if x["id"] == cid), None)
        if not c:
            raise ValueError("carta non trovata")
        now = time.time()
        c["reviews"] += 1
        if grade <= 0:
            c["box"] = 1
            c["lapses"] += 1
            c["due"] = now + 60
        elif grade == 1:
            c["box"] = max(1, c["box"])
            c["due"] = now + max(1, BOX_DAYS[c["box"]] // 2) * 86400 - 3600
        else:
            c["box"] = min(len(BOX_DAYS) - 1, c["box"] + 1)
            c["due"] = now + BOX_DAYS[c["box"]] * 86400 - 3600
        cards_save(cards)
        return c


CARDS_SCHEMA = {"type": "object", "properties": {"carte": {"type": "array", "items": {
    "type": "object", "properties": {"fronte": STR, "retro": STR}, "required": ["fronte", "retro"]}}}, "required": ["carte"]}


def generate_cards(deck, n=10, topic=None):
    existing = [c["front"] for c in cards_load() if c["deck"] == deck][-25:]
    if topic:
        what = topic
    elif deck == "logica":
        what = ("strategie di ragionamento e problem solving: principio dei cassetti, lavorare all'indietro, casi limite, invarianti, "
                "forza bruta contro formula, complessità O-grande, tecniche classiche degli algoritmi (due puntatori, hash map, ricorsione, ricerca binaria)")
    elif deck.startswith("colloquio/"):
        t = INTERVIEW_BY[deck.split("/")[1]]
        what = f"domande rapide da colloquio per «{t['title']}»: {t['topic']}" + (" (fronte e retro in INGLESE)" if t.get("en") else "")
    else:
        lang, uid = deck.split("/", 1)
        i, u = unit_of(lang, uid)
        what = f"{path_desc(lang)}, «{u['title']}»: {u['concepts']}"
    prompt = (f"Crea {n} flashcard in italiano per ripassare: {what}.\n"
              "\"fronte\": una domanda breve e precisa, oppure un frammento di codice con la domanda «cosa stampa?» o «cosa c'è di sbagliato?». "
              "\"retro\": la risposta in 1-3 frasi, con il codice tra backtick. Una carta = un solo concetto. Niente domande banali."
              + ("\nNon ripetere queste carte già presenti: " + " | ".join(existing) if existing else ""))
    d = llm_json([{"role": "system", "content": SYS_GEN}, {"role": "user", "content": prompt}], CARDS_SCHEMA, temperature=0.5)
    added = 0
    for c in d.get("carte") or []:
        f, b = str(c.get("fronte") or "").strip(), str(c.get("retro") or "").strip()
        if f and b and card_add(deck, f, b, "generata"):
            added += 1
    return added


def cards_from_result(key, ex_id):
    info = key_info(key)
    if info["kind"] == "path":
        return
    e = next((x for x in pool_load(key) if x["id"] == ex_id), None)
    if not e:
        return
    if e["type"] == "logica":
        card_add("logica", e["question"], f"**{e['answer']}**. {e.get('explain', '')}", ex_id)
    elif e["type"] == "orale":
        card_add(f"colloquio/{key.split('/')[1]}", e["question"], e.get("model", ""), ex_id)
