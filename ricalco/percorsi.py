"""Percorsi: archivio degli esercizi, progressi, livelli, sessioni e lavoro in sottofondo."""

import random
import sys
import threading
import time

from .curriculum import (
    CURRICULUM, INTERVIEW, INTERVIEW_LEVEL_NAMES, INTERVIEW_MIX, LEVELS, LOGIC, LOGIC_LEVEL_NAMES, MIX, MIX_REVIEW,
    MIX_SPRING, PATHS, SEEDS, THEMES, TYPE_ORDER)
from .config import DATA, LANGNAME, LESSONS, LangDir, Preempted, ROOT, SPRING, _TL, load_json, log_event, save_json, user_busy
from .llm import current_model
from .esecuzione import run_proc
from .generazione import EX_TYPES, generate_exercise
from .generazione_sql import prep_sql


# ---------------------------------------------------------------- percorsi: pool, progressi, worker
POOL = LangDir("pool")
THEORY = LangDir("theory")
PROGRESS_FILE = DATA / "progress.json"
_PLOCK = threading.RLock()
FOCUS = {"key": None}
WORKER = {"job": None, "made": 0, "error": None, "since": None}


def units(path):
    return CURRICULUM.get(path, [])


def xl(path):
    """Linguaggio in cui si esegue il codice di un percorso (algopy → python)."""
    return PATHS[path]["lang"] if path in PATHS else path


def path_desc(path):
    P = PATHS[path]
    return f"«{P['goal']}» in {LANGNAME[P['lang']]}" if P.get("algo") else LANGNAME[P["lang"]]


_PYMOD = {}


def py_has(mods):
    key = tuple(sorted(mods))
    if key not in _PYMOD:
        rc, _, _, _ = run_proc([sys.executable, "-c", "import " + ", ".join(key)], str(ROOT), 30)
        _PYMOD[key] = rc == 0
    return _PYMOD[key]


def unit_mode(lang, u):
    mode = u.get("exec", "output")
    if mode == "tests" and xl(lang) == "python" and u.get("requires") and not py_has(u["requires"]):
        return "review"
    if mode == "spring":
        return "spring" if SPRING.ready() else "review"
    return mode


def mix_for(key):
    return key_info(key)["mix"]


def unit_of(lang, uid):
    for i, u in enumerate(units(lang)):
        if u["id"] == uid:
            return i, u
    raise ValueError("unità sconosciuta")


DIFF_OF = {l["id"]: l["diff"] for l in LEVELS}
LEVEL_NAME = {l["id"]: l["name"] for l in LEVELS}
LOGIC_BY = {c["id"]: c for c in LOGIC}
INTERVIEW_EN = [dict(t, id=t["id"] + "_en", title=t["title"] + " · English", en=True) for t in INTERVIEW]
INTERVIEW_ALL = [dict(t, en=False) for t in INTERVIEW] + INTERVIEW_EN
INTERVIEW_BY = {t["id"]: t for t in INTERVIEW_ALL}


def key_info(key):
    """Descrive un livello: del percorso (python/u3/base), della logica (logica/rompicapo/base) o del colloquio."""
    parts = str(key).split("/")
    if len(parts) != 3 or parts[2] not in MIX:
        raise ValueError("livello non valido")
    a, b, lvl = parts
    seq = [f"{a}/{b}/{l['id']}" for l in LEVELS]
    if a in PATHS:
        i, u = unit_of(a, b)
        mode = unit_mode(a, u)
        return {"kind": "path", "lang": xl(a), "path": a, "unit": u, "n": i + 1, "level": lvl, "mode": mode,
                "mix": {"review": MIX_REVIEW, "spring": MIX_SPRING}.get(mode, MIX)[lvl], "seq": level_sequence(a), "title": u["title"],
                "label": f"{PATHS[a]['name']} · Unità {i + 1} · {u['title']} · {LEVEL_NAME[lvl]}"}
    if a == "logica" and b in LOGIC_BY:
        c = LOGIC_BY[b]
        return {"kind": "logic", "lang": c["lang"], "cat": c, "level": lvl, "mode": c["mode"], "mix": c["mix"][lvl], "seq": seq,
                "title": c["title"], "label": f"Logica · {c['title']} · {LOGIC_LEVEL_NAMES[lvl]}"}
    if a == "colloquio" and b in INTERVIEW_BY:
        t = INTERVIEW_BY[b]
        return {"kind": "interview", "lang": t["lang"], "track": t, "level": lvl, "mode": "interview", "mix": INTERVIEW_MIX[lvl],
                "seq": seq, "title": t["title"], "label": f"Colloquio · {t['title']} · {INTERVIEW_LEVEL_NAMES[lvl]}"}
    raise ValueError("livello non valido")


