"""Progetti a tappe: scrittura dei file, esecuzione (script, Maven, SQL) e viste."""

import os
import shutil
import sqlite3
import subprocess
import sys
import time

from .projects import PROJECTS, snapshot, step_view
from .sql_runner import run_sql
from .config import DATA, ROOT, SPRING, log_event
from .esecuzione import run_proc
from .percorsi import _PLOCK, _PYMOD, progress, progress_save, py_has, today


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
