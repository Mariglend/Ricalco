#!/usr/bin/env python3
"""Ricalco locale: impara a programmare riscrivendo il codice, con Qwen via Ollama.

Solo libreria standard: nessun pip install.
Avvio:  python server.py          (apre il browser su http://127.0.0.1:8765)
Opzioni (variabili d'ambiente):
  RICALCO_OLLAMA  indirizzo di Ollama   (predefinito http://127.0.0.1:11434)
  RICALCO_PORT    porta dell'app        (predefinita 8765)
  RICALCO_MODEL   modello da usare      (predefinito: il primo "qwen" installato)
"""
import contextlib
import glob
import json
import os
import random
import sqlite3
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from curriculum import (ALGO, CURRICULUM, INTERVIEW, INTERVIEW_LEVEL_NAMES, INTERVIEW_MIX, LEVELS, LOGIC, LOGIC_LEVEL_NAMES, MIX,
                        MIX_REVIEW, MIX_SPRING, PATHS, SEEDS, SESSION_SIZE, THEMES, TYPE_ORDER)
from projects import PROJECTS, snapshot, step_view
from quick import QUICK_SEEDS, QUICK_TOPICS, TIER_DESC, TIERS, patterns_for, tier_rating
from spring_runner import SpringRunner, make_runners
from sql_runner import as_text as sql_as_text, is_ordered, run_sql, same_result, script_output

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
DATA = ROOT / "data"
LESSONS = DATA / "lessons"
CONFIG_FILE = DATA / "config.json"
OLLAMA = os.environ.get("RICALCO_OLLAMA", "http://127.0.0.1:11434").rstrip("/")
PORT = int(os.environ.get("RICALCO_PORT", "8765"))
NUM_CTX = int(os.environ.get("RICALCO_CTX", "6144"))
RUN_TIMEOUT = 10
JAVA_TIMEOUT = 25
NOWINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
LANGNAME = {"python": "Python 3", "java": "Java", "sql": "SQL (SQLite)"}


class LLMError(Exception):
    pass


class Preempted(Exception):
    """Il worker in sottofondo cede Ollama a una richiesta dell'utente."""


_TL = threading.local()
_USER = {"n": 0}
_USER_LOCK = threading.Lock()


class user_priority:
    def __enter__(self):
        with _USER_LOCK:
            _USER["n"] += 1

    def __exit__(self, *a):
        with _USER_LOCK:
            _USER["n"] -= 1


def user_busy():
    return _USER["n"] > 0


# ---------------------------------------------------------------- storage
def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


CONFIG = load_json(CONFIG_FILE, {})

# ---------------------------------------------------------------- log d'uso (solo sul tuo PC, in data/logs/)
LOGS = DATA / "logs"
_LOGLOCK = threading.Lock()


def log_event(ev, **kw):
    """Una riga JSON per evento in data/logs/AAAA-MM-GG.jsonl. Non deve mai far fallire nulla."""
    try:
        rec = {"t": round(time.time(), 3), "ev": ev, "src": kw.pop("src", "server")}
        rec.update(kw)
        line = json.dumps(rec, ensure_ascii=False, default=str)
        with _LOGLOCK:
            LOGS.mkdir(parents=True, exist_ok=True)
            with open(LOGS / (time.strftime("%Y-%m-%d") + ".jsonl"), "a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception:
        pass
RUNNERS = make_runners(DATA)
SPRING = RUNNERS[""]
if os.environ.get("RICALCO_MODEL"):
    CONFIG["model"] = os.environ["RICALCO_MODEL"]


# ---------------------------------------------------------------- ollama
def ollama_request(path, body=None, timeout=900):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        OLLAMA + path, data=data, method="POST" if data else "GET",
        headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=timeout)


def list_models():
    with ollama_request("/api/tags", timeout=4) as r:
        return [m["name"] for m in json.load(r).get("models", [])]


def pick_model(models):
    if CONFIG.get("model") in models:
        return CONFIG["model"]
    if not models:
        return None

    def score(name):
        n = name.lower()
        return ("qwen" in n) * 8 + ("coder" in n) * 4 + ("7b" in n) * 2 + ("embed" not in n)
    return max(models, key=score)


def current_model():
    try:
        return pick_model(list_models())
    except Exception:
        return None


_CAPS = {}


def model_caps(model):
    """Capacità del modello (es. "thinking" per Qwen3), lette da Ollama una volta sola."""
    if model not in _CAPS:
        try:
            with ollama_request("/api/show", {"model": model}, timeout=10) as r:
                _CAPS[model] = set(json.load(r).get("capabilities") or [])
        except Exception:
            _CAPS[model] = {"thinking"} if "qwen3" in model.lower() else set()
    return _CAPS[model]


def chat_body(model, messages, stream, temperature, num_ctx, fmt=None):
    body = {"model": model, "messages": messages, "stream": stream, "keep_alive": "30m",
            "options": {"temperature": temperature, "num_ctx": num_ctx or NUM_CTX}}
    if fmt is not None:
        body["format"] = fmt
    if "thinking" in model_caps(model):
        body["think"] = False   # Qwen3: niente ragionamento nascosto, risposte molto più rapide
    return body


THINK_RE = re.compile(r"<think>.*?</think>", re.S)


def parse_json_loose(text):
    text = THINK_RE.sub("", text).strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    a, b = text.find("{"), text.rfind("}")
    if a >= 0 and b > a:
        return json.loads(text[a:b + 1])
    raise ValueError("risposta non in JSON")


def llm_what(messages):
    u = next((m["content"] for m in messages if m["role"] == "user"), "")
    return re.sub(r"\s+", " ", u)[:70]


def llm_json(messages, schema, temperature=0.3, num_ctx=None):
    t0 = time.time()
    try:
        out = _llm_json(messages, schema, temperature, num_ctx)
        log_event("llm", what=llm_what(messages), secs=round(time.time() - t0, 2), ok=True, bg=getattr(_TL, "worker", False), model=CONFIG.get("model") or "")
        return out
    except Preempted:
        log_event("llm", what=llm_what(messages), secs=round(time.time() - t0, 2), ok=False, err="interrotto per dare precedenza a te", bg=True)
        raise
    except Exception as e:
        log_event("llm", what=llm_what(messages), secs=round(time.time() - t0, 2), ok=False, err=str(e)[:200], bg=getattr(_TL, "worker", False))
        raise


def _llm_json(messages, schema, temperature=0.3, num_ctx=None):
    model = current_model()
    if not model:
        raise LLMError("Ollama non risponde o non c'è nessun modello installato.")
    worker = getattr(_TL, "worker", False)
    body = chat_body(model, messages, worker, temperature, num_ctx, schema)
    for attempt in range(2):
        try:
            if worker:
                # In sottofondo: streaming, così si può interrompere appena l'utente chiede qualcosa.
                parts = []
                with ollama_request("/api/chat", body) as r:
                    for line in r:
                        if user_busy():
                            raise Preempted()
                        if not line.strip():
                            continue
                        obj = json.loads(line)
                        parts.append(obj.get("message", {}).get("content", ""))
                        if obj.get("done"):
                            break
                return parse_json_loose("".join(parts))
            with ollama_request("/api/chat", body) as r:
                res = json.load(r)
            return parse_json_loose(res.get("message", {}).get("content", ""))
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")
            if attempt == 0 and "format" in msg.lower():
                body["format"] = "json"   # Ollama vecchio: niente schema, solo JSON
                continue
            raise LLMError("Ollama ha risposto con un errore: " + msg[:300])
        except urllib.error.URLError:
            raise LLMError("Ollama non risponde su " + OLLAMA + ".")
        except ValueError:
            if attempt == 0:
                continue
            raise LLMError("Il modello non ha restituito un JSON valido.")
    raise LLMError("Il modello non ha restituito un JSON valido.")


def llm_stream(messages, temperature=0.4, num_ctx=None):
    model = current_model()
    if not model:
        raise LLMError("Ollama non risponde o non c'è nessun modello installato.")
    body = chat_body(model, messages, True, temperature, num_ctx)
    try:
        resp = ollama_request("/api/chat", body)
    except urllib.error.URLError:
        raise LLMError("Ollama non risponde su " + OLLAMA + ".")

    def gen():
        in_think = False
        t0, first, n = time.time(), None, 0
        try:
            for piece in raw():
                if first is None:
                    first = round(time.time() - t0, 2)
                n += len(piece)
                yield piece
        finally:
            log_event("llm_stream", what=llm_what(messages), first=first, secs=round(time.time() - t0, 2), chars=n)

    def raw():
        in_think = False
        with resp:
            for line in resp:
                if not line.strip():
                    continue
                obj = json.loads(line)
                piece = obj.get("message", {}).get("content", "")
                if "<think>" in piece:
                    in_think = True
                    piece = piece.split("<think>")[0]
                if "</think>" in piece:
                    in_think = False
                    piece = piece.split("</think>", 1)[1]
                elif in_think:
                    piece = ""
                if piece:
                    yield piece
                if obj.get("done"):
                    break
    return gen()


# ---------------------------------------------------------------- esecuzione codice
def run_proc(cmd, cwd, timeout):
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout, stdin=subprocess.DEVNULL,
                           creationflags=NOWINDOW, env=env)
        return p.returncode, p.stdout, p.stderr, False
    except subprocess.TimeoutExpired as e:
        def s(x):
            return x.decode("utf-8", "replace") if isinstance(x, bytes) else (x or "")
        return -1, s(e.stdout), s(e.stderr), True


def clean_err(text, tmpdir):
    text = "\n".join(l for l in text.splitlines() if not l.startswith("Picked up JAVA_TOOL_OPTIONS"))
    for p in {str(tmpdir), str(Path(tmpdir).resolve())}:
        text = text.replace(p + os.sep, "").replace(p + "/", "").replace(p, "")
    return text.strip()


_JAVA = {"checked": False, "exe": None, "version": None}


def _java_version(exe):
    try:
        _, out, err, _ = run_proc([exe, "-version"], str(ROOT), 15)
    except OSError:
        return None, 0
    m = re.search(r'version "([^"]+)"', err + out)
    if not m:
        return None, 0
    v = m.group(1)
    nums = re.findall(r"\d+", v)
    major = int(nums[1]) if v.startswith("1.") and len(nums) > 1 else int(nums[0]) if nums else 0
    return v, major


