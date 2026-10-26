"""Esecuzione di SQL su SQLite in un sottoprocesso (con limite di tempo) e confronto dei risultati."""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

TIMEOUT = 10
MAX_ROWS = 200
NOWINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

HARNESS = r'''
import json, sqlite3, sys

def split(sql):
    out, buf = [], ""
    for ch in sql:
        buf += ch
        if ch == ";" and sqlite3.complete_statement(buf):
            if buf.strip():
                out.append(buf.strip())
            buf = ""
    if buf.strip():
        out.append(buf.strip())
    return out

def val(v):
    if isinstance(v, bytes):
        return v.hex()
    if isinstance(v, float) and v.is_integer():
        return v
    return v

def result(cur):
    cols = [d[0] for d in cur.description]
    rows = [[val(v) for v in r] for r in cur.fetchmany(MAX)]
    return {"cols": cols, "rows": rows}

MAX = int(sys.argv[2])
job = json.load(open(sys.argv[1], encoding="utf-8"))
out = {"error": None, "result": None, "outputs": [], "where": None, "tables": {}}
con = sqlite3.connect(":memory:", isolation_level=None)  # autocommit: BEGIN/COMMIT scritti dallo studente funzionano
con.execute("PRAGMA foreign_keys = ON")
try:
    if job.get("setup"):
        con.executescript(job["setup"])
except Exception as e:
    out["error"] = "Errore nella preparazione del database: %s" % e
    out["where"] = "setup"
    print("##RES##" + json.dumps(out)); sys.exit()
for stmt in split(job.get("code") or ""):
    try:
        cur = con.execute(stmt)
        if cur.description:
            r = result(cur)
            out["result"] = r
            out["outputs"].append(dict(r, sql=stmt[:200]))
    except Exception as e:
        out["error"] = "%s: %s" % (type(e).__name__, e)
        out["where"] = stmt[:300]
        break
con.commit()
if not out["error"] and job.get("check"):
    try:
        cur = con.execute(job["check"])
        out["result"] = result(cur) if cur.description else None
    except Exception as e:
        out["error"] = "Errore nella query di verifica: %s" % e
        out["where"] = "check"
if job.get("tables"):
    try:
        names = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY rowid")]
        for n in names[:6]:
            out["tables"][n] = result(con.execute('SELECT * FROM "%s" LIMIT 12' % n.replace('"', '""')))
    except Exception:
        pass
print("##RES##" + json.dumps(out, default=str))
'''


def run_sql(setup, code, check=None, tables=False):
    """Esegue setup + codice (+ query di verifica). Restituisce {error, result:{cols, rows}, outputs, tables}."""
    with tempfile.TemporaryDirectory(prefix="ricalco_sql_") as d:
        Path(d, "job.json").write_text(json.dumps({"setup": setup or "", "code": code or "", "check": check or "", "tables": tables}),
                                       encoding="utf-8")
        Path(d, "h.py").write_text(HARNESS, encoding="utf-8")
        try:
            p = subprocess.run([sys.executable, "-I", "h.py", "job.json", str(MAX_ROWS)], cwd=d, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=TIMEOUT, stdin=subprocess.DEVNULL, creationflags=NOWINDOW)
        except subprocess.TimeoutExpired:
            return {"error": "Tempo scaduto: la query non finisce (forse una CTE ricorsiva senza condizione di uscita).", "result": None, "outputs": []}
        m = re.search(r"##RES##(.*)", p.stdout or "")
        if not m:
            return {"error": (p.stderr or "Esecuzione interrotta.")[-800:], "result": None, "outputs": []}
        return json.loads(m.group(1))


def _norm_val(v):
    """Numeri confrontati per valore (24, 24.0 e "24" sono uguali); il resto come testo."""
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, str):
        try:
            v = float(v.strip())
        except ValueError:
            return v.strip()
    if isinstance(v, (int, float)):
        f = round(float(v), 6)
        return int(f) if f.is_integer() else f
    return v


def _key(row):
    return json.dumps([_norm_val(v) for v in row], default=str)


def same_result(expected, got, ordered):
    """Confronta due risultati: stesse righe (in ordine se richiesto). I nomi delle colonne non contano, il loro numero sì."""
    if not expected or not got:
        return False
    if len(expected["cols"]) != len(got["cols"]) or len(expected["rows"]) != len(got["rows"]):
        return False
    a = [_key(r) for r in expected["rows"]]
    b = [_key(r) for r in got["rows"]]
    return a == b if ordered else sorted(a) == sorted(b)


def is_ordered(sql):
    return bool(re.search(r"\border\s+by\b", re.sub(r"--.*", "", sql or ""), re.I))


def fmtv(v):
    if v is None:
        return "NULL"
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() else str(round(v, 4))
    return str(v)


def as_text(res):
    """Righe come testo «a | b», per gli esercizi «prevedi il risultato»."""
    if not res:
        return ""
    return "\n".join(" | ".join(fmtv(v) for v in r) for r in res["rows"])


def script_output(r):
    """Output leggibile di uno script: ogni SELECT con le sue righe."""
    parts = []
    for o in r.get("outputs", []):
        lines = [" | ".join(o["cols"])] + [" | ".join(fmtv(v) for v in row) for row in o["rows"]]
        parts.append("\n".join(lines))
    return "\n\n".join(parts)
