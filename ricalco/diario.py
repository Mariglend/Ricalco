"""Diario d'uso: riassunto dei log ed errori di ragionamento."""

import json
import time

from .config import LOGS


# ---- diario d'uso: riassunto dei log
def logs_read(days=14):
    out = []
    for f in sorted(LOGS.glob("*.jsonl"))[-days:]:
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    return out


def _avg(xs):
    xs = [x for x in xs if isinstance(x, (int, float))]
    return round(sum(xs) / len(xs), 1) if xs else None


def _p90(xs):
    xs = sorted(x for x in xs if isinstance(x, (int, float)))
    return round(xs[int(len(xs) * 0.9) - 1 if len(xs) >= 10 else -1], 1) if xs else None


def reasoning_errors(ev):
    """Gli errori di ragionamento, separati da quelli di battitura: piani sbagliati o incompleti prima di scrivere,
    spiegazioni (Feynman) poco corrette o incomplete, domande di ragionamento sbagliate negli esercizi."""
    out = []
    t2 = lambda x: time.strftime("%d/%m %H:%M", time.localtime(x["t"]))
    names = {x["id"]: x["title"] for x in ev if x.get("id") and x.get("title")}
    for x in ev:
        e = x.get("ev")
        if e == "plan_try" and (x.get("ok") is False or x.get("verdict") in ("parziale", "sbagliato")):
            how = {"mc": "Piano a scelta", "free": "Piano scritto da te", "flashcard": "Ripasso: spiegazione a parole"}.get(x.get("how"), "Piano")
            out.append({"t": t2(x), "title": x.get("title") or names.get(x.get("id"), x.get("id", "")), "kind": how,
                        "what": "sbagliato" if x.get("ok") is False or x.get("verdict") == "sbagliato" else "incompleto",
                        "answer": x.get("answer", ""), "comment": x.get("comment", "")})
        elif e == "plan_done" and x.get("plan") == "shown":
            out.append({"t": t2(x), "title": x.get("title", ""), "kind": "Piano", "what": "ti sei fatto mostrare il piano", "answer": "", "comment": ""})
        elif e == "feynman" and x.get("stage") == "judge" and (min(x.get("correct", 5), x.get("complete", 5)) <= 2):
            out.append({"t": t2(x), "title": x.get("title", ""), "kind": "Spiegazione (Feynman)",
                        "what": f"correttezza {x.get('correct')}/5, completezza {x.get('complete')}/5", "answer": "", "comment": x.get("missing", "")})
        elif e == "ex_result" and x.get("type") in ("quiz", "logica", "orale") and x.get("result") not in ("first", None):
            out.append({"t": t2(x), "title": x.get("title", ""), "kind": {"quiz": "Domanda di ragionamento", "logica": "Problema di logica", "orale": "Domanda da colloquio"}[x["type"]],
                        "what": "giusta al secondo tentativo" if x.get("result") == "retry" else "sbagliata", "answer": "", "comment": ""})
    return out[-40:][::-1]


def logs_summary(days=14):
    ev = logs_read(days)
    app = [e for e in ev if e.get("src") == "app"]
    byday = {}
    for e in app:
        d = time.strftime("%Y-%m-%d", time.localtime(e["t"]))
        byday.setdefault(d, []).append(e)
    rows = []
    for d, es in sorted(byday.items()):
        ts = sorted(x["t"] for x in es)
        active = sum(min(b - a, 300) for a, b in zip(ts, ts[1:]) if b - a <= 300)
        done = [x for x in es if x["ev"] == "quick_done"]
        rows.append({"day": d, "min": round(active / 60), "done": len(done), "avg": _avg([x.get("s", 0) * 100 for x in done]),
                     "skips": len([x for x in es if x["ev"] == "skip"]), "hints": sum(x.get("hints", 0) for x in done),
                     "variants": len([x for x in es if x["ev"] == "code_task" and x.get("kind") == "variant"]),
                     "exercises": len([x for x in es if x["ev"] == "ex_result"])})
    def pick(name):
        return [x for x in app if x["ev"] == name]
    plans = pick("plan_done")
    blocks = pick("block")
    vt = [x for x in pick("code_task") if x.get("kind") == "variant"]
    pr = pick("predict")
    waits = {}
    for w in pick("wait"):
        waits.setdefault(w.get("what", "?"), []).append(w.get("secs", 0))
    hard = sorted(blocks, key=lambda b: (b.get("err", 0) + 3 * b.get("hints", 0)), reverse=True)[:6]
    skips = {}
    for x in pick("skip"):
        skips[x.get("title", "?")] = skips.get(x.get("title", "?"), 0) + 1
    llm = [x for x in ev if x.get("ev") == "llm"]
    fg = [x for x in llm if not x.get("bg")]
    kinds = {}
    for x in llm:
        k = x.get("what", "")[:34]
        kinds.setdefault(k, []).append(x)
    gen = [x for x in ev if x.get("ev") == "gen"]
    return {
        "days": rows,
        "totals": {"activeMin": sum(r["min"] for r in rows), "activeDays": len(rows), "done": sum(r["done"] for r in rows),
                   "avg": _avg([x.get("s", 0) * 100 for x in pick("quick_done")]),
                   "variants": len(vt), "variantsOk": len([x for x in vt if x.get("result") != "miss"]),
                   "predict": len(pr), "predictOk": len([x for x in pr if x.get("ok")]), "tutor": len(pick("tutor")),
                   "skips": len(pick("skip"))},
        "phases": {"ragiona": _avg([x.get("secs") for x in plans]), "scrivi": _avg([x.get("secs") for x in pick("quick_done")]),
                   "planFirst": len([x for x in plans if x.get("plan") in ("first", "free")]), "planShown": len([x for x in plans if x.get("plan") == "shown"]),
                   "plans": len(plans)},
        "hardBlocks": [{"title": b.get("title"), "k": b.get("k"), "err": b.get("err", 0), "hints": b.get("hints", 0), "secs": b.get("secs")} for b in hard if b.get("err") or b.get("hints")],
        "skipped": sorted(({"title": k, "n": v} for k, v in skips.items()), key=lambda x: -x["n"])[:6],
        "waits": [{"what": k, "n": len(v), "avg": _avg(v), "max": round(max(v), 1)} for k, v in waits.items()],
        "llm": {"n": len(llm), "fail": len([x for x in llm if not x.get("ok")]), "avg": _avg([x["secs"] for x in llm if x.get("ok")]),
                "p90": _p90([x["secs"] for x in llm if x.get("ok")]), "fgAvg": _avg([x["secs"] for x in fg if x.get("ok")]),
                "tutorFirst": _avg([x.get("first") for x in ev if x.get("ev") == "llm_stream"]),
                "kinds": sorted(({"what": k, "n": len(v), "avg": _avg([x["secs"] for x in v if x.get("ok")]),
                                  "fail": len([x for x in v if not x.get("ok")])} for k, v in kinds.items()), key=lambda x: -x["n"])[:8],
                "gen": len(gen), "genAvg": _avg([x.get("secs") for x in gen]), "genFail": len([x for x in ev if x.get("ev") == "gen_fail"])},
        "reasoning": reasoning_errors(ev),
        "notes": [{"t": time.strftime("%d/%m %H:%M", time.localtime(x["t"])), "text": x.get("text", ""), "where": x.get("where", "")}
                  for x in pick("note")][-30:][::-1],
        "errors": [{"t": time.strftime("%d/%m %H:%M", time.localtime(x["t"])), "msg": x.get("msg", "")} for x in pick("js_error")][-10:],
    }