def _java_candidates():
    """Tutti i java che troviamo: JAVA_HOME, il PATH e le cartelle di installazione più comuni su Windows
    (Oracle, Adoptium, Microsoft, Zulu, Corretto, le JDK scaricate da IntelliJ)."""
    exe = "java.exe" if os.name == "nt" else "java"
    out = []
    if os.environ.get("JAVA_HOME"):
        out.append(str(Path(os.environ["JAVA_HOME"]) / "bin" / exe))
    w = shutil.which("java")
    if w:
        out.append(w)
    if os.name == "nt":
        roots = [os.environ.get("ProgramFiles", r"C:\Program Files"), os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")]
        for r in roots:
            for vendor in ("Java", "Eclipse Adoptium", "Microsoft", "Zulu", "Amazon Corretto", "BellSoft", "Semeru"):
                out += glob.glob(str(Path(r) / vendor / "*" / "bin" / exe))
        out += glob.glob(str(Path.home() / ".jdks" / "*" / "bin" / exe))
    seen, res = set(), []
    for p in out:
        k = os.path.normcase(os.path.abspath(p))
        if k not in seen and Path(p).exists():
            seen.add(k)
            res.append(p)
    return res


def java_info():
    """Sceglie il Java più recente (serve almeno Java 11 per eseguire un file .java direttamente; consigliato 17+).
    Su Windows il primo java del PATH è spesso un vecchio Java 8 di Oracle (cartella javapath): lo saltiamo."""
    if not _JAVA["checked"]:
        _JAVA["checked"] = True
        best = None
        for exe in _java_candidates():
            v, major = _java_version(exe)
            jdk = (Path(exe).parent / ("javac.exe" if os.name == "nt" else "javac")).exists()
            # prima i JDK (hanno javac: servono a Maven e a `java File.java`), poi la versione più recente
            if v and (not best or (jdk, major) > (best[3], best[2])):
                best = (exe, v, major, jdk)
        if best:
            _JAVA.update(exe=best[0], version=best[1], major=best[2], jdk=best[3], home=str(Path(best[0]).parent.parent))
            if best[2] < 11:
                _JAVA["old"] = True
            if best[3]:
                SpringRunner.java_home = _JAVA["home"]
            else:
                _JAVA["jre"] = True
    return _JAVA


def JAVA_MISSING_MSG():
    i = java_info()
    what = f"Java {i['version']}" + (" senza compilatore (è un JRE, non un JDK)" if i.get("jre") else "")
    return (f"Ho trovato solo {what} in {i.get('home')}. Serve un JDK 17 o più recente: installa Eclipse Temurin 21 "
            "(adoptium.net, spunta «Set JAVA_HOME») e riavvia Ricalco.")


def java_run_cmd(name):
    """Comando per eseguire un file .java. Con Java 11+ basta `java File.java`; con Java più vecchi non si può."""
    info = java_info()
    return [info["exe"], "-Dfile.encoding=UTF-8", "-Dstdout.encoding=UTF-8", name]


PY_HARNESS = r'''
import io, json, math, sys, contextlib, traceback

def fmt_exc(e):
    if isinstance(e, SyntaxError):
        t = ("\n    " + e.text.rstrip()) if e.text else ""
        return "Errore di sintassi alla riga %s: %s%s" % (e.lineno, e.msg, t)
    frames = [f for f in traceback.extract_tb(e.__traceback__) if f.filename == "soluzione.py"]
    loc = (" (riga %d: %s)" % (frames[-1].lineno, (frames[-1].line or "").strip())) if frames else ""
    return "%s: %s%s" % (type(e).__name__, e, loc)

def eq(a, b):
    if isinstance(a, float) or isinstance(b, float):
        try:
            return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)
        except TypeError:
            return False
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)) and type(a) == type(b):
        return len(a) == len(b) and all(eq(x, y) for x, y in zip(a, b))
    return a == b

src = open("soluzione.py", encoding="utf-8").read()
tests = json.load(open("tests.json", encoding="utf-8"))
res = {"error": None, "stdout": "", "tests": []}
out = io.StringIO()
ns = {"__name__": "__soluzione__"}
try:
    with contextlib.redirect_stdout(out):
        exec(compile(src, "soluzione.py", "exec"), ns)
except BaseException as e:
    res["error"] = fmt_exc(e)
if not res["error"]:
    for t in tests:
        r = {"desc": t.get("desc", ""), "call": t["call"], "expected": t["expected"], "ok": False}
        try:
            with contextlib.redirect_stdout(out):
                got = eval(t["call"], ns)
            exp = eval(t["expected"], dict(ns))
            r["ok"] = bool(eq(got, exp))
            r["got"] = repr(got)[:400]
        except BaseException as e:
            r["error"] = fmt_exc(e)[:500]
        res["tests"].append(r)
res["stdout"] = out.getvalue()[:4000]
sys.stdout.write("\n##RES##" + json.dumps(res) + "\n")
'''

JAVA_HARNESS = r'''import java.util.*;
import java.util.stream.*;
@@IMPORTS@@
public class Main {
    static String fmt(Object o) {
        if (o == null) return "null";
        if (o.getClass().isArray()) { String s = Arrays.deepToString(new Object[]{o}); return s.substring(1, s.length() - 1); }
        if (o instanceof String) return "\"" + o + "\"";
        if (o instanceof Character) return "'" + o + "'";
        return String.valueOf(o);
    }
    static boolean isInt(Object o) { return o instanceof Integer || o instanceof Long || o instanceof Short || o instanceof Byte; }
    static boolean eq(Object a, Object b) {
        if (a instanceof Number && b instanceof Number) {
            if (isInt(a) && isInt(b)) return ((Number) a).longValue() == ((Number) b).longValue();
            return Math.abs(((Number) a).doubleValue() - ((Number) b).doubleValue()) < 1e-9;
        }
        return Objects.deepEquals(a, b);
    }
    static void out(int i, boolean ok, String got) {
        System.out.println("##T##" + i + "|" + ok + "|" + got.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", ""));
    }
    public static void main(String[] args) {
@@TESTS@@
        System.out.println("##END##");
    }
}
'''


def norm_code(code):
    code = str(code or "").replace("\r\n", "\n").replace("\r", "\n").replace("\t", "    ")
    return "\n".join(l.rstrip() for l in code.split("\n")).strip("\n")


def norm_tests(tests):
    out = []
    for t in tests or []:
        if not isinstance(t, dict):
            continue
        call = str(t.get("call") or t.get("chiamata") or "").strip()
        exp = str(t.get("expected") if t.get("expected") is not None else t.get("atteso", "")).strip()
        if call and exp:
            out.append({"desc": str(t.get("desc") or t.get("descrizione") or ""), "call": call, "expected": exp})
    return out


def run_python_tests(code, tests):
    with tempfile.TemporaryDirectory(prefix="ricalco_") as d:
        Path(d, "soluzione.py").write_text(code, encoding="utf-8")
        Path(d, "tests.json").write_text(json.dumps(tests), encoding="utf-8")
        Path(d, "harness.py").write_text(PY_HARNESS, encoding="utf-8")
        rc, out, err, timeout = run_proc([sys.executable, "-I", "harness.py"], d, RUN_TIMEOUT)
        if timeout:
            return {"error": f"Tempo scaduto ({RUN_TIMEOUT} s): probabilmente un ciclo infinito.", "tests": [], "stdout": ""}
        m = re.search(r"##RES##(.*)", out)
        if not m:
            return {"error": clean_err(err, d) or "Esecuzione interrotta.", "tests": [], "stdout": ""}
        return json.loads(m.group(1))


def split_java_imports(code):
    imports, rest = [], []
    for line in code.split("\n"):
        if re.match(r"\s*import\s+[\w.*]+\s*;\s*$", line):
            imports.append(line.strip())
            rest.append("")
        else:
            rest.append(line)
    return imports, "\n".join(rest)


def run_java_tests(code, tests):
    info = java_info()
    if not info["exe"]:
        return {"error": "Java non trovato. Installa un JDK 17 o più recente (per esempio Eclipse Temurin).", "tests": [], "stdout": ""}
    if info.get("old") or info.get("jre"):
        return {"error": JAVA_MISSING_MSG(), "tests": [], "stdout": ""}
    imports, body = split_java_imports(code)
    body = re.sub(r"\bpublic\s+(final\s+)?class\s+Soluzione\b", lambda m: (m.group(1) or "") + "class Soluzione", body)
    lines = []
    for i, t in enumerate(tests):
        lines.append(f'        try {{ Object got = (Object)({t["call"]}); Object exp = (Object)({t["expected"]}); '
                     f'out({i}, eq(got, exp), fmt(got)); }} catch (Throwable e) {{ out({i}, false, "ERR:" + e); }}')
    harness = JAVA_HARNESS.replace("@@IMPORTS@@", "\n".join(imports)).replace("@@TESTS@@", "\n".join(lines))
    head = harness.count("\n") + 1
    src = harness + "\n" + body + "\n"
    with tempfile.TemporaryDirectory(prefix="ricalco_") as d:
        Path(d, "Main.java").write_text(src, encoding="utf-8")
        rc, out, err, timeout = run_proc(
            java_run_cmd("Main.java"), d, JAVA_TIMEOUT)
        if timeout:
            return {"error": f"Tempo scaduto: probabilmente un ciclo infinito.", "tests": [], "stdout": ""}
        results = {}
        stdout = []
        for line in out.splitlines():
            if line.startswith("##T##"):
                idx, ok, got = line[5:].split("|", 2)
                results[int(idx)] = (ok == "true", got.replace("\\n", "\n").replace("\\\\", "\\"))
            elif line != "##END##":
                stdout.append(line)
        if not results and rc != 0:
            e = clean_err(err, d)
            parts = [p.strip() for p in re.split(r"(?=Main\.java:\d+: )", e) if p.strip().startswith("Main.java:")]
            user, test = [], []
            for p in parts:
                p = re.sub(r"\n\d+ errors?\s*$|\nerror: compilation failed\s*$", "", p).strip()
                p = re.sub(r"\n\d+ errors?$", "", p).replace("\nerror: compilation failed", "").strip()
                n = int(re.match(r"Main\.java:(\d+)", p).group(1))
                if n > head:
                    user.append(re.sub(r"^Main\.java:\d+: error:", f"Riga {n - head}: errore:", p))
                else:
                    test.append(p)
            if user:
                e = "\n\n".join(user[:4])
            elif test:
                m = re.search(r"symbol:\s+method (\w+)", test[0])
                e = ("I test non trovano il metodo " + (f"«{m.group(1)}»" if m else "richiesto")
                     + " con i parametri previsti: non cambiare nome, parametri o tipo di ritorno della firma data.")
            return {"error": e or "Compilazione fallita.", "tests": [], "stdout": "\n".join(stdout)}
        res = []
        for i, t in enumerate(tests):
            ok, got = results.get(i, (False, "ERR:test non eseguito"))
            r = {"desc": t.get("desc", ""), "call": t["call"], "expected": t["expected"], "ok": ok}
            if got.startswith("ERR:"):
                r["error"] = got[4:]
            else:
                r["got"] = got
            res.append(r)
        return {"error": None, "tests": res, "stdout": "\n".join(stdout)[:4000]}


def run_program(lang, code):
    if lang == "sql":
        r = run_sql("", code)
        return {"ok": not r.get("error"), "stdout": script_output(r), "error": r.get("error") and (r["error"] + ("\nNell'istruzione: " + r["where"] if r.get("where") else ""))}
    with tempfile.TemporaryDirectory(prefix="ricalco_") as d:
        if lang == "python":
            Path(d, "soluzione.py").write_text(code, encoding="utf-8")
            rc, out, err, timeout = run_proc([sys.executable, "-I", "soluzione.py"], d, RUN_TIMEOUT)
        else:
            info = java_info()
            if not info["exe"]:
                return {"ok": False, "stdout": "", "error": "Java non trovato. Installa un JDK 17 o più recente."}
            if info.get("old") or info.get("jre"):
                return {"ok": False, "stdout": "", "error": JAVA_MISSING_MSG()}
            m = re.search(r"public\s+(?:final\s+)?class\s+(\w+)", code)
            name = (m.group(1) if m else "Main") + ".java"
            Path(d, name).write_text(code, encoding="utf-8")
            rc, out, err, timeout = run_proc(java_run_cmd(name), d, JAVA_TIMEOUT)
        if timeout:
            return {"ok": False, "stdout": out[:4000], "error": "Tempo scaduto: probabilmente un ciclo infinito."}
        e = clean_err(err, d)
        return {"ok": rc == 0, "stdout": out[:6000], "error": e[:3000] if rc != 0 else (e[:1000] or None)}


import builtins as _bi
_PY_BUILTINS = set(dir(_bi))


def adapt_names(lang, code, tests):
    """Se hai chiamato la funzione (o la classe) con un nome diverso da quello che usano i test, il tuo codice va bene lo stesso:
    collega il tuo nome a quello atteso. Restituisce (codice adattato, note per te)."""
    tests = norm_tests(tests)
    notes = []
    if lang == "python":
        called = set()
        for t in tests:
            called |= set(re.findall(r"(?<![\w.])([A-Za-z_]\w*)\s*\(", t["call"]))
        called -= _PY_BUILTINS
        for kind, pat in (("funzione", r"^def\s+(\w+)\s*\("), ("classe", r"^class\s+(\w+)\b")):
            mine = re.findall(pat, code, re.M)
            exp_names = [c for c in called if (c[:1].isupper() if kind == "classe" else not c[:1].isupper())]
            missing = [c for c in exp_names if c not in mine]
            extra = [m for m in mine if m not in called and not m.startswith("_")]
            if len(missing) == 1 and len(extra) == 1:
                code += f"\n\n{missing[0]} = {extra[0]}  # collegato da Ricalco: i test usano questo nome\n"
                notes.append(f"I test chiamano «{missing[0]}», tu l'hai chiamata «{extra[0]}»: va bene lo stesso, li ho collegati.")
        return code, notes
    # Java: i test usano Classe.metodo(...)
    calls = set()
    for t in tests:
        calls |= set(re.findall(r"\b([A-Z]\w*)\.(\w+)\s*\(", t["call"]))
    classes = re.findall(r"\b(?:class|record)\s+([A-Z]\w*)", code)
    for cls in {c for c, _ in calls}:
        if cls not in classes and len(classes) == 1:
            code = re.sub(rf"\b{re.escape(classes[0])}\b", cls, code)
            notes.append(f"I test usano la classe «{cls}», tu l'hai chiamata «{classes[0]}»: l'ho rinominata per farli girare.")
            classes = [cls]
    mine = [m for m in re.findall(r"\bstatic\s+(?:final\s+)?[\w<>\[\],.? ]+?\s+(\w+)\s*\(", code) if m != "main"]
    wanted = {m for _, m in calls}
    missing = [m for m in wanted if m not in mine]
    extra = [m for m in dict.fromkeys(mine) if m not in wanted]
    if len(missing) == 1 and len(extra) == 1:
        code = re.sub(rf"\b{re.escape(extra[0])}\s*\(", missing[0] + "(", code)
        notes.append(f"I test chiamano «{missing[0]}», tu hai scritto «{extra[0]}»: l'ho rinominato per farli girare.")
    return code, notes


def review_schema():
    S, A = {"type": "string"}, {"type": "array", "items": {"type": "string"}}
    return {"type": "object", "properties": {
        "funziona": {"type": "boolean"}, "giudizio": S, "bene": A, "da_migliorare": A, "versione_migliore": S, "perche_migliore": S},
        "required": ["funziona", "giudizio", "bene", "da_migliorare", "versione_migliore", "perche_migliore"]}


def code_review(lang, task, code, reference="", outcome=""):
    """Revisione del codice scritto da te: cosa va, cosa non va e una versione migliore (che parte dalla tua, non da quella di riferimento)."""
    if not code.strip():
        raise ValueError("Scrivi prima del codice.")
    prompt = (f"Linguaggio: {LANGNAME[lang]}.\nConsegna: {task}\n\nCodice dello studente:\n```\n{code}\n```\n"
              + (f"\nEsito dell'esecuzione: {outcome}\n" if outcome else "")
              + (f"\nUna soluzione di riferimento (solo per tuo confronto, lo studente può aver seguito un'altra strada valida):\n```\n{reference}\n```\n" if reference else "")
              + "\nFai una revisione da collega esperto, in italiano, dando del tu. Una strada diversa da quella di riferimento va bene se è corretta: "
                "giudica il codice dello studente, non quanto somiglia al riferimento. Nomi diversi vanno bene se sono chiari.\n"
                "\"funziona\": true se risolve la consegna (anche con nomi o metodo diversi). \"giudizio\": 1-2 frasi. "
                "\"bene\": 1-3 cose fatte bene. \"da_migliorare\": 0-4 punti concreti (errori, casi limite, leggibilità, complessità), "
                "ognuno con la riga o il nome a cui si riferisce. \"versione_migliore\": il codice dello studente corretto e migliorato, completo, "
                "mantenendo la sua impostazione e i suoi nomi quando sono buoni. \"perche_migliore\": 1-3 frasi su cosa cambia e perché.")
    d = llm_json([{"role": "system", "content": SYS_GEN}, {"role": "user", "content": prompt}], review_schema(), temperature=0.2)
    return {"ok": bool(d.get("funziona")), "verdict": str(d.get("giudizio") or ""), "good": [str(x) for x in d.get("bene") or []][:3],
            "fix": [str(x) for x in d.get("da_migliorare") or []][:4], "better": norm_code(d.get("versione_migliore")), "why": str(d.get("perche_migliore") or "")}


def run_tests(lang, code, tests):
    tests = norm_tests(tests)
    res = run_python_tests(code, tests) if lang == "python" else run_java_tests(code, tests)
    res["all_ok"] = not res.get("error") and bool(res.get("tests")) and all(t["ok"] for t in res["tests"])
    return res


def failing_summary(res, limit=4):
    if res.get("error"):
        return res["error"][:800]
    lines = []
    for t in res.get("tests", []):
        if not t["ok"] and not t.get("expected"):
            lines.append(f"- test {t['call']} fallito: {t.get('error', '?')}")
        elif not t["ok"]:
            lines.append(f"- {t['call']} doveva dare {t['expected']} ma ha dato "
                         + (t.get("got") or "errore: " + t.get("error", "?")))
    return "\n".join(lines[:limit])


# ---------------------------------------------------------------- generazione
SYS_GEN = ("Sei un insegnante di programmazione che prepara materiale per studenti junior italiani. "
           "Scrivi codice corretto, semplice e idiomatico, con nomi di variabili e funzioni in italiano senza accenti. "
           "Tutti i testi sono in italiano. Rispondi solo con JSON valido.")

STR = {"type": "string"}
LESSON_SCHEMA = {
    "type": "object",
    "properties": {
        "titolo": STR, "obiettivo": STR,
        "concetti": {"type": "array", "items": STR},
        "blocchi": {"type": "array", "items": {
            "type": "object",
            "properties": {"codice": STR, "domanda": STR, "opzioni": {"type": "array", "items": STR},
                           "corretta": {"type": "integer"}, "perche": STR, "spiegazione": STR},
            "required": ["codice", "domanda", "opzioni", "corretta", "perche", "spiegazione"]}}},
    "required": ["titolo", "obiettivo", "concetti", "blocchi"]}


def lang_rules_program(lang):
    if lang == "sql":
        return ("Il codice è uno script SQLite completo: crea le tabelle con CREATE TABLE, inserisce pochi dati realistici con INSERT, "
                "poi esegue le query che mostrano i concetti, ciascuna preceduta da un commento -- che dice cosa fa. Solo SQL supportato da SQLite.")
    if lang == "python":
        return ("Il codice è uno script Python 3 completo ed eseguibile: definisce funzioni o classi e in fondo le usa "
                "con alcuni print che mostrano i risultati. Niente input(), file esterni, librerie esterne o numeri casuali.")
    return ("Il codice è un programma Java completo con una sola classe `public class Main` che contiene "
            "`public static void main(String[] args)` e, se servono, altri metodi static o classi annidate static. "
            "Il main usa il codice e stampa i risultati con System.out.println. Solo librerie standard "
            "(gli import vanno all'inizio). Niente Scanner, file o numeri casuali.")


def lesson_prompt(req, lang, level):
    size = ("principiante: concetti base, 15-35 righe in tutto" if level == "base"
            else "intermedio: 30-60 righe, gestisci anche i casi limite")
    return f"""Lo studente vuole imparare: «{req}»
Linguaggio: {LANGNAME[lang]}. Livello: {size}.

Prepara una lezione. {lang_rules_program(lang)}

Dividi il programma in 4-7 blocchi CONSECUTIVI: concatenandoli in ordine si ottiene il programma completo, con l'indentazione corretta. Ogni blocco è un'idea (una funzione, un controllo, un ciclo, la parte che stampa...).
Per ogni blocco:
- "codice": le righe del blocco.
- "domanda": una domanda di RAGIONAMENTO che lo studente affronta PRIMA di vedere il blocco. Deve farlo pensare alla logica: cosa serve fare, cosa succede in un caso limite, quale scelta è giusta e perché. Non chiedere sintassi a memoria e non mostrare il codice del blocco.
- "opzioni": 4 risposte brevi, una sola giusta, le altre plausibili ma sbagliate.
- "corretta": indice (0-3) della risposta giusta; non metterla sempre nella stessa posizione.
- "perche": 1-2 frasi che spiegano perché la risposta è giusta.
- "spiegazione": 2-4 frasi sul PERCHÉ il blocco è scritto così: il concetto chiave, cosa succederebbe senza, l'errore tipico di chi inizia.
"titolo": massimo 6 parole. "obiettivo": una frase su cosa saprà fare lo studente. "concetti": 2-5 concetti chiave in poche parole."""


def build_lesson(data):
    blocks = []
    for b in data.get("blocchi") or []:
        if not isinstance(b, dict):
            continue
        code = norm_code(b.get("codice"))
        if not code.strip():
            continue
        opts = [str(o).strip() for o in (b.get("opzioni") or []) if str(o).strip()]
        c = b.get("corretta")
        q = None
        if str(b.get("domanda") or "").strip() and len(opts) >= 2 and isinstance(c, int) and 0 <= c < len(opts):
            q = {"q": str(b["domanda"]), "options": opts, "correct": c, "why": str(b.get("perche") or "")}
        blocks.append({"code": code, "question": q, "explain": str(b.get("spiegazione") or "")})
    return blocks


# Errori che Qwen ripete spesso: oltre al messaggio gli diciamo la causa e come si corregge.
ERROR_HINTS = [
    (r"stream has already been operated upon or closed",
     "CAUSA: uno stream Java si può usare UNA SOLA VOLTA. Non salvare mai uno stream in una variabile (Stream<...> s = lista.stream()) "
     "per riusarlo: per ogni operazione crea un nuovo stream partendo dalla collezione, per esempio lista.stream().filter(...) "
     "e poi di nuovo lista.stream().anyMatch(...). Se ti serve riusare dei dati, salva il RISULTATO in una List con .toList()."),
    (r"ConcurrentModificationException",
     "CAUSA: stai modificando una collezione mentre la scorri con for-each. Usa un Iterator con remove(), removeIf, oppure una copia."),
    (r"UnsupportedOperationException",
     "CAUSA: List.of, Map.of, Arrays.asList e .toList() restituiscono collezioni immutabili. Se devi aggiungere o togliere elementi "
     "usa new ArrayList<>(...) o new HashMap<>(...)."),
    (r"NullPointerException",
     "CAUSA: usi un valore null. Inizializza le variabili e controlla i get() delle mappe (usa getOrDefault)."),
    (r"(IndexOutOfBounds|ArrayIndexOutOfBounds)",
     "CAUSA: un indice fuori dai limiti. Controlla i cicli: l'ultimo indice valido è length-1 / size()-1."),
    (r"NoSuchElementException",
     "CAUSA: get() su un Optional vuoto o next() su un iteratore finito. Usa orElse/orElseThrow con un controllo, o hasNext()."),
    (r"IllegalStateException: Duplicate key",
     "CAUSA: Collectors.toMap con chiavi ripetute. Passa una funzione di unione come terzo argomento, per esempio (a, b) -> a + b."),
    (r"(KeyError|IndexError|TypeError|AttributeError|NameError)",
     "Leggi la riga indicata nel traceback e correggi la causa: la soluzione deve girare senza eccezioni dall'inizio alla fine."),
]


def error_hint(err):
    hints = [h for pat, h in ERROR_HINTS if re.search(pat, err or "")]
    return ("\n" + "\n".join(hints[:2])) if hints else ""


def generate_lesson(req, lang, level, extra="", run_check=True):
    msgs = [{"role": "system", "content": SYS_GEN}, {"role": "user", "content": lesson_prompt(req, lang, level) + ("\n\n" + extra if extra else "")}]
    last = None
    for attempt in range(3):
        data = llm_json(msgs, LESSON_SCHEMA, temperature=0.35 if attempt == 0 else 0.2)
        blocks = build_lesson(data)
        if len(blocks) < 2:
            feedback = "Servono almeno 3 blocchi con codice. Restituisci di nuovo tutto il JSON."
        else:
            code = "\n".join(b["code"] for b in blocks)
            run = run_program(lang, code) if run_check else {"ok": True, "stdout": "", "error": None, "skipped": True}
            last = (data, blocks, run)
            if run["ok"]:
                break
            feedback = ("Eseguendo il programma ottenuto concatenando i blocchi c'è questo errore:\n"
                        + (run["error"] or "")[:1200] + error_hint(run["error"])
                        + "\nCorreggi il codice (attenzione all'indentazione tra un blocco e l'altro) "
                          "e restituisci di nuovo tutto il JSON.")
        msgs = msgs[:2] + [{"role": "assistant", "content": json.dumps(data, ensure_ascii=False)},
                           {"role": "user", "content": feedback}]
    if not last:
        raise LLMError("Il modello non è riuscito a preparare la lezione. Riprova o riformula la richiesta.")
    data, blocks, run = last
    now = time.time()
    return {
        "id": "l" + uuid.uuid4().hex[:10], "kind": "lesson", "request": req, "lang": lang, "level": level,
        "title": str(data.get("titolo") or req)[:80], "goal": str(data.get("obiettivo") or ""),
        "concepts": [str(c) for c in (data.get("concetti") or [])][:6],
        "blocks": blocks, "verified": None if run.get("skipped") else run["ok"], "output": run["stdout"] if run["ok"] else "",
        "runError": None if run["ok"] else run["error"],
        "progress": {"block": 0, "phase": "ragiona", "done": False, "stats": {}},
        "exercises": [], "created": now, "updated": now}


TEST_ITEMS = {"type": "array", "items": {"type": "object", "properties": {
    "descrizione": STR, "chiamata": STR, "atteso": STR}, "required": ["chiamata", "atteso"]}}

EX_TYPES = {
    "logica": "Problema di logica",
    "orale": "Domanda da colloquio",
    "quiz": "Domanda",
    "riempi": "Completa gli spazi",
    "predici": "Prevedi l'output",
    "riordina": "Riordina le righe",
    "completa": "Completa il codice",
    "bug": "Trova il bug",
    "zero": "Scrivi da zero",
}
DIFF_TEXT = {
    "facile": "FACILE: un solo concetto, soluzione di 3-8 righe, nessun caso limite complicato",
    "medio": "MEDIA: uno o due concetti, soluzione di 6-15 righe, almeno un caso limite (vuoto, zero, negativo...)",
    "difficile": "DIFFICILE: combina più concetti, soluzione di 12-30 righe, più casi limite",
}
ARR = {"type": "array", "items": STR}
LOGIC_DIFF = {"facile": "FACILE: si risolve con uno o due passaggi di ragionamento",
              "medio": "MEDIA: servono 3-4 passaggi o un piccolo conteggio",
              "difficile": "DIFFICILE: bisogna combinare più vincoli o trovare un'idea non ovvia"}


def ex_schema(kind, mode="tests"):
    if kind == "predici":
        props = {"titolo": STR, "codice": STR, "spiegazione": STR}
    elif kind == "logica":
        props = {"titolo": STR, "problema": STR, "opzioni": ARR, "risposta": STR, "spiegazione": STR, "codice_verifica": STR}
    elif kind == "orale":
        props = {"titolo": STR, "domanda": STR, "punti_chiave": ARR, "risposta_modello": STR, "domanda_approfondimento": STR}
    elif kind == "quiz":
        props = {"titolo": STR, "domanda": STR, "codice": STR, "opzioni": ARR, "corretta": {"type": "integer"}, "spiegazione": STR}
    elif kind == "riempi":
        props = {"titolo": STR, "consegna": STR, "codice": STR, "risposte": ARR, "spiegazione": STR}
    else:
        props = {"titolo": STR, "consegna": STR, "soluzione": STR}
        if mode == "tests":
            props["test"] = TEST_ITEMS
        if mode == "spring":
            props["test_junit"] = STR
        if mode == "review":
            props["criteri"] = ARR
        props["suggerimenti"] = ARR
        if kind in ("completa", "zero"):
            props["codice_iniziale"] = STR
        if kind == "bug":
            props["codice_con_bug"] = STR
            props["spiegazione_bug"] = STR
    return {"type": "object", "properties": props, "required": list(props)}


def program_rule(lang):
    if lang == "python":
        return "script Python 3 completo ed eseguibile"
    return "programma Java completo con `public class Main` e `public static void main(String[] args)`"


def lang_rules_tests(lang):
    if lang == "python":
        return ("La soluzione definisce funzioni (ed eventualmente classi) Python 3 che RESTITUISCONO un valore: niente input(), niente print obbligatori, "
                "niente eccezioni non gestite. Ogni test ha \"chiamata\": un'espressione Python come `conta_vocali(\"ciao\")` "
                "o `Punto(3, 4).distanza()`, e \"atteso\": il valore atteso come letterale Python, per esempio `2`, `\"abc\"`, `[1, 2]`, `True`, `None`.")
    return ("La soluzione è codice Java SENZA main e senza la parola public davanti alle classi: una `class Soluzione { ... }` con metodi `static` "
            "che RESTITUISCONO un valore (niente void, niente Scanner), più eventuali altre classi o interfacce (anche loro senza public). "
            "Eventuali import (es. `import java.util.*;`) vanno in cima. Ogni test ha \"chiamata\": un'espressione Java come "
            "`Soluzione.contaVocali(\"ciao\")` o `new Punto(3, 4).getX()`, e \"atteso\": il valore atteso come espressione Java dello stesso tipo, "
            "per esempio `2`, `\"abc\"`, `true`, `new int[]{1, 2}`, `List.of(1, 2)`, `2.5`.")


def exercise_prompt(kind, lang, diff, topic, avoid, mode="tests"):
    avoid_txt = ("\nNon ripetere questi esercizi già presenti: " + "; ".join(avoid[-12:]) + ".") if avoid else ""
    if kind == "logica":
        return (f"Tema: {topic}\nDifficoltà {LOGIC_DIFF[diff]}.{avoid_txt}\n\n"
                "Scrivi UN problema di logica originale, in italiano, con una sola risposta corretta e breve (un numero, un nome, una parola). "
                "\"problema\": testo completo e autosufficiente, senza ambiguità. \"opzioni\": 4 risposte brevi e plausibili, una è quella giusta. "
                "\"risposta\": la risposta corretta, scritta ESATTAMENTE come nella sua opzione. \"spiegazione\": il ragionamento passo per passo. "
                "\"codice_verifica\": uno script Python 3 che risolve il problema da zero, in modo indipendente (calcolo diretto o forza bruta, "
                "per esempio con itertools), e stampa SOLO la risposta, scritta esattamente come in \"risposta\". Non scrivere la risposta già pronta "
                "dentro il print: il codice deve calcolarla. \"titolo\": massimo 4 parole.")
    if kind == "orale":
        return (f"Contesto: {topic}.{avoid_txt}\n\n"
                "Prepara UNA domanda da colloquio tecnico, come la farebbe un selezionatore, su un argomento diverso da quelli già presenti. "
                "\"domanda\": chiara e concreta. \"punti_chiave\": 3-6 punti che una buona risposta deve toccare. "
                "\"risposta_modello\": la risposta ideale di un candidato preparato, 60-150 parole, con nomi e frammenti di codice tra backtick. "
                "\"domanda_approfondimento\": la domanda successiva che farebbe il selezionatore. \"titolo\": massimo 4 parole.")
    head = f"Argomento: {topic}\nLinguaggio: {LANGNAME[lang]}. Difficoltà {DIFF_TEXT[diff]}.{avoid_txt}\n\n"
    prog = program_rule(lang)
    if kind == "predici":
        return head + (f"Scrivi un esercizio «prevedi l'output»: un breve {prog} (4-18 righe) che lo studente deve leggere "
                       "per prevedere ESATTAMENTE cosa stampa. Deve stampare da 1 a 6 righe, senza input e senza numeri casuali. "
                       "Inserisci un dettaglio che richieda ragionamento (un ciclo, una condizione, un indice, un aggiornamento di variabile, una conversione). "
                       "In \"codice\" il programma completo. In \"spiegazione\" spiega passo per passo perché stampa quello. "
                       "\"titolo\": massimo 5 parole.")
    if kind == "quiz":
        return head + ("Scrivi una domanda a scelta multipla che verifica la COMPRENSIONE di un concetto (cosa succede, perché, quale scelta è giusta), "
                       f"non la memoria di un nome. Se serve, in \"codice\" metti un frammento di codice (al massimo 8 righe) a cui la domanda si riferisce, "
                       f"altrimenti una stringa vuota. Se la domanda chiede cosa stampa, il frammento deve essere un {prog} e una delle opzioni "
                       "deve essere ESATTAMENTE l'output. \"opzioni\": 4 risposte brevi, una sola giusta, le altre basate su errori tipici. "
                       "\"corretta\": indice 0-3 della giusta (varia la posizione). \"spiegazione\": 1-2 frasi. \"titolo\": massimo 5 parole.")
    if kind == "riempi":
        return head + (f"Scrivi un esercizio «completa gli spazi»: un {prog} di 3-14 righe che stampa qualcosa, in cui da 1 a 3 parti brevi "
                       "(una parola chiave, un operatore, un nome di metodo o di variabile, un valore) sono sostituite da ___ (tre trattini bassi). "
                       "\"risposte\": le parti mancanti, nell'ordine in cui compaiono. Inserendo le risposte il programma deve funzionare. "
                       "\"consegna\": in una frase, cosa deve stampare o fare il programma. \"spiegazione\": perché quelle risposte. "
                       "\"titolo\": massimo 5 parole.")
    if mode == "spring" and kind in ("completa", "bug", "zero", "riordina"):
        return head + spring_prompt(kind)
    if mode in ("review", "spring"):
        return head + review_prompt(kind, lang)
    hints = ("In \"suggerimenti\" 3 indizi progressivi, dal più vago al quasi-soluzione, senza mai scrivere il codice completo. "
             "\"titolo\": massimo 5 parole.")
    if mode == "output":
        common = (f"La soluzione è un {prog} che stampa il risultato (niente input, niente numeri casuali, da 1 a 10 righe di output). "
                  "I dati di partenza sono già scritti nel codice. In \"consegna\" spiega cosa deve fare il programma e cosa deve stampare. " + hints)
        if kind == "zero":
            extra = ("Esercizio da risolvere da zero. In \"codice_iniziale\" metti solo il punto di partenza: i dati già assegnati alle variabili "
                     + ("e un commento `# TODO`." if lang == "python" else "dentro il main e un commento `// TODO`, con la classe Main completa."))
        elif kind == "completa":
            extra = ("Esercizio «completa il codice». In \"codice_iniziale\" metti la soluzione con 1-3 parti importanti sostituite da un commento "
                     + ("`# TODO: ...`" if lang == "python" else "`// TODO: ...`") + " in modo che il programma giri ma NON stampi il risultato giusto. "
                     "Il commento dice cosa manca, non come farlo.")
        elif kind == "bug":
            extra = ("Esercizio «trova il bug». In \"codice_con_bug\" metti la soluzione con UN solo errore logico realistico "
                     "(off-by-one, condizione invertita, variabile non aggiornata, operatore sbagliato...) che cambia l'output, senza errori di sintassi. "
                     "La \"consegna\" descrive cosa DOVREBBE stampare il programma, senza dire dov'è il bug. In \"spiegazione_bug\" spiega il bug.")
        else:
            extra = ("Esercizio «riordina le righe»: la soluzione deve avere 5-14 righe non vuote, una istruzione per riga, senza righe vuote né commenti: "
                     "lo studente riceverà le righe mescolate e dovrà rimetterle in ordine.")
        return head + extra + "\n" + common
    common = lang_rules_tests(lang) + " Scrivi 3-6 test. In \"consegna\" spiega cosa deve fare il codice, con un esempio. " + hints
    if kind == "zero":
        extra = ("Esercizio da risolvere da zero. In \"codice_iniziale\" metti SOLO la firma della funzione/metodo con un commento TODO "
                 + ("e `pass` come corpo." if lang == "python" else "dentro `class Soluzione { }` e un return provvisorio (es. `return 0;`, `return \"\";`, `return null;`)."))
    elif kind == "completa":
        extra = ("Esercizio «completa il codice». In \"codice_iniziale\" metti la soluzione con 1-3 parti importanti sostituite da un commento "
                 + ("`# TODO: ...` seguito da `pass` dove serve," if lang == "python" else "`// TODO: ...` (lascia un return provvisorio se serve),")
                 + " in modo che il codice compili ma NON superi i test. Il commento dice cosa manca, non come farlo.")
    elif kind == "bug":
        extra = ("Esercizio «trova il bug». In \"codice_con_bug\" metti la soluzione con UN solo errore logico realistico "
                 "(off-by-one, condizione invertita, variabile non aggiornata, return nel posto sbagliato...) che fa fallire almeno un test "
                 "senza errori di sintassi. La \"consegna\" descrive cosa DOVREBBE fare il codice, senza dire dov'è il bug. "
                 "In \"spiegazione_bug\" spiega il bug.")
    else:
        extra = ("Esercizio «riordina le righe»: la soluzione deve avere 5-12 righe non vuote, una istruzione per riga, "
                 "senza righe vuote né commenti: lo studente riceverà le righe mescolate e dovrà rimetterle in ordine.")
    return head + extra + "\n" + common


def spring_prompt(kind):
    base = ("Questo esercizio viene ESEGUITO DAVVERO con Maven: Spring Boot 3 (Java 17, import jakarta.*), JUnit 5, database H2 in memoria. "
            "La classe @SpringBootApplication esiste già (si chiama App, package com.ricalco.app): NON scriverla e NON scrivere la riga package. "
            "In \"soluzione\" metti tutte le classi necessarie (entity, repository, service, controller...) con gli import completi; "
            "più classi possono stare nello stesso testo, una dopo l'altra. "
            "In \"test_junit\" una classe `class EsercizioTest` JUnit 5 con 2-4 metodi @Test e import completi: per le API usa @SpringBootTest "
            "e @AutoConfigureMockMvc con MockMvc (status(), jsonPath(), content()); per repository e service @SpringBootTest con @Autowired; "
            "per codice senza Spring bastano test JUnit semplici. Nomi dei metodi di test descrittivi in camelCase italiano. "
            "I test devono passare con la soluzione. Mantieni il codice breve e concentrato sul concetto. ")
    hints = ("In \"suggerimenti\" 3 indizi progressivi, senza scrivere il codice completo. \"titolo\": massimo 5 parole. "
             "\"consegna\": cosa deve fare il codice, citando endpoint, classi e metodi che i test usano.")
    if kind == "zero":
        extra = ("Esercizio da scrivere da zero: in \"codice_iniziale\" lo scheletro con i nomi delle classi e dei metodi che i test usano, "
                 "un commento TODO e corpi provvisori (return null; o simili) in modo che compili ma i test falliscano.")
    elif kind == "completa":
        extra = ("Esercizio «completa il codice»: in \"codice_iniziale\" la soluzione con 1-3 parti importanti sostituite da un commento TODO "
                 "(lascia return provvisori), in modo che compili ma i test falliscano.")
    else:
        extra = ("Esercizio «trova il bug»: in \"codice_con_bug\" la soluzione con UN errore realistico che compila ma fa fallire almeno un test "
                 "(annotazione sbagliata, mapping HTTP sbagliato, query derivata con nome errato, condizione invertita...). "
                 "La consegna dice cosa DOVREBBE fare il codice. In \"spiegazione_bug\" spiega il bug.")
    return base + extra + " " + hints


def review_prompt(kind, lang):
    base = ("Questo codice NON verrà eseguito (usa framework o librerie esterne): deve essere corretto, realistico e completo di import "
            "e annotazioni, come in un progetto vero. Mantienilo breve e concentrato sul concetto. ")
    hints = ("In \"suggerimenti\" 3 indizi progressivi, dal più vago al quasi-soluzione, senza scrivere il codice completo. "
             "In \"criteri\" 2-5 controlli concreti che una soluzione corretta deve rispettare (per esempio «usa @PathVariable per l'id»). "
             "\"titolo\": massimo 5 parole.")
    if kind == "riempi":
        return base + ("Esercizio «completa gli spazi»: in \"codice\" un frammento di 4-16 righe in cui da 1 a 3 parti brevi "
                       "(un'annotazione, un nome di metodo, un tipo, una parola chiave) sono sostituite da ___ (tre trattini bassi). "
                       "\"risposte\": le parti mancanti in ordine. \"consegna\": cosa fa il codice. \"spiegazione\": perché quelle risposte. "
                       "\"titolo\": massimo 5 parole.")
    if kind == "zero":
        extra = "Esercizio da scrivere da zero: in \"codice_iniziale\" metti solo lo scheletro (classe, firma, import) con un commento TODO."
    elif kind == "completa":
        extra = "Esercizio «completa il codice»: in \"codice_iniziale\" la soluzione con 1-3 parti importanti sostituite da un commento TODO che dice cosa manca."
    elif kind == "bug":
        extra = ("Esercizio «trova il bug»: in \"codice_con_bug\" la soluzione con UN errore realistico (annotazione sbagliata o mancante, "
                 "metodo HTTP sbagliato, query errata, dipendenza non iniettata...). La consegna dice cosa DOVREBBE fare il codice. "
                 "In \"spiegazione_bug\" spiega il bug.")
    else:
        extra = "Esercizio «riordina le righe»: la soluzione ha 5-14 righe non vuote, senza righe vuote né commenti; lo studente le rimetterà in ordine."
    return base + extra + " In \"soluzione\" il codice di riferimento completo. In \"consegna\" cosa deve fare il codice. " + hints


def norm_out(s):
    return "\n".join(l.rstrip() for l in str(s or "").replace("\r", "").split("\n")).strip("\n")


def simple(x):
    """Normalizza una risposta breve: minuscole, spazi, virgola decimale, punto finale."""
    x = str(x).strip().strip("`\"'").lower().rstrip(".")
    x = re.sub(r"\s+", " ", x)
    m = re.fullmatch(r"(-?\d+)[.,](\d+)(.*)", x)
    if m:
        dec = m.group(2).rstrip("0")
        x = m.group(1) + ("," + dec if dec else "") + m.group(3)
    return x


def fill_blanks(code, answers):
    for a in answers:
        code = code.replace("___", str(a), 1)
    return code


def shuffled_lines(sol):
    lines = [l for l in sol.split("\n") if l.strip()]
    order = list(range(len(lines)))
    if len(lines) > 1:
        while order == sorted(order):
            random.shuffle(order)
    return lines, [lines[i] for i in order]


def generate_exercise(kind, lang, diff, topic, avoid, mode="tests", attempts=4, runner=""):
    if kind not in EX_TYPES or diff not in DIFF_TEXT or lang not in LANGNAME:
        raise ValueError("parametri non validi")
    if lang == "sql" and kind not in ("logica", "orale"):
        return generate_sql_exercise(kind, diff, topic, avoid, attempts)
    msgs = [{"role": "system", "content": SYS_GEN},
            {"role": "user", "content": exercise_prompt(kind, lang, diff, topic, avoid, mode)}]
    schema = ex_schema(kind, mode)
    base = {"id": "e" + uuid.uuid4().hex[:10], "type": kind, "difficulty": diff, "lang": lang}
    RUN = RUNNERS.get(runner) or SPRING
    if mode == "spring" and runner:
        base["runner"] = runner
    for attempt in range(attempts):
        data = llm_json(msgs, schema, temperature=0.6 if attempt == 0 else 0.35)
        problem, ex = None, None
        title = str(data.get("titolo") or EX_TYPES[kind])[:70]
        if kind == "logica":
            opts = [str(o).strip() for o in (data.get("opzioni") or []) if str(o).strip()][:5]
            ans = str(data.get("risposta") or "").strip()
            code = norm_code(data.get("codice_verifica"))
            low = [simple(o) for o in opts]
            if not data.get("problema") or len(opts) < 3 or not ans or not code:
                problem = "Servono problema, 4 opzioni, risposta e codice_verifica."
            elif simple(ans) not in low:
                problem = "La risposta deve essere scritta esattamente come una delle opzioni."
            elif len(set(low)) < len(low):
                problem = "Le opzioni devono essere tutte diverse."
            elif re.fullmatch(r"\s*print\(\s*[\"'].*[\"']\s*\)\s*", code, re.S):
                problem = "Il codice_verifica deve CALCOLARE la risposta, non stamparla già pronta."
            else:
                run = run_program("python", code)
                out = norm_out(run.get("stdout")).split("\n")[-1] if run.get("stdout") else ""
                if not run["ok"]:
                    problem = "Il codice_verifica va in errore:\n" + (run.get("error") or "")[:700]
                elif simple(out) != simple(ans):
                    problem = (f"Il codice_verifica stampa «{out}» ma la risposta indicata è «{ans}». Controlla il problema: "
                               "se il codice ha ragione, correggi risposta e opzioni; se il problema è ambiguo, riscrivilo.")
                else:
                    ex = dict(base, title=title, question=str(data["problema"]), options=opts, correct=low.index(simple(ans)),
                              answer=ans, explain=str(data.get("spiegazione") or ""), verify=code)
        elif kind == "orale":
            pts = [str(x).strip() for x in (data.get("punti_chiave") or []) if str(x).strip()]
            if not data.get("domanda") or len(pts) < 2 or not data.get("risposta_modello"):
                problem = "Servono domanda, almeno 3 punti chiave e la risposta modello."
            else:
                ex = dict(base, title=title, question=str(data["domanda"]), points=pts[:6], model=str(data["risposta_modello"]),
                          followup=str(data.get("domanda_approfondimento") or ""))
        elif kind == "predici":
            code = norm_code(data.get("codice"))
            run = run_program(lang, code) if code else {"ok": False, "error": "codice vuoto", "stdout": ""}
            out = norm_out(run.get("stdout"))
            if not run["ok"]:
                problem = "Il programma non funziona:\n" + (run.get("error") or "")[:1000] + error_hint(run.get("error"))
            elif not out:
                problem = "Il programma non stampa nulla: deve stampare da 1 a 6 righe."
            elif out.count("\n") > 11:
                problem = "Il programma stampa troppe righe: al massimo 6."
            else:
                ex = dict(base, title=title, code=code, output=out, explain=str(data.get("spiegazione") or ""))
        elif kind == "quiz":
            opts = [str(o).strip() for o in (data.get("opzioni") or []) if str(o).strip()][:5]
            c = data.get("corretta")
            code = norm_code(data.get("codice"))
            q = str(data.get("domanda") or "").strip()
            if not q or len(opts) < 3 or not isinstance(c, int) or not 0 <= c < len(opts):
                problem = "Servono una domanda, 4 opzioni e l'indice della risposta corretta."
            elif len(set(o.lower() for o in opts)) < len(opts):
                problem = "Le opzioni devono essere tutte diverse."
            else:
                if code and mode not in ("review", "spring") and re.search(r"stamp|output|print", q, re.I):
                    run = run_program(lang, code)
                    out = norm_out(run.get("stdout"))
                    match = [i for i, o in enumerate(opts) if norm_out(o.strip("`")) == out]
                    if run["ok"] and out and match:
                        c = match[0]          # la risposta giusta è quella che il programma stampa davvero
                    elif run["ok"] and out:
                        problem = f"Il programma stampa:\n{out}\nma nessuna opzione è uguale a questo output. Una opzione deve esserlo esattamente."
                    else:
                        problem = "La domanda chiede l'output ma il codice non è un programma eseguibile:\n" + (run.get("error") or "")[:600]
                if not problem:
                    ex = dict(base, title=title, question=q, code=code, options=opts, correct=c, explain=str(data.get("spiegazione") or ""))
        elif kind == "riempi":
            code = norm_code(data.get("codice"))
            ans = [str(a).strip().strip("`") for a in (data.get("risposte") or []) if str(a).strip()]
            n = code.count("___")
            if not 1 <= n <= 3 or n != len(ans):
                problem = f"Il codice deve avere da 1 a 3 spazi ___ e lo stesso numero di risposte (ora: {n} spazi, {len(ans)} risposte)."
            elif mode in ("review", "spring"):
                ex = dict(base, title=title, statement=str(data.get("consegna") or ""), code=code, answers=ans,
                          output="", check="review", explain=str(data.get("spiegazione") or ""))
            else:
                run = run_program(lang, fill_blanks(code, ans))
                out = norm_out(run.get("stdout"))
                if not run["ok"] or not out:
                    problem = "Con le risposte inserite il programma non funziona o non stampa nulla:\n" + (run.get("error") or "")[:800]
                else:
                    ex = dict(base, title=title, statement=str(data.get("consegna") or ""), code=code, answers=ans,
                              output=out, explain=str(data.get("spiegazione") or ""))
        else:
            sol = norm_code(data.get("soluzione"))
            hints = [str(h) for h in (data.get("suggerimenti") or []) if str(h).strip()][:4]
            ex = dict(base, title=title, statement=str(data.get("consegna") or ""), solution=sol, hints=hints, check=mode)
            if not sol:
                problem = "Manca la soluzione."
            elif mode == "spring":
                test = norm_code(data.get("test_junit"))
                ex["check"], ex["tests_java"] = "spring", test
                if "@Test" not in test:
                    problem = "Manca test_junit con almeno un metodo @Test."
                else:
                    r = RUN.run(sol, test)
                    if not r.get("all_ok"):
                        problem = "Eseguendo i test con la soluzione:\n" + failing_summary(r) + "\nCorreggi soluzione o test."
                if not problem:
                    start = norm_code(data.get("codice_con_bug" if kind == "bug" else "codice_iniziale"))
                    if not start:
                        problem = "Manca il codice di partenza."
                    else:
                        rs = RUN.run(start, test)
                        if rs.get("all_ok"):
                            problem = "Il codice di partenza supera già i test: deve farne fallire almeno uno."
                        elif kind == "bug" and rs.get("error"):
                            problem = "Il codice_con_bug non compila: il bug deve essere logico.\n" + rs["error"][:500]
                        ex["starter"] = start
                        if kind == "bug":
                            ex["bugExplain"] = str(data.get("spiegazione_bug") or "")
            elif mode == "review":
                ex["criteria"] = [str(c) for c in (data.get("criteri") or []) if str(c).strip()][:6]
                if kind in ("completa", "zero", "bug"):
                    start = norm_code(data.get("codice_con_bug" if kind == "bug" else "codice_iniziale"))
                    if not start or start == sol:
                        problem = "Il codice di partenza manca o è identico alla soluzione."
                    ex["starter"] = start
                    if kind == "bug":
                        ex["bugExplain"] = str(data.get("spiegazione_bug") or "")
            elif mode == "output":
                run = run_program(lang, sol)
                out = norm_out(run.get("stdout"))
                if not run["ok"] or not out:
                    problem = "La soluzione non funziona o non stampa nulla:\n" + (run.get("error") or "")[:800]
                elif out.count("\n") > 15:
                    problem = "La soluzione stampa troppe righe: al massimo 10."
                else:
                    ex["output"] = out

                    def same(code):
                        r = run_program(lang, code)
                        return r["ok"] and norm_out(r.get("stdout")) == out, r
                    if kind in ("completa", "zero"):
                        start = norm_code(data.get("codice_iniziale"))
                        if not start:
                            problem = "Manca codice_iniziale."
                        elif same(start)[0]:
                            problem = "Il codice_iniziale stampa già il risultato giusto: togli le parti da completare."
                        ex["starter"] = start
                    elif kind == "bug":
                        bug = norm_code(data.get("codice_con_bug"))
                        ok, rb = same(bug) if bug else (True, {})
                        if not bug or ok:
                            problem = "Il codice_con_bug stampa lo stesso risultato della soluzione: il bug deve cambiare l'output."
                        elif not rb.get("ok"):
                            problem = "Il codice_con_bug va in errore: il bug deve essere logico, non di sintassi.\n" + (rb.get("error") or "")[:500]
                        ex["starter"] = bug
                        ex["bugExplain"] = str(data.get("spiegazione_bug") or "")
            else:
                tests = norm_tests(data.get("test"))
                ex["tests"] = tests
                if len(tests) < 2:
                    problem = "Servono almeno 3 test."
                else:
                    r = run_tests(lang, sol, tests)
                    if not r["all_ok"]:
                        problem = "La soluzione non supera i test:\n" + failing_summary(r) + "\nCorreggi soluzione o test."
                if not problem and kind in ("completa", "zero"):
                    start = norm_code(data.get("codice_iniziale"))
                    if not start:
                        problem = "Manca codice_iniziale."
                    elif run_tests(lang, start, tests)["all_ok"]:
                        problem = "Il codice_iniziale supera già tutti i test: togli le parti da completare."
                    ex["starter"] = start
                elif not problem and kind == "bug":
                    bug = norm_code(data.get("codice_con_bug"))
                    rb = run_tests(lang, bug, tests) if bug else {"all_ok": True, "error": None}
                    if not bug or rb["all_ok"]:
                        problem = "Il codice_con_bug supera tutti i test: il bug deve far fallire almeno un test."
                    elif rb.get("error"):
                        problem = "Il codice_con_bug non compila o va in errore: il bug deve essere logico, non di sintassi.\n" + rb["error"][:500]
                    ex["starter"] = bug
                    ex["bugExplain"] = str(data.get("spiegazione_bug") or "")
            if not problem and kind == "riordina":
                lines, mixed = shuffled_lines(sol)
                if not 3 <= len(lines) <= 18:
                    problem = "La soluzione deve avere tra 5 e 12 righe non vuote."
                else:
                    ex["solution"] = "\n".join(lines)
                    ex["lines"] = mixed
        if ex and not problem:
            ex["state"] = {"solved": False, "attempts": 0, "hints": 0, "revealed": False}
            ex["genAttempts"] = attempt + 1
            return ex
        msgs = msgs[:2] + [{"role": "assistant", "content": json.dumps(data, ensure_ascii=False)},
                           {"role": "user", "content": (problem or "Errore") + "\nRestituisci di nuovo tutto il JSON corretto."}]
    raise LLMError("Il modello non è riuscito a creare un esercizio che funzioni. Riprova o scegli un altro tipo.")


JUDGE_SCHEMA = {"type": "object", "properties": {
    "esito": {"type": "string", "enum": ["giusto", "parziale", "sbagliato"]}, "commento": STR},
    "required": ["esito", "commento"]}


def judge(question, reference, why, answer):
    prompt = (f"Domanda di ragionamento: {question}\nRisposta corretta di riferimento: {reference}\nMotivo: {why}\n\n"
              f"Risposta dello studente, scritta con parole sue: «{answer}»\n\n"
              "Valuta il ragionamento, non la forma né l'ortografia. \"esito\": giusto, parziale o sbagliato. "
              "\"commento\": 1-2 frasi rivolte allo studente (dagli del tu). Se è parziale o sbagliata, NON rivelare la risposta: "
              "dai un indizio che lo faccia ragionare.")
    d = llm_json([{"role": "system", "content": SYS_GEN}, {"role": "user", "content": prompt}], JUDGE_SCHEMA, temperature=0.1, num_ctx=3072)
    esito = d.get("esito") if d.get("esito") in ("giusto", "parziale", "sbagliato") else "parziale"
    return {"verdict": esito, "comment": str(d.get("commento") or "")}


REVIEW_SCHEMA = {"type": "object", "properties": {
    "esito": {"type": "string", "enum": ["giusto", "parziale", "sbagliato"]}, "commento": STR, "problemi": ARR},
    "required": ["esito", "commento", "problemi"]}


def review_code(lang, statement, solution, criteria, code):
    prompt = (f"Sei un revisore di codice {LANGNAME[lang]} per uno studente. Il codice non può essere eseguito: valutalo leggendolo.\n"
              f"Consegna: {statement}\nCriteri da rispettare:\n" + "\n".join("- " + c for c in criteria) +
              f"\n\nSoluzione di riferimento (solo per te, non mostrarla):\n{solution}\n\nCodice dello studente:\n{code}\n\n"
              "Una soluzione diversa da quella di riferimento è GIUSTA se fa la stessa cosa e rispetta i criteri. "
              "Ignora differenze di stile, nomi, spazi e commenti. \"esito\": giusto, parziale o sbagliato. "
              "\"commento\": 1-3 frasi rivolte allo studente (dagli del tu), senza scrivere la soluzione. "
              "\"problemi\": elenco breve dei problemi concreti (vuoto se giusto).")
    d = llm_json([{"role": "system", "content": SYS_GEN}, {"role": "user", "content": prompt}], REVIEW_SCHEMA, temperature=0.1)
    v = d.get("esito") if d.get("esito") in ("giusto", "parziale", "sbagliato") else "parziale"
    return {"verdict": v, "comment": str(d.get("commento") or ""), "problems": [str(x) for x in (d.get("problemi") or [])][:6]}


TUTOR_SYS = ("Sei il tutor di Ricalco, un'app che insegna a programmare a studenti junior facendo riscrivere il codice invece di copiarlo. "
             "Rispondi in italiano, dando del tu, in modo concreto e breve (massimo 150 parole, salvo richiesta). "
             "Usa piccoli esempi di codice tra backtick o in blocchi ```. "
             "Se lo studente sta svolgendo un esercizio NON dargli la soluzione completa: guidalo con indizi e domande, "
             "a meno che non chieda esplicitamente la soluzione.")


# ---------------------------------------------------------------- SQL
SQL_SETUP_RULE = ("Database SQLite. In \"setup\" scrivi CREATE TABLE e INSERT con dati realistici in italiano (al massimo 3 tabelle "
                  "e 12 righe per tabella), coerenti con l'ambientazione; inserisci qualche NULL o caso particolare se serve all'esercizio. "
                  "Usa solo SQL supportato da SQLite (niente funzioni di MySQL o PostgreSQL). ")


def sql_schema(kind):
    props = {"titolo": STR, "setup": STR}
    if kind == "quiz":
        props.update(domanda=STR, codice=STR, opzioni=ARR, corretta={"type": "integer"}, spiegazione=STR)
    elif kind == "predici":
        props.update(codice=STR, spiegazione=STR)
    elif kind == "riempi":
        props.update(consegna=STR, codice=STR, risposte=ARR, spiegazione=STR)
    else:
        props.update(consegna=STR, soluzione=STR, verifica=STR, suggerimenti=ARR)
        if kind in ("completa", "zero"):
            props["codice_iniziale"] = STR
        if kind == "bug":
            props.update(codice_con_bug=STR, spiegazione_bug=STR)
    return {"type": "object", "properties": props, "required": list(props)}


def sql_prompt(kind, diff, topic, avoid):
    avoid_txt = ("\nNon ripetere questi esercizi già presenti: " + "; ".join(avoid[-12:]) + ".") if avoid else ""
    head = f"Argomento: {topic}\nLinguaggio: SQL (SQLite). Difficoltà {DIFF_TEXT[diff]}.{avoid_txt}\n\n" + SQL_SETUP_RULE
    verifica = ("\"verifica\": se la soluzione modifica dati o tabelle (INSERT, UPDATE, DELETE, CREATE...), una SELECT con ORDER BY che mostra "
                "lo stato finale da confrontare; se la soluzione è una SELECT, stringa vuota. ")
    hints = "\"suggerimenti\": 3 indizi progressivi senza scrivere la query completa. \"titolo\": massimo 5 parole."
    if kind == "predici":
        return head + ("Esercizio «prevedi il risultato»: in \"codice\" una query di 2-10 righe il cui risultato ha da 1 a 6 righe e al massimo "
                       "4 colonne. Lo studente deve prevedere esattamente le righe. Inserisci un dettaglio che richieda ragionamento "
                       "(un filtro, un raggruppamento, un NULL, una join). Se il risultato ha più righe usa ORDER BY. "
                       "\"spiegazione\": perché il risultato è quello. \"titolo\": massimo 5 parole.")
    if kind == "quiz":
        return head + ("Esercizio a scelta multipla sulla COMPRENSIONE (cosa fa una clausola, quale query è giusta, cosa succede con i NULL...). "
                       "\"codice\": una query a cui la domanda si riferisce, oppure stringa vuota. \"opzioni\": 4 risposte brevi, una sola giusta. "
                       "\"corretta\": indice 0-3. \"spiegazione\": 1-2 frasi. \"titolo\": massimo 5 parole.")
    if kind == "riempi":
        return head + ("Esercizio «completa gli spazi»: in \"codice\" una query di 2-10 righe in cui da 1 a 3 parti brevi (una parola chiave, "
                       "una funzione, un operatore, un nome di colonna) sono sostituite da ___ (tre trattini bassi). \"risposte\": le parti mancanti "
                       "in ordine. Con le risposte la query deve funzionare e restituire almeno una riga. \"consegna\": cosa deve restituire. "
                       "\"spiegazione\": perché quelle risposte. \"titolo\": massimo 5 parole.")
    base = ("\"consegna\": cosa deve restituire o fare la query, citando colonne e ordinamento del risultato atteso. "
            "\"soluzione\": la query (o le istruzioni) corretta, che restituisce almeno una riga. " + verifica)
    if kind == "riordina":
        extra = "Esercizio «riordina le righe»: la soluzione ha 4-10 righe, una clausola per riga (SELECT, FROM, JOIN, WHERE, GROUP BY, HAVING, ORDER BY...)."
    elif kind == "zero":
        extra = "Esercizio da scrivere da zero: \"codice_iniziale\" contiene solo il commento `-- scrivi qui la query`."
    elif kind == "completa":
        extra = ("Esercizio «completa la query»: in \"codice_iniziale\" la soluzione con 1-2 parti importanti sostituite da un commento "
                 "`-- TODO: ...` che dice cosa manca, in modo che il risultato NON sia quello giusto.")
    else:
        extra = ("Esercizio «trova il bug»: in \"codice_con_bug\" la soluzione con UN errore logico realistico (INNER al posto di LEFT JOIN, "
                 "WHERE al posto di HAVING, condizione sbagliata, COUNT(*) al posto di COUNT(colonna), ordinamento invertito...) che cambia "
                 "il risultato senza errori di sintassi. \"spiegazione_bug\": spiega il bug.")
    return head + extra + " " + base + hints


def sql_tables(setup):
    r = run_sql(setup, "", tables=True)
    return r.get("tables") or {}


def prep_sql(ex):
    """Completa un esercizio SQL (seed o generato) con anteprima tabelle e risultato atteso."""
    setup = ex.get("setup", "")
    ex["check"] = ex.get("check") or "sql"
    if ex["check"] == "sql" and "tables" not in ex:
        ex["tables"] = sql_tables(setup)
    t = ex["type"]
    if t == "predici" and "output" not in ex:
        r = run_sql(setup, ex["code"])
        ex["output"] = sql_as_text(r.get("result"))
        ex["outCols"] = (r.get("result") or {}).get("cols", [])
    elif t == "riempi" and "expected" not in ex:
        r = run_sql(setup, fill_blanks(ex["code"], ex["answers"]), ex.get("verify"))
        ex["expected"], ex["ordered"] = r.get("result"), is_ordered(ex["code"])
    elif t in ("riordina", "completa", "bug", "zero") and "expected" not in ex:
        r = run_sql(setup, ex["solution"], ex.get("verify"))
        ex["expected"], ex["ordered"] = r.get("result"), is_ordered(ex.get("verify") or ex["solution"])
        if t == "riordina" and "lines" not in ex:
            lines, mixed = shuffled_lines(ex["solution"])
            ex["solution"], ex["lines"] = "\n".join(lines), mixed
    return ex


def generate_sql_exercise(kind, diff, topic, avoid, attempts=4):
    msgs = [{"role": "system", "content": SYS_GEN}, {"role": "user", "content": sql_prompt(kind, diff, topic, avoid)}]
    schema = sql_schema(kind)
    base = {"id": "e" + uuid.uuid4().hex[:10], "type": kind, "difficulty": diff, "lang": "sql", "check": "sql"}
    for attempt in range(attempts):
        data = llm_json(msgs, schema, temperature=0.6 if attempt == 0 else 0.35)
        problem, ex = None, None
        title = str(data.get("titolo") or EX_TYPES[kind])[:70]
        setup = str(data.get("setup") or "").strip()
        rs = run_sql(setup, "")
        if not setup:
            problem = "Manca il setup con CREATE TABLE e INSERT."
        elif rs.get("error"):
            problem = "Il setup va in errore: " + rs["error"][:500]
        elif kind == "quiz":
            opts = [str(o).strip() for o in (data.get("opzioni") or []) if str(o).strip()][:5]
            c = data.get("corretta")
            if not data.get("domanda") or len(opts) < 3 or not isinstance(c, int) or not 0 <= c < len(opts):
                problem = "Servono domanda, 4 opzioni e l'indice della risposta giusta."
            else:
                ex = dict(base, title=title, setup=setup, question=str(data["domanda"]), code=norm_code(data.get("codice")),
                          options=opts, correct=c, explain=str(data.get("spiegazione") or ""))
        elif kind == "predici":
            code = norm_code(data.get("codice"))
            r = run_sql(setup, code)
            res = r.get("result")
            if r.get("error") or not res:
                problem = "La query non funziona o non restituisce righe: " + str(r.get("error") or "nessun risultato")[:500]
            elif not 1 <= len(res["rows"]) <= 6 or len(res["cols"]) > 4:
                problem = f"Il risultato ha {len(res['rows'])} righe e {len(res['cols'])} colonne: servono 1-6 righe e al massimo 4 colonne."
            else:
                ex = dict(base, title=title, setup=setup, code=code, explain=str(data.get("spiegazione") or ""))
        elif kind == "riempi":
            code = norm_code(data.get("codice"))
            ans = [str(a).strip().strip("`") for a in (data.get("risposte") or []) if str(a).strip()]
            n = code.count("___")
            if not 1 <= n <= 3 or n != len(ans):
                problem = f"Servono da 1 a 3 spazi ___ e altrettante risposte (ora {n} spazi e {len(ans)} risposte)."
            else:
                r = run_sql(setup, fill_blanks(code, ans))
                if r.get("error") or not r.get("result") or not r["result"]["rows"]:
                    problem = "Con le risposte la query non funziona o non restituisce righe: " + str(r.get("error") or "")[:400]
                else:
                    ex = dict(base, title=title, setup=setup, code=code, answers=ans, statement=str(data.get("consegna") or ""),
                              explain=str(data.get("spiegazione") or ""))
        else:
            sol = norm_code(data.get("soluzione"))
            verify = norm_code(data.get("verifica")) or None
            r = run_sql(setup, sol, verify)
            res = r.get("result")
            if r.get("error") or not res or not res["rows"]:
                problem = "La soluzione non funziona o non restituisce righe: " + str(r.get("error") or "nessun risultato")[:500]
            else:
                ex = dict(base, title=title, setup=setup, solution=sol, verify=verify, statement=str(data.get("consegna") or ""),
                          hints=[str(h) for h in (data.get("suggerimenti") or []) if str(h).strip()][:4])
                if kind in ("completa", "zero", "bug"):
                    start = norm_code(data.get("codice_con_bug" if kind == "bug" else "codice_iniziale"))
                    rr = run_sql(setup, start, verify) if start else {"error": "vuoto"}
                    if not start:
                        problem = "Manca il codice di partenza."
                    elif kind == "bug" and rr.get("error"):
                        problem = "La query con il bug va in errore: il bug deve essere logico. " + rr["error"][:300]
                    elif not rr.get("error") and same_result(res, rr.get("result"), is_ordered(verify or sol)):
                        problem = "Il codice di partenza restituisce già il risultato giusto: deve essere diverso."
                    ex["starter"] = start
                    if kind == "bug":
                        ex["bugExplain"] = str(data.get("spiegazione_bug") or "")
                if kind == "riordina" and not problem:
                    lines = [l for l in sol.split("\n") if l.strip()]
                    if not 3 <= len(lines) <= 12:
                        problem = "La soluzione deve avere 4-10 righe, una clausola per riga."
        if ex and not problem:
            ex = prep_sql(ex)
            ex["state"] = {"solved": False, "attempts": 0, "hints": 0, "revealed": False}
            ex["genAttempts"] = attempt + 1
            return ex
        msgs = msgs[:2] + [{"role": "assistant", "content": json.dumps(data, ensure_ascii=False)},
                           {"role": "user", "content": (problem or "Errore") + "\nRestituisci di nuovo tutto il JSON corretto."}]
    raise LLMError("Il modello non è riuscito a creare un esercizio SQL che funzioni. Riprova o scegli un altro tipo.")


# ---------------------------------------------------------------- percorsi: pool, progressi, worker
POOL = DATA / "pool"
THEORY = DATA / "theory"
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
                if lang in PATHS and not (THEORY / f"{lang}_{uid}.json").exists() and fails.get("theory", 0) < 3:
                    key = "theory"
                    WORKER["job"] = f"teoria · {unit_of(lang, uid)[1]['title']}"
                    get_theory(lang, uid)
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


# ---------------------------------------------------------------- pagina «Oggi»: esercizi a livello, punteggio tipo Elo
QUICK = DATA / "quick"
QUICK_FOCUS = {"lang": None, "variant": None}
QUICK_WANT = 4
ELO_START = 800
PLAN_SCORE = {"first": 1.0, "free": 1.0, "partial": 0.7, "retry": 0.6, "shown": 0.2, "none": 0.5}
LEVEL_WEIGHT = {1: 0.75, 2: 0.9, 3: 1.0, 4: 1.0}
QUICK_SCHEMA = {"type": "object", "properties": {
    "titolo": STR, "problema": STR, "piano_domanda": STR, "opzioni": ARR, "corretta": {"type": "integer"}, "perche": STR, "passi": ARR,
    "blocchi": {"type": "array", "items": {"type": "object", "properties": {"codice": STR, "cosa_fa": STR, "perche": STR},
                                           "required": ["codice", "cosa_fa", "perche"]}}},
    "required": ["titolo", "problema", "piano_domanda", "opzioni", "corretta", "perche", "passi", "blocchi"]}


def tier_of(r):
    return max(1, min(5, round((r - 650) / 150)))


def elo_state(p, lang):
    return p.setdefault("elo", {}).setdefault(lang, {"r": ELO_START, "n": 0, "hist": []})


# ---- la home segue il percorso: le unità che si possono eseguire, poi gli algoritmi, una dopo l'altra
HOME_STEP = 30      # punti Elo per passare all'argomento successivo
HOME_FROM = 725     # punteggio da cui parte la prima unità


HOME_SKIP = {"python": {"u14", "u18", "u19", "u20"}, "java": {"u16"}}   # file, test, database e HTTP: non diventano algoritmi


def home_units(lang):
    out = []
    for i, u in enumerate(CURRICULUM.get(lang, [])):
        if u.get("exec") in ("output", "tests", "sql") and not u.get("requires") and u["id"] not in HOME_SKIP.get(lang, ()):
            out.append({"label": f"Unità {i + 1} · {u['title']}", "title": u["title"], "concepts": u["concepts"], "notes": u.get("notes", "")})
    if lang in ("python", "java"):
        for i, u in enumerate(ALGO):
            out.append({"label": f"Algoritmi {i + 1} · {u['title']}", "title": u["title"], "concepts": u["concepts"], "notes": ""})
    return out


def home_index(lang, r):
    n = len(home_units(lang))
    return max(0, min(n - 1, int((r - HOME_FROM) // HOME_STEP))) if n else 0


def home_labels(lang, r):
    hu = home_units(lang)
    i = home_index(lang, r)
    return {hu[j]["label"] for j in (i, i + 1) if j < len(hu)}


def home_topic(lang, idx):
    hu = home_units(lang)
    u = hu[idx]
    before = ", ".join(x["title"] for x in hu[max(0, idx - 4):idx])
    after = ", ".join(x["title"] for x in hu[idx + 1:idx + 3])
    t = (f"{u['label']} del percorso: {u['concepts']}. Trasformalo in un piccolo problema ALGORITMICO (dati in ingresso → risultato) "
         f"che si risolve proprio con questi concetti.")
    if before:
        t += f" Puoi usare anche quello che lo studente ha già visto ({before})."
    if after:
        t += f" Non usare argomenti che vengono dopo ({after})."
    if u.get("notes"):
        t += " " + u["notes"]
    return u, t


def elo_view(e, lang=None):
    r, t = e["r"], tier_of(e["r"])
    lo, hi = tier_rating(t) - 75, tier_rating(t) + 75
    out = {"r": round(r), "n": e["n"], "tier": t, "tierName": TIERS[t], "pct": max(0, min(100, round((r - lo) / (hi - lo) * 100))),
           "nextName": TIERS.get(t + 1), "nextAt": tier_rating(t + 1) - 75 if t < 5 else None, "hist": e.get("hist", [])[-12:]}
    if lang and home_units(lang):
        hu = home_units(lang)
        i = home_index(lang, r)
        out.update(unit=hu[i]["label"], unitNext=hu[i + 1]["label"] if i + 1 < len(hu) else None,
                   unitNextAt=HOME_FROM + HOME_STEP * (i + 1) if i + 1 < len(hu) else None)
    return out


def norm_quick(q, lang):
    q = dict(q)
    q.setdefault("lang", lang)
    q["tier"] = q.get("tier") or 2
    q.setdefault("problem", "")
    q.setdefault("steps", [])
    q.setdefault("plan", None)
    if q.get("pattern") not in patterns_for(lang):
        q["pattern"] = next(iter(patterns_for(lang)))
    q["blocks"] = [dict(b, what=b.get("what") or "", explain=b.get("explain") or "") for b in q.get("blocks", [])]
    return q


def quick_items(lang):
    gen = [norm_quick(q, lang) for q in load_json(QUICK / f"{lang}.json", [])]
    seeds = [norm_quick(dict(q, id=f"q{lang[0]}s{i}", seed=True, verified=True), lang) for i, q in enumerate(QUICK_SEEDS.get(lang, []))]
    return gen, seeds


def quick_item(lang, item_id):
    gen, seeds = quick_items(lang)
    return next((q for q in gen + seeds if q["id"] == item_id), None)


def item_rating(p, q):
    return p.get("qd", {}).get(q["id"], tier_rating(q["tier"]))


def start_level(r, d, help_level=1):
    """Livello di aiuto con cui parte l'esercizio: quello che hai raggiunto (sale dopo un esercizio pulito),
    o più alto se l'esercizio è molto sotto il tuo punteggio."""
    by_gap = 3 if r - d > 260 else 2 if r - d > 110 else 1
    return max(by_gap, help_level)


def quick_pick(lang, skip=(), pattern=None):
    """Sceglie il prossimo esercizio seguendo solo l'Elo.
    Il bersaglio è un esercizio con difficoltà poco sotto il tuo punteggio (circa 55-65% di probabilità attesa di farlo bene),
    con un po' di varietà. Sali di livello perché il tuo punteggio sale. Se l'esercizio nuovo più vicino è troppo sopra di te
    (oltre 100 punti), ne riprendi uno già fatto mentre Qwen ne prepara altri al tuo livello."""
    p = progress()
    e = elo_state(p, lang)
    r = e["r"]
    seen = p.get("quickSeen", {})
    gen, seeds = quick_items(lang)
    allq = gen + seeds
    recent = p.get("quickRecent", {}).get(lang, [])
    fresh = [q for q in allq if q["id"] not in seen and q["id"] not in skip and item_rating(p, q) <= r + 100]
    if pattern and any(q["pattern"] == pattern for q in fresh):
        fresh = [q for q in fresh if q["pattern"] == pattern]
    target = r - 50 + random.uniform(-60, 60)
    repeat_reason = None
    labels = home_labels(lang, r) if home_units(lang) else set()

    def off_path(q):
        # prima gli esercizi dell'argomento del percorso a cui sei arrivato
        if not labels:
            return 0
        return 0 if q.get("unit") in labels else 60 if not q.get("unit") else 110

    if fresh:
        item = min(fresh, key=lambda q: abs(item_rating(p, q) - target) + off_path(q) + (90 if (q.get("topic") or q["title"]) in recent else 0) + random.random() * 25)
    else:
        pool = [q for q in allq if q["id"] not in skip and item_rating(p, q) <= r + 100] or [q for q in allq if q["id"] not in skip] or allq
        item = min(pool, key=lambda q: (seen.get(q["id"], 0), abs(item_rating(p, q) - target))) if pool else None
        repeat_reason = "Al tuo punteggio non ci sono ancora esercizi nuovi: ne riprendi uno già fatto mentre Qwen ne prepara altri."
    near = len([q for q in allq if q["id"] not in seen and abs(item_rating(p, q) - r) <= 150])
    return {"item": item, "startLevel": start_level(r, item_rating(p, item), e.get("help", 1)) if item else 1, "elo": elo_view(e, lang),
            "itemRating": round(item_rating(p, item)) if item else None, "fresh": near, "repeat": bool(item and item["id"] in seen),
            "repeatReason": repeat_reason if item and item["id"] in seen else None,
            "blockHist": p.get("qblocks", {}).get(item["id"]) if item else None}


def quick_prompt(lang, tier, topic, avoid):
    av = ("\nNon ripetere questi esercizi già presenti: " + "; ".join(avoid[-15:]) + ".") if avoid else ""
    return f"""Prepara un esercizio di «ricalco»: lo studente prima ragiona su come risolvere il problema, poi riscrive il codice blocco per blocco.
Argomento: {topic}. Linguaggio: {LANGNAME[lang]}. Difficoltà {tier} su 5, {TIER_DESC[tier]}.{av}

{lang_rules_program(lang)}
- "titolo": massimo 5 parole.
- "problema": cosa deve fare il programma in 1-3 frasi, con un esempio di input e risultato. NON dire come risolverlo.
- "piano_domanda": una domanda sul METODO per risolverlo (es. «Come eviti di provare tutte le coppie?», «Quale struttura dati ti serve?»).
- "opzioni": 4 metodi brevi, uno solo giusto, gli altri plausibili ma sbagliati o inefficienti. "corretta": indice 0-3, non sempre lo stesso.
- "perche": 1-2 frasi sul perché quel metodo funziona{"" if lang == "sql" else ", con la complessità O-grande"}.
- "passi": 2-5 passi logici della soluzione, in parole, senza codice.
- "blocchi": da 2 a 5 blocchi CONSECUTIVI: concatenandoli in ordine si ottiene il programma completo con l'indentazione corretta. Per ognuno:
  "codice": le righe del blocco; "cosa_fa": UNA frase su cosa fa il blocco (es. «Scorre la lista e conta le vocali»);
  "perche": 1-3 frasi sul perché è scritto così, l'errore tipico da evitare{"" if lang == "sql" else " o la complessità"}.
L'ultimo blocco prova il codice su 2-3 casi, compreso un caso limite, e stampa i risultati."""


def generate_quick(lang, tier, topic, avoid):
    pats = patterns_for(lang)
    schema = {"type": "object", "properties": dict(QUICK_SCHEMA["properties"], schema={"type": "string", "enum": list(pats)}),
              "required": QUICK_SCHEMA["required"] + ["schema"]}
    prompt = quick_prompt(lang, tier, topic, avoid) + "\n- \"schema\": lo schema principale usato, uno tra: " + ", ".join(f"{k} ({v})" for k, v in pats.items()) + "."
    msgs = [{"role": "system", "content": SYS_GEN}, {"role": "user", "content": prompt}]
    for attempt in range(3):
        d = llm_json(msgs, schema, temperature=0.45 if attempt == 0 else 0.25)
        blocks = [{"code": norm_code(b.get("codice")), "what": str(b.get("cosa_fa") or ""), "explain": str(b.get("perche") or "")}
                  for b in (d.get("blocchi") or []) if isinstance(b, dict) and str(b.get("codice") or "").strip()]
        opts = [str(o).strip() for o in (d.get("opzioni") or []) if str(o).strip()]
        c = d.get("corretta")
        if len(blocks) < 2:
            problem = "Servono da 2 a 5 blocchi con codice."
        elif len(opts) < 3 or not isinstance(c, int) or not 0 <= c < len(opts):
            problem = "Servono 4 opzioni nel piano e l'indice di quella corretta."
        else:
            run = run_program(lang, "\n".join(b["code"] for b in blocks))
            if run["ok"]:
                return {"id": "q" + uuid.uuid4().hex[:10], "title": str(d.get("titolo") or topic[:40])[:60], "topic": topic, "lang": lang, "tier": tier,
                        "kind": "query" if lang == "sql" else "algoritmo", "verified": True, "output": run["stdout"][:2000],
                        "pattern": d.get("schema") if d.get("schema") in pats else next(iter(pats)),
                        "problem": str(d.get("problema") or ""), "steps": [str(x) for x in (d.get("passi") or [])][:6],
                        "plan": {"q": str(d.get("piano_domanda") or "Come lo risolveresti?"), "options": opts, "correct": c, "why": str(d.get("perche") or "")},
                        "blocks": blocks, "genAttempts": attempt + 1}
            problem = ("Eseguendo il programma ottenuto concatenando i blocchi c'è questo errore:\n" + (run["error"] or "")[:1200] + error_hint(run["error"])
                       + "\nCorreggi il codice (attenzione all'indentazione tra un blocco e l'altro).")
        msgs = msgs[:2] + [{"role": "assistant", "content": json.dumps(d, ensure_ascii=False)},
                           {"role": "user", "content": problem + " Restituisci di nuovo tutto il JSON."}]
    raise LLMError("Il modello non è riuscito a preparare un esercizio che funzioni.")


def quick_job(fails):
    """In sottofondo: prepara esercizi al tuo livello (e uno al livello sopra), verificati eseguendoli."""
    lang = QUICK_FOCUS["lang"]
    if not lang or not current_model():
        return False
    v = QUICK_FOCUS.get("variant")
    if v and not variant_get(*v) and fails.get("variant:" + v[1], 0) < 2:
        WORKER["job"] = "variante da zero"
        WORKER["since"] = time.time()
        try:
            t0 = time.time()
            variant_make(*v)
            log_event("gen", what="variante", lang=v[0], secs=round(time.time() - t0, 1))
        except Preempted:
            raise
        except Exception as e:
            fails["variant:" + v[1]] = fails.get("variant:" + v[1], 0) + 1
            WORKER["error"] = str(e)[:200]
        return True
    if weekly_due(lang) and not weekly_pending(lang) and fails.get("weekly", 0) < 2:
        WORKER["job"] = "prova settimanale"
        WORKER["since"] = time.time()
        try:
            t0 = time.time()
            weekly_make(lang)
            log_event("gen", what="prova settimanale", lang=lang, secs=round(time.time() - t0, 1))
        except Preempted:
            raise
        except Exception as e:
            fails["weekly"] = fails.get("weekly", 0) + 1
            WORKER["error"] = str(e)[:200]
        return True
    if fails.get("quick", 0) >= 3:
        # dopo 3 errori di fila una pausa di 5 minuti, poi si riprova (prima si fermava fino al riavvio)
        if time.time() - fails.get("quick_t", 0) < 300:
            return False
        fails["quick"] = 0
    p = progress()
    seen = p.get("quickSeen", {})
    t = tier_of(elo_state(p, lang)["r"])
    gen, seeds = quick_items(lang)
    fresh = [q for q in gen + seeds if q["id"] not in seen]
    hu = home_units(lang)
    if hu:
        # servono esercizi nuovi sull'argomento del percorso a cui sei arrivato (o il successivo)
        labels = home_labels(lang, elo_state(p, lang)["r"])
        fu = [q for q in fresh if q.get("unit") in labels]
        if len(fu) >= 3:
            return False
        tier = t + 1 if t < 5 and len(fu) >= 2 and not any(q["tier"] == t + 1 for q in fu) else t
    else:
        want = [(t, QUICK_WANT)] + ([(t + 1, 1)] if t < 5 else [])
        tier = next((tt for tt, n in want if len([q for q in fresh if q["tier"] == tt]) < n), None)
        if not tier:
            return False
    unit = None
    if hu:
        # l'argomento segue il percorso: quello del tuo punteggio (o il successivo, per l'esercizio «sopra»)
        idx = home_index(lang, elo_state(p, lang)["r"]) + (1 if tier > t else 0)
        idx = min(idx, len(hu) - 1)
        cand = [i for i in (idx, idx + 1) if i < len(hu)]
        idx = min(cand, key=lambda i: len([q for q in fresh if q.get("unit") == hu[i]["label"]]))
        unit, topic_text = home_topic(lang, idx)
        topic = unit["label"]
    else:
        used = {q.get("topic") for q in gen}
        topics = [x for x in QUICK_TOPICS[lang][tier] if x not in used] or QUICK_TOPICS[lang][tier]
        topic = topic_text = random.choice(topics)
    WORKER["job"] = f"esercizio di oggi · {TIERS[tier]} · {topic}"
    WORKER["since"] = time.time()
    try:
        t0 = time.time()
        item = generate_quick(lang, tier, topic_text, [q["title"] for q in gen])
        item["topic"] = topic
        if unit:
            item["unit"] = unit["label"]
        log_event("gen", what="oggi", lang=lang, tier=tier, topic=topic, secs=round(time.time() - t0, 1), attempts=item.get("genAttempts", 1))
        with _PLOCK:
            items = load_json(QUICK / f"{lang}.json", [])
            items.append(item)
            save_json(QUICK / f"{lang}.json", items[-300:])
        fails["quick"] = 0
    except Preempted:
        raise
    except Exception as e:
        log_event("gen_fail", what="oggi", lang=lang, tier=tier, err=str(e)[:200])
        fails["quick"] = fails.get("quick", 0) + 1
        fails["quick_t"] = time.time()
        WORKER["error"] = str(e)[:200]
    return True


def code_words(blocks):
    """Quante «parole» ha il codice (quelle che «Mostra parola» può rivelare), commenti esclusi."""
    n = 0
    for b in blocks:
        for ln in b["code"].split("\n"):
            ln = re.split(r"\s(#|//|--)\s", " " + ln + " ")[0]
            if not ln.strip().startswith(("#", "//", "--")):
                n += len(ln.split())
    return max(1, n)


def quick_score(plan, level, acc, hints, words=40, levels=None):
    """Piano 40%, codice 60%. Gli aiuti pesano in proporzione alla lunghezza del codice:
    farsi mostrare 1 parola su 10 toglie il 15% del punteggio del codice.
    Con livelli diversi per blocco, il peso del livello è la media dei blocchi."""
    revealed = min(1.0, hints / max(1, words))
    weight = sum(LEVEL_WEIGHT.get(l, 0.55) for l in levels) / len(levels) if levels else LEVEL_WEIGHT.get(level, 0.55)
    code = weight * min(1.0, acc / 100) * max(0.0, 1 - 1.5 * revealed)
    return round(0.4 * PLAN_SCORE.get(plan, 0.5) + 0.6 * code, 3)


def pattern_update(p, lang, pattern, s=None, variant=None):
    st = p.setdefault("patterns", {}).setdefault(lang, {}).setdefault(pattern, {"n": 0, "avg": 0.0, "vn": 0, "vok": 0})
    if s is not None:
        st["avg"] = s if st["n"] == 0 else round(0.7 * st["avg"] + 0.3 * s, 3)
        st["n"] += 1
    if variant is not None:
        st["vn"] += 1
        st["vok"] += bool(variant)


def patterns_view(p, lang):
    pats = patterns_for(lang)
    st = p.get("patterns", {}).get(lang, {})
    out = [{"id": k, "name": v, "n": st.get(k, {}).get("n", 0), "avg": round(st.get(k, {}).get("avg", 0) * 100),
            "vn": st.get(k, {}).get("vn", 0), "vok": st.get(k, {}).get("vok", 0)} for k, v in pats.items()]
    return sorted([x for x in out if x["n"] or x["vn"]], key=lambda x: x["avg"])


def _norm_out(t):
    return "\n".join(ln.rstrip() for ln in str(t or "").strip().splitlines() if ln.strip())


def quick_free_run(lang, item_id, code):
    """Livello 4 «Scrivi tu»: esegue il tuo programma e lo confronta con l'output della soluzione di riferimento."""
    q = quick_item(lang, item_id)
    if not q:
        raise ValueError("esercizio non trovato")
    if not code.strip():
        raise ValueError("Scrivi prima il tuo programma.")
    expected = q.get("output")
    if not expected:
        expected = run_program(lang, "\n".join(b["code"] for b in q["blocks"])).get("stdout", "")
    run = run_program(lang, code)
    match = bool(run["ok"]) and _norm_out(run["stdout"]) == _norm_out(expected)
    log_event("quick_free", id=item_id, ok=run["ok"], match=match)
    return {"ok": run["ok"], "stdout": run["stdout"], "error": run.get("error"), "expected": expected, "match": match}


def quick_done(lang, item_id, level, acc, hints, plan, mode="new", card_id=None, blocks=None):
    """Fine di un esercizio di «Oggi»: punteggio, aggiornamento Elo (solo la prima volta) e programmazione del ripasso."""
    q = quick_item(lang, item_id)
    if not q:
        raise ValueError("esercizio non trovato")
    words = code_words(q["blocks"])
    blocks = [b for b in (blocks or []) if isinstance(b, dict)][:len(q["blocks"])]
    levels = [int(b.get("lvl") or level) for b in blocks] if len(blocks) == len(q["blocks"]) else None
    s = quick_score(plan, level, acc, hints, words, levels)
    g = 2 if s >= 0.85 else 1 if s >= 0.6 else 0
    out = {"s": s, "grade": g, "delta": 0, "revealed": round(min(1.0, hints / words) * 100), "words": words}
    with _PLOCK:
        p = progress()
        e = elo_state(p, lang)
        seen = p.setdefault("quickSeen", {})
        best = p.setdefault("qbest", {})
        first = mode == "new" and item_id not in seen
        # rifatto: conta anche lui, a metà peso e solo se fai meglio dell'ultima volta (così non si «farma» lo stesso esercizio)
        again = mode in ("new", "repeat") and item_id in seen and s > best.get(item_id, 0) + 0.02
        if first or again:
            d = item_rating(p, q)
            exp = 1 / (1 + 10 ** ((d - e["r"]) / 400))
            k = 64 if e["n"] < 10 else 32  # i primi 10 esercizi calibrano in fretta
            if again:
                k /= 2
            delta = k * (s - exp)
            e["r"] = max(400, e["r"] + delta)
            e["n"] += 1
            e.setdefault("hist", []).append({"t": int(time.time()), "id": item_id, "title": q["title"], "s": s, "d": round(delta, 1), "r": round(e["r"])})
            e["hist"] = e["hist"][-60:]
            if first:
                p.setdefault("qd", {})[item_id] = d - 16 * (s - exp)
            out["delta"] = round(delta)
            # livello di aiuto di partenza: sale di uno dopo un esercizio pulito, scende dopo uno andato male
            clean = acc >= 90 and out["revealed"] <= 5 and plan in ("first", "free", "retry")
            bad = acc < 75 or out["revealed"] >= 20
            lv_used = round(sum(levels) / len(levels)) if levels else level
            h = e.get("help", 1)
            if clean and lv_used >= h:
                e["help"] = min(3, lv_used + 1)
            elif bad:
                e["help"] = max(1, min(h, lv_used) - 1) if lv_used <= h else h
            out["help"] = e.get("help", 1)
            rec = p.setdefault("quickRecent", {}).setdefault(lang, [])
            rec.append(q.get("topic") or q["title"])
            p["quickRecent"][lang] = rec[-4:]
        seen[item_id] = int(time.time())
        best[item_id] = max(best.get(item_id, 0), s)
        if blocks:
            p.setdefault("qblocks", {})[item_id] = [{"err": int(b.get("err") or 0), "hints": int(b.get("hints") or 0), "lvl": int(b.get("lvl") or level)} for b in blocks]
        if mode in ("new", "review"):
            pattern_update(p, lang, q["pattern"], s)
        qs = p.setdefault("quickStats", {"n": 0})
        qs["n"] = qs.get("n", 0) + 1
        gain = {1: 4, 2: 6, 3: 10}.get(level, 4) + (4 if mode == "review" else 0)
        p["xp"] += gain
        if today() not in p["days"]:
            p["days"].append(today())
        progress_save(p)
        out.update(gain=gain, xp=p["xp"], elo=elo_view(e, lang), streak=streak(p["days"]))
    # ripasso: l'esercizio torna come flashcard (piano + riscrittura a memoria)
    if mode == "review" and card_id:
        grade_card(card_id, g)
    elif mode == "new":
        front = f"«{q['title']}»\n\n{q.get('problem') or ''}"
        card_add("ricalco", front, "\n".join(b["code"] for b in q["blocks"]), item_id,
                 extra={"kind": "quick", "item": item_id, "lang": lang, "path": lang, "box": 1 if g < 2 else 2,
                        "due": time.time() + (4 * 3600 if g == 0 else 20 * 3600 if g == 1 else 3 * 86400 - 3600)})
    return out


# ---- variante da zero: stesso schema, problema diverso, test veri
def variant_path(lang):
    return QUICK / f"var_{lang}.json"


def variant_get(lang, item_id):
    return load_json(variant_path(lang), {}).get(item_id)


def variant_make(lang, item_id):
    q = quick_item(lang, item_id)
    if not q:
        raise ValueError("esercizio non trovato")
    diff = "facile" if q["tier"] <= 2 else "medio" if q["tier"] == 3 else "difficile"
    topic = (f"VARIANTE dell'esercizio «{q['title']}». Problema originale: {q.get('problem')}. Lo studente ha appena riscritto questa soluzione:\n"
             + "\n".join(b["code"] for b in q["blocks"]) +
             f"\nCrea un problema GEMELLO: stesso schema ({patterns_for(lang)[q['pattern']]}; passi: {' '.join(q.get('steps') or [])}) "
             "ma con un obiettivo diverso (per esempio: il minimo invece del massimo, contare invece di cercare, restituire la posizione, "
             "un vincolo in più). Non deve bastare copiare la soluzione originale: va adattata. Nomi di funzioni e variabili diversi.")
    ex = generate_exercise("zero", lang, diff, topic, [q["title"]], "tests", attempts=3)
    ex.pop("state", None)
    ex.update(variantOf=item_id, pattern=q["pattern"])
    with _PLOCK:
        d = load_json(variant_path(lang), {})
        d[item_id] = ex
        save_json(variant_path(lang), d)
    return ex


def variant_done(lang, item_id, result, secs):
    q = quick_item(lang, item_id)
    with _PLOCK:
        p = progress()
        ok = result in ("first", "retry")
        if q:
            pattern_update(p, lang, q["pattern"], variant=ok)
        gain = {"first": 15, "retry": 8}.get(result, 0)
        p["xp"] += gain
        vs = p.setdefault("variants", [])
        vs.append({"t": int(time.time()), "lang": lang, "item": item_id, "result": result, "secs": int(secs or 0)})
        p["variants"] = vs[-300:]
        progress_save(p)
        return {"gain": gain, "xp": p["xp"], "patterns": patterns_view(p, lang)}


# ---- prova settimanale: un problema mai visto, da zero, senza aiuti, con il tempo
WEEK = 7 * 86400
WEEKLY_MIN = {1: 15, 2: 20, 3: 25, 4: 35, 5: 45}


def weekly_hist(p, lang):
    return p.get("weekly", {}).get(lang, [])


def weekly_due(lang, p=None):
    h = weekly_hist(p or progress(), lang)
    return not h or time.time() - h[-1]["t"] >= WEEK - 3600


def weekly_pending(lang):
    return load_json(QUICK / f"weekly_{lang}.json", None)


def weekly_make(lang):
    p = progress()
    t = tier_of(elo_state(p, lang)["r"])
    diff = "facile" if t <= 2 else "medio" if t == 3 else "difficile"
    done = [w.get("title") for w in weekly_hist(p, lang)]
    topic = (random.choice(QUICK_TOPICS[lang][t]) + ". È la PROVA SETTIMANALE: un problema nuovo da risolvere da zero, "
             "senza aiuti, come a un colloquio. Consegna chiara con un esempio.")
    ex = generate_exercise("zero", lang, diff, topic, done, "tests", attempts=3)
    ex.pop("state", None)
    ex.update(tier=t, minutes=WEEKLY_MIN[t])
    save_json(QUICK / f"weekly_{lang}.json", ex)
    return ex


def weekly_view(lang):
    p = progress()
    h = weekly_hist(p, lang)
    nxt = 0 if weekly_due(lang, p) else int((h[-1]["t"] + WEEK - 3600 - time.time()) // 86400) + 1
    return {"due": weekly_due(lang, p), "ready": bool(weekly_pending(lang)), "nextDays": nxt, "hist": h[-12:]}


def weekly_done(lang, ok, secs, tries, revealed):
    ex = weekly_pending(lang)
    with _PLOCK:
        p = progress()
        rec = {"t": int(time.time()), "title": ex.get("title") if ex else "", "ok": bool(ok) and not revealed, "secs": int(secs or 0),
               "tries": int(tries or 0), "tier": (ex or {}).get("tier"), "minutes": (ex or {}).get("minutes")}
        p.setdefault("weekly", {}).setdefault(lang, []).append(rec)
        if rec["ok"]:
            p["xp"] += 40
        progress_save(p)
    try:
        (QUICK / f"weekly_{lang}.json").unlink()
    except OSError:
        pass
    return weekly_view(lang)


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


# ---- metodo Feynman: spiega la soluzione a un principiante
FY_ASK = {"type": "object", "properties": {"domande": ARR}, "required": ["domande"]}
FY_JUDGE = {"type": "object", "properties": {"chiarezza": {"type": "integer"}, "completezza": {"type": "integer"}, "correttezza": {"type": "integer"},
                                             "commento": STR, "mancava": STR, "spiegazione_semplice": STR},
            "required": ["chiarezza", "completezza", "correttezza", "commento", "mancava", "spiegazione_semplice"]}


def feynman(stage, lang, title, problem, code, explanation, qa):
    head = (f"Esercizio «{title}» ({LANGNAME.get(lang, lang)}). Problema: {problem}\nSoluzione:\n{code[:3500]}\n\n"
            f"Lo studente ha spiegato la soluzione con parole sue, come a un principiante:\n«{explanation}»\n")
    if qa:
        head += "".join(f"\nDomanda del principiante: {x.get('q')}\nRisposta dello studente: «{x.get('a')}»" for x in qa) + "\n"
    if stage == "ask":
        prompt = head + ("\nFai la parte di un PRINCIPIANTE curioso che non sa programmare bene. Hai letto la spiegazione: individua al massimo 2 punti "
                         "vaghi, saltati o sbagliati (il perché di una scelta, cosa succede in un caso limite, perché quella struttura dati, la complessità) "
                         "e fai una domanda breve per ciascuno, in italiano, dando del tu. Le domande devono costringere a spiegare meglio, "
                         "non rivelare la risposta. Se la spiegazione è già chiara e completa, \"domande\" è una lista vuota.")
        d = llm_json([{"role": "system", "content": SYS_GEN}, {"role": "user", "content": prompt}], FY_ASK, temperature=0.3, num_ctx=4096)
        return {"questions": [str(x).strip() for x in (d.get("domande") or []) if str(x).strip()][:2]}
    prompt = head + ("\nOra fai il tutor. Valuta la spiegazione dello studente (comprese le risposte) da 1 a 5 su: "
                     "\"chiarezza\" (parole semplici, ordine logico), \"completezza\" (idea, scelte, casi limite), \"correttezza\" (niente errori). "
                     "Sii esigente ma giusto: 5 solo se la capirebbe davvero un principiante. "
                     "\"commento\": 1-2 frasi rivolte allo studente. \"mancava\": il punto più importante che non ha spiegato bene, in una frase "
                     "(stringa vuota se non manca nulla). \"spiegazione_semplice\": come lo spiegheresti tu a un principiante, in 3-4 frasi senza codice.")
    d = llm_json([{"role": "system", "content": SYS_GEN}, {"role": "user", "content": prompt}], FY_JUDGE, temperature=0.1, num_ctx=4096)
    clamp = lambda v: max(1, min(5, int(v))) if isinstance(v, (int, float)) else 3
    res = {"clarity": clamp(d.get("chiarezza")), "complete": clamp(d.get("completezza")), "correct": clamp(d.get("correttezza")),
           "comment": str(d.get("commento") or ""), "missing": str(d.get("mancava") or "").strip(), "model": str(d.get("spiegazione_semplice") or "")}
    if res["missing"]:
        card_add("spiega", f"Spiega a un principiante: «{title}»\n\nIl punto che ti era sfuggito: {res['missing']}",
                 res["model"] or res["missing"], "feynman")
    return res


# ---- progetti a tappe (cartelle vere in progetti/, accanto all'app)
PROJ_DIR = ROOT / "progetti"


def project_dir(pid, copy=False):
    return PROJ_DIR / (PROJECTS[pid]["folder"] + ("-mia" if copy else ""))


def project_req_ok(pid):
    P = PROJECTS[pid]
    if P.get("kind") == "maven":
        return SPRING.ready()
    return P["lang"] != "python" or not P.get("requires") or py_has(P["requires"])


def projects_view():
    p = progress()
    return [{"id": k, "title": P["title"], "lang": P["lang"], "desc": P["desc"], "steps": len(P["steps"]),
             "done": p.get("projects", {}).get(k, {}).get("done", 0), "requires": P.get("requires", []), "ready": project_req_ok(k),
             "kind": P.get("kind", "script")}
            for k, P in PROJECTS.items()]


def project_view(pid, k=None):
    if pid not in PROJECTS:
        raise ValueError("progetto sconosciuto")
    P = PROJECTS[pid]
    st = progress().get("projects", {}).get(pid, {})
    done = st.get("done", 0)
    n = len(P["steps"])
    k = min(done, n - 1) if k is None else max(0, min(int(k), n - 1, done))
    return {"id": pid, "title": P["title"], "lang": P["lang"], "main": P["main"], "requires": P.get("requires", []),
            "kind": P.get("kind", "script"), "url": P.get("url"),
            "ready": project_req_ok(pid), "done": done, "titles": [x["title"] for x in P["steps"]],
            "folder": str(project_dir(pid)), "copy": str(project_dir(pid, True)), "copyExists": project_dir(pid, True).exists(),
            "step": step_view(pid, k), "best": st.get("best", {})}


def project_write(pid, upto):
    folder = project_dir(pid)
    folder.mkdir(parents=True, exist_ok=True)
    for name, src in snapshot(pid, upto).items():
        f = folder / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(src, encoding="utf-8")
    return str(folder)


def project_step_done(pid, k, acc, level):
    n = len(PROJECTS[pid]["steps"])
    k = max(0, min(int(k), n - 1))
    with _PLOCK:
        p = progress()
        st = p.setdefault("projects", {}).setdefault(pid, {"done": 0, "best": {}})
        st["done"] = max(st.get("done", 0), k + 1)
        st.setdefault("best", {})[str(k)] = max(st.get("best", {}).get(str(k), 0), int(level))
        p["xp"] += 15
        if today() not in p["days"]:
            p["days"].append(today())
        progress_save(p)
    folder = project_write(pid, st["done"])
    return {"done": st["done"], "folder": folder}


def project_run(pid, copy=False):
    P = PROJECTS[pid]
    folder = project_dir(pid, copy)
    if not (folder / P["main"]).exists():
        raise ValueError("Completa almeno la prima tappa: i file non ci sono ancora." if not copy else "Crea prima la tua copia.")
    if not project_req_ok(pid):
        return {"ok": False, "missing": P.get("requires", []), "kind": P.get("kind", "script")}
    if P.get("kind") == "sql":
        r = project_sql_run(pid, folder)
        log_event("project_run", project=pid, copy=copy, ok=r["ok"], n=len(r["outputs"]))
        return r
    if P.get("kind") == "maven":
        r = SPRING.run_project(folder)
        log_event("project_test", project=pid, copy=copy, ok=r.get("all_ok"), n=len(r.get("tests", [])), secs=r.get("secs"))
        return {"ok": bool(r.get("all_ok")), "kind": "maven", "result": r}
    logf = DATA / "progetto_output.txt"
    with open(logf, "w", encoding="utf-8") as f:
        proc = subprocess.Popen([sys.executable, P["main"]], cwd=str(folder), stdout=f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
        try:
            rc = proc.wait(timeout=4)
        except subprocess.TimeoutExpired:
            rc = None
    out = logf.read_text(encoding="utf-8", errors="replace")[-3000:]
    log_event("project_run", project=pid, copy=copy, rc=rc)
    if rc is None:
        return {"ok": True, "running": True, "output": out}
    return {"ok": rc == 0, "running": False, "output": out, "error": None if rc == 0 else out or f"Il programma è terminato con codice {rc}."}


def project_sql_run(pid, folder):
    """Esegue gli script SQL del progetto nell'ordine giusto, mostra ogni SELECT e ricrea il file .db."""
    P = PROJECTS[pid]
    files = [(n, (folder / n).read_text(encoding="utf-8")) for n in P["order"] if (folder / n).exists()]
    code = "\n".join(src for _, src in files)
    r = run_sql("", code)
    outs = []
    for o in r.get("outputs", []):
        title = next((ln.strip()[2:].strip() for ln in o.get("sql", "").split("\n") if ln.strip().startswith("--")), "")
        outs.append({"title": title, "cols": o["cols"], "rows": o["rows"]})
    res = {"ok": not r.get("error"), "kind": "sql", "outputs": outs, "error": r.get("error"), "files": [n for n, _ in files]}
    if r.get("error"):
        where = (r.get("where") or "").strip()
        body = [ln for ln in where.split("\n") if ln.strip() and not ln.strip().startswith("--")]
        res["where"] = "\n".join(body)
        probe = body[0].strip() if body else ""
        res["file"] = next((n for n, src in files if probe and probe in src), None)
        return res
    dbf = folder / P.get("db", "progetto.db")
    try:
        if dbf.exists():
            dbf.unlink()
        con = sqlite3.connect(str(dbf), isolation_level=None)
        t0 = time.time()
        con.set_progress_handler(lambda: 1 if time.time() - t0 > 10 else 0, 10000)
        con.executescript(code)
        con.close()
        res["db"] = str(dbf)
    except (OSError, sqlite3.Error) as e:
        res["dbError"] = f"Non ho potuto ricreare {dbf.name}: {e}. Se è aperto in un altro programma, chiudilo e riprova."
    return res


def project_start(pid, copy=False):
    folder = project_dir(pid, copy)
    if not (folder / "pom.xml").exists():
        raise ValueError("Completa almeno la prima tappa.")
    SPRING.start_app(folder)
    log_event("project_start", project=pid, copy=copy)
    return {"ok": True, "url": PROJECTS[pid].get("url")}


def project_install(pid):
    req = PROJECTS[pid].get("requires", [])
    rc, out, err, timeout = run_proc([sys.executable, "-m", "pip", "install", *req], str(ROOT), 600)
    _PYMOD.clear()
    return {"ok": rc == 0 and project_req_ok(pid), "output": (out + err)[-2000:]}


def project_copy(pid, force=False):
    src, dst = project_dir(pid), project_dir(pid, True)
    if not src.exists():
        raise ValueError("Completa almeno la prima tappa.")
    if dst.exists() and not force:
        return {"path": str(dst), "existed": True}
    shutil.copytree(src, dst, dirs_exist_ok=True)
    return {"path": str(dst), "existed": False}


def open_folder(path):
    if sys.platform.startswith("win"):
        os.startfile(path)  # noqa
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def rewrite_card(title, explain, code, lang, path, src):
    """Un blocco di codice da riscrivere a memoria nei giorni successivi (mazzo «ricalco»)."""
    real = [ln for ln in code.split("\n") if ln.strip() and not ln.strip().startswith(("#", "//", "--"))]
    if len(real) < 2:
        return False
    return card_add("ricalco", f"{title}\n\n{explain or 'Riscrivi il codice a memoria.'}", code, src,
                    extra={"kind": "rewrite", "lang": lang, "path": path, "due": time.time() + 20 * 3600})


def home_view():
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
            "worker": dict(WORKER, focus=FOCUS["key"])}


MASTERY_ACC = 85
MASTERY_HINTS = 2


def lesson_done(lesson_id, level, acc, hints):
    """Lezione finita: aggiorna l'unità (impara/fissa) e crea le carte di ripasso da riscrivere."""
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


# ---------------------------------------------------------------- HTTP
MIME = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
        ".js": "text/javascript; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon"}
ID_RE = re.compile(r"^[a-z0-9]{4,20}$")


class Handler(BaseHTTPRequestHandler):
    server_version = "Ricalco/1.0"

    def log_message(self, fmt, *args):
        if "/api/" in (args[0] if args else ""):
            sys.stderr.write("  " + (fmt % args) + "\n")

    # -- helpers
    def host_ok(self):
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in ("127.0.0.1", "localhost", "[::1]")

    def send_json(self, obj, code=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > 2_000_000:
            raise ValueError("richiesta troppo grande")
        return json.loads(self.rfile.read(n) or b"{}")

    def guard_api(self):
        # Solo la pagina dell'app può chiamare l'API: blocca altri siti (CSRF) e DNS rebinding.
        if not self.host_ok() or self.headers.get("X-Ricalco") != "1":
            self.send_json({"error": "Richiesta non autorizzata."}, 403)
            return False
        return True

    # -- GET
    def do_GET(self):
        if not self.host_ok():
            return self.send_error(403)
        path = self.path.split("?")[0]
        if path.startswith("/api/"):
            if not self.guard_api():
                return
            try:
                return self.api_get(path, {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()})
            except Exception as e:
                return self.send_json({"error": str(e)}, 500)
        if path == "/":
            path = "/index.html"
        f = (STATIC / path.lstrip("/")).resolve()
        if STATIC.resolve() not in f.parents or not f.is_file():
            return self.send_error(404)
        data = f.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", MIME.get(f.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def api_get(self, path, q):
        if path == "/api/logic":
            return self.send_json(logic_view())
        if path == "/api/spring":
            return self.send_json(SPRING.status())
        if path == "/api/selftest":
            p = progress()
            return self.send_json({"steps": selftest_steps(), "flags": p.get("flags", {}), "typestats": p.get("typestats", {}),
                                   "model": current_model(), "spring": SPRING.status(), "java": java_info()["version"],
                                   "python": sys.version.split()[0]})
        if path == "/api/interview":
            return self.send_json(interview_view())
        if path == "/api/cards":
            return self.send_json(decks_view())
        m = re.match(r"^/api/interviews/([a-z0-9]+)$", path)
        if m:
            d = load_json(INTERVIEWS / f"{m.group(1)}.json", None)
            return self.send_json(d) if d else self.send_json({"error": "Colloquio non trovato."}, 404)
        if path == "/api/logs/summary":
            return self.send_json(logs_summary(int(q.get("days") or 14)))
        if path == "/api/logs/export":
            data = "".join(f.read_text(encoding="utf-8", errors="replace") for f in sorted(LOGS.glob("*.jsonl"))[-30:]).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="ricalco-log-{time.strftime("%Y%m%d")}.jsonl"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if path == "/api/projects":
            return self.send_json({"projects": projects_view()})
        if path == "/api/project":
            return self.send_json(project_view(str(q.get("id")), q.get("step")))
        if path == "/api/home":
            FOCUS["key"] = None
            return self.send_json(home_view())
        if path == "/api/quick":
            lang = q.get("lang") if q.get("lang") in LANGNAME else "python"
            QUICK_FOCUS["lang"] = lang
            FOCUS["key"] = None
            d = quick_pick(lang, [x for x in (q.get("skip") or "").split(",") if x], q.get("pattern"))
            if d["item"]:
                QUICK_FOCUS["variant"] = (lang, d["item"]["id"])
            return self.send_json(dict(d, model=bool(current_model()), worker=dict(WORKER)))
        if path == "/api/weekly":
            lang = q.get("lang") if q.get("lang") in LANGNAME else "python"
            QUICK_FOCUS["lang"] = lang
            v = weekly_view(lang)
            if q.get("start") and v["due"]:
                ex = weekly_pending(lang)
                if not ex:
                    try:
                        with user_priority():
                            ex = weekly_make(lang)
                    except LLMError as e:
                        return self.send_json({"error": str(e)}, 502)
                v["exercise"] = ex
            return self.send_json(v)
        if path == "/api/quick/variant":
            lang = q.get("lang") if q.get("lang") in LANGNAME else "python"
            iid = str(q.get("id"))
            ex = variant_get(lang, iid)
            if not ex:
                try:
                    with user_priority():
                        ex = variant_make(lang, iid)
                except LLMError as e:
                    return self.send_json({"error": str(e)}, 502)
            return self.send_json({"exercise": ex})
        if path == "/api/quick/item":
            lang = q.get("lang") if q.get("lang") in LANGNAME else "python"
            it = quick_item(lang, str(q.get("id")))
            if not it:
                return self.send_json({"error": "Esercizio non trovato."}, 404)
            p = progress()
            return self.send_json({"item": it, "elo": elo_view(elo_state(p, lang), lang), "itemRating": round(item_rating(p, it)),
                                   "blockHist": p.get("qblocks", {}).get(it["id"])})
        if path == "/api/unit_lesson/status":
            lang = q.get("lang") if q.get("lang") in PATHS else "python"
            unit_of(lang, q.get("unit"))
            st = lesson_status(lang, q.get("unit"))
            if st["ready"]:
                return self.send_json(dict(get_unit_lesson(lang, q.get("unit")), ready=True))
            return self.send_json(st)
        if path == "/api/curriculum":
            lang = q.get("lang") if q.get("lang") in PATHS else "python"
            return self.send_json(curriculum_view(lang))
        if path == "/api/theory":
            lang = q.get("lang") if q.get("lang") in PATHS else "python"
            try:
                unit_of(lang, q.get("unit"))
                with user_priority():
                    return self.send_json(get_theory(lang, q.get("unit")))
            except LLMError as e:
                return self.send_json({"error": str(e)}, 502)
            except ValueError as e:
                return self.send_json({"error": str(e)}, 400)
        if path == "/api/status":
            try:
                models = list_models()
                ok = True
            except Exception:
                models, ok = [], False
            j = java_info()
            return self.send_json({"ollama": ok, "ollamaUrl": OLLAMA, "models": models, "model": pick_model(models),
                                   "python": sys.version.split()[0], "java": j["version"]})
        if path == "/api/lessons":
            items = [load_json(p, None) for p in LESSONS.glob("*.json")]
            items = [i for i in items if i]
            items.sort(key=lambda x: x.get("updated", 0), reverse=True)
            return self.send_json(items)
        m = re.match(r"^/api/lessons/([a-z0-9]+)$", path)
        if m and ID_RE.match(m.group(1)):
            d = load_json(LESSONS / (m.group(1) + ".json"), None)
            if d:
                d = lesson_recheck(d, LESSONS / (m.group(1) + ".json"))
            return self.send_json(d) if d else self.send_json({"error": "Lezione non trovata."}, 404)
        self.send_json({"error": "Percorso sconosciuto."}, 404)

    # -- DELETE / PUT
    def do_DELETE(self):
        if not self.guard_api():
            return
        m = re.match(r"^/api/lessons/([a-z0-9]+)$", self.path)
        if m and ID_RE.match(m.group(1)):
            p = LESSONS / (m.group(1) + ".json")
            if p.exists():
                p.unlink()
            return self.send_json({"ok": True})
        self.send_json({"error": "Percorso sconosciuto."}, 404)

    def do_PUT(self):
        if not self.guard_api():
            return
        m = re.match(r"^/api/lessons/([a-z0-9]+)$", self.path)
        if not (m and ID_RE.match(m.group(1))):
            return self.send_json({"error": "Percorso sconosciuto."}, 404)
        try:
            obj = self.body()
            obj["id"] = m.group(1)
            obj["updated"] = time.time()
            save_json(LESSONS / (m.group(1) + ".json"), obj)
            self.send_json({"ok": True, "updated": obj["updated"]})
        except Exception as e:
            self.send_json({"error": str(e)}, 400)

    # -- POST
    def do_POST(self):
        if not self.guard_api():
            return
        path = self.path.split("?")[0]
        try:
            b = self.body()
        except Exception:
            return self.send_json({"error": "JSON non valido."}, 400)
        prio = path in ("/api/lesson", "/api/exercise", "/api/judge", "/api/ask", "/api/judge_answer", "/api/followup",
                        "/api/interview/turn", "/api/interview/report", "/api/cards/generate")
        with (user_priority() if prio else contextlib.nullcontext()):
            self.post(path, b)

    def post(self, path, b):
        try:
            if path in ("/api/session", "/api/session/more", "/api/result", "/api/level_done", "/api/flag", "/api/focus"):
                key = str(b.get("key") or "")
                info = key_info(key)
            if path == "/api/focus":
                FOCUS["key"] = key
                return self.send_json({"ok": True})
            if path == "/api/session":
                p = progress()
                if not unlocked(key, p):
                    return self.send_json({"error": "Livello bloccato: completa prima quello precedente."}, 400)
                FOCUS["key"] = key
                size = max(1, min(SESSION_SIZE, int(b.get("size") or SESSION_SIZE)))
                types = set(b.get("types") or [])
                ex = pick_session(key, SESSION_SIZE * 3 if types else size, p=p, with_review=not types)
                if types:
                    ex = [e for e in ex if e["type"] in types][:size]
                adapt = adaptive_mix(key, p)[1]
                return self.send_json({"key": key, "exercises": ex, "missing": size - len(ex), "size": size,
                                       "label": info["label"], "kind": info["kind"], "lang": info["lang"], "path": info.get("path"), "adapt": adapt,
                                       "model": bool(current_model())})
            if path == "/api/session/more":
                FOCUS["key"] = key
                have = set(str(x) for x in (b.get("have") or []))
                types = set(b.get("types") or [])
                ex = pick_session(key, SESSION_SIZE * 3, exclude=have)
                ex = [e for e in ex if not types or e["type"] in types][:1]
                if not ex and not current_model():
                    rest = [e for e in pool_load(key) if e["id"] not in have]
                    ex = [random.choice(rest)] if rest else []
                return self.send_json({"exercise": ex[0] if ex else None, "model": bool(current_model()),
                                       "worker": dict(WORKER, focus=FOCUS["key"])})
            if path == "/api/review":
                lang = b.get("lang") if b.get("lang") in PATHS else "python"
                p = progress()
                out, ids = [], set()
                for m in reversed(p["mistakes"]):
                    if not m["key"].startswith(lang + "/") or m["id"] in ids:
                        continue
                    e = next((x for x in pool_load(m["key"]) if x["id"] == m["id"]), None)
                    if e:
                        out.append(dict(e, key=m["key"], lang=e.get("lang") or xl(lang)))
                        ids.add(m["id"])
                    if len(out) >= SESSION_SIZE:
                        break
                out.sort(key=lambda e: TYPE_ORDER.index(e["type"]) if e["type"] in TYPE_ORDER else 99)
                return self.send_json({"exercises": out, "lang": xl(lang)})
            if path == "/api/result":
                res = str(b.get("result"))
                if res not in ("first", "retry", "miss"):
                    raise ValueError("esito non valido")
                return self.send_json(record_result(key, str(b.get("id")), res, bool(b.get("review"))))
            if path == "/api/level_done":
                return self.send_json(record_level(key, int(b.get("first") or 0), int(b.get("total") or SESSION_SIZE)))
            if path == "/api/flag":
                ex_id = str(b.get("id"))
                e = next((x for x in pool_load(key) if x["id"] == ex_id), None)
                pool_remove(key, ex_id)
                with _PLOCK:
                    p = progress()
                    p["seen"][ex_id] = int(time.time())
                    p["mistakes"] = [m for m in p["mistakes"] if m["id"] != ex_id]
                    if e:
                        fl = p.setdefault("flags", {})
                        fl[e["type"]] = fl.get(e["type"], 0) + 1
                    progress_save(p)
                return self.send_json({"ok": True})
            if path == "/api/free":
                with _PLOCK:
                    p = progress()
                    p["free"] = bool(b.get("free"))
                    progress_save(p)
                return self.send_json({"ok": True, "free": p["free"]})
            if path == "/api/selftest/step":
                steps = selftest_steps()
                i = int(b.get("i", -1))
                if not 0 <= i < len(steps):
                    raise ValueError("passo non valido")
                with user_priority():
                    return self.send_json(dict(selftest_run(steps[i]), label=steps[i]["label"]))
            if path == "/api/check_sql":
                r = run_sql(str(b.get("setup") or ""), str(b.get("code") or ""), b.get("verify") or None)
                ok = not r.get("error") and same_result(b.get("expected"), r.get("result"), bool(b.get("ordered")))
                return self.send_json({"ok": ok, "result": r.get("result"), "error": r.get("error"), "where": r.get("where")})
            if path == "/api/run_spring":
                return self.send_json((RUNNERS.get(str(b.get("runner") or "")) or SPRING).run(norm_code(b.get("code")), norm_code(b.get("test"))))
            if path == "/api/spring/setup":
                if not SPRING.busy:
                    threading.Thread(target=SPRING.setup, daemon=True).start()
                return self.send_json({"ok": True, "status": SPRING.status()})
            if path == "/api/unit_lesson":
                lang = b.get("lang") if b.get("lang") in PATHS else "python"
                uid = str(b.get("unit"))
                unit_of(lang, uid)
                if not unit_available(lang, uid, progress()):
                    raise ValueError("Unità bloccata: prima riscrivi a memoria la lezione dell'unità precedente.")
                FOCUS["key"] = f"{lang}/{uid}/base"
                if unit_lesson_path(lang, uid).exists():
                    return self.send_json(get_unit_lesson(lang, uid))
                if b.get("wait"):   # vecchio comportamento: aspetta la lezione nella stessa richiesta
                    with user_priority():
                        return self.send_json(get_unit_lesson(lang, uid))
                return self.send_json(dict(lesson_request(lang, uid), pending=True))
            if path == "/api/unit/reset":
                lang = b.get("lang") if b.get("lang") in PATHS else "python"
                return self.send_json(unit_reset(lang, str(b.get("unit")), bool(b.get("progress"))))
            if path == "/api/unit_lesson/regen":
                lang = b.get("lang") if b.get("lang") in PATHS else "python"
                uid = str(b.get("unit"))
                unit_of(lang, uid)
                return self.send_json(dict(lesson_regen(lang, uid), pending=True))
            if path == "/api/log":
                for e in (b.get("events") or [])[:300]:
                    if isinstance(e, dict) and isinstance(e.get("ev"), str):
                        d = {str(k)[:30]: (v[:2000] if isinstance(v, str) else v) for k, v in list(e.items())[:30]
                             if k not in ("ev", "src") and isinstance(v, (str, int, float, bool, type(None)))}
                        log_event(e["ev"][:30], src="app", **d)
                return self.send_json({"ok": True})
            if path == "/api/feynman":
                stage = "ask" if b.get("stage") == "ask" else "judge"
                lang = b.get("lang") if b.get("lang") in LANGNAME else "python"
                expl = str(b.get("explanation") or "").strip()[:3000]
                if len(expl) < 20:
                    raise ValueError("Scrivi una spiegazione di almeno un paio di frasi.")
                qa = [{"q": str(x.get("q", ""))[:400], "a": str(x.get("a", ""))[:1500]} for x in (b.get("qa") or []) if isinstance(x, dict)][:3]
                with user_priority():
                    out = feynman(stage, lang, str(b.get("title") or "")[:120], str(b.get("problem") or "")[:1500],
                                  str(b.get("code") or ""), expl, qa)
                log_event("feynman", stage=stage, title=str(b.get("title") or "")[:120], len=len(expl), **({k: out[k] for k in ("clarity", "complete", "correct")} | {"missing": str(out.get("missing") or "")[:300]} if stage == "judge" else {"n": len(out["questions"])}))
                return self.send_json(out)
            if path.startswith("/api/project/"):
                pid = str(b.get("id"))
                if pid not in PROJECTS:
                    raise ValueError("progetto sconosciuto")
                if path == "/api/project/step_done":
                    return self.send_json(project_step_done(pid, b.get("step", 0), float(b.get("acc") or 0), int(b.get("level") or 1)))
                if path == "/api/project/run":
                    return self.send_json(project_run(pid, bool(b.get("copy"))))
                if path == "/api/project/start":
                    return self.send_json(project_start(pid, bool(b.get("copy"))))
                if path == "/api/project/install":
                    return self.send_json(project_install(pid))
                if path == "/api/project/copy":
                    return self.send_json(project_copy(pid, bool(b.get("force"))))
                if path == "/api/project/open":
                    d = project_dir(pid, bool(b.get("copy")))
                    if not d.exists():
                        raise ValueError("La cartella non c'è ancora.")
                    open_folder(str(d))
                    return self.send_json({"ok": True, "path": str(d)})
            if path == "/api/quick/free":
                lang = b.get("lang") if b.get("lang") in LANGNAME else "python"
                return self.send_json(quick_free_run(lang, str(b.get("id")), norm_code(b.get("code"))))
            if path == "/api/quick/done":
                lang = b.get("lang") if b.get("lang") in LANGNAME else "python"
                mode = b.get("mode") if b.get("mode") in ("new", "repeat", "review") else "new"
                return self.send_json(quick_done(lang, str(b.get("id")), int(b.get("level") or 1), float(b.get("acc") or 0),
                                                 int(b.get("hints") or 0), str(b.get("plan") or "none"), mode, b.get("card"), b.get("blocks")))
            if path == "/api/quick/variant_done":
                lang = b.get("lang") if b.get("lang") in LANGNAME else "python"
                res = b.get("result") if b.get("result") in ("first", "retry", "miss") else "miss"
                return self.send_json(variant_done(lang, str(b.get("id")), res, b.get("secs")))
            if path == "/api/weekly/done":
                lang = b.get("lang") if b.get("lang") in LANGNAME else "python"
                return self.send_json(weekly_done(lang, bool(b.get("ok")), b.get("secs"), b.get("tries"), bool(b.get("revealed"))))
            if path == "/api/rewrite_card":
                lang = b.get("lang") if b.get("lang") in LANGNAME else "python"
                pth = b.get("path") if b.get("path") in PATHS else lang
                blocks = b.get("blocks") or [{"code": b.get("code"), "explain": b.get("explain")}]
                n = 0
                for k, bl in enumerate(blocks[:8]):
                    t = str(b.get("title") or "Codice") + (f" · blocco {k + 1}" if len(blocks) > 1 else "")
                    n += rewrite_card(f"«{t}»", str(bl.get("explain") or ""), norm_code(bl.get("code")), lang, pth, str(b.get("src") or "manuale"))
                return self.send_json({"added": n})
            if path == "/api/lesson_done":
                return self.send_json(lesson_done(str(b.get("id")), int(b.get("level") or 1), float(b.get("acc") or 0), int(b.get("hints") or 0)))
            if path == "/api/judge_answer":
                return self.send_json(judge_answer(str(b.get("question", "")), [str(x) for x in (b.get("points") or [])],
                                                   str(b.get("model", "")), str(b.get("answer", ""))[:4000], bool(b.get("en"))))
            if path == "/api/followup":
                lang = b.get("lang") if b.get("lang") in LANGNAME else "python"
                return self.send_json(followup(lang, str(b.get("statement", "")), str(b.get("code", ""))[:6000], bool(b.get("en"))))
            if path in ("/api/interview/turn", "/api/interview/report"):
                track, level = str(b.get("track")), str(b.get("level"))
                if track not in INTERVIEW_BY or level not in INTERVIEW_MIX:
                    raise ValueError("colloquio non valido")
                hist = [{"role": m["role"], "content": str(m["content"])[:4000]} for m in (b.get("history") or [])
                        if isinstance(m, dict) and m.get("role") in ("user", "assistant") and str(m.get("content", "")).strip()]
                if path == "/api/interview/report":
                    if not any(m["role"] == "user" for m in hist):
                        raise ValueError("Rispondi ad almeno una domanda prima di chiedere la valutazione.")
                    return self.send_json(interview_report(track, level, hist, b.get("leaves") or 0))
                msgs = [{"role": "system", "content": interviewer_system(track, level)}]
                msgs += hist[-24:] if hist else []
                if not hist or hist[-1]["role"] != "user":
                    msgs.append({"role": "user", "content": "Hi, I'm ready for the interview." if INTERVIEW_BY[track].get("en") else "Ciao, sono pronto per il colloquio."})
                gen = llm_stream(msgs, temperature=0.6)
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                try:
                    for piece in gen:
                        self.wfile.write(piece.encode("utf-8"))
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                self.close_connection = True
                return
            if path == "/api/cards/study":
                deck = str(b.get("deck") or "")
                now = time.time()
                cs = [c for c in cards_load() if (deck == "tutte" or c["deck"] == deck) and c["due"] <= now]
                cs.sort(key=lambda c: (c["box"] > 0, c["due"]))
                out = []
                for c in cs[:40]:
                    c = dict(c, deckTitle=deck_title(c["deck"]))
                    if c.get("kind") == "quick":
                        c["itemData"] = quick_item(c.get("lang", "python"), c.get("item"))
                        c["blockHist"] = progress().get("qblocks", {}).get(c.get("item"))
                        if not c["itemData"]:
                            continue
                    out.append(c)
                return self.send_json({"cards": out})
            if path == "/api/cards/grade":
                return self.send_json(grade_card(str(b.get("id")), int(b.get("grade") or 0)))
            if path == "/api/interview/save_question":
                with user_priority():
                    return self.send_json(interview_save_question(str(b.get("question") or ""), str(b.get("track") or ""), str(b.get("model") or "")))
            if path == "/api/interview/drill":
                with user_priority():
                    return self.send_json(interview_drill(str(b.get("point") or ""), str(b.get("track") or "")))
            if path == "/api/cards/generate":
                deck = str(b.get("deck") or "")
                if deck not in [g["id"] for g in decks_view()["generators"]]:
                    raise ValueError("mazzo non valido")
                return self.send_json({"added": generate_cards(deck)})
            if path == "/api/cards/delete":
                with _PLOCK:
                    cards_save([c for c in cards_load() if c["id"] != str(b.get("id"))])
                return self.send_json({"ok": True})
            if path == "/api/review_code":
                lang = b.get("lang") if b.get("lang") in LANGNAME else "python"
                with user_priority():
                    return self.send_json(review_code(lang, str(b.get("statement", "")), str(b.get("solution", "")),
                                                      [str(c) for c in (b.get("criteria") or [])], str(b.get("code", ""))[:8000]))
            if path in ("/api/check_fill", "/api/check_output"):
                lang = b.get("lang") if b.get("lang") in LANGNAME else "python"
                code = norm_code(b.get("code"))
                if path == "/api/check_fill":
                    code = fill_blanks(code, [str(a) for a in (b.get("answers") or [])])
                r = run_program(lang, code)
                out = norm_out(r.get("stdout"))
                return self.send_json({"ok": bool(r["ok"] and out == norm_out(b.get("output"))), "stdout": out,
                                       "error": r.get("error") if not r["ok"] else None})
            if path == "/api/config":
                if b.get("model"):
                    CONFIG["model"] = str(b["model"])
                    save_json(CONFIG_FILE, CONFIG)
                return self.send_json({"ok": True, "model": CONFIG.get("model")})
            if path == "/api/lesson":
                req = str(b.get("request") or "").strip()[:400]
                lang = b.get("lang") if b.get("lang") in LANGNAME else "python"
                level = "intermedio" if b.get("level") == "intermedio" else "base"
                if not req:
                    return self.send_json({"error": "Scrivi cosa vuoi imparare."}, 400)
                lesson = generate_lesson(req, lang, level)
                save_json(LESSONS / (lesson["id"] + ".json"), lesson)
                return self.send_json(lesson)
            if path == "/api/topic":
                title = str(b.get("title") or "").strip()[:120]
                lang = b.get("lang") if b.get("lang") in LANGNAME else "python"
                if not title:
                    return self.send_json({"error": "Scrivi un argomento."}, 400)
                now = time.time()
                t = {"id": "t" + uuid.uuid4().hex[:10], "kind": "topic", "title": title, "request": title, "lang": lang,
                     "concepts": [], "blocks": [], "exercises": [], "created": now, "updated": now}
                save_json(LESSONS / (t["id"] + ".json"), t)
                return self.send_json(t)
            if path == "/api/exercise":
                ex = generate_exercise(b.get("type"), b.get("lang"), b.get("difficulty"),
                                       str(b.get("topic") or "")[:600], [str(a) for a in (b.get("avoid") or [])])
                return self.send_json(ex)
            if path == "/api/run":
                lang = b.get("lang") if b.get("lang") in LANGNAME else "python"
                code = norm_code(b.get("code"))
                if b.get("mode") == "program":
                    return self.send_json(run_program(lang, code))
                if b.get("tolerant"):
                    r = run_tests(lang, code, b.get("tests"))
                    if not r["all_ok"]:
                        code2, notes = adapt_names(lang, code, b.get("tests"))
                        if notes:
                            r2 = run_tests(lang, code2, b.get("tests"))
                            if r2["all_ok"] or len([t for t in r2.get("tests", []) if t["ok"]]) > len([t for t in r.get("tests", []) if t["ok"]]):
                                r = dict(r2, adapted=notes)
                    return self.send_json(r)
                return self.send_json(run_tests(lang, code, b.get("tests")))
            if path == "/api/code_review":
                lang = b.get("lang") if b.get("lang") in LANGNAME else "python"
                with user_priority():
                    return self.send_json(code_review(lang, str(b.get("task") or "")[:2000], norm_code(b.get("code")),
                                                      norm_code(b.get("reference")), str(b.get("outcome") or "")[:1500]))
            if path == "/api/judge":
                return self.send_json(judge(str(b.get("question", "")), str(b.get("reference", "")),
                                            str(b.get("why", "")), str(b.get("answer", ""))[:1500]))
            if path == "/api/ask":
                ctx = str(b.get("context") or "")[:8000]
                turns = [t for t in (b.get("messages") or []) if isinstance(t, dict)
                         and t.get("role") in ("user", "assistant") and str(t.get("content", "")).strip()][-10:]
                if not turns or turns[-1]["role"] != "user":
                    return self.send_json({"error": "Scrivi una domanda."}, 400)
                msgs = [{"role": "system", "content": TUTOR_SYS + ("\n\nContesto attuale:\n" + ctx if ctx else "")}]
                msgs += [{"role": t["role"], "content": str(t["content"])[:4000]} for t in turns]
                gen = llm_stream(msgs)
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Accel-Buffering", "no")
                self.end_headers()
                try:
                    for piece in gen:
                        self.wfile.write(piece.encode("utf-8"))
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                self.close_connection = True
                return
            self.send_json({"error": "Percorso sconosciuto."}, 404)
        except LLMError as e:
            self.send_json({"error": str(e)}, 502)
        except ValueError as e:
            self.send_json({"error": str(e)}, 400)
        except Exception as e:
            log_event("api_error", path=path, err=str(e)[:300])
            self.send_json({"error": f"Errore interno: {e}"}, 500)


def main():
    for d in (LESSONS, POOL, THEORY, INTERVIEWS, QUICK):
        d.mkdir(parents=True, exist_ok=True)
    threading.Thread(target=worker_loop, daemon=True, name="ricalco-worker").start()
    threading.Thread(target=lesson_loop, daemon=True, name="ricalco-lezioni").start()
    srv = None
    port = PORT
    for port in range(PORT, PORT + 10):
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            break
        except OSError:
            continue
    if not srv:
        sys.exit("Nessuna porta libera tra %d e %d." % (PORT, PORT + 9))
    url = f"http://127.0.0.1:{port}/"
    print(f"\n  Ricalco è attivo su {url}")
    model = current_model()
    print(f"  Ollama: {'ok, modello ' + model if model else 'NON raggiungibile su ' + OLLAMA}")
    j = java_info()
    print(f"  Java: {j['version'] or 'non trovato (servirà solo per gli esercizi in Java)'}"
          + (f"  ({'JDK' if j.get('jdk') else 'JRE, senza compilatore: serve un JDK'} in {j.get('home')})" if j.get('version') else ""))
    print("  Per chiudere: Ctrl+C oppure chiudi questa finestra.\n")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