def parse_key(key):
    key_info(key)
    return str(key).split("/")


def level_sequence(lang):
    return [f"{lang}/{u['id']}/{l['id']}" for u in units(lang) for l in LEVELS]


def pool_path(key):
    return POOL / (key.replace("/", "_") + ".json")


def pool_load(key):
    with _PLOCK:
        items = load_json(pool_path(key), None)
        if items is None:
            items = []
            lang, uid, lvl = key.split("/")
            diff = next(l["diff"] for l in LEVELS if l["id"] == lvl)
            for i, s in enumerate(SEEDS.get(key, [])):
                e = dict(s, id=f"s{uid}{lvl[0]}{lang[0]}{i}", lang=xl(lang), difficulty=diff, seed=True)
                items.append(prep_sql(e) if xl(lang) == "sql" else e)
            save_json(pool_path(key), items)
        return items


def pool_add(key, ex):
    with _PLOCK:
        items = pool_load(key)
        ex = {k: v for k, v in ex.items() if k != "state"}
        items.append(ex)
        save_json(pool_path(key), items)


def pool_remove(key, ex_id):
    with _PLOCK:
        items = [e for e in pool_load(key) if e["id"] != ex_id]
        save_json(pool_path(key), items)


def progress():
    with _PLOCK:
        p = load_json(PROGRESS_FILE, {})
        p.setdefault("xp", 0)
        p.setdefault("days", [])
        p.setdefault("seen", {})
        p.setdefault("levels", {})
        p.setdefault("mistakes", [])
        p.setdefault("free", False)
        return p


def progress_save(p):
    with _PLOCK:
        save_json(PROGRESS_FILE, p)


def today():
    return time.strftime("%Y-%m-%d")


def streak(days):
    s = set(days)
    d = time.time()
    if time.strftime("%Y-%m-%d", time.localtime(d)) not in s:
        d -= 86400
    n = 0
    while time.strftime("%Y-%m-%d", time.localtime(d)) in s:
        n += 1
        d -= 86400
    return n


def unseen(key, p=None):
    p = p or progress()
    return [e for e in pool_load(key) if e["id"] not in p["seen"]]


def unit_state(lang, uid, p):
    return p.get("units", {}).get(f"{lang}/{uid}", {})


def unit_available(lang, uid, p):
    """Un'unità si apre quando hai riscritto a memoria (livello 3) la lezione della precedente."""
    if p.get("free"):
        return True
    i, _ = unit_of(lang, uid)
    if i == 0 or unit_state(lang, units(lang)[i - 1]["id"], p).get("mastered", False):
        return True
    # un'unità già iniziata resta aperta anche se davanti ne è stata aggiunta una nuova
    st = unit_state(lang, uid, p)
    return bool(st.get("learned") or st.get("mastered") or any(p["levels"].get(f"{lang}/{uid}/{l['id']}", {}).get("runs") for l in LEVELS))


def unlocked(key, p):
    info = key_info(key)
    if p.get("free") or info["kind"] != "path":
        return True
    lang, uid, lvl = key.split("/")
    if not unit_available(lang, uid, p) or not unit_state(lang, uid, p).get("learned"):
        return False
    if lvl == "base":
        return True
    prev = "base" if lvl == "pratica" else "pratica"
    return p["levels"].get(f"{lang}/{uid}/{prev}", {}).get("stars", 0) >= 1


