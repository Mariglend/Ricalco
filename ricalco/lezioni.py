"""Lezioni delle unità: coda con precedenza, rigenerazione e ripreparazione di un'unità."""

import os
import re
import threading
import time

from .curriculum import LEVELS, PATHS
from .config import load_json, log_event, save_json, user_priority
from .esecuzione import run_program
from .generazione import error_hint, generate_lesson
from .percorsi import (
    FOCUS, THEORY, _PLOCK, path_desc, pool_path, progress, progress_save, unit_lesson_id, unit_lesson_path, unit_mode,
    unit_of, units, xl)


# ---- lezioni chieste da te: una coda con precedenza sul lavoro in sottofondo, così la pagina non resta appesa
LESSON_JOBS = {}          # "lang/uid" → {"state": queue|run|error, "t0", "error"}
_LJ_LOCK = threading.Lock()
_LJ_WAKE = threading.Event()


def lesson_request(lang, uid, note=""):
    """Mette in coda la lezione (se manca) e restituisce lo stato. Una lezione già pronta torna subito."""
    if unit_lesson_path(lang, uid).exists():
        return {"ready": True}
    k = f"{lang}/{uid}"
    with _LJ_LOCK:
        j = LESSON_JOBS.get(k)
        if not j or j["state"] == "error":
            LESSON_JOBS[k] = j = {"state": "queue", "t0": time.time(), "q": time.time(), "error": None, "note": note}
            _LJ_WAKE.set()
    return lesson_status(lang, uid)


def lesson_status(lang, uid):
    if unit_lesson_path(lang, uid).exists():
        return {"ready": True}
    k = f"{lang}/{uid}"
    with _LJ_LOCK:
        j = LESSON_JOBS.get(k)
        if not j:
            return {"ready": False, "state": "none"}
        ahead = len([x for x in LESSON_JOBS.values() if x["state"] in ("queue", "run") and x["q"] < j["q"]])
        return {"ready": False, "state": j["state"], "secs": round(time.time() - j["t0"]), "ahead": ahead, "error": j["error"]}


def lesson_loop():
    while True:
        _LJ_WAKE.wait(5)
        _LJ_WAKE.clear()
        while True:
            with _LJ_LOCK:
                todo = sorted([(j["q"], k) for k, j in LESSON_JOBS.items() if j["state"] == "queue"])
                if not todo:
                    break
                k = todo[0][1]
                LESSON_JOBS[k].update(state="run", t0=time.time())
                note = LESSON_JOBS[k].get("note") or ""
            lang, uid = k.split("/")
            try:
                with user_priority():      # il lavoro in sottofondo si ferma finché la lezione non è pronta
                    t0 = time.time()
                    get_unit_lesson(lang, uid, note)
                    log_event("gen", what="lezione chiesta", key=k, secs=round(time.time() - t0, 1))
                with _LJ_LOCK:
                    LESSON_JOBS.pop(k, None)
            except Exception as e:
                log_event("gen_fail", key=k, what="lezione", err=str(e)[:200])
                with _LJ_LOCK:
                    LESSON_JOBS[k].update(state="error", error=str(e)[:300])


def lesson_recheck(L, path):
    """Una lezione salvata con l'errore del vecchio Java 8 («classe principale Main.java»): il codice non c'entra,
    quindi la riesegue con il Java giusto e, se va, toglie l'avviso."""
    if L.get("verified") is False and L.get("lang") == "java" and re.search(r"classe principale|main class", L.get("runError") or "", re.I):
        run = run_program("java", "\n".join(b["code"] for b in L["blocks"]))
        if run["ok"]:
            L.update(verified=True, runError=None, output=run["stdout"])
            save_json(path, L)
        elif not re.search(r"classe principale|main class", run.get("error") or "", re.I):
            L["runError"] = run["error"]
            save_json(path, L)
    return L


