/* Ricalco: frontend. Nessuna dipendenza esterna. */
"use strict";

/* ================================================================ utilità */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
const inl = s => esc(s).replace(/`([^`\n]+)`/g, "<code>$1</code>").replace(/\*\*([^*\n]+)\*\*/g, "<b>$1</b>");
const LANG = {python: "Python", java: "Java", sql: "SQL"};
const FREE_LANGS = ["python", "java"];
const PATHS = {
  python: {name: "Python", goal: "Da zero a FastAPI", lang: "python"},
  java: {name: "Java", goal: "Da zero a Spring Boot", lang: "java"},
  sql: {name: "SQL", goal: "Da zero a SQL da colloquio", lang: "sql"},
  algopy: {name: "Algoritmi · Python", goal: "Algoritmi e strutture dati", lang: "python", algo: true},
  algojava: {name: "Algoritmi · Java", goal: "Algoritmi e strutture dati", lang: "java", algo: true}
};
const LEVELS = {
  1: {name: "Ricalco", desc: "Il blocco appare in trasparenza: ricalcalo."},
  2: {name: "Struttura", desc: "Vedi parole chiave e punteggiatura; nomi e valori li scrivi tu."},
  3: {name: "Memoria", desc: "Il codice non si vede: scrivi il blocco partendo dalla spiegazione."},
  4: {name: "Scrivi tu", desc: "Scrivi il programma come vuoi tu: Ricalco lo esegue e Qwen lo corregge."}
};
const DIFFS = {facile: "Facile", medio: "Medio", difficile: "Difficile"};
const TYPES = {
  predici: {name: "Prevedi l'output", desc: "Leggi il codice e scrivi cosa stampa."},
  riordina: {name: "Riordina le righe", desc: "Le righe giuste sono mescolate: rimettile in ordine."},
  completa: {name: "Completa il codice", desc: "Mancano dei pezzi segnati con TODO."},
  bug: {name: "Trova il bug", desc: "Il codice ha un errore logico: trovalo e correggilo."},
  zero: {name: "Scrivi da zero", desc: "Hai solo la firma: il resto è tuo."}
};
const TYPES_BY_DIFF = {facile: ["predici", "riordina", "completa"], medio: ["completa", "bug", "predici", "riordina"], difficile: ["zero", "bug", "completa"]};
const EXAMPLES = {
  python: ["Contare quante volte compare ogni parola in un testo", "Una classe ContoBancario con deposito e prelievo",
           "Ricorsione: fattoriale e Fibonacci", "Filtrare e ordinare una lista di dizionari"],
  java: ["ArrayList: aggiungere, cercare e rimuovere elementi", "Una classe Studente con costruttore, getter e toString",
         "HashMap per contare le occorrenze di parole", "Gestire le eccezioni con try/catch"]
};

function md(text) {
  const out = [];
  const parts = String(text).split(/```[\w+#-]*\n?([\s\S]*?)(?:```|$)/g);
  parts.forEach((p, i) => {
    if (i % 2 === 1) { if (p.trim()) out.push(`<pre class="snip askable">${esc(p.replace(/\n$/, ""))}</pre>`); return; }
    const paras = p.split(/\n{2,}/);
    for (const para of paras) {
      if (!para.trim()) continue;
      const lines = para.split("\n");
      if (lines.every(l => /^\s*([-*]|\d+[.)])\s+/.test(l) || !l.trim())) {
        const ordered = /^\s*\d/.test(lines[0]);
        out.push(`<${ordered ? "ol" : "ul"}>` + lines.filter(l => l.trim()).map(l => `<li>${inl(l.replace(/^\s*([-*]|\d+[.)])\s+/, ""))}</li>`).join("") + `</${ordered ? "ol" : "ul"}>`);
      } else {
        out.push(`<p>${lines.map(inl).join("<br>")}</p>`);
      }
    }
  });
  return out.join("");
}

async function api(path, {method = "GET", body, signal} = {}) {
  const headers = {"X-Ricalco": "1"};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  let r;
  try {
    r = await fetch(path, {method, headers, signal, body: body !== undefined ? JSON.stringify(body) : undefined});
  } catch (e) {
    if (e.name === "AbortError") throw e;
    throw new Error("Il server di Ricalco non risponde: è ancora aperta la finestra di avvio?");
  }
  const isJson = (r.headers.get("Content-Type") || "").includes("json");
  const data = isJson ? await r.json() : await r.text();
  if (!r.ok) throw new Error((data && data.error) || `Errore ${r.status}`);
  return data;
}

