"""Lingua inglese: traduce i testi italiani fissi (interfaccia, messaggi, curriculum, esercizi pronti) nelle risposte dell'API.

Il dizionario è uno solo, static/i18n/en.js, condiviso con la pagina. Le chiavi con {} sono modelli:
«Livello {} · {}» traduce anche «Livello 3 · Pratica», e i pezzi al posto di {} vengono tradotti a loro volta.
Il codice non si traduce mai (vedi CODE_KEYS)."""

import json
import re

from .config import ROOT, app_lang

DICT_FILE = ROOT / "static" / "i18n" / "en.js"
# chiavi delle risposte che contengono codice, output o identificatori: restano come sono
CODE_KEYS = {"code", "solution", "starter", "output", "expected", "stdout", "stderr", "tests", "tests_java", "setup", "verify",
             "files", "before", "after", "removed", "lines", "id", "uid", "unit", "lang", "model", "models", "path", "file",
             "answer_code", "reference", "schema", "sql", "query", "diff", "ref", "key", "deck", "kind", "type", "status"}

_exact = None
_patterns = []


def _load():
    global _exact, _patterns
    if _exact is not None:
        return
    try:
        text = DICT_FILE.read_text(encoding="utf-8")
        m = re.search(r"window\.I18N_EN\s*=\s*(\{.*?\n\});", text, re.S)
        _exact = json.loads(m.group(1))
    except Exception:
        _exact = {}
    pats = []
    for k, v in _exact.items():
        if "{}" in k and len(k.replace("{}", "")) >= 3 and re.search(r"[a-zà-ù]", k.replace("{}", ""), re.I):
            rx = "^" + "(.+?)".join(re.escape(p) for p in k.split("{}")) + "$"
            pats.append((len(k.replace("{}", "")), re.compile(rx, re.S), v))
    # i modelli più lunghi (più specifici) prima
    _patterns = sorted(pats, key=lambda x: -x[0])


def _by_pattern(st, depth, long):
    for n, rx, v in _patterns:
        if (n >= 14) != long:
            continue
        m = rx.match(st)
        if m:
            out = v
            for g in m.groups():
                out = out.replace("{}", tr(g, depth + 1), 1)
            return out
    return None


def tr(s, depth=0):
    """Traduce una stringa: corrispondenza esatta, poi i modelli con {}; se non la conosce la lascia com'è."""
    _load()
    if not isinstance(s, str) or not s.strip():
        return s
    if s in _exact:
        return _exact[s]
    st = s.strip()
    if st != s and st in _exact:
        return s.replace(st, _exact[st])
    if depth > 3 or len(s) > 600:
        return s
    # prima i modelli lunghi (specifici), poi gli elenchi «13 esercizi passati, 33 carte» pezzo per pezzo, poi i modelli corti
    hit = _by_pattern(st, depth, True)
    if hit is not None:
        return s.replace(st, hit)
    for sep in (" · ", ", "):
        if sep in st:
            parts = st.split(sep)
            out = [tr(x, depth + 1) for x in parts]
            if all(o != x or re.fullmatch(r"[\d\s.,%/+-]*", x) for o, x in zip(out, parts)):
                return s.replace(st, sep.join(out))
    hit = _by_pattern(st, depth, False)
    if hit is not None:
        return s.replace(st, hit)
    # testi composti da più pezzi: «13 esercizi valutati · Avanzato a 1175»
    if " · " in st:
        out = " · ".join(tr(x, depth + 1) for x in st.split(" · "))
        if out != st:
            return s.replace(st, out)
    m = re.match(r"^([\d.,%+-]+\s+)(\D.*)$", st, re.S)
    if m:
        w = tr(m.group(2), depth + 1)
        if w != m.group(2):
            return s.replace(st, m.group(1) + w)
    return s


def translate_obj(obj, key=None):
    if key in CODE_KEYS:
        return obj
    if isinstance(obj, str):
        return tr(obj)
    if isinstance(obj, list):
        return [translate_obj(x, key) for x in obj]
    if isinstance(obj, dict):
        return {k: translate_obj(v, k) for k, v in obj.items()}
    return obj


def localize(obj):
    """Applicata a ogni risposta JSON: in italiano non fa niente."""
    return translate_obj(obj) if app_lang() == "en" else obj