def adaptive_mix(key, p=None):
    """Sposta fino a 2 esercizi dal tipo in cui vai meglio a quello in cui sbagli di più (solo nel percorso)."""
    info = key_info(key)
    mix = dict(info["mix"])
    if info["kind"] != "path":
        return mix, ""
    p = p or progress()
    ts = p.get("typestats", {})
    rate = {}
    for t in mix:
        st = ts.get(f"{info['path']}:{t}", {})
        if st.get("n", 0) >= 3:
            rate[t] = st.get("first", 0) / st["n"]
    note = ""
    for _ in range(2):
        if len(rate) < 2:
            break
        worst = min(rate, key=rate.get)
        donors = [t for t in rate if t != worst and mix[t] > 1]
        if not donors:
            break
        best = max(donors, key=rate.get)
        if rate[best] - rate[worst] < 0.25:
            break
        mix[best] -= 1
        mix[worst] += 1
        note = (f"Più esercizi «{EX_TYPES[worst]}»: è il tipo in cui sbagli di più "
                f"({round(rate[worst] * 100)}% giusti al primo colpo).")
    return mix, note


def pick_session(key, n, exclude=(), p=None, with_review=False):
    p = p or progress()
    items = [e for e in unseen(key, p) if e["id"] not in exclude]
    mix, _ = adaptive_mix(key, p)
    review = []
    if with_review and key_info(key)["kind"] == "path":
        seq = key_info(key)["seq"]
        before = set(seq[:seq.index(key)])
        for m in reversed(p.get("mistakes", [])):
            if m["key"] in before and len(review) < 2:
                e = next((x for x in pool_load(m["key"]) if x["id"] == m["id"]), None)
                if e and e["id"] not in exclude and all(r["id"] != e["id"] for r in review):
                    review.append(dict(e, key=m["key"], ripasso=True))
    by_type = {}
    for e in items:
        by_type.setdefault(e["type"], []).append(e)
    chosen = []
    for t, c in mix.items():
        chosen += by_type.get(t, [])[:c]
    chosen += [e for e in items if e not in chosen]
    chosen = chosen[:max(0, n - len(review))] + review
    chosen.sort(key=lambda e: TYPE_ORDER.index(e["type"]) if e["type"] in TYPE_ORDER else 99)
    return chosen


def unit_topic(lang, uid):
    i, u = unit_of(lang, uid)
    before = [x["title"] for x in units(lang)[:i]]
    after = [x["title"] for x in units(lang)[i + 1:i + 4]]
    t = f"unità {i + 1} del percorso {path_desc(lang)}, «{u['title']}». Concetti dell'unità: {u['concepts']}."
    if u.get("notes"):
        t += " Indicazioni tecniche (seguile alla lettera): " + u["notes"]
    if PATHS[lang].get("algo"):
        t += (" È un percorso di algoritmi e strutture dati: ogni esercizio è un piccolo problema algoritmico classico, "
              "con casi limite nei test (lista vuota, un solo elemento, valori ripetuti). Quando conta, chiedi o spiega la complessità.")
    t += " Lo studente conosce già: " + (", ".join(before) if before else "nulla, è la prima unità") + "."
    if after:
        t += " NON usare concetti delle unità successive (" + ", ".join(after) + ")."
    t += f" Ambienta l'esercizio in questo contesto: {random.choice(THEMES)}."
    return t


def generate_for_key(key, kind):
    info = key_info(key)
    diff = DIFF_OF[info["level"]]
    avoid = [e.get("title", "") for e in pool_load(key)][-20:]
    runner = ""
    if info["kind"] == "path":
        topic, mode = unit_topic(info["path"], info["unit"]["id"]), info["mode"]
        runner = info["unit"].get("runner", "")
    elif info["kind"] == "logic":
        topic = info["cat"]["topic"] + f". Ambientazione: {random.choice(THEMES)}."
        mode = "tests" if info["mode"] == "tests" else "output"
    else:
        topic = f"colloquio per {info['track']['title']}, livello {INTERVIEW_LEVEL_NAMES[info['level']]}. Argomenti: {info['track']['topic']}"
        if info["track"].get("en"):
            topic += (". IL COLLOQUIO È IN INGLESE: scrivi domanda, punti chiave, risposta modello e domanda di approfondimento in inglese "
                      "chiaro, come in un colloquio reale con un'azienda internazionale")
        mode = "tests"
    return generate_exercise(kind, info["lang"], diff, topic, avoid, mode, attempts=3, runner=runner)


