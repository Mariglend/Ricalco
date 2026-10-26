"""Client di Ollama: chiamate con risposta JSON (schema) e in streaming, interrompibili dal lavoro in sottofondo."""

import json
import re
import time
import urllib.request

from .config import CONFIG, LLMError, NUM_CTX, OLLAMA, Preempted, _TL, app_lang, log_event, user_busy


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


_MODEL_CACHE = {"t": 0.0, "models": None}


def current_model():
    """Il modello in uso. L'elenco di Ollama si rilegge al massimo ogni 20 secondi, non a ogni chiamata."""
    now = time.time()
    if _MODEL_CACHE["models"] is None or now - _MODEL_CACHE["t"] > 20:
        try:
            _MODEL_CACHE.update(models=list_models(), t=now)
        except Exception:
            _MODEL_CACHE.update(models=None, t=0.0)
            return None
    return pick_model(_MODEL_CACHE["models"])


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


LANG_EN = ("LANGUAGE: the student is using Ricalco in ENGLISH. Write every text meant for the student in clear, simple English "
           "(titles, explanations, questions, options, comments, hints, feedback), even though these instructions are in Italian. "
           "Keep JSON keys exactly as requested (they stay in Italian). Code identifiers may stay as they are, comments in code in English.")


# Tetto alla lunghezza della risposta: una generazione che si incarta (ripete all'infinito) si ferma invece di
# occupare la GPU per minuti. Le lezioni più lunghe stanno sotto i 3000 token.
NUM_PREDICT = 4096


def chat_body(model, messages, stream, temperature, num_ctx, fmt=None):
    """Corpo della richiesta a Ollama. Il contesto è sempre lo stesso (NUM_CTX): se cambia da una chiamata all'altra,
    Ollama ricarica il modello in memoria e ogni cambio costa diversi secondi. num_ctx resta come parametro per
    compatibilità ma non viene usato."""
    if app_lang() == "en":
        messages = list(messages) + [{"role": "system", "content": LANG_EN}]
    body = {"model": model, "messages": messages, "stream": stream, "keep_alive": "30m",
            "options": {"temperature": temperature, "num_ctx": NUM_CTX, "num_predict": NUM_PREDICT}}
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
