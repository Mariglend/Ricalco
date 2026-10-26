"""Server HTTP: le API, i file statici e l'avvio."""

import contextlib
import json
import random
import re
import sys
import threading
import time
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .curriculum import INTERVIEW_MIX, PATHS, SESSION_SIZE, TYPE_ORDER
from .projects import PROJECTS
from .sql_runner import run_sql, same_result
from .config import app_lang
from .config import (
    CONFIG, CONFIG_FILE, LANGNAME, LESSONS, LLMError, LOGS, OLLAMA, PORT, RUNNERS, SPRING, STATIC, load_json,
    log_event, save_json, user_priority)
from .llm import current_model, list_models, llm_stream, pick_model
from .esecuzione import adapt_names, code_review, java_info, norm_code, run_program, run_tests
from .generazione import TUTOR_SYS, fill_blanks, generate_exercise, generate_lesson, judge, norm_out, review_code
from .percorsi import (
    FOCUS, INTERVIEW_BY, POOL, THEORY, WORKER, _PLOCK, adaptive_mix, key_info, pick_session, pool_load, pool_remove,
    progress, progress_save, unit_available, unit_lesson_path, unit_of, unlocked, worker_loop, xl)
from .lezioni import (
    get_unit_lesson, lesson_loop, lesson_recheck, lesson_regen, lesson_request, lesson_status, unit_reset)
from .oggi import (
    QUICK, QUICK_FOCUS, elo_state, elo_view, item_rating, quick_done, quick_free_run, quick_item, quick_pick,
    variant_done, variant_get, variant_make, weekly_done, weekly_make, weekly_pending, weekly_view)
from .diario import logs_summary
from .feynman import feynman
from .progetti import (
    open_folder, project_copy, project_dir, project_install, project_run, project_start, project_step_done,
    project_view, projects_view)
from .progressi import curriculum_view, get_theory, home_view, lesson_done, record_level, record_result, rewrite_card
from .colloquio import (
    INTERVIEWS, followup, interview_drill, interview_report, interview_save_question, interview_view,
    interviewer_system, judge_answer, logic_view)
from .flashcard import cards_load, cards_save, deck_title, decks_view, generate_cards, grade_card
from .catalogo import catalog_view
from .approfondimenti import (
    banca_answer, banca_next, banca_view, design_followup, design_get, design_judge, design_list, review_get, review_judge,
    review_list, soft_judge, soft_list)
from .diagnostica import selftest_run, selftest_steps


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
        from .i18n import localize
        data = json.dumps(localize(obj), ensure_ascii=False).encode("utf-8")
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
        if f.name == "index.html":
            data = data.replace(b'<html lang="it">', f'<html lang="{app_lang()}">'.encode(), 1)
        self.send_response(200)
        self.send_header("Content-Type", MIME.get(f.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def api_get(self, path, q):
        # catalogo di algoritmi e colloquio approfondito
        if path == "/api/algoritmi":
            return self.send_json(catalog_view("java" if q.get("lang") == "java" else "python"))
        if path == "/api/bank":
            return self.send_json(banca_view())
        if path == "/api/bank/next":
            try:
                return self.send_json(banca_next(q.get("area") or None, q.get("level") or None,
                                                 [x for x in (q.get("skip") or "").split(",") if x], q.get("id") or None))
            except ValueError as e:
                return self.send_json({"error": str(e)}, 400)
        if path == "/api/design":
            return self.send_json({"items": design_list()} if not q.get("id") else design_get(q["id"]))
        if path == "/api/review_ex":
            return self.send_json({"items": review_list()} if not q.get("id") else review_get(q["id"]))
        if path == "/api/soft":
            return self.send_json({"items": soft_list()})
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
            from .oggi import start_level
            e = elo_state(p, lang)
            return self.send_json({"item": it, "elo": elo_view(e, lang), "itemRating": round(item_rating(p, it)),
                                   "startLevel": start_level(e["r"], item_rating(p, it), e.get("help", 1)),
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
                from .llm import _MODEL_CACHE
                _MODEL_CACHE.update(models=models, t=time.time())
            except Exception:
                models, ok = [], False
            j = java_info()
            return self.send_json({"ollama": ok, "ollamaUrl": OLLAMA, "models": models, "model": pick_model(models),
                                   "python": sys.version.split()[0], "java": j["version"], "lang": app_lang()})
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
                        "/api/interview/turn", "/api/interview/report", "/api/cards/generate", "/api/bank/answer", "/api/design/judge",
                        "/api/design/followup", "/api/review_ex/judge", "/api/soft/judge")
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
            if path == "/api/bank/answer":
                return self.send_json(banca_answer(str(b.get("id")), int(b.get("step") or 0), str(b.get("answer") or ""), bool(b.get("en"))))
            if path == "/api/design/judge":
                return self.send_json(design_judge(str(b.get("id")), str(b.get("text") or "")))
            if path == "/api/design/followup":
                return self.send_json(design_followup(str(b.get("id")), str(b.get("question") or ""), str(b.get("answer") or ""), bool(b.get("en"))))
            if path == "/api/review_ex/judge":
                return self.send_json(review_judge(str(b.get("id")), str(b.get("text") or "")))
            if path == "/api/soft/judge":
                return self.send_json(soft_judge(str(b.get("id")), str(b.get("answer") or ""), bool(b.get("en"))))
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
                if b.get("lang") in ("it", "en"):
                    CONFIG["lang"] = b["lang"]
                save_json(CONFIG_FILE, CONFIG)
                return self.send_json({"ok": True, "model": CONFIG.get("model"), "lang": app_lang()})
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

