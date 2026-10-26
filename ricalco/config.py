"""Configurazione, percorsi dei dati, salvataggio JSON, log d'uso e priorità delle richieste."""

import json
import os
import subprocess
import threading
import time
from pathlib import Path

from .spring_runner import make_runners


ROOT = Path(__file__).resolve().parent.parent   # la cartella di Ricalco (qui ci sono static/, data/, progetti/)
STATIC = ROOT / "static"
DATA = ROOT / "data"


def app_lang():
    """Lingua dell'app: "it" (predefinita) o "en". La sceglie lo studente dal selettore in alto."""
    return "en" if CONFIG.get("lang") == "en" else "it"


class LangDir:
    """Una cartella di contenuti generati che cambia con la lingua: data/<nome> in italiano, data/en/<nome> in inglese.
    Così le lezioni e gli esercizi italiani e quelli inglesi restano separati e si cambia lingua senza perdere niente."""

    def __init__(self, name):
        self.name = name

    def path(self):
        return DATA / self.name if app_lang() == "it" else DATA / "en" / self.name

    def __truediv__(self, other):
        return self.path() / other

    def glob(self, pattern):
        return self.path().glob(pattern)

    def mkdir(self, *a, **k):
        return self.path().mkdir(*a, **k)

    def exists(self):
        return self.path().exists()

    def __fspath__(self):
        return str(self.path())

    def __str__(self):
        return str(self.path())


LESSONS = LangDir("lessons")
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