/* ---- log d'uso: eventi salvati sul tuo PC (data/logs) per capire dove ti blocchi */
const LOG = {
  q: [], timer: null,
  ev(ev, d = {}) {
    this.q.push(Object.assign({t: Date.now() / 1000, ev, view: App.view}, d));
    clearTimeout(this.timer); this.timer = setTimeout(() => this.flush(), 2000);
    if (this.q.length > 40) this.flush();
  },
  flush() {
    if (!this.q.length) return;
    const events = this.q.splice(0);
    fetch("/api/log", {method: "POST", keepalive: true, headers: {"X-Ricalco": "1", "Content-Type": "application/json"}, body: JSON.stringify({events})}).catch(() => {});
  }
};
addEventListener("pagehide", () => LOG.flush());
document.addEventListener("visibilitychange", () => { if (document.hidden) LOG.flush(); });
addEventListener("error", e => LOG.ev("js_error", {msg: String(e.message || e).slice(0, 300)}));
const secsSince = t => Math.round((Date.now() - t) / 100) / 10;

let toastTimer;
function toast(msg) {
  const t = $("#toast");
  t.textContent = msg; t.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => { t.hidden = true; }, 3200);
}
function shuffled(n) {
  const a = [...Array(n).keys()];
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
  return a;
}
function timerEl(el) {
  const t0 = Date.now();
  const id = setInterval(() => { if (!document.body.contains(el)) return clearInterval(id); const s = Math.round((Date.now() - t0) / 1000); el.textContent = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; }, 500);
  return () => clearInterval(id);
}
function insertText(ta, text) {
  ta.focus();
  if (!document.execCommand || !document.execCommand("insertText", false, text)) {
    const s = ta.selectionStart;
    ta.setRangeText(text, s, ta.selectionEnd, "end");
    ta.dispatchEvent(new Event("input"));
  }
}

/* ================================================================ stato */
const App = {
  status: null, lessons: [], L: null, view: "home",
  lang: FREE_LANGS.includes(localStorage.getItem("ricalco.lang")) ? localStorage.getItem("ricalco.lang") : "python",
  path: PATHS[localStorage.getItem("ricalco.path")] ? localStorage.getItem("ricalco.path") : (localStorage.getItem("ricalco.lang") === "java" ? "java" : "python"),
  qlang: localStorage.getItem("ricalco.qlang") || "python",
  qlevel: +(localStorage.getItem("ricalco.qlevel") || 1),
  level: localStorage.getItem("ricalco.newlevel") || "base",
  traceLevel: +(localStorage.getItem("ricalco.trace") || 1),
  diff: "facile", exType: null, exId: null, tracer: null, gen: null
};
let saveTimer = null;
function saveLesson(now) {
  const L = App.L; if (!L) return;
  clearTimeout(saveTimer);
  const go = () => api(`/api/lessons/${L.id}`, {method: "PUT", body: L}).catch(e => toast("Salvataggio non riuscito: " + e.message));
  if (now) go(); else saveTimer = setTimeout(go, 600);
}

/* ================================================================ stato modello */
async function refreshStatus() {
  try { App.status = await api("/api/status"); } catch (e) { App.status = {ollama: false, models: [], error: e.message}; }
  const s = App.status, sel = $("#modelSel"), dot = $("#modelDot");
  dot.className = "dot " + (s.ollama && s.model ? "on" : "off");
  sel.innerHTML = s.models && s.models.length
    ? s.models.map(m => `<option ${m === s.model ? "selected" : ""}>${esc(m)}</option>`).join("")
    : `<option>${s.ollama ? "nessun modello" : "Ollama spento"}</option>`;
  sel.disabled = !(s.models && s.models.length);
  return s;
}
$("#modelSel").addEventListener("change", async e => {
  await api("/api/config", {method: "POST", body: {model: e.target.value}});
  await refreshStatus(); toast("Modello: " + e.target.value);
});
function ollamaBanner() {
  const s = App.status;
  if (!s) return "";
  if (s.error) return `<div class="banner err"><b>Il server di Ricalco non risponde.</b><span>Riavvialo con <code>avvia.bat</code> (o <code>python server.py</code>).</span></div>`;
  if (!s.ollama) return `<div class="banner err"><b>Ollama non risponde su ${esc(s.ollamaUrl || "127.0.0.1:11434")}.</b>
    <span>Apri l'app Ollama (o lancia <code>ollama serve</code>) e poi premi Riprova. Se non hai ancora il modello: <code>ollama pull qwen2.5-coder:7b</code></span>
    <div><button class="btn small" id="retryStatus">Riprova</button></div></div>`;
  if (!s.model) return `<div class="banner"><b>Ollama è acceso ma non c'è nessun modello.</b><span>Installa Qwen: <code>ollama pull qwen2.5-coder:7b</code>, poi premi Riprova.</span><div><button class="btn small" id="retryStatus">Riprova</button></div></div>`;
  if (!/qwen/i.test(s.model)) return `<div class="banner"><span>Stai usando <code>${esc(s.model)}</code>. Ricalco è tarato su Qwen: puoi cambiarlo dal menu in alto a destra.</span></div>`;
  return "";
}