def lesson_regen(lang, uid):
    """Rifà la lezione di un'unità: la vecchia resta come .bak, e a Qwen si dice quale errore dava."""
    path = unit_lesson_path(lang, uid)
    old = load_json(path, None) or {}
    note = ""
    if old.get("runError"):
        note = ("La versione precedente di questa lezione, eseguita, dava questo errore: " + old["runError"][:600]
                + error_hint(old["runError"]) + " Scrivi un programma diverso che non abbia questo problema.")
    if path.exists():
        os.replace(path, path.with_suffix(".bak"))
    return lesson_request(lang, uid, note)


def unit_reset(lang, uid, reset_progress=False):
    """Ripreparare un'unità intera: lezione, scheda di teoria ed esercizi dei tre livelli vengono rifatti da Qwen.
    I file vecchi restano come .bak. Con reset_progress si azzerano anche stelle, lezione riscritta e errori dell'unità."""
    unit_of(lang, uid)
    moved = []
    files = [unit_lesson_path(lang, uid), THEORY / f"{lang}_{uid}.json"] + [pool_path(f"{lang}/{uid}/{l['id']}") for l in LEVELS]
    with _PLOCK:
        for f in files:
            if f.exists():
                os.replace(f, f.with_suffix(".bak"))
                moved.append(f.name)
        if reset_progress:
            p = progress()
            p.get("units", {}).pop(f"{lang}/{uid}", None)
            for l in LEVELS:
                p["levels"].pop(f"{lang}/{uid}/{l['id']}", None)
            p["mistakes"] = [m for m in p.get("mistakes", []) if not str(m.get("key", "")).startswith(f"{lang}/{uid}/")]
            progress_save(p)
    with _LJ_LOCK:
        LESSON_JOBS.pop(f"{lang}/{uid}", None)
    FOCUS["key"] = f"{lang}/{uid}/base"
    log_event("unit_reset", unit=f"{lang}/{uid}", progress=bool(reset_progress), files=len(moved))
    return dict(lesson_request(lang, uid), moved=moved)


def get_unit_lesson(lang, uid, note=""):
    """La lezione da ricalcare di un'unità del percorso: generata una volta e salvata."""
    path = unit_lesson_path(lang, uid)
    L = load_json(path, None)
    if L:
        return lesson_recheck(L, path)
    i, u = unit_of(lang, uid)
    before = [x["title"] for x in units(lang)[:i]]
    after = [x["title"] for x in units(lang)[i + 1:i + 4]]
    extra = (f"È la lezione dell'unità {i + 1} del percorso {path_desc(lang)}, «{u['title']}». Deve mostrare questi concetti: {u['concepts']}. "
             "Lo studente conosce già: " + (", ".join(before) or "nulla") + ". " +
             ("Non usare concetti delle unità successive (" + ", ".join(after) + "). " if after else "") +
             "Scegli un esempio concreto e realistico." + (" Indicazioni tecniche: " + u["notes"] if u.get("notes") else "")
             + (" " + note if note else ""))
    if PATHS[lang].get("algo"):
        extra += (" È una lezione di algoritmi: implementa l'algoritmo in funzioni chiare, con un commento sulla complessità (O-grande) "
                  "di ogni funzione, e in fondo provale su 2-3 casi, compreso un caso limite, stampando i risultati.")
    mode = unit_mode(lang, u)
    if mode in ("review", "spring"):
        extra += (" Questa unità usa librerie esterne (Spring/JUnit/JDBC/FastAPI): il codice non verrà eseguito, quindi scrivi classi realistiche "
                  "con gli import completi invece di un main che stampa.")
    L = generate_lesson(f"{u['title']}: {u['concepts']}", xl(lang), "base" if i < 8 else "intermedio", extra,
                        run_check=mode not in ("review", "spring"))
    L.update(id=unit_lesson_id(lang, uid), unitKey=f"{lang}/{uid}", title=f"{i + 1}. {u['title']}")
    save_json(path, L)
    return L