def worker_targets():
    k = FOCUS["key"]
    if not k:
        return []
    seq = key_info(k)["seq"]
    i = seq.index(k)
    out = [(k, 12)]
    if i + 1 < len(seq):
        out.append((seq[i + 1], 8))
    if i + 2 < len(seq):
        out.append((seq[i + 2], 4))
    return out


def needed_kind(key, want, p):
    items = unseen(key, p)
    if len(items) >= want:
        return None
    mix, _ = adaptive_mix(key, p)
    tot = sum(mix.values())
    have = {}
    for e in items:
        have[e["type"]] = have.get(e["type"], 0) + 1
    return max(mix, key=lambda t: mix[t] / tot * want - have.get(t, 0) + random.random() * 0.01)


def worker_loop():
    from .lezioni import get_unit_lesson
    from .oggi import quick_job
    from .progressi import get_theory
    _TL.worker = True
    fails, last_focus = {}, None
    while True:
        key = None
        try:
            if FOCUS["key"] != last_focus:
                fails, last_focus = {}, FOCUS["key"]
            if user_busy():
                time.sleep(0.7)
                continue
            if not FOCUS["key"]:
                if not quick_job(fails):
                    WORKER["job"] = None
                    time.sleep(1.5)
                continue
            p = progress()
            job = None
            fk = FOCUS["key"].split("/")
            if fk[0] in PATHS and not unit_lesson_path(fk[0], fk[1]).exists() and fails.get("lesson", 0) < 3:
                key = "lesson"
                WORKER["job"] = f"lezione · {unit_of(fk[0], fk[1])[1]['title']}"
                WORKER["since"] = time.time()
                get_unit_lesson(fk[0], fk[1])
                continue
            for k, want in worker_targets():
                kind = needed_kind(k, want, p)
                if kind and fails.get(k, 0) < 5:
                    job = (k, kind)
                    break
            if not job:
                lang, uid, _ = FOCUS["key"].split("/")
                nxt = None
                if lang in PATHS:
                    i = unit_of(lang, uid)[0]
                    nxt = units(lang)[i + 1]["id"] if i + 1 < len(units(lang)) else None
                if lang in PATHS and not (THEORY / f"{lang}_{uid}.json").exists() and fails.get("theory", 0) < 3:
                    key = "theory"
                    WORKER["job"] = f"teoria · {unit_of(lang, uid)[1]['title']}"
                    get_theory(lang, uid)
                elif nxt and not unit_lesson_path(lang, nxt).exists() and fails.get("next_lesson", 0) < 2:
                    # la lezione dell'unità dopo, così quando ci arrivi è già pronta invece di aspettare mezzo minuto
                    key = "next_lesson"
                    WORKER["job"] = f"lezione · {unit_of(lang, nxt)[1]['title']}"
                    WORKER["since"] = time.time()
                    get_unit_lesson(lang, nxt)
                elif not quick_job(fails):
                    WORKER["job"] = None
                    time.sleep(2)
                continue
            if not current_model():
                WORKER["job"] = None
                time.sleep(8)
                continue
            key, kind = job
            WORKER["job"] = f"{key_info(key)['label']} · {EX_TYPES[kind]}"
            WORKER["since"] = time.time()
            t0 = time.time()
            ex = generate_for_key(key, kind)
            pool_add(key, ex)
            log_event("gen", what="esercizio", key=key, kind=kind, secs=round(time.time() - t0, 1), attempts=ex.get("genAttempts", 1))
            WORKER["made"] += 1
            WORKER["error"] = None
            fails[key] = 0
        except Preempted:
            time.sleep(0.3)
        except Exception as e:
            log_event("gen_fail", key=key, err=str(e)[:200])
            if key:
                fails[key] = fails.get(key, 0) + 1
            WORKER["error"] = str(e)[:200]
            time.sleep(3)
        finally:
            WORKER["since"] = None if not WORKER.get("job") else WORKER["since"]


def unit_lesson_id(lang, uid):
    return f"u{PATHS[lang]['pre']}{uid}"


def unit_lesson_path(lang, uid):
    return LESSONS / f"{unit_lesson_id(lang, uid)}.json"
