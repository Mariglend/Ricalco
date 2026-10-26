"""Prova del modello: un esercizio per sezione, verificato come nell'app."""

import time

from .config import SPRING
from .llm import llm_stream
from .generazione import TUTOR_SYS
from .percorsi import generate_for_key, pool_add


# ---------------------------------------------------------------- prova del modello
SELFTEST = [
    ("Percorso Python · domanda", "python/u3/base", "quiz"),
    ("Percorso Python · completa gli spazi", "python/u3/base", "riempi"),
    ("Percorso Python · prevedi l'output", "python/u5/base", "predici"),
    ("Percorso Python · trova il bug", "python/u5/pratica", "bug"),
    ("Percorso Python · scrivi da zero (test)", "python/u7/sfida", "zero"),
    ("Percorso Java · prevedi l'output", "java/u5/base", "predici"),
    ("Percorso Java · scrivi da zero (test)", "java/u8/pratica", "zero"),
    ("Percorso SQL · prevedi il risultato", "sql/u6/base", "predici"),
    ("Percorso SQL · scrivi la query", "sql/u7/pratica", "zero"),
    ("Algoritmi in Python · scrivi da zero (test)", "algopy/u3/pratica", "zero"),
    ("Algoritmi in Java · trova il bug (test)", "algojava/u8/pratica", "bug"),
    ("Logica · rompicapo", "logica/rompicapo/pratica", "logica"),
    ("Logica · sequenze", "logica/sequenze/pratica", "logica"),
    ("Colloquio · domanda", "colloquio/java_backend/base", "orale"),
    ("Colloquio in inglese · domanda", "colloquio/java_backend_en/base", "orale"),
]


def selftest_steps():
    steps = [{"label": "Tutor · prima risposta", "kind": "tutor"}]
    steps += [{"label": l, "key": k, "kind": t} for l, k, t in SELFTEST]
    if SPRING.ready():
        steps.append({"label": "Spring · completa il codice (Maven)", "key": "java/u22/pratica", "kind": "completa"})
    return steps


def selftest_run(step):
    t0 = time.time()
    if step["kind"] == "tutor":
        gen = llm_stream([{"role": "system", "content": TUTOR_SYS}, {"role": "user", "content": "In una frase: cos'è una variabile?"}], num_ctx=2048)
        first, text = None, ""
        for piece in gen:
            if first is None:
                first = time.time() - t0
            text += piece
        return {"ok": bool(text.strip()), "secs": round(time.time() - t0, 1), "first": round(first or 0, 1), "sample": text[:200]}
    try:
        ex = generate_for_key(step["key"], step["kind"])
        pool_add(step["key"], ex)
        return {"ok": True, "secs": round(time.time() - t0, 1), "attempts": ex.get("genAttempts", 1), "title": ex.get("title")}
    except Exception as e:
        return {"ok": False, "secs": round(time.time() - t0, 1), "attempts": 3, "error": str(e)[:300]}
