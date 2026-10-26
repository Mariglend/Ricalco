"""Catalogo di algoritmi da colloquio: circa 170 problemi scritti a mano, in Python e in Java, divisi per schema.

Ogni problema è già verificato (il programma è stato eseguito e l'output confrontato). Entrano anche in «Oggi»:
il punteggio Elo li propone quando sono al tuo livello, come gli altri esercizi."""

import json
from pathlib import Path

DATI = Path(__file__).resolve().parent / "dati" / "algoritmi.json"
_CACHE = {}


def catalogo():
    if "all" not in _CACHE:
        _CACHE["all"] = json.loads(DATI.read_text(encoding="utf-8")) if DATI.exists() else []
    return _CACHE["all"]


def catalog_id(lang, key):
    return f"c{lang[0]}_{key.replace('-', '_')}"


def catalog_items(lang):
    """Gli esercizi del catalogo nel formato di «Oggi» (solo Python e Java)."""
    if lang not in ("python", "java"):
        return []
    out = []
    for c in catalogo():
        it = c.get(lang)
        if not it:
            continue
        out.append(dict(it, id=catalog_id(lang, c["key"]), lang=lang, pattern=c["pattern"], tier=c["tier"], kind="algoritmo",
                        output=it.get("expected", ""), seed=True, verified=True, catalog=True))
    return out


def catalog_view(lang):
    from .oggi import patterns_for
    from .percorsi import progress
    p = progress()
    seen, best = p.get("quickSeen", {}), p.get("qbest", {})
    pats = patterns_for(lang)
    groups = {}
    for it in catalog_items(lang):
        groups.setdefault(it["pattern"], []).append({"id": it["id"], "title": it["title"], "tier": it["tier"], "problem": it["problem"],
                                                     "done": it["id"] in seen, "best": round(best.get(it["id"], 0) * 100)})
    out = []
    for k, name in pats.items():
        items = sorted(groups.get(k, []), key=lambda x: (x["tier"], x["title"]))
        if items:
            out.append({"id": k, "name": name, "items": items, "done": len([x for x in items if x["done"]])})
    n = sum(len(g["items"]) for g in out)
    return {"lang": lang, "patterns": out, "n": n, "done": sum(g["done"] for g in out)}
