"""Esecuzione del codice: Python e Java con i test, programmi completi, scelta del JDK, nomi adattati."""

import builtins as _bi
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .spring_runner import SpringRunner
from .sql_runner import run_sql, script_output
from .config import JAVA_TIMEOUT, LANGNAME, NOWINDOW, ROOT, RUN_TIMEOUT
from .llm import llm_json


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
    from .generazione import SYS_GEN
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