/* ================================================================ router */
function crumbs(items, current = items.length - 1) {
  if (items[0].href !== "#/percorso") { items = [{href: "#/percorso", label: "Percorsi"}].concat(items); current += 1; }
  $("#crumbs").innerHTML = items.map((it, i) => (i ? `<span class="sep">/</span>` : "") +
    `<a href="${it.href}" ${i === current ? 'aria-current="page"' : ""}>${esc(it.label)}</a>`).join("");
}
async function route() {
  const h = location.hash.slice(1) || "/";
  LOG.ev("view", {hash: h});
  let m;
  App.tracer = null;
  if (P.s) { clearTimeout(P.s.poll); P.s = null; }
  clearInterval(App.liveInt); App.sim = null; App.study = null;
  $("#view").onclick = null;
  $("#view").scrollTop = 0;
  try {
    if ((m = h.match(/^\/l\/([a-z0-9]+)/))) return await openLesson(m[1]);
    if ((m = h.match(/^\/e\/([a-z0-9]+)(?:\/([a-z0-9]+))?/))) return await openExercises(m[1], m[2]);
    if ((m = h.match(/^\/s\/([a-z]+\/[a-z0-9_]+\/(?:base|pratica|sfida))$/))) return await startSession(m[1]);
    if ((m = h.match(/^\/live\/(logica\/[a-z_]+\/(?:base|pratica|sfida))$/))) return await startSession(m[1], false, {live: true});
    if ((m = h.match(/^\/sim\/([a-z_]+)\/(base|pratica|sfida)$/))) return await showSim(m[1], m[2]);
    if ((m = h.match(/^\/report\/([a-z0-9]+)$/))) return await showReport(m[1]);
    if ((m = h.match(/^\/carte\/(.+)$/))) return await studyDeck(decodeURIComponent(m[1]));
    if (h === "/carte") return await showCards();
    if (h === "/prova") return await showSelftest();
    if (h === "/diario") return await showDiary();
    if (h === "/progetti") return await showProjects();
    if ((m = h.match(/^\/progetto\/([a-z-]+)(?:\/(\d+))?$/))) return await showProject(m[1], m[2] ? +m[2] - 1 : undefined);
    if (h === "/logica") return await showLogic();
    if (h === "/algoritmi") return await showCatalog();
    if ((m = h.match(/^\/oggi\/(python|java|sql)\/([A-Za-z0-9_-]+)$/))) return await openQuickItem(m[1], m[2]);
    if (h === "/colloquio") return await showInterview();
    if (h === "/colloquio/domande") return await showBank();
    if ((m = h.match(/^\/colloquio\/domande\/q\/([a-z]+-\d+)$/))) return await bankSession(m[1].split("-")[0], null, m[1]);
    if ((m = h.match(/^\/colloquio\/domande\/([a-z]+)(?:\/(\d))?$/))) return await bankSession(m[1], m[2]);
    if (h === "/colloquio/design") return await showDesignList();
    if ((m = h.match(/^\/colloquio\/design\/([a-z0-9-]+)$/))) return await showDesign(m[1]);
    if (h === "/colloquio/review") return await showReviewList();
    if ((m = h.match(/^\/colloquio\/review\/([a-z0-9-]+)$/))) return await showReviewEx(m[1]);
    if (h === "/colloquio/soft") return await showSoft();
    if ((m = h.match(/^\/r\/([a-z]+)$/)) && PATHS[m[1]]) return await startSession(m[1], true);
    if ((m = h.match(/^\/t\/([a-z]+)\/(u\d+)$/)) && PATHS[m[1]]) return await showTheory(m[1], m[2]);
    if (h === "/libere") return showHome();
    if ((m = h.match(/^\/percorso(?:\/([a-z]+))?$/))) { if (m[1] && PATHS[m[1]]) setPath(m[1]); return showPath(); }
  } catch (e) {
    toast(e.message); location.hash = "#/"; return;
  }
  showStart();
}
window.addEventListener("hashchange", route);

async function loadLesson(id) {
  if (App.L && App.L.id === id) return App.L;
  const L = await api(`/api/lessons/${id}`);
  if (App.L && App.L.id !== id) Tutor.reset();
  App.L = L;
  return L;
}
