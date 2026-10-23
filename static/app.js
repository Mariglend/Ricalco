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
    if (h === "/colloquio") return await showInterview();
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

/* ================================================================ home */
async function showHome() {
  App.view = "home"; App.L = App.L || null;
  if (!FREE_LANGS.includes(App.lang)) App.lang = "python";
  mainNav("libere");
  Tutor.setContext("", "Sei nella home. Puoi chiedere al tutor qualsiasi cosa sulla programmazione.");
  Tutor.setQuick(["Da dove comincio con Python?", "Differenza tra Python e Java?"]);
  const v = $("#view");
  v.innerHTML = `<section class="home">
    <div class="ask-card">
      <h1>Lezione libera: cosa vuoi imparare?</h1>
      <p class="sub">Descrivi un programma o un concetto. Il tuo modello prepara una lezione: prima ti fa ragionare con una domanda, poi riscrivi il codice blocco per blocco, poi ti eserciti a tre livelli di difficoltà.</p>
      <form id="newForm" class="ask-card" style="gap:10px;padding:0">
        <textarea id="newReq" class="new-req" rows="2" placeholder="Es. contare quante volte compare ogni parola in un testo"></textarea>
        <div class="form-row">
          <div class="seg" role="group" aria-label="Linguaggio">
            ${FREE_LANGS.map(k => `<button type="button" data-lang="${k}" aria-pressed="${App.lang === k}">${LANG[k]}</button>`).join("")}
          </div>
          <div class="seg" role="group" aria-label="Livello">
            <button type="button" data-level="base" aria-pressed="${App.level === "base"}">Principiante</button>
            <button type="button" data-level="intermedio" aria-pressed="${App.level === "intermedio"}">Intermedio</button>
          </div>
          <span class="spacer"></span>
          <button type="button" class="btn" id="onlyEx" title="Salta la lezione e vai dritto agli esercizi su questo argomento">Solo esercizi</button>
          <button type="submit" class="btn primary">Crea la lezione</button>
        </div>
        <div class="chips" id="exampleChips"></div>
      </form>
      <div id="genBox"></div>
    </div>
    <div id="warn">${ollamaBanner()}</div>
    <div class="stats-row" id="stats"></div>
    <div><h2 class="section-title">Le tue lezioni</h2><div class="lesson-list" id="lessonList"><div class="empty">Caricamento…</div></div></div>
  </section>`;
  const paintChips = () => {
    $("#exampleChips").innerHTML = EXAMPLES[App.lang].map(x => `<button type="button" class="chip" data-ex="${esc(x)}">${esc(x)}</button>`).join("");
  };
  paintChips();
  v.onclick = homeClick;
  $("#newForm").addEventListener("submit", e => { e.preventDefault(); createLesson(); });
  $("#newReq").addEventListener("keydown", e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); createLesson(); } });
  function homeClick(e) {
    const t = e.target.closest("button"); if (!t) return;
    if (t.dataset.lang) { App.lang = t.dataset.lang; localStorage.setItem("ricalco.lang", App.lang); $$("[data-lang]").forEach(b => b.setAttribute("aria-pressed", String(b === t))); paintChips(); }
    else if (t.dataset.level) { App.level = t.dataset.level; localStorage.setItem("ricalco.newlevel", App.level); $$("[data-level]").forEach(b => b.setAttribute("aria-pressed", String(b === t))); }
    else if (t.dataset.ex) { $("#newReq").value = t.dataset.ex; $("#newReq").focus(); }
    else if (t.id === "onlyEx") createTopic();
    else if (t.id === "retryStatus") refreshStatus().then(() => { $("#warn").innerHTML = ollamaBanner(); });
    else if (t.dataset.del) {
      if (t.dataset.armed) { api(`/api/lessons/${t.dataset.del}`, {method: "DELETE"}).then(() => { if (App.L && App.L.id === t.dataset.del) App.L = null; renderLessonList(); }); }
      else { t.dataset.armed = "1"; t.textContent = "Conferma"; setTimeout(() => { if (t.isConnected) { delete t.dataset.armed; t.textContent = "Elimina"; } }, 3500); }
    }
  }
  if (App.gen) renderGen();
  renderLessonList();
  if (!App.status) refreshStatus().then(() => { if ($("#warn")) $("#warn").innerHTML = ollamaBanner(); });
}

async function renderLessonList() {
  try { App.lessons = await api("/api/lessons"); } catch (e) { App.lessons = []; }
  const list = $("#lessonList"); if (!list) return;
  const Ls = App.lessons;
  let solved = {facile: 0, medio: 0, difficile: 0}, done = 0;
  Ls.forEach(L => { if (L.progress && L.progress.done) done++; (L.exercises || []).forEach(x => { if (x.state && x.state.solved && !x.state.revealed) solved[x.difficulty]++; }); });
  $("#stats").innerHTML = `
    <div class="stat"><b>${Ls.filter(l => l.kind === "lesson").length}</b><span>Lezioni</span></div>
    <div class="stat"><b>${done}</b><span>Completate</span></div>
    <div class="stat"><b>${solved.facile}</b><span>Esercizi facili</span></div>
    <div class="stat"><b>${solved.medio}</b><span>Esercizi medi</span></div>
    <div class="stat"><b>${solved.difficile}</b><span>Esercizi difficili</span></div>`;
  if (!Ls.length) { list.innerHTML = `<div class="empty">Nessuna lezione ancora. Scrivi qui sopra cosa vuoi imparare, o parti da un esempio.</div>`; return; }
  list.innerHTML = Ls.map(L => {
    const n = (L.blocks || []).length, p = L.progress || {};
    const pct = L.kind === "lesson" ? (p.done ? 100 : Math.round(((p.block || 0) / Math.max(1, n)) * 100)) : 0;
    const exs = (L.exercises || []), ok = exs.filter(x => x.state && x.state.solved).length;
    return `<article class="lcard">
      <div class="meta"><span class="tag acc">${LANG[L.lang] || L.lang}</span><span class="tag ${p.done ? "ok" : ""}">${L.kind === "lesson" ? (p.done ? "Completata" : "Lezione") : "Solo esercizi"}</span></div>
      <h3>${esc(L.title)}</h3>
      ${L.kind === "lesson" ? `<div class="bar" title="${pct}%"><i style="width:${pct}%"></i></div>` : ""}
      <span class="muted" style="font-size:13px">${L.kind === "lesson" ? `${n} blocchi · ` : ""}${ok}/${exs.length} esercizi risolti</span>
      <div class="acts">
        ${L.kind === "lesson" ? `<a class="btn ${p.done ? "" : "primary"} small" href="#/l/${L.id}">${p.done ? "Rivedi" : (p.block ? "Continua" : "Inizia")}</a>` : ""}
        <a class="btn small ${L.kind === "lesson" && !p.done ? "" : "primary"}" href="#/e/${L.id}">Esercizi</a>
        <span class="spacer"></span>
        <button class="btn small ghost danger" data-del="${L.id}">Elimina</button>
      </div></article>`;
  }).join("");
  $$(".lcard a.btn").forEach(a => a.style.textDecoration = "none");
}

function renderGen() {
  const box = $("#genBox"); if (!box) return;
  const g = App.gen;
  if (!g) { box.innerHTML = ""; return; }
  if (g.error) {
    box.innerHTML = `<div class="banner err"><b>Non sono riuscito a preparare la lezione.</b><span>${esc(g.error)}</span><div class="row"><button class="btn small" id="genRetry">Riprova</button><button class="btn small ghost" id="genClose">Chiudi</button></div></div>`;
    $("#genRetry").onclick = () => { $("#newReq").value = g.req; App.gen = null; createLesson(); };
    $("#genClose").onclick = () => { App.gen = null; renderGen(); };
    return;
  }
  box.innerHTML = `<div class="gen"><span class="spin"></span><div style="display:flex;flex-direction:column;gap:4px;flex:1">
    <p><b>Preparo la lezione su «${esc(g.req)}»</b> <span class="timer" id="genTimer">0:00</span></p>
    <p class="muted" style="font-size:13.5px">Qwen scrive il codice e le domande, poi Ricalco esegue il programma per controllare che funzioni prima di fartelo studiare. Con un 7B ci vuole da 30 secondi a 2 minuti.</p></div>
    <button class="btn small ghost" id="genCancel">Annulla</button></div>`;
  const t = $("#genTimer"), t0 = g.t0;
  const id = setInterval(() => { if (!t.isConnected) return clearInterval(id); const s = Math.round((Date.now() - t0) / 1000); t.textContent = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; }, 500);
  $("#genCancel").onclick = () => { g.ctl.abort(); App.gen = null; renderGen(); };
}

async function createLesson() {
  const req = $("#newReq").value.trim();
  if (!req) { $("#newReq").focus(); toast("Scrivi cosa vuoi imparare."); return; }
  if (App.gen && !App.gen.error) return;
  const ctl = new AbortController();
  App.gen = {req, t0: Date.now(), ctl};
  renderGen();
  try {
    const L = await api("/api/lesson", {method: "POST", body: {request: req, lang: App.lang, level: App.level}, signal: ctl.signal});
    App.gen = null; App.L = L; Tutor.reset();
    location.hash = `#/l/${L.id}`;
  } catch (e) {
    if (e.name === "AbortError") return;
    App.gen = {req, error: e.message}; renderGen();
  }
}
async function createTopic() {
  const req = $("#newReq").value.trim();
  if (!req) { $("#newReq").focus(); toast("Scrivi l'argomento su cui vuoi esercitarti."); return; }
  const T = await api("/api/topic", {method: "POST", body: {title: req, lang: App.lang}});
  App.L = T; Tutor.reset(); location.hash = `#/e/${T.id}`;
}

/* ================================================================ motore di ricalco */
const KW = new Set(("and as assert async await break class continue def del elif else except False finally for from global if import in is lambda None nonlocal not or pass raise return True try while with yield print self len range " +
  "abstract boolean byte case catch char const default do double enum extends final float goto implements instanceof int interface long native new null package private protected public short static super switch synchronized this throw throws transient void volatile var record true false String System").split(" "));

const SQL_KW = new Set(("SELECT FROM WHERE AND OR NOT IN IS NULL AS ON JOIN LEFT RIGHT INNER OUTER FULL CROSS GROUP BY ORDER HAVING LIMIT OFFSET " +
  "DISTINCT INSERT INTO VALUES UPDATE SET DELETE CREATE TABLE VIEW INDEX DROP ALTER ADD PRIMARY KEY FOREIGN REFERENCES UNIQUE DEFAULT CHECK " +
  "INTEGER TEXT REAL BLOB NUMERIC CASE WHEN THEN ELSE END EXISTS BETWEEN LIKE ASC DESC UNION ALL WITH RECURSIVE OVER PARTITION BEGIN COMMIT " +
  "ROLLBACK TRANSACTION CASCADE IF COUNT SUM AVG MIN MAX ROUND COALESCE UPPER LOWER LENGTH SUBSTR ABS RANK DENSE_RANK ROW_NUMBER LAG LEAD " +
  "EXPLAIN QUERY PLAN AUTOINCREMENT TRUE FALSE").split(" "));
function tokenize(t, lang) {
  const ty = new Array(t.length).fill("pun");
  const hash = lang === "python", slash = lang === "java", sql = lang === "sql";
  const fill = (a, b, v) => { for (let k = a; k < b; k++) ty[k] = v; };
  let i = 0;
  while (i < t.length) {
    const c = t[i], n = t[i + 1];
    if (c === " " || c === "\n") { ty[i] = "ws"; i++; continue; }
    if ((c === "#" && hash) || (c === "/" && n === "/" && slash) || (c === "-" && n === "-" && sql)) { let j = t.indexOf("\n", i); if (j < 0) j = t.length; fill(i, j, "com"); i = j; continue; }
    if (c === "/" && n === "*" && (slash || sql)) { let j = t.indexOf("*/", i + 2); j = j < 0 ? t.length : j + 2; fill(i, j, "com"); for (let k = i; k < j; k++) if (t[k] === "\n") ty[k] = "ws"; i = j; continue; }
    if (c === '"' || c === "'") {
      const triple = hash && t.slice(i, i + 3) === c.repeat(3);
      let j = i + (triple ? 3 : 1);
      while (j < t.length) {
        if (t[j] === "\\") { j += 2; continue; }
        if (triple ? t.slice(j, j + 3) === c.repeat(3) : t[j] === c) break;
        if (!triple && t[j] === "\n") break;
        j++;
      }
      const end = Math.min(j + (triple ? 3 : 1), t.length);
      fill(i, end, "str"); ty[i] = "q"; if (end - 1 > i && t[end - 1] === c) ty[end - 1] = "q";
      for (let k = i; k < end; k++) if (t[k] === "\n") ty[k] = "ws";
      i = end; continue;
    }
    if (/[0-9]/.test(c)) { let j = i; while (j < t.length && /[0-9._xa-fA-FlLdD]/.test(t[j])) j++; fill(i, j, "num"); i = j; continue; }
    if (/[A-Za-z_$]/.test(c)) { let j = i; while (j < t.length && /[\w$]/.test(t[j])) j++; fill(i, j, (sql ? SQL_KW.has(t.slice(i, j).toUpperCase()) : KW.has(t.slice(i, j))) ? "kw" : "id"); i = j; continue; }
    i++;
  }
  return ty;
}

// Accenti: nel foglio da ricalcare la «è» diventa «é», e scrivendo valgono tutte e due (anche per à/á, ì/í, ò/ó, ù/ú).
const ACC_FOLD = {"è": "e", "é": "e", "È": "E", "É": "E", "à": "a", "á": "a", "ì": "i", "í": "i", "ò": "o", "ó": "o", "ù": "u", "ú": "u"};
const sameChar = (a, b) => a === b || (ACC_FOLD[a] !== undefined && ACC_FOLD[a] === ACC_FOLD[b]);
class Tracer {
  constructor(sheet, L, opts) {
    this.sheet = sheet; this.pre = $(".code", sheet); this.trap = $(".trap", sheet); this.opts = opts;
    this.L = L; this.level = opts.level || 1; this.blockLevel = opts.blockLevel || null;
    const B = L.blocks;
    this.text = B.map(b => b.code).join("\n").replace(/è/g, "é").replace(/È/g, "É");
    this.ty = tokenize(this.text, L.lang);
    this.bi = new Array(this.text.length).fill(0);
    this.B = [];
    let off = 0;
    B.forEach((b, k) => {
      const from = off, to = off + b.code.length;
      for (let i = from; i < Math.min(to + 1, this.text.length); i++) this.bi[i] = k;
      let e = to;
      while (e > from && !this.real(e - 1)) e--;
      this.B.push({from, to, effEnd: e});
      off = to + 1;
    });
    this.revealed = new Set(); this.missStreak = 0;
    this.pre.textContent = "";
    const frag = document.createDocumentFragment();
    this.spans = [];
    for (let i = 0; i < this.text.length; i++) { const s = document.createElement("span"); s.textContent = this.text[i]; frag.appendChild(s); this.spans.push(s); }
    this.pre.appendChild(frag);
    this.bind();
  }
  real(i) { const c = this.text[i]; return c !== " " && c !== "\n" && this.ty[i] !== "com"; }
  setState(k, phase) {
    this.cur = k; this.phase = phase; this.revealed.clear(); this.missStreak = 0;
    if (k >= this.B.length) this.pos = this.text.length;
    else { let p = this.B[k].from; while (p < this.text.length && !this.real(p)) p++; this.pos = p; }
    this.paint(); this.follow();
  }
  setLevel(n, blockLevel) { this.level = n; if (blockLevel !== undefined) this.blockLevel = blockLevel; this.paint(); }
  lv(k) { return (this.blockLevel && this.blockLevel[k]) || this.level; }
  paint() {
    const {text, ty, spans, pos, bi} = this;
    const vis = this.phase === "scrivi" ? this.cur : this.cur - 1;
    for (let i = 0; i < spans.length; i++) {
      const t = ty[i];
      let cls = "t-" + t + (text[i] === "\n" ? " nl" : "");
      if (i < pos) cls += " ok" + (this.revealed.has(i) ? " rev" : "");
      else if (bi[i] > vis) cls += " gone";
      else if (t === "com") cls += " gh";
      else if (this.lv(bi[i]) === 1) cls += " gh";
      else if (this.lv(bi[i]) === 2) cls += ((t === "id" || t === "num" || t === "str") && !this.revealed.has(i)) ? " mk" : " gh";
      else cls += this.revealed.has(i) ? " gh rev" : " gone";
      if (i === pos && this.phase === "scrivi") cls += " cur";
      if (spans[i].className !== cls) spans[i].className = cls;
      // i caratteri nascosti non restano nella pagina: selezionandoli o copiandoli non si leggono
      const hide = / (mk|gone)\b/.test(cls) && text[i] !== "\n";
      const ch = hide ? " " : text[i];
      if (spans[i].textContent !== ch) spans[i].textContent = ch;
    }
  }
  follow() {
    const sh = this.sheet;
    const c = this.spans[Math.min(this.pos, this.spans.length - 1)];
    if (!c) return;
    if (this.phase !== "scrivi") { sh.scrollTop = Math.max(0, (this.spans[Math.max(0, this.pos - 1)] || c).offsetTop - sh.clientHeight + 80); return; }
    const top = c.offsetTop, left = c.offsetLeft, lh = c.offsetHeight || 24;
    this.trap.style.top = top + "px"; this.trap.style.left = Math.min(left, this.pre.scrollWidth - 4) + "px";
    if (top < sh.scrollTop + lh) sh.scrollTop = Math.max(0, top - lh * 2);
    else if (top + lh * 2 > sh.scrollTop + sh.clientHeight) sh.scrollTop = top - sh.clientHeight / 2;
    if (left < sh.scrollLeft + 20) sh.scrollLeft = Math.max(0, left - 60);
    else if (left + 40 > sh.scrollLeft + sh.clientWidth) sh.scrollLeft = left - sh.clientWidth + 120;
  }
  skipComment() { while (this.pos < this.text.length && this.ty[this.pos] === "com") this.pos++; }
  skipAll() { while (this.pos < this.text.length && !this.real(this.pos)) this.pos++; }
  input(ch) {
    if (this.phase !== "scrivi") { this.opts.onLocked && this.opts.onLocked(ch); return; }
    const t = this.text, exp = t[this.pos], st = this.opts.stats;
    let ok = false;
    if (ch === "\n") {
      let j = this.pos;
      while (j < t.length && (t[j] === " " || this.ty[j] === "com")) j++;
      if (j >= t.length || t[j] === "\n") { this.pos = j; this.skipAll(); ok = true; }
    } else if (ch === " " || ch === "\t") {
      if (exp === " ") { while (this.pos < t.length && t[this.pos] === " ") this.pos++; this.skipComment(); ok = true; }
    } else if (sameChar(ch, exp)) { this.pos++; this.skipComment(); ok = true; }
    if (ok) {
      st.typed++; this.missStreak = 0;
      if (this.pos >= this.B[this.cur].effEnd) {
        this.phase = "wait"; this.paint();
        this.opts.onBlockDone(this.cur);
        return;
      }
    } else {
      st.errors++; this.missStreak++;
      st.blockErr[this.cur] = (st.blockErr[this.cur] || 0) + 1;
      if (this.lv(this.cur) > 1 && this.missStreak >= 3) { this.reveal(false); this.missStreak = 0; }
      this.miss(ch);
    }
    this.paint(); this.follow(); this.opts.onChange && this.opts.onChange();
  }
  reveal(manual) {
    if (this.phase !== "scrivi") return;
    if (this.lv(this.cur) === 1) { toast("Al livello 1 il blocco è già visibile."); return; }
    let i = this.pos, added = 0;
    while (i < this.text.length && this.text[i] !== " " && this.text[i] !== "\n") { if (!this.revealed.has(i)) { this.revealed.add(i); added++; } i++; }
    if (!added) return;
    this.opts.stats.hints++;
    const bh = this.opts.stats.blockHint = this.opts.stats.blockHint || {};
    bh[this.cur] = (bh[this.cur] || 0) + 1;
    if (!manual) toast("Tre errori di fila: ecco la parola.");
    this.paint(); this.opts.onChange && this.opts.onChange();
  }
  miss(ch) {
    const c = this.spans[this.pos]; if (!c) return;
    c.classList.add("miss");
    const tag = $(".miss-tag", this.sheet);
    tag.textContent = ch === " " ? "spazio" : ch === "\n" ? "invio" : ch === "\t" ? "tab" : ch;
    tag.style.left = c.offsetLeft + "px"; tag.style.top = c.offsetTop + "px";
    tag.classList.add("show");
    clearTimeout(this.missT);
    this.missT = setTimeout(() => { tag.classList.remove("show"); c.classList.remove("miss"); }, 450);
  }
  focus() { this.trap.focus({preventScroll: true}); }
  bind() {
    const trap = this.trap, sh = this.sheet;
    sh.addEventListener("mouseup", () => setTimeout(() => { if (!String(getSelection()).trim()) this.focus(); }, 0));
    trap.addEventListener("focus", () => sh.classList.add("focused"));
    trap.addEventListener("blur", () => sh.classList.remove("focused"));
    trap.addEventListener("keydown", e => {
      if (e.isComposing) return;
      if (e.key === "Enter") { e.preventDefault(); this.input("\n"); }
      else if (e.key === "Tab") { e.preventDefault(); this.input("\t"); }
      else if (e.key === "Backspace") e.preventDefault();
      else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "v") { e.preventDefault(); toast("Niente incolla: il punto è scriverlo."); }
    });
    trap.addEventListener("paste", e => { e.preventDefault(); toast("Niente incolla: il punto è scriverlo."); });
    trap.addEventListener("drop", e => e.preventDefault());
    trap.addEventListener("input", e => {
      if (e.isComposing) return;
      const v = trap.value; trap.value = "";
      for (const ch of v) this.input(ch === "\r" ? "\n" : ch);
    });
    trap.addEventListener("compositionend", () => { const v = trap.value; trap.value = ""; for (const ch of v) this.input(ch); });
  }
}

/* ================================================================ lezione */
function ensureProgress(L) {
  L.progress = L.progress || {};
  const p = L.progress;
  p.block = p.block || 0;
  p.phase = p.phase || "ragiona";
  p.stats = Object.assign({typed: 0, errors: 0, hints: 0, blockErr: {}}, p.stats || {});
  p.answers = p.answers || {};
  p.q = p.q || {};
  if (p.block < L.blocks.length && p.phase === "ragiona" && (!L.blocks[p.block].question || p.skipQuestions)) p.phase = "scrivi";
  if (p.block >= L.blocks.length) { p.phase = "fatto"; p.done = true; }
  L.blocks.forEach((b, k) => { if (b.question && !b.order) b.order = shuffled(b.question.options.length); });
  return p;
}

async function openLesson(id) {
  const L = await loadLesson(id);
  if (L.kind !== "lesson") { location.hash = `#/e/${id}`; return; }
  App.view = "lesson";
  const p = ensureProgress(L);
  if (L.unitKey) crumbs([{href: "#/percorso", label: "Percorsi"}, {href: `#/l/${L.id}`, label: L.title}], 1);
  else crumbs([{href: "#/libere", label: "Lezioni libere"}, {href: `#/l/${L.id}`, label: L.title}, {href: `#/e/${L.id}`, label: "Esercizi"}], 1);
  const v = $("#view");
  v.innerHTML = `<section class="lesson">
    <header class="l-head">
      <div style="min-width:0;flex:1 1 380px">
        <p class="eyebrow">${LANG[L.lang]} · Lezione · ${L.blocks.length} blocchi</p>
        <h1>${esc(L.title)}</h1>
        ${L.goal ? `<p class="goal">${inl(L.goal)}</p>` : ""}
        <div class="concepts">${(L.concepts || []).map(c => `<span class="tag">${esc(c)}</span>`).join("")}</div>
      </div>
      <div class="l-tools">
        <div class="seg" role="group" aria-label="Livello di aiuto">
          ${[1, 2, 3].map(n => `<button type="button" data-tl="${n}" aria-pressed="${App.traceLevel === n}"><span class="num">${n}</span>${LEVELS[n].name}</button>`).join("")}
        </div>
        <span class="muted" id="tlDesc">${LEVELS[App.traceLevel].desc}</span>
      </div>
    </header>
    <div class="strip" id="strip"></div>
    ${L.verified === false ? `<div class="banner"><b>Attenzione: il programma generato non è stato eseguito con successo.</b><span>Puoi studiarlo comunque, ma potrebbe contenere errori. Errore: </span><pre>${esc(L.runError || "")}</pre>${L.unitKey ? `<div class="row"><button class="btn small" data-act="regenLesson">Fai riscrivere la lezione a Qwen</button><span class="muted" id="regenMsg" style="font-size:12.5px">Qwen sa quale errore dava questa versione.</span></div>` : ""}</div>` : ""}
    <div class="sheet" id="sheet">
      <pre class="code askable" id="code" aria-label="Codice della lezione"></pre>
      <textarea class="trap" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" aria-label="Scrivi qui il codice"></textarea>
      <div class="miss-tag"></div>
      <div class="sheet-hint" id="sheetHint"></div>
    </div>
    <div class="sheet-foot">
      <p class="status" id="lstatus"></p>
      <div class="acts">
        <button class="btn small" id="hintBtn">Mostra parola</button>
        <button class="btn small ghost" id="restartBtn">Ricomincia la lezione</button>
      </div>
    </div>
    <p class="keys"><kbd>Invio</kbd> va a capo con l'indentazione · <kbd>Spazio</kbd> salta gli spazi in fila · i commenti si scrivono da soli · seleziona del codice e premi <b>Cosa fa?</b> per chiederlo al tutor</p>
    <div id="stepCard"></div>
    <details class="past" id="past"></details>
  </section>`;

  const tr = new Tracer($("#sheet"), L, {
    level: App.traceLevel, stats: p.stats,
    onLocked: ch => {
      if (p.phase === "rivedi") { if (ch === "\n") advanceBlock(p.block); else toast("Scegli se riscriverlo più difficile o andare avanti (Invio)."); return; }
      toast("Prima rispondi alla domanda qui sotto."); const q = $("#stepCard"); q && q.scrollIntoView({block: "nearest", behavior: "smooth"});
    },
    onBlockDone: k => blockDone(k),
    onChange: () => lessonStatus()
  });
  App.tracer = tr;
  if (p.phase === "rivedi") tr.setState(p.block + 1, "wait");
  else tr.setState(p.block, p.phase === "fatto" ? "wait" : p.phase);
  if (p.phase === "scrivi" && p.redoLevel) tr.setLevel(p.redoLevel);
  v.onclick = lessonClick;
  renderStep(); renderPast(); lessonStatus();
  if (p.phase === "scrivi") tr.focus();
  else if (p.phase === "ragiona") setTimeout(() => { const c = $("#stepCard"); if (c) c.scrollIntoView({block: "nearest"}); }, 50);
  if (p.done && !p.reported) reportLessonDone();
}

function lessonContext() {
  const L = App.L, p = L.progress, k = p.block;
  const shown = L.blocks.slice(0, p.phase === "ragiona" ? k : k + 1).map(b => b.code).join("\n");
  let ctx = `Lezione di ${LANG[L.lang]}: «${L.title}». Obiettivo: ${L.goal || ""}\nRichiesta iniziale dello studente: ${L.request}\n\nCodice che lo studente ha già visto:\n${shown || "(ancora nessuno)"}`;
  if (k < L.blocks.length) {
    const b = L.blocks[k];
    if (p.phase === "ragiona" && b.question) ctx += `\n\nLo studente sta ragionando su questa domanda prima di vedere il blocco ${k + 1}: «${b.question.q}». Opzioni: ${b.question.options.join(" | ")}. NON rivelare quale opzione è giusta: aiutalo a ragionare.`;
    if (p.phase === "scrivi") ctx += `\n\nSta riscrivendo il blocco ${k + 1}:\n${b.code}\nSpiegazione del blocco: ${b.explain}`;
  } else ctx += "\n\nHa completato la lezione.";
  return ctx;
}
function lessonStatus() {
  const L = App.L, p = L.progress, n = L.blocks.length;
  $("#strip").innerHTML = L.blocks.map((b, k) => `<span class="${k < p.block || p.done || (k === p.block && p.phase === "rivedi") ? "done" : k === p.block ? (p.phase === "ragiona" ? "wait" : "cur") : ""}"></span>`).join("");
  const s = p.stats, tot = s.typed + s.errors;
  const acc = tot ? Math.round(s.typed / tot * 100) + "%" : "—";
  $("#lstatus").textContent = p.done ? `Lezione completata · precisione ${acc}` :
    `Blocco ${p.block + 1} di ${n} · ${p.phase === "ragiona" ? "ragiona" : p.phase === "rivedi" ? "scritto" : "scrivi"} · precisione ${acc} · aiuti ${s.hints}`;
  $("#sheet").classList.toggle("compact", p.phase !== "scrivi");
  const hint = $("#sheetHint");
  hint.className = "sheet-hint" + (p.phase === "scrivi" ? " when-blur" : "");
  hint.textContent = p.done ? "Lezione completata" : p.phase === "ragiona" ? "Rispondi alla domanda qui sotto per sbloccare il blocco" : p.phase === "rivedi" ? "Riscrivilo più difficile o premi Invio per andare avanti" : "Clicca sul foglio e scrivi";
  $("#hintBtn").hidden = (p.redoLevel || App.traceLevel) === 1 || p.phase !== "scrivi";
  const b = L.blocks[p.block];
  Tutor.setContext(lessonContext(), p.done ? `Lezione «${L.title}» completata` : `Lezione «${L.title}» · blocco ${p.block + 1}, ${p.phase === "ragiona" ? "domanda di ragionamento" : "scrittura"}`);
  Tutor.setQuick(p.done ? ["Riassumimi i concetti della lezione", "Come potrei migliorare questo programma?"]
    : p.phase === "ragiona" ? ["Non capisco la domanda", "Dammi un indizio senza la risposta"]
    : ["Spiegami questo blocco riga per riga", "Perché è scritto così e non in un altro modo?", "Fammi un esempio diverso"]);
}

function questionHtml(k) {
  const L = App.L, b = L.blocks[k], q = b.question, st = L.progress.q[k] || {wrong: [], tries: 0};
  const letters = "ABCDEFGH";
  const opts = b.order.map((oi, pos) => {
    const wrong = st.wrong.includes(oi);
    return `<button class="opt ${wrong ? "wrong" : ""}" data-opt="${oi}" ${wrong ? "disabled" : ""}><span class="k">${letters[pos]}</span><span>${inl(q.options[oi])}</span></button>`;
  }).join("");
  let fb = "";
  if (st.judge) fb = `<p class="fb ${st.judge.verdict === "giusto" ? "" : st.judge.verdict === "parziale" ? "mid" : "bad"}"><b>${st.judge.verdict === "parziale" ? "Quasi." : st.judge.verdict === "giusto" ? "Giusto." : "Non ci siamo."}</b> ${inl(st.judge.comment)}</p>`;
  else if (st.tries) fb = `<p class="fb bad"><b>Non è giusta.</b> Ripensaci e scegli un'altra risposta, oppure vai avanti e vedi quella corretta.</p>`;
  const open = st.mode === "open";
  return `<p class="q">${inl(q.q)}</p>
    ${open ? `<textarea class="open-ans" id="openAns" placeholder="Spiega il tuo ragionamento con parole tue…">${esc(st.draft || "")}</textarea>
      <div class="row"><button class="btn primary" id="judgeBtn">Valuta la mia risposta</button><button class="linkish" id="modeBtn">Torna alle risposte a scelta</button></div>`
      : `<div class="opts">${opts}</div>`}
    ${fb}
    <div class="row">
      ${!open ? `<button class="linkish" id="modeBtn">Preferisco rispondere a parole mie</button>` : ""}
      <span class="spacer"></span>
      ${st.tries ? `<button class="btn" id="skipBtn">Vai avanti e mostrami la risposta</button>` : ""}
    </div>`;
}

function renderStep() {
  const L = App.L, p = L.progress, k = p.block, n = L.blocks.length;
  const card = $("#stepCard");
  const prevK = p.phase === "fatto" ? n - 1 : k - 1;
  const prev = prevK >= 0 && L.blocks[prevK] ? `<div class="prev"><span class="lbl">Blocco ${prevK + 1} · perché è scritto così</span><p class="explain">${inl(L.blocks[prevK].explain || "")}</p>
    <div class="row"><button class="linkish" data-askblock="${prevK}">Non mi è chiaro: chiedi al tutor</button></div></div>` : "";
  if (p.phase === "fatto") {
    const s = p.stats, tot = s.typed + s.errors, acc = tot ? Math.round(s.typed / tot * 100) : 100;
    const ans = Object.values(p.answers), qn = L.blocks.filter(b => b.question).length;
    const worst = Object.entries(s.blockErr).sort((a, b) => b[1] - a[1]).filter(x => x[1] > 0).slice(0, 2);
    card.className = "step";
    card.innerHTML = `${prev}<div class="step-head"><span class="n">✓</span><h2>Lezione completata</h2><span class="tag acc">Livello ${App.traceLevel} · ${LEVELS[App.traceLevel].name}</span></div>
      <div class="sum">
        <div class="stat"><b>${acc}%</b><span>Precisione</span></div>
        <div class="stat"><b>${s.errors}</b><span>Errori di battitura</span></div>
        <div class="stat"><b>${s.hints}</b><span>Aiuti</span></div>
        <div class="stat"><b>${ans.filter(a => a === "first").length}/${qn}</b><span>Domande al 1° colpo</span></div>
      </div>
      ${worst.length ? `<p class="explain">Blocchi con più errori: ${worst.map(([b, e]) => `blocco ${+b + 1} (${e} errori)`).join(", ")}.</p>` : ""}
      ${unitNextHtml(L, acc)}
      ${L.unitKey ? `<div class="row"><button class="btn" id="runLesson">Esegui il programma</button></div>` : `
      ${App.traceLevel < 3 ? `<p class="explain">Prossimo passo: rifalla al livello ${App.traceLevel + 1}, con meno aiuto. Poi passa agli esercizi.</p>` : `<p class="explain">L'hai scritta a memoria. Ora mettiti alla prova con gli esercizi.</p>`}
      <div class="row">
        <a class="btn primary" href="#/e/${L.id}" style="text-decoration:none">Vai agli esercizi</a>
        ${App.traceLevel < 3 ? `<button class="btn" id="nextLevel">Rifai al livello ${App.traceLevel + 1} · ${LEVELS[App.traceLevel + 1].name}</button>` : ""}
        <button class="btn" id="runLesson">Esegui il programma</button>
      </div>`}
      <div id="runOut"></div>`;
    return;
  }
  const b = L.blocks[k];
  if (p.phase === "ragiona") {
    card.className = "step ragiona";
    card.innerHTML = `${prev}<div class="step-head"><span class="n">${k + 1}</span><h2>Ragiona prima di scrivere</h2><span class="tag wait">Blocco ${k + 1} di ${n}</span></div>${questionHtml(k)}`;
    return;
  }
  if (p.phase === "rivedi") {
    const done = (p.blockLevels || {})[k] || App.traceLevel;
    const higher = [2, 3].filter(n => n > done);
    card.className = "step";
    card.innerHTML = `<div class="prev" style="border:0;padding:0"><span class="lbl">Blocco ${k + 1} · perché è scritto così</span><p class="explain">${inl(b.explain || "")}</p>
      <div class="row"><button class="linkish" data-askblock="${k}">Non mi è chiaro: chiedi al tutor</button></div></div>
      <div class="redo">
        <p class="explain"><b>Blocco scritto al livello ${done} · ${LEVELS[done].name}.</b> Vuoi riscriverlo con meno aiuto prima di andare avanti?</p>
        <div class="row">
          ${higher.map(n => `<button class="btn" data-redo="${n}">Riscrivi al livello ${n} · ${LEVELS[n].name}</button>`).join("")}
          <button class="btn primary" id="advBtn">${k + 1 >= L.blocks.length ? "Concludi la lezione" : "Vai al blocco " + (k + 2)}</button>
          <span class="muted" style="font-size:12.5px"><kbd>Invio</kbd> per andare avanti</span>
        </div>
        <label class="toggle"><input type="checkbox" id="noRedo"> Non chiedermelo più in questa lezione</label>
      </div>`;
    return;
  }
  const st = p.q[k] || {};
  const res = p.answers[k];
  const why = b.question && res ? `<p class="fb ${res === "skipped" ? "mid" : ""}"><b>${res === "first" ? "Giusto al primo colpo." : res === "retry" ? "Giusto." : "La risposta era:"}</b> ${res === "skipped" ? inl(b.question.options[b.question.correct]) + ". " : ""}${inl(b.question.why)}</p>` : "";
  card.className = "step scrivi";
  card.innerHTML = `${prev}<div class="step-head"><span class="n">${k + 1}</span><h2>Ora scrivi il blocco</h2><span class="tag acc">Blocco ${k + 1} di ${n}</span></div>
    ${b.question ? `<p class="explain muted">${inl(b.question.q)}</p>` : ""}${why}
    ${st.judge && st.judge.verdict === "giusto" ? `<p class="fb"><b>Valutazione:</b> ${inl(st.judge.comment)}</p>` : ""}
    ${p.redoLevel ? `<p class="fb mid"><b>Riscrittura al livello ${p.redoLevel} · ${LEVELS[p.redoLevel].name}.</b> Stesso blocco, meno aiuto.</p>` : ""}
    ${(p.redoLevel || App.traceLevel) === 3 ? `<div class="prev" style="border:0;padding:0"><span class="lbl" style="color:var(--accent)">Cosa deve fare questo blocco</span><p class="explain">${inl(b.explain)}</p></div>`
      : `<p class="explain muted">${(p.redoLevel || App.traceLevel) === 1 ? "Ricalca il codice che vedi in trasparenza sul foglio." : "Ricostruisci nomi e valori dove vedi la linea tratteggiata."}${p.redoLevel ? "" : " La spiegazione del perché arriva quando finisci il blocco."}</p>`}
    <div class="row"><button class="btn" id="focusSheet">Scrivi sul foglio</button></div>`;
}

async function reportLessonDone() {
  const L = App.L, p = L.progress;
  if (p.reported) return;
  LOG.ev("lesson_done", {lesson: L.id, title: L.title, level: p.minLevel || App.traceLevel, errors: p.stats.errors, hints: p.stats.hints});
  p.reported = true;
  const s = p.stats, tot = s.typed + s.errors;
  const acc = tot ? Math.round(s.typed / tot * 100) : 100;
  try {
    p.doneInfo = await api("/api/lesson_done", {method: "POST", body: {id: L.id, level: p.minLevel || App.traceLevel, acc, hints: s.hints}});
  } catch (e) { p.doneInfo = {error: e.message}; }
  saveLesson(true);
  if (App.L === L && App.view === "lesson") renderStep();
}

function unitNextHtml(L, acc) {
  const p = L.progress, di = p.doneInfo, lvl = p.minLevel || App.traceLevel;
  if (!di) return `<p class="muted"><span class="spin small"></span> Salvo i progressi…</p>`;
  if (di.error) return `<p class="muted">${esc(di.error)}</p>`;
  const cards = di.cards ? ` Ho aggiunto ${di.cards} blocchi al ripasso: torneranno da riscrivere a memoria domani.` : "";
  if (!L.unitKey) return cards ? `<p class="explain">${cards.trim()}</p>` : "";
  if (lvl < 3) return `<div class="unit-next"><b>Passo 2 · Fissa.</b> Ora riscrivi tutta la lezione a memoria, senza domande e senza aiuti visivi: è questo che apre l'unità successiva.${cards}
    <div class="row"><button class="btn primary" data-memory-now>Riscrivila a memoria · livello 3</button><a class="btn" href="#/s/${L.unitKey}/base">Prima qualche esercizio</a></div></div>`;
  if (di.mastered) return `<div class="unit-next ok"><b>${di.newlyMastered ? "Unità fissata." : "Unità già fissata."}</b> Precisione ${acc}%.${di.newlyMastered ? " Si è aperta l'unità successiva." : ""} Ora usa quello che sai negli esercizi.
    <div class="row"><a class="btn primary" href="#/s/${L.unitKey}/base">Esercizi Base</a><a class="btn" href="#/percorso">Torna al percorso</a></div></div>`;
  return `<div class="unit-next warn"><b>Quasi.</b> Precisione ${acc}% con ${p.stats.hints} aiuti: per fissare l'unità servono almeno 85% e al massimo 2 aiuti. Guarda i blocchi con più errori qui sopra e riprova.
    <div class="row"><button class="btn primary" data-memory-now>Riprova a memoria</button><button class="btn" data-relearn>Riguardala al livello 1</button></div></div>`;
}

function renderPast() {
  const L = App.L, p = L.progress, upto = p.done ? L.blocks.length : p.block;
  const el = $("#past");
  if (upto < 2) { el.hidden = true; return; }
  el.hidden = false;
  el.innerHTML = `<summary>Spiegazioni dei blocchi completati (${upto})</summary><ol>${L.blocks.slice(0, upto).map(b => `<li>${inl(b.explain)}</li>`).join("")}</ol>`;
}

function answerQuestion(k, result) {
  const L = App.L, p = L.progress;
  p.answers[k] = result;
  p.phase = "scrivi";
  App.tracer.setState(k, "scrivi");
  renderStep(); lessonStatus(); saveLesson();
  App.tracer.focus();
}

function blockDone(k) {
  const L = App.L, p = L.progress, lv = App.tracer.level;
  LOG.ev("lesson_block", {lesson: L.id, title: L.title, k, level: lv, err: (p.stats.blockErr || {})[k] || 0});
  if (!p.redoLevel) p.minLevel = Math.min(p.minLevel || 9, lv);
  p.blockLevels = p.blockLevels || {};
  p.blockLevels[k] = Math.max(p.blockLevels[k] || 0, lv);
  if (lv < 3 && p.askRedo !== false) {
    p.phase = "rivedi"; p.block = k; delete p.redoLevel;
    App.tracer.setState(k + 1, "wait");
    renderStep(); renderPast(); lessonStatus(); saveLesson();
    App.tracer.focus();
    $("#stepCard").scrollIntoView({block: "nearest", behavior: "smooth"});
    return;
  }
  advanceBlock(k);
}

function redoBlock(k, level) {
  const p = App.L.progress;
  p.phase = "scrivi"; p.block = k; p.redoLevel = level;
  App.tracer.setLevel(level);
  App.tracer.setState(k, "scrivi");
  renderStep(); lessonStatus(); saveLesson();
  App.tracer.focus();
  $("#sheet").scrollIntoView({block: "nearest", behavior: "smooth"});
}

function advanceBlock(k) {
  const L = App.L, p = L.progress;
  delete p.redoLevel;
  App.tracer.setLevel(App.traceLevel);
  p.block = k + 1;
  if (p.block >= L.blocks.length) { p.phase = "fatto"; p.done = true; App.tracer.setState(p.block, "wait"); }
  else { p.phase = L.blocks[p.block].question && !p.skipQuestions ? "ragiona" : "scrivi"; App.tracer.setState(p.block, p.phase); }
  if (p.done) reportLessonDone();
  renderStep(); renderPast(); lessonStatus(); saveLesson();
  if (p.phase === "scrivi") App.tracer.focus();
  else $("#stepCard").scrollIntoView({block: "nearest", behavior: "smooth"});
}

async function lessonClick(e) {
  const L = App.L; if (!L) return;
  const p = L.progress, k = p.block;
  const t = e.target.closest("button"); if (!t) return;
  if (t.dataset.act === "regenLesson") {
    const [path, uid] = L.unitKey.split("/"), id = L.id;
    t.disabled = true;
    try {
      let r = await api("/api/unit_lesson/regen", {method: "POST", body: {lang: path, unit: uid}});
      while (r.pending || r.ready === false) {
        if (r.state === "error") throw new Error(r.error || "Qwen non ci è riuscito.");
        const m = $("#regenMsg"); if (m) m.innerHTML = `<span class="spin small"></span> Qwen riscrive la lezione… ${r.secs || 0} s`;
        await new Promise(res => setTimeout(res, 1500));
        if (!App.L || App.L.id !== id) return;
        r = await api(`/api/unit_lesson/status?lang=${path}&unit=${uid}`);
      }
      LOG.ev("lesson_regen", {unit: L.unitKey, ok: r.verified !== false});
      App.L = null;   // la lezione è cambiata: va riletta dal server
      await openLesson(id);
    } catch (err) { toast(err.message); t.disabled = false; }
    return;
  }
  if (t.dataset.tl) {
    App.traceLevel = +t.dataset.tl; localStorage.setItem("ricalco.trace", App.traceLevel);
    $$("[data-tl]").forEach(x => x.setAttribute("aria-pressed", String(x === t)));
    $("#tlDesc").textContent = LEVELS[App.traceLevel].desc;
    App.tracer.setLevel(App.traceLevel); renderStep(); lessonStatus();
    if (p.phase === "scrivi") App.tracer.focus();
    return;
  }
  if (t.id === "hintBtn") { App.tracer.reveal(true); App.tracer.focus(); return; }
  if (t.dataset.redo) { redoBlock(p.block, +t.dataset.redo); return; }
  if (t.hasAttribute("data-memory-now") || t.hasAttribute("data-relearn")) {
    const lv = t.hasAttribute("data-memory-now") ? 3 : 1;
    App.traceLevel = lv; localStorage.setItem("ricalco.trace", lv);
    L.progress = {block: 0, phase: "ragiona", done: false, skipQuestions: lv === 3, askRedo: lv === 3 ? false : undefined};
    L.blocks.forEach(b => { if (b.question) b.order = shuffled(b.question.options.length); });
    saveLesson(true); openLesson(L.id); return;
  }
  if (t.id === "advBtn") { advanceBlock(p.block); return; }
  if (t.id === "focusSheet") { App.tracer.focus(); $("#sheet").scrollIntoView({block: "nearest", behavior: "smooth"}); return; }
  if (t.id === "restartBtn") {
    if (!t.dataset.armed) { t.dataset.armed = "1"; t.textContent = "Sicuro? Si riparte dal blocco 1"; setTimeout(() => { if (t.isConnected) { delete t.dataset.armed; t.textContent = "Ricomincia la lezione"; } }, 3500); return; }
    restartLesson(); return;
  }
  if (t.id === "nextLevel") { App.traceLevel = Math.min(3, App.traceLevel + 1); localStorage.setItem("ricalco.trace", App.traceLevel); restartLesson(); return; }
  if (t.id === "runLesson") {
    const out = $("#runOut"); out.innerHTML = `<p class="muted">Eseguo…</p>`;
    try {
      const r = await api("/api/run", {method: "POST", body: {lang: L.lang, mode: "program", code: L.blocks.map(b => b.code).join("\n")}});
      out.innerHTML = `<pre class="out askable">${esc(r.stdout || "(nessun output)")}</pre>${r.ok ? "" : `<div class="res-err"><pre>${esc(r.error)}</pre></div>`}`;
    } catch (err) { out.innerHTML = `<div class="res-err">${esc(err.message)}</div>`; }
    return;
  }
  if (t.dataset.askblock) {
    const b = L.blocks[+t.dataset.askblock];
    Tutor.ask(`Non mi è chiaro il blocco ${+t.dataset.askblock + 1}. Me lo spieghi in modo più semplice?\n\`\`\`\n${b.code}\n\`\`\``);
    return;
  }
  if (p.phase !== "ragiona") return;
  const b = L.blocks[k], q = b.question;
  const st = p.q[k] = p.q[k] || {wrong: [], tries: 0};
  if (t.dataset.opt !== undefined) {
    const oi = +t.dataset.opt;
    if (oi === q.correct) { answerQuestion(k, st.tries ? "retry" : "first"); return; }
    st.tries++; st.wrong.push(oi); delete st.judge;
    renderStep(); saveLesson(); return;
  }
  if (t.id === "skipBtn") { answerQuestion(k, "skipped"); return; }
  if (t.id === "modeBtn") { st.mode = st.mode === "open" ? "choice" : "open"; delete st.judge; renderStep(); if (st.mode === "open") $("#openAns").focus(); return; }
  if (t.id === "judgeBtn") {
    const ans = $("#openAns").value.trim();
    if (ans.length < 3) { toast("Scrivi il tuo ragionamento, anche breve."); return; }
    st.draft = ans; t.disabled = true; t.textContent = "Il modello sta valutando…";
    try {
      const r = await api("/api/judge", {method: "POST", body: {question: q.q, reference: q.options[q.correct], why: q.why, answer: ans}});
      st.judge = r;
      if (r.verdict === "giusto") { answerQuestion(k, st.tries ? "retry" : "first"); return; }
      st.tries++;
    } catch (err) { toast(err.message); }
    renderStep(); saveLesson();
  }
}
document.addEventListener("change", e => { if (e.target.id === "noRedo" && App.L) { App.L.progress.askRedo = !e.target.checked; saveLesson(); } });
document.addEventListener("input", e => { if (e.target.id === "openAns" && App.L) { const st = App.L.progress.q[App.L.progress.block]; if (st) st.draft = e.target.value; } });

function restartLesson() {
  const L = App.L;
  L.progress = {block: 0, phase: "ragiona", done: false};
  L.blocks.forEach(b => { if (b.question) b.order = shuffled(b.question.options.length); });
  saveLesson(true);
  openLesson(L.id);
}

/* ================================================================ esercizi */
function topicOf(L) {
  if (L.kind !== "lesson") return L.title;
  return `${L.title}. ${L.goal || ""} Concetti: ${(L.concepts || []).join(", ")}. Richiesta originale: ${L.request}`;
}

async function openExercises(id, exId) {
  const L = await loadLesson(id);
  App.view = "ex";
  L.exercises = L.exercises || [];
  if (exId) { const ex = L.exercises.find(x => x.id === exId); if (ex) { App.exId = exId; App.diff = ex.difficulty; } }
  else if (!L.exercises.find(x => x.id === App.exId)) {
    const last = L.exercises.filter(x => !(x.state && x.state.solved)).pop() || L.exercises[L.exercises.length - 1];
    App.exId = last ? last.id : null;
    if (last) App.diff = last.difficulty;
  }
  if (!TYPES_BY_DIFF[App.diff].includes(App.exType)) App.exType = TYPES_BY_DIFF[App.diff][0];
  crumbs([{href: "#/libere", label: "Lezioni libere"}].concat(L.kind === "lesson" ? [{href: `#/l/${L.id}`, label: L.title}] : []).concat([{href: `#/e/${L.id}`, label: L.kind === "lesson" ? "Esercizi" : L.title}]));
  renderExercises();
}

function renderExercises() {
  const L = App.L;
  const count = d => L.exercises.filter(x => x.difficulty === d && x.state && x.state.solved && !x.state.revealed).length;
  const v = $("#view");
  v.innerHTML = `<section class="ex">
    <header class="l-head"><div style="min-width:0">
      <p class="eyebrow">${LANG[L.lang]} · Esercizi</p>
      <h1>${esc(L.title)}</h1>
      ${L.kind === "lesson" && !(L.progress && L.progress.done) ? `<p class="goal">Non hai ancora finito la lezione: <a href="#/l/${L.id}">riprendila</a> se gli esercizi ti sembrano difficili.</p>` : ""}
    </div></header>
    <div class="ex-gen">
      <div class="row">
        <div class="seg" role="group" aria-label="Difficoltà">
          ${Object.keys(DIFFS).map(d => `<button type="button" data-diff="${d}" aria-pressed="${App.diff === d}">${DIFFS[d]} <span class="muted" style="font-size:12px">· ${count(d)} risolti</span></button>`).join("")}
        </div>
      </div>
      <div class="types">${TYPES_BY_DIFF[App.diff].map(t => `<button type="button" class="type" data-type="${t}" aria-pressed="${App.exType === t}"><b>${TYPES[t].name}</b><small>${TYPES[t].desc}</small></button>`).join("")}</div>
      <div class="row"><button class="btn primary" id="genEx">Nuovo esercizio · ${DIFFS[App.diff]} · ${TYPES[App.exType].name}</button><span class="muted" style="font-size:12.5px">Ricalco esegue la soluzione del modello sui test prima di dartelo: se non funziona, lo fa rifare.</span></div>
    </div>
    <div class="history" id="history"></div>
    <div id="exBody"></div>
  </section>`;
  v.onclick = exClick;
  renderHistory();
  renderExercise();
}

function renderHistory() {
  const L = App.L, list = L.exercises.filter(x => x.difficulty === App.diff);
  $("#history").innerHTML = list.length ? list.map(x => `<button class="chip" data-open="${x.id}" aria-current="${x.id === App.exId}">${x.state && x.state.solved ? "✓ " : ""}${esc(x.title)}</button>`).join("") : "";
}

function exContext(ex) {
  const L = App.L;
  let ctx = `Esercizio di ${LANG[L.lang]} (${DIFFS[ex.difficulty]}, tipo «${TYPES[ex.type].name}») sull'argomento: ${L.title}.\n`;
  if (ex.type === "predici") ctx += `Lo studente deve prevedere l'output di questo codice:\n${ex.code}\n` + (ex.state.solved || ex.state.revealed ? `Output reale:\n${ex.output}\n` : "NON rivelare l'output: aiutalo a seguire il codice passo per passo.\n");
  else {
    ctx += `Consegna: ${ex.statement}\nTest: ${ex.tests.map(t => `${t.call} -> ${t.expected}`).join("; ")}\n`;
    const code = ex.type === "riordina" ? (ex.state.order || []).map(i => ex.lines[i]).join("\n") : (ex.state.code ?? ex.starter ?? "");
    ctx += `Codice attuale dello studente:\n${code}\n`;
    if (ex.state.last) ctx += `Ultimo risultato dei test:\n${ex.state.last}\n`;
    if (!ex.state.solved && !ex.state.revealed) ctx += "Non dare la soluzione completa: guida con indizi.\n";
  }
  return ctx;
}

function renderExercise() {
  const L = App.L, body = $("#exBody");
  const ex = L.exercises.find(x => x.id === App.exId);
  if (App.exGen) {
    body.innerHTML = `<div class="gen"><span class="spin"></span><div style="flex:1;display:flex;flex-direction:column;gap:4px">
      <p><b>Preparo un esercizio ${DIFFS[App.exGen.diff].toLowerCase()} · ${TYPES[App.exGen.type].name}</b> <span class="timer" id="exTimer">0:00</span></p>
      <p class="muted" style="font-size:13.5px">Il modello scrive consegna, soluzione e test; Ricalco li esegue per controllare che siano giusti.</p></div></div>`;
    timerEl($("#exTimer"));
    return;
  }
  if (!ex) {
    body.innerHTML = `<div class="empty">Scegli difficoltà e tipo qui sopra e premi <b>Nuovo esercizio</b>. Ogni esercizio viene controllato eseguendo davvero il codice: i test che vedi sono veri.</div>`;
    Tutor.setContext(`Lo studente sta per fare esercizi di ${LANG[L.lang]} su: ${L.title}`, `Esercizi · ${L.title}`);
    Tutor.setQuick(["Che tipo di esercizio mi consigli?"]);
    return;
  }
  const s = ex.state = Object.assign({solved: false, attempts: 0, hints: 0, revealed: false}, ex.state || {});
  let main = "";
  if (ex.type === "predici") {
    main = `<p class="statement">Leggi il codice e scrivi <b>esattamente</b> cosa stampa, una riga per riga.</p>
      <pre class="ro askable">${esc(ex.code)}</pre>
      <label class="muted" for="guess" style="font-size:13px">Il tuo output</label>
      <textarea class="guess" id="guess" spellcheck="false" ${s.solved || s.revealed ? "readonly" : ""}>${esc(s.guess || "")}</textarea>
      <div class="row"><button class="btn primary" id="checkGuess" ${s.solved || s.revealed ? "disabled" : ""}>Verifica</button>
        ${s.attempts >= 2 && !s.solved && !s.revealed ? `<button class="btn" id="revealOut">Mostra l'output e la spiegazione</button>` : ""}
        <button class="btn ghost" data-quick="trace">Seguiamo il codice insieme</button></div>`;
  } else if (ex.type === "riordina") {
    if (!s.order) s.order = ex.lines.map((_, i) => i);
    main = `<p class="statement">${inl(ex.statement)}</p>
      ${testsPreview(ex)}
      <p class="muted" style="margin:0;font-size:13px">Trascina le righe oppure usa le frecce. ${L.lang === "python" ? "L'indentazione è già giusta: conta solo l'ordine." : ""}</p>
      <ol class="parsons askable" id="parsons">${s.order.map((li, pos) => `<li draggable="true" data-pos="${pos}"><span class="grip">⋮⋮</span><pre>${esc(ex.lines[li])}</pre><span class="mv"><button data-mv="-1" data-pos="${pos}" aria-label="Sposta su">↑</button><button data-mv="1" data-pos="${pos}" aria-label="Sposta giù">↓</button></span></li>`).join("")}</ol>
      <div class="row"><button class="btn primary" id="runEx">Verifica l'ordine</button>${hintBtns(ex)}</div>`;
  } else {
    main = `<p class="statement">${inl(ex.statement)}</p>
      ${testsPreview(ex)}
      <div id="editorHost"></div>
      <div class="row"><button class="btn primary" id="runEx">Esegui i test</button><span class="muted" style="font-size:12.5px"><kbd>Ctrl</kbd>+<kbd>Invio</kbd></span><span class="spacer"></span>${hintBtns(ex)}
        <button class="btn ghost small" id="resetCode">Ripristina il codice iniziale</button></div>`;
  }
  body.innerHTML = `<article class="exc">
    <div class="exc-head"><span class="tag acc">${TYPES[ex.type].name}</span><span class="tag">${DIFFS[ex.difficulty]}</span><h2>${esc(ex.title)}</h2><span class="spacer"></span>
      <span class="tag ${s.solved ? "ok" : s.revealed ? "wait" : ""}">${s.solved ? (s.revealed ? "Risolto con soluzione vista" : "Risolto") : s.revealed ? "Soluzione vista" : `Tentativi: ${s.attempts}`}</span></div>
    ${main}
    ${s.hints && ex.hints && ex.hints.length ? `<div><span class="eyebrow">Suggerimenti</span><ol class="hints">${ex.hints.slice(0, s.hints).map(h => `<li>${inl(h)}</li>`).join("")}</ol></div>` : ""}
    <div class="results" id="results">${s.lastHtml || ""}</div>
    <div id="solvedBox">${solvedHtml(ex)}</div>
  </article>`;
  if (ex.type !== "predici" && ex.type !== "riordina") {
    App.editor = makeEditor($("#editorHost"), s.code ?? ex.starter ?? "", {
      readonly: false,
      onChange: val => { s.code = val; saveLesson(); Tutor.setContext(exContext(ex)); },
      onRun: () => runExercise(ex)
    });
  }
  if (ex.type === "riordina") bindParsons(ex);
  if (ex.type !== "predici" && (s.solved || s.revealed) && ex.solution) startSolutionRicalco(ex, L.lang, !s.solved);
  Tutor.setContext(exContext(ex), `Esercizio «${ex.title}» · ${TYPES[ex.type].name}`);
  Tutor.setQuick(ex.type === "predici" ? ["Cosa fa la prima riga?", "Come si comporta il ciclo?"]
    : ["Dammi un indizio", "Spiegami meglio la consegna", "Cosa significa l'errore che ho?"]);
}

function testsPreview(ex) {
  return `<div><span class="eyebrow">I test che il codice deve superare</span><ul class="tests-preview askable">${ex.tests.map(t => `<li><span>${esc(t.call)}</span> <span class="arrow">→</span> <span>${esc(t.expected)}</span></li>`).join("")}</ul></div>`;
}
function hintBtns(ex) {
  const s = ex.state, nh = (ex.hints || []).length;
  return `${nh ? `<button class="btn" id="hintEx" ${s.hints >= nh ? "disabled" : ""}>Suggerimento ${Math.min(s.hints + 1, nh)}/${nh}</button>` : ""}
    <button class="btn" id="explainErr" ${s.last ? "" : "hidden"}>Spiega il mio errore</button>
    ${s.revealed ? "" : `<button class="btn ghost" id="revealSol">Mostra la soluzione</button>`}`;
}
function solvedHtml(ex) {
  const s = ex.state;
  if (!s.solved && !s.revealed) return "";
  if (ex.type === "predici") {
    return `<div class="${s.solved ? "solved" : "banner"}">${s.solved ? `<b>Giusto${s.attempts > 1 ? `, al tentativo ${s.attempts}` : " al primo colpo"}.</b>` : "<b>Output reale</b>"}
      ${s.solved ? "" : `<pre class="out askable">${esc(ex.output)}</pre>`}
      <p class="explain">${inl(ex.explain)}</p>${nextBtn()}</div>`;
  }
  return `<div class="${s.solved ? "solved" : "banner"}">
    ${s.solved ? `<b>Tutti i test passano${s.revealed ? " (dopo aver visto la soluzione)" : ""}.</b><span>Tentativi: ${s.attempts} · suggerimenti usati: ${s.hints}.</span>` : "<b>Soluzione di riferimento</b><span>Studiala, poi prova a riscriverla da solo senza guardarla: l'esercizio resta da risolvere.</span>"}
    ${ex.bugExplain && (s.solved || s.revealed) ? `<p class="explain"><b style="color:inherit">Il bug:</b> ${inl(ex.bugExplain)}</p>` : ""}
    <div class="rc-host" id="rcHost"></div><div class="fy-host" id="fyHost"></div>
    ${s.solved ? nextBtn() : ""}</div>`;
}
function nextBtn() { return `<div class="row"><button class="btn primary" id="nextEx">Prossimo esercizio</button></div>`; }

function resultsHtml(r) {
  if (r.error) return `<div class="res-err"><b>${/^Tempo/.test(r.error) ? "Tempo scaduto" : "Il codice non si esegue"}</b><pre>${esc(r.error)}</pre></div>`;
  const ok = r.tests.filter(t => t.ok).length;
  return `<span class="eyebrow">${ok}/${r.tests.length} test superati</span>` + r.tests.map(t => `<div class="tres ${t.ok ? "pass" : "fail"}"><span class="ic">${t.ok ? "✓" : "✗"}</span><div>
      ${t.expected === "" ? `<b>${esc(t.desc)}</b> <code class="muted">${esc(t.call)}</code>` : `<code>${esc(t.call)}</code>`}${t.ok ? "" : `<div class="det">${t.expected === "" ? esc(t.error || "fallito") : `atteso ${esc(t.expected)} · ${t.error ? "errore: " + esc(t.error) : "ottenuto " + esc(t.got)}`}</div>`}</div></div>`).join("")
    + (r.stdout && r.stdout.trim() ? `<details><summary class="muted" style="font-size:12.5px;cursor:pointer">Output stampato dal tuo codice</summary><pre class="out">${esc(r.stdout)}</pre></details>` : "");
}
function resultsText(r) {
  if (r.error) return "Errore: " + r.error;
  return r.tests.map(t => `${t.ok ? "OK" : "FALLITO"} ${t.call} atteso ${t.expected}` + (t.ok ? "" : t.error ? ` errore ${t.error}` : ` ottenuto ${t.got}`)).join("\n");
}

async function runExercise(ex) {
  const s = ex.state, btn = $("#runEx");
  const code = ex.type === "riordina" ? s.order.map(i => ex.lines[i]).join("\n") : (App.editor ? App.editor.get() : s.code);
  if (btn) { btn.disabled = true; btn.textContent = "Eseguo…"; }
  try {
    const r = await api("/api/run", {method: "POST", body: {lang: App.L.lang, mode: "tests", code, tests: ex.tests}});
    s.attempts++;
    s.lastHtml = resultsHtml(r); s.last = resultsText(r);
    if (r.all_ok) s.solved = true;
    saveLesson();
    $("#results").innerHTML = s.lastHtml;
    $("#solvedBox").innerHTML = solvedHtml(ex);
    if (s.solved) startSolutionRicalco(ex, App.L.lang, false);
    const head = $(".exc-head .tag:last-child"); if (head) { head.className = "tag " + (s.solved ? "ok" : ""); head.textContent = s.solved ? (s.revealed ? "Risolto con soluzione vista" : "Risolto") : `Tentativi: ${s.attempts}`; }
    const ee = $("#explainErr"); if (ee) ee.hidden = !!s.solved;
    Tutor.setContext(exContext(ex));
    if (s.solved) { renderHistory(); $("#solvedBox").scrollIntoView({block: "nearest", behavior: "smooth"}); }
  } catch (e) { toast(e.message); }
  if (btn) { btn.disabled = false; btn.textContent = ex.type === "riordina" ? "Verifica l'ordine" : "Esegui i test"; }
}

function normOut(s) { return String(s).replace(/\r/g, "").split("\n").map(l => l.replace(/\s+$/, "")).join("\n").replace(/\n+$/, ""); }

async function exClick(e) {
  const L = App.L;
  const t = e.target.closest("button"); if (!t) return;
  const ex = L.exercises.find(x => x.id === App.exId);
  if (t.dataset.diff) { App.diff = t.dataset.diff; App.exType = TYPES_BY_DIFF[App.diff][0]; const lst = L.exercises.filter(x => x.difficulty === App.diff); App.exId = lst.length ? lst[lst.length - 1].id : null; renderExercises(); return; }
  if (t.dataset.type) { App.exType = t.dataset.type; $$("[data-type]").forEach(x => x.setAttribute("aria-pressed", String(x === t))); $("#genEx").textContent = `Nuovo esercizio · ${DIFFS[App.diff]} · ${TYPES[App.exType].name}`; return; }
  if (t.dataset.open) { App.exId = t.dataset.open; renderHistory(); renderExercise(); return; }
  if (t.id === "genEx" || t.id === "nextEx") { generateExercise(t.id === "nextEx" && ex ? ex.type : App.exType); return; }
  if (!ex) return;
  const s = ex.state;
  if (t.id === "runEx") return runExercise(ex);
  if (t.id === "hintEx") { s.hints = Math.min((ex.hints || []).length, s.hints + 1); saveLesson(); keepCode(); renderExercise(); return; }
  if (t.id === "explainErr") { Tutor.ask("Perché il mio codice non supera i test? Spiegami l'errore e dammi un indizio, senza scrivere la soluzione completa."); return; }
  if (t.id === "resetCode") {
    if (!t.dataset.armed) { t.dataset.armed = "1"; t.textContent = "Sicuro? Perdi le modifiche"; setTimeout(() => { if (t.isConnected) { delete t.dataset.armed; t.textContent = "Ripristina il codice iniziale"; } }, 3500); return; }
    s.code = ex.starter; saveLesson(); renderExercise(); return;
  }
  if (t.id === "revealSol") {
    if (!t.dataset.armed) { t.dataset.armed = "1"; t.textContent = "Sicuro? Conta come aiuto"; setTimeout(() => { if (t.isConnected) { delete t.dataset.armed; t.textContent = "Mostra la soluzione"; } }, 3500); return; }
    s.revealed = true; saveLesson(); keepCode(); renderExercise(); $("#solvedBox").scrollIntoView({block: "nearest", behavior: "smooth"}); return;
  }
  if (t.id === "showSol") { s.showSol = true; $("#solvedBox").innerHTML = solvedHtml(ex); return; }
  if (t.id === "checkGuess") {
    const g = $("#guess").value; s.guess = g; s.attempts++;
    const a = normOut(g).split("\n"), b = normOut(ex.output).split("\n");
    const ok = normOut(g) === normOut(ex.output);
    if (ok) s.solved = true;
    const rows = Array.from({length: Math.max(a.length, b.length)}, (_, i) => ({you: a[i] ?? "", real: b[i] ?? ""}));
    s.lastHtml = ok ? "" : `<span class="eyebrow">Non ancora: le righe evidenziate sono diverse</span><div class="cmp-wrap"><table class="cmp"><tr><th>#</th><th>Il tuo output</th></tr>${rows.map((r, i) => `<tr class="${r.you === r.real ? "" : "bad"}"><td>${i + 1}</td><td>${esc(r.you) || "<span class='muted'>(vuota)</span>"}</td></tr>`).join("")}</table></div>
      <p class="muted" style="margin:0;font-size:13px">${a.length !== b.length ? `Il programma stampa ${b.length} ${b.length === 1 ? "riga" : "righe"}, tu ne hai scritte ${a.length}.` : "Il numero di righe è giusto: ricontrolla i valori."}</p>`;
    s.last = ok ? "" : `Lo studente ha previsto:\n${g}`;
    saveLesson(); renderExercise(); return;
  }
  if (t.id === "revealOut") { s.revealed = true; saveLesson(); renderExercise(); return; }
  if (t.dataset.quick === "trace") { Tutor.ask("Seguiamo questo codice insieme, una riga alla volta. Fammi domande tu, senza dirmi subito l'output."); return; }
  if (t.dataset.mv) {
    const pos = +t.dataset.pos, to = pos + +t.dataset.mv;
    if (to < 0 || to >= s.order.length) return;
    [s.order[pos], s.order[to]] = [s.order[to], s.order[pos]];
    saveLesson(); renderExercise();
    const btn = $(`#parsons [data-pos="${to}"][data-mv="${t.dataset.mv}"]`); if (btn) btn.focus();
  }
}
function keepCode() { const ex = App.L.exercises.find(x => x.id === App.exId); if (ex && App.editor && ex.type !== "predici" && ex.type !== "riordina") ex.state.code = App.editor.get(); }

function bindParsons(ex) {
  const ol = $("#parsons"); let from = null;
  ol.addEventListener("dragstart", e => { const li = e.target.closest("li"); if (!li) return; from = +li.dataset.pos; li.classList.add("drag"); e.dataTransfer.effectAllowed = "move"; e.dataTransfer.setData("text/plain", ""); });
  ol.addEventListener("dragend", e => { $$("li", ol).forEach(li => li.classList.remove("drag", "over")); });
  ol.addEventListener("dragover", e => { e.preventDefault(); const li = e.target.closest("li"); $$("li", ol).forEach(x => x.classList.toggle("over", x === li)); });
  ol.addEventListener("drop", e => {
    e.preventDefault(); const li = e.target.closest("li"); if (!li || from === null) return;
    const to = +li.dataset.pos, s = ex.state;
    const [item] = s.order.splice(from, 1); s.order.splice(to, 0, item);
    from = null; saveLesson(); renderExercise();
  });
}

async function generateExercise(type) {
  const L = App.L;
  if (App.exGen) return;
  keepCode();
  App.exGen = {diff: App.diff, type};
  renderExercise();
  try {
    const ex = await api("/api/exercise", {method: "POST", body: {type, lang: L.lang, difficulty: App.diff, topic: topicOf(L), avoid: L.exercises.map(x => x.title)}});
    App.exGen = null;
    if (App.L !== L) { L.exercises.push(ex); api(`/api/lessons/${L.id}`, {method: "PUT", body: L}); return; }
    L.exercises.push(ex); App.exId = ex.id; App.exType = type;
    saveLesson(true);
    if (App.view === "ex") renderExercises();
  } catch (e) {
    App.exGen = null;
    if (App.view === "ex") { renderExercise(); $("#exBody").insertAdjacentHTML("afterbegin", `<div class="banner err" style="margin-bottom:12px"><b>Esercizio non creato.</b><span>${esc(e.message)}</span></div>`); }
  }
}

/* ================================================================ editor */
function makeEditor(host, value, {onChange, onRun}) {
  host.innerHTML = `<div class="ed"><pre class="ed-gutter" aria-hidden="true"></pre><textarea class="ed-ta askable-ta" spellcheck="false" autocomplete="off" autocorrect="off" autocapitalize="off" aria-label="Il tuo codice"></textarea></div>`;
  const ta = $(".ed-ta", host), gut = $(".ed-gutter", host);
  ta.value = value;
  const lines = () => { const n = ta.value.split("\n").length; gut.textContent = Array.from({length: n}, (_, i) => i + 1).join("\n"); ta.rows = Math.min(28, Math.max(10, n + 2)); };
  lines();
  ta.addEventListener("input", () => { lines(); onChange && onChange(ta.value); });
  ta.addEventListener("scroll", () => { gut.scrollTop = ta.scrollTop; });
  ta.addEventListener("keydown", e => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); onRun && onRun(); return; }
    if (e.key === "Tab") {
      e.preventDefault();
      const s = ta.selectionStart, en = ta.selectionEnd, v = ta.value;
      if (s === en && !e.shiftKey) { insertText(ta, "    "); return; }
      const ls = v.lastIndexOf("\n", s - 1) + 1, le = v.indexOf("\n", en - 1) < 0 ? v.length : v.indexOf("\n", Math.max(en - 1, s));
      const block = v.slice(ls, le);
      const nb = e.shiftKey ? block.replace(/^ {1,4}/gm, "") : block.replace(/^/gm, "    ");
      ta.setSelectionRange(ls, le); insertText(ta, nb); ta.setSelectionRange(ls, ls + nb.length);
      return;
    }
    if (e.key === "Enter") {
      e.preventDefault();
      const s = ta.selectionStart, v = ta.value, ls = v.lastIndexOf("\n", s - 1) + 1, line = v.slice(ls, s);
      let ind = (line.match(/^ */) || [""])[0];
      if (/[:{(\[]\s*$/.test(line)) ind += "    ";
      insertText(ta, "\n" + ind); return;
    }
    if (e.key === "}") {
      const s = ta.selectionStart, v = ta.value, ls = v.lastIndexOf("\n", s - 1) + 1, line = v.slice(ls, s);
      if (/^ {4,}$/.test(line)) { e.preventDefault(); ta.setSelectionRange(s - 4, s); insertText(ta, "}"); }
    }
  });
  ta.addEventListener("paste", e => { e.preventDefault(); toast("Niente incolla: scrivilo tu, è così che si impara."); });
  ta.addEventListener("drop", e => e.preventDefault());
  return {get: () => ta.value, focus: () => ta.focus(), ta};
}

/* ================================================================ tutor */
const Tutor = {
  turns: [], ctx: "", ctl: null,
  reset() { this.turns = []; if (this.ctl) this.ctl.abort(); this.render(); },
  setContext(ctx, label) { this.ctx = ctx; if (label !== undefined) $("#tutorCtx").textContent = label ? "Contesto: " + label : ""; },
  setQuick(list) { $("#tutorQuick").innerHTML = (list || []).map(q => `<button class="chip" type="button" data-q="${esc(q)}">${esc(q)}</button>`).join(""); },
  render() {
    const box = $("#tutorMsgs");
    if (!this.turns.length) {
      box.innerHTML = `<p class="t-empty">Chiedi qualsiasi cosa sul codice che stai studiando: cosa fa una riga, perché si usa un certo metodo, un esempio diverso. Puoi anche <b>selezionare del codice</b> e premere <b>Cosa fa?</b>. Il tutor sa cosa stai guardando e negli esercizi ti guida senza darti la soluzione.</p>`;
      return;
    }
    box.innerHTML = this.turns.map(t => t.role === "user" ? `<div class="msg user">${esc(t.content)}</div>`
      : `<div class="msg bot ${t.error ? "err" : ""}">${t.content ? md(t.content) : `<span class="think">Sto pensando…</span>`}</div>`).join("");
    box.scrollTop = box.scrollHeight;
  },
  async ask(text) {
    text = String(text || "").trim(); if (!text) return;
    openTutor();
    if (this.ctl) this.ctl.abort();
    this.turns.push({role: "user", content: text});
    LOG.ev("tutor", {len: text.length, where: $("#tutorCtx").textContent.slice(0, 80), q: text.slice(0, 200)});
    const bot = {role: "assistant", content: ""};
    this.turns.push(bot); this.render();
    const ctl = this.ctl = new AbortController();
    $("#tutorStop").hidden = false; $("#tutorSend").disabled = true;
    try {
      const msgs = this.turns.filter(t => t !== bot && !t.error && t.content).slice(-10).map(({role, content}) => ({role, content}));
      const r = await fetch("/api/ask", {method: "POST", signal: ctl.signal, headers: {"X-Ricalco": "1", "Content-Type": "application/json"}, body: JSON.stringify({context: this.ctx, messages: msgs})});
      if (!r.ok) { const d = await r.json().catch(() => ({})); throw new Error(d.error || `Errore ${r.status}`); }
      const reader = r.body.getReader(), dec = new TextDecoder();
      let last = 0;
      for (;;) {
        const {done, value} = await reader.read();
        if (done) break;
        bot.content += dec.decode(value, {stream: true});
        if (Date.now() - last > 60) { this.render(); last = Date.now(); }
      }
      if (!bot.content.trim()) { bot.content = "Il modello non ha risposto. Riprova."; bot.error = true; }
    } catch (e) {
      if (e.name === "AbortError") { if (!bot.content) { this.turns.pop(); } }
      else { bot.content = bot.content || e.message; bot.error = !bot.content || bot.content === e.message; }
    }
    if (this.ctl === ctl) { this.ctl = null; $("#tutorStop").hidden = true; $("#tutorSend").disabled = false; }
    this.render();
  }
};
function openTutor() { document.body.classList.add("tutor-open"); }
$("#tutorFab").onclick = () => { openTutor(); $("#tutorIn").focus(); };
$("#tutorClose").onclick = () => document.body.classList.remove("tutor-open");
$("#tutorNew").onclick = () => Tutor.reset();
$("#tutorStop").onclick = () => { if (Tutor.ctl) Tutor.ctl.abort(); };
$("#tutorForm").addEventListener("submit", e => { e.preventDefault(); const v = $("#tutorIn").value; $("#tutorIn").value = ""; Tutor.ask(v); });
$("#tutorIn").addEventListener("keydown", e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); $("#tutorForm").requestSubmit(); } });
$("#tutorQuick").addEventListener("click", e => { const b = e.target.closest("[data-q]"); if (b) Tutor.ask(b.dataset.q); });

/* ---- "Cosa fa?" sulla selezione */
const selBtn = $("#selAsk");
let selText = "";
function placeSel(x, y) {
  selBtn.hidden = false;
  selBtn.style.left = Math.max(8, Math.min(innerWidth - 100, x)) + "px";
  selBtn.style.top = Math.max(8, y - 38) + "px";
}
document.addEventListener("selectionchange", () => {
  clearTimeout(placeSel.t);
  placeSel.t = setTimeout(() => {
    const a = document.activeElement;
    if (a && a.classList && a.classList.contains("askable-ta")) {
      const t = a.value.slice(a.selectionStart, a.selectionEnd);
      if (t.trim().length < 2) { selBtn.hidden = true; return; }
      selText = t;
      const r = a.getBoundingClientRect();
      if (selBtn.hidden) placeSel(r.right - 110, r.top + 6 + 38);
      return;
    }
    const s = getSelection();
    const t = String(s || "");
    const node = s && s.anchorNode, el = node && (node.nodeType === 1 ? node : node.parentElement);
    if (t.trim().length < 2 || !el || !el.closest(".askable")) { selBtn.hidden = true; return; }
    selText = t;
    const rect = s.getRangeAt(0).getBoundingClientRect();
    placeSel(rect.left + rect.width / 2 - 36, rect.top);
  }, 120);
});
selBtn.addEventListener("mousedown", e => e.preventDefault());
selBtn.addEventListener("click", () => {
  selBtn.hidden = true;
  Tutor.ask(`Cosa fa questo pezzo di codice, e perché è scritto così?\n\`\`\`\n${selText.trim()}\n\`\`\``);
});

/* ================================================================ percorso */
const LEVEL_NAMES = {base: "Base", pratica: "Pratica", sfida: "Sfida"};
const MODE_NOTE = {
  output: "Si esegue il programma e si confronta l'output.",
  tests: "Il tuo codice viene eseguito contro dei test.",
  review: "Codice non eseguibile qui: lo valuta il modello."
};
const stars = n => `<span class="stars" aria-label="${n} stelle su 3">${[1, 2, 3].map(i => `<i class="${i <= n ? "on" : ""}">★</i>`).join("")}</span>`;
let pathTimer = null;

const NAV = [["home", "#/", "Oggi"], ["percorso", "#/percorso", "Percorsi"], ["progetti", "#/progetti", "Progetti"], ["logica", "#/logica", "Logica"], ["carte", "#/carte", "Flashcard"],
             ["colloquio", "#/colloquio", "Colloquio"], ["libere", "#/libere", "Lezioni libere"]];
function mainNav(active) {
  $("#crumbs").innerHTML = NAV.map(([id, h, l]) => `<a href="${h}" ${id === active ? 'aria-current="page"' : ""}>${l}</a>`).join("");
}
function navPath() { mainNav("percorso"); }

function setPath(p) { App.path = p; localStorage.setItem("ricalco.path", p); }
async function showPath() {
  App.view = "path";
  navPath();
  const P = PATHS[App.path], algo = !!P.algo;
  Tutor.setContext(`Lo studente sta guardando il percorso «${P.name}: ${P.goal}».`, `Percorso ${P.name}`);
  Tutor.setQuick(["Da dove mi conviene partire?", algo ? "Quali algoritmi chiedono di più ai colloqui?" : App.path === "sql" ? "Quanto SQL serve a un junior?" : `Cosa serve sapere di ${App.path === "java" ? "Java per arrivare a Spring" : "Python per arrivare a FastAPI"}?`]);
  const v = $("#view");
  v.innerHTML = `<section class="path">
    <header class="path-head">
      <div>
        <p class="eyebrow">Il tuo percorso${algo ? ` · in ${LANG[P.lang]}` : ""}</p>
        <h1>${esc(P.goal)}</h1>
      </div>
      <div class="row">
        <div class="seg" role="group" aria-label="Percorso">
          ${[["python", "Python"], ["java", "Java"], ["sql", "SQL"], [App.path === "algojava" ? "algojava" : "algopy", "Algoritmi"]].map(([k, l]) => `<button type="button" data-plang="${k}" aria-pressed="${App.path === k}">${l}</button>`).join("")}
        </div>
        ${algo ? `<div class="seg" role="group" aria-label="Linguaggio degli algoritmi">
          <button type="button" data-plang="algopy" aria-pressed="${App.path === "algopy"}">in Python</button><button type="button" data-plang="algojava" aria-pressed="${App.path === "algojava"}">in Java</button></div>` : ""}
      </div>
    </header>
    <div id="warn">${ollamaBanner()}</div>
    <div id="pathBody"><div class="empty">Caricamento…</div></div>
  </section>`;
  v.onclick = pathClick;
  await refreshPath();
  clearInterval(pathTimer);
  pathTimer = setInterval(() => { if (App.view === "path") refreshPath(true); else clearInterval(pathTimer); }, 8000);
}

async function refreshPath(quiet) {
  let C;
  const pathAt = App.path;
  try { C = await api(`/api/curriculum?lang=${pathAt}`); } catch (e) { if (!quiet) $("#pathBody").innerHTML = `<div class="banner err">${esc(e.message)}</div>`; return; }
  if (App.path !== pathAt || App.view !== "path") return;
  App.C = C;
  if (C.current) api("/api/focus", {method: "POST", body: {key: C.current}}).catch(() => {});
  const body = $("#pathBody"); if (!body) return;
  const cu = C.units.find(u => u.id === C.curUnit);
  const w = C.worker || {};
  const scroll = $("#view").scrollTop;
  const fixed = C.units.filter(u => u.mastered).length;
  const stepOf = u => !u.learned ? 1 : !u.mastered ? 2 : 3;
  let resume;
  if (!cu) {
    resume = `<div class="resume"><h2>Percorso fissato</h2><p class="muted">Hai riscritto a memoria tutte le lezioni. Continua con gli esercizi Pratica e Sfida, il ripasso quotidiano e il colloquio.</p></div>`;
  } else {
    const st = stepOf(cu), base = cu.levels[0];
    const steps = [["Impara", "riscrivi la lezione con l'aiuto"], ["Fissa", "riscrivila a memoria"], ["Usa", "esercizi sugli stessi concetti"], ["Ripassa", "riscrivi i blocchi nei giorni dopo"]];
    const stepper = `<ol class="stepper">${steps.map(([t, d], k) => `<li class="${k + 1 < st ? "done" : k + 1 === st ? "cur" : ""}"><b>${k + 1}. ${t}</b><small>${d}</small></li>`).join("")}</ol>`;
    const main = st === 1
      ? `<button class="btn primary" data-learn="${cu.id}">${cu.bestLevel ? "Continua la lezione" : "Inizia la lezione"}</button>`
      : `<button class="btn primary" data-memory="${cu.id}">Riscrivila a memoria · livello 3</button>${base.unlocked ? `<a class="btn" href="#/s/${base.key}">Esercizi Base</a>` : ""}<button class="btn ghost" data-learn="${cu.id}">Riguarda la lezione</button>`;
    const sub = st === 1 ? (cu.lessonReady ? "Lezione pronta: prima ragioni su ogni blocco, poi lo riscrivi." : "La lezione la prepara Qwen in sottofondo: la prima volta ci vuole circa un minuto.")
      : `Per aprire l'unità ${cu.n + 1}: almeno ${C.mastery.acc}% di precisione e al massimo ${C.mastery.hints} aiuti.${cu.bestL3 ? ` Il tuo migliore finora: ${Math.round(cu.bestL3)}%.` : ""}`;
    resume = `<div class="resume"><p class="eyebrow">Unità ${cu.n} di ${C.units.length}</p><h2>${esc(cu.title)}</h2><p class="muted">${esc(cu.concepts)}</p>
      ${stepper}<div class="row">${main}<a class="btn ghost" href="#/t/${App.path}/${cu.id}">Scheda di teoria</a></div><p class="ready muted">${sub}</p></div>`;
  }
  body.innerHTML = `
    ${C.reviewDue ? `<a class="review-banner" href="#/carte/ricalco"><b>Ripasso di oggi: ${C.reviewDue} ${C.reviewDue === 1 ? "blocco" : "blocchi"} da riscrivere a memoria.</b><span>Prima il ripasso, poi la lezione nuova: è il modo più rapido per non dimenticare.</span></a>` : ""}
    <div class="path-top">
      ${resume}
      <div class="kpis">
        <div class="stat"><b>${fixed}/${C.units.length}</b><span>Unità fissate</span></div>
        <div class="stat"><b>${C.reviewDue}</b><span>Blocchi da ripassare</span></div>
        <div class="stat"><b>${C.streak}</b><span>Giorni di fila${C.today ? "" : " · oggi no"}</span></div>
        <div class="stat"><b>${C.xp}</b><span>XP</span></div>
      </div>
    </div>
    <div class="row path-tools">
      ${C.mistakes ? `<a class="btn" href="#/r/${App.path}">Ripassa gli esercizi sbagliati (${Math.min(C.mistakes, C.sessionSize)})</a>` : ""}
      <label class="toggle"><input type="checkbox" id="freeMode" ${C.free ? "checked" : ""}> Sblocca tutte le unità (se conosci già le basi)</label>
      <span class="spacer"></span>
      <span class="worker muted" title="${esc(w.error || "")}">${w.job ? `<span class="spin small"></span> In sottofondo Qwen prepara: ${esc(w.job)}` : ""}</span>
    </div>
    <ol class="units">
      ${C.units.map(u => {
        const isCur = cu && u.id === cu.id;
        return `<li class="unit ${u.available ? "" : "locked"} ${isCur ? "current" : ""} ${u.mastered ? "fixed" : ""}" id="unit-${u.id}">
          <span class="u-n">${u.n}</span>
          <div class="u-main">
            <div class="u-title"><h3>${esc(u.title)}</h3>${u.mastered ? `<span class="tag ok">fissata</span>` : ""}${u.mode === "review" ? `<span class="tag wait" title="${esc(MODE_NOTE.review)}">valutato dal modello</span>` : u.mode === "spring" ? `<span class="tag ok" title="Compilato ed eseguito con Maven e JUnit sul tuo PC">test Spring reali</span>` : ""}</div>
            <p class="u-concepts">${esc(u.concepts)}</p>
            ${u.springSetup && u.available ? `<p class="u-missing">Per eseguire davvero questi esercizi con Maven e JUnit: <a href="#/prova">Prova il modello → Prepara Spring</a> (una volta sola).</p>` : ""}
            ${u.missing && u.available ? `<p class="u-missing">Per eseguire davvero questi esercizi installa: <code>${esc(u.missing.join(" "))}</code> (lancia <code>installa_extra.bat</code>).</p>` : ""}
            ${u.available ? `<div class="u-levels">
              <button class="lvl core ${u.learned ? "done" : isCur ? "cur" : ""}" data-learn="${u.id}"><b>1 · Lezione</b><small>${u.learned ? "✓ riscritta" : u.lessonReady ? "pronta" : u.lessonJob === "run" ? "in preparazione…" : u.lessonJob === "queue" ? "in coda" : "da preparare"}</small></button>
              ${u.learned ? `<button class="lvl core ${u.mastered ? "done" : isCur ? "cur" : ""}" data-memory="${u.id}"><b>2 · A memoria</b><small>${u.mastered ? `✓ ${Math.round(u.bestL3)}%` : u.bestL3 ? `migliore ${Math.round(u.bestL3)}%` : "da fare"}</small></button>`
                : `<span class="lvl off"><b>2 · A memoria</b><small>dopo la lezione</small></span>`}
              ${u.levels.map(l => l.unlocked
                ? `<a class="lvl ${l.stars ? "done" : ""}" href="#/s/${l.key}"><b>${l.name}</b>${stars(l.stars)}<small>${l.stars ? `migliore ${l.best}/${C.sessionSize}` : readyShort(l.ready, C.sessionSize)}</small></a>`
                : `<span class="lvl off" title="${u.learned ? "Supera il livello precedente" : "Prima riscrivi la lezione"}"><b>${l.name}</b><small>bloccato</small></span>`).join("")}
              <a class="lvl theory" href="#/t/${App.path}/${u.id}"><b>Teoria</b><small>${u.theory ? "pronta" : "da preparare"}</small></a>
              <span class="u-reset" id="reset-${u.id}"><button class="linkish" data-reset="${u.id}" title="Qwen rifà lezione, teoria ed esercizi di questa unità">↻ Riprepara l'unità</button></span>
            </div>` : `<p class="u-concepts">Si apre quando riscrivi a memoria la lezione dell'unità ${u.n - 1}.</p>`}
          </div>
        </li>`;
      }).join("")}
    </ol>`;
  if (quiet) $("#view").scrollTop = scroll;
  else if (cu) { const el = $(`#unit-${cu.id}`); if (el && cu.n > 2) el.scrollIntoView({block: "center"}); }
}
function readyText(n, size) {
  if (n >= size) return `${size} esercizi pronti.`;
  if (n > 0) return `${n} esercizi già pronti, gli altri arrivano mentre fai i primi.`;
  return App.status && App.status.model ? "Qwen sta preparando gli esercizi: il primo arriva in circa mezzo minuto." : "Accendi Ollama per generare gli esercizi.";
}
function readyShort(n, size) { return n >= size ? "pronto" : n ? `${n} pronti` : "in preparazione"; }

async function pathClick(e) {
  const t = e.target.closest("button, input"); if (!t) return;
  if (t.dataset.plang) { setPath(t.dataset.plang); showPath(); return; }
  if (t.id === "freeMode") { await api("/api/free", {method: "POST", body: {free: t.checked}}); refreshPath(true); return; }
  if (t.id === "retryStatus") { await refreshStatus(); $("#warn").innerHTML = ollamaBanner(); return; }
  if (t.dataset.reset) {
    $(`#reset-${t.dataset.reset}`).innerHTML = `<span class="muted" style="font-size:12.5px">Rifare lezione, teoria ed esercizi?</span>
      <button class="btn small" data-reset-go="${t.dataset.reset}">Sì, tengo i progressi</button>
      <button class="btn small ghost" data-reset-go="${t.dataset.reset}" data-progress="1">Sì, e azzero i progressi</button>
      <button class="linkish" data-reset-no="1">Annulla</button>`;
    return;
  }
  if (t.dataset.resetNo) { refreshPath(true); return; }
  if (t.dataset.resetGo) {
    const uid = t.dataset.resetGo;
    try {
      await api("/api/unit/reset", {method: "POST", body: {lang: App.path, unit: uid, progress: !!t.dataset.progress}});
      LOG.ev("unit_reset", {unit: `${App.path}/${uid}`, progress: !!t.dataset.progress});
      toast("Qwen riprepara l'unità: prima la lezione, poi teoria ed esercizi. I file vecchi restano come .bak.");
    } catch (err) { toast(err.message); }
    refreshPath(true); return;
  }
  if (t.dataset.learn) return openUnitLesson(t.dataset.learn, 1, t);
  if (t.dataset.memory) return openUnitLesson(t.dataset.memory, 3, t);
  if (t.dataset.guided) {
    const u = App.C.units.find(x => x.id === t.dataset.guided);
    t.disabled = true; t.textContent = "Preparo la lezione…";
    try {
      const L = await api("/api/lesson", {method: "POST", body: {request: `${u.title}: ${u.concepts}`, lang: PATHS[App.path].lang, level: u.n > 6 ? "intermedio" : "base"}});
      App.L = L; Tutor.reset(); location.hash = `#/l/${L.id}`;
    } catch (err) { toast(err.message); t.disabled = false; t.textContent = "Lezione guidata da riscrivere"; }
  }
}

async function openUnitLesson(uid, level, btn) {
  const tw = Date.now();
  const old = btn ? btn.innerHTML : "";
  if (btn) { btn.disabled = true; btn.innerHTML = `<span class="spin small"></span> Qwen prepara la lezione…`; }
  const path = App.path, hash = location.hash;
  try {
    let L = await api("/api/unit_lesson", {method: "POST", body: {lang: path, unit: uid}});
    // La lezione non c'è ancora: Qwen la prepara con precedenza sul lavoro in sottofondo. Puoi intanto sceglierne un'altra.
    while (L.pending || L.ready === false) {
      if (L.state === "error") throw new Error("Qwen non è riuscito a preparare la lezione: " + (L.error || "") + " Riprova.");
      if (btn && document.body.contains(btn)) btn.innerHTML = `<span class="spin small"></span> ${L.state === "queue" && L.ahead ? `In coda dopo ${L.ahead} ${L.ahead === 1 ? "lezione" : "lezioni"}…` : `Qwen prepara la lezione… ${L.secs || 0} s`}`;
      await new Promise(r => setTimeout(r, 1500));
      if (location.hash !== hash) { toast("La lezione continua a prepararsi: la trovi pronta nel percorso."); return; }
      L = await api(`/api/unit_lesson/status?lang=${path}&unit=${uid}`);
    }
    delete L.ready; delete L.pending;
    const p = L.progress || {};
    const fresh = level === 3 || p.done || !p.block;
    if (fresh) {
      L.progress = {block: 0, phase: "ragiona", done: false, skipQuestions: level === 3, askRedo: level === 3 ? false : undefined};
      App.traceLevel = level; localStorage.setItem("ricalco.trace", level);
      L.blocks.forEach(b => { if (b.question) b.order = shuffled(b.question.options.length); });
      await api(`/api/lessons/${L.id}`, {method: "PUT", body: L});
    }
    App.L = L; Tutor.reset();
    if (secsSince(tw) > 2) LOG.ev("wait", {what: "lezione del percorso", secs: secsSince(tw)});
    location.hash = `#/l/${L.id}`;
  } catch (e) { toast(e.message); if (btn) { btn.disabled = false; btn.innerHTML = old; } }
}

/* ================================================================ teoria */
async function showTheory(lang, uid) {
  App.view = "theory";
  if (lang !== App.path) setPath(lang);
  navPath();
  const C = App.C && App.C.lang === lang ? App.C : await api(`/api/curriculum?lang=${lang}`);
  App.C = C;
  const u = C.units.find(x => x.id === uid); if (!u) { location.hash = "#/percorso"; return; }
  const first = u.levels.find(l => l.unlocked && !l.stars) || u.levels.find(l => l.unlocked);
  const v = $("#view");
  v.innerHTML = `<section class="theory">
    <p class="eyebrow">${esc(PATHS[lang].name)} · Unità ${u.n} · Teoria</p>
    <h1>${esc(u.title)}</h1>
    <div id="thBody"><div class="gen"><span class="spin"></span><div><p><b>Preparo la scheda di teoria</b> <span class="timer" id="thTimer">0:00</span></p><p class="muted" style="font-size:13.5px">La prima volta la scrive Qwen e Ricalco controlla che l'esempio funzioni; poi resta salvata.</p></div></div></div>
  </section>`;
  timerEl($("#thTimer"));
  Tutor.setContext(`Lo studente legge la teoria dell'unità «${u.title}» (${PATHS[lang].name}): ${u.concepts}`, `Teoria · ${u.title}`);
  Tutor.setQuick(["Fammi un altro esempio", "Spiegamelo come se fossi alle prime armi", "Qual è l'errore più comune?"]);
  let T;
  try { T = await api(`/api/theory?lang=${lang}&unit=${uid}`); }
  catch (e) { $("#thBody").innerHTML = `<div class="banner err"><b>Teoria non disponibile.</b><span>${esc(e.message)}</span></div>`; return; }
  if (App.view !== "theory") return;
  Tutor.setContext(`Teoria dell'unità «${u.title}» (${PATHS[lang].name}):\n${T.text}\nEsempio:\n${T.example}`);
  $("#thBody").innerHTML = `
    <div class="th-text">${md(T.text)}</div>
    <div><span class="eyebrow">Esempio${T.runnable === false ? " · non eseguibile qui" : ""}</span><pre class="ro askable">${esc(T.example)}</pre>
      ${T.output ? `<details class="th-out"><summary>Cosa stampa</summary><pre class="out">${esc(T.output)}</pre></details>` : ""}</div>
    ${T.points && T.points.length ? `<div class="th-box"><span class="eyebrow">Da ricordare</span><ul>${T.points.map(p => `<li>${inl(p)}</li>`).join("")}</ul></div>` : ""}
    ${T.pitfall ? `<div class="th-box warnbox"><span class="eyebrow">Errore tipico</span><p>${inl(T.pitfall)}</p></div>` : ""}
    <div class="row">
      ${first ? `<a class="btn primary" href="#/s/${first.key}">Esercitati · ${first.name}</a>` : ""}
      <a class="btn" href="#/percorso">Torna al percorso</a>
    </div>`;
}

/* ================================================================ sessione */
const P = {s: null};

async function startSession(key, review, opts = {}) {
  App.view = "session";
  const top = review ? "path" : key.split("/")[0];
  mainNav(top === "logica" ? (opts.live ? "colloquio" : "logica") : top === "colloquio" ? "colloquio" : "percorso");
  const v = $("#view");
  v.innerHTML = `<section class="session"><div id="sessBody"><div class="empty">Preparo la sessione…</div></div></section>`;
  v.onclick = sessionClick;
  let data;
  try {
    data = review ? await api("/api/review", {method: "POST", body: {lang: key}})
                  : await api("/api/session", {method: "POST", body: opts.live ? {key, types: ["zero"], size: 3} : {key}});
  } catch (e) { $("#sessBody").innerHTML = `<div class="banner err"><b>Non posso iniziare.</b><span>${esc(e.message)}</span><div><a class="btn small" href="#/percorso">Torna al percorso</a></div></div>`; return; }
  const kind = review ? "path" : data.kind;
  const path = review ? key : (data.path || key.split("/")[0]);
  const lang = data.lang || (PATHS[path] ? PATHS[path].lang : "python");
  const [, uid, lvl] = review ? [key, null, null] : key.split("/");
  let unit = null;
  if (kind === "path" && !review) {
    const C = App.C && App.C.lang === path ? App.C : await api(`/api/curriculum?lang=${path}`).catch(() => null);
    App.C = C || App.C;
    unit = C ? C.units.find(u => u.id === uid) : null;
  }
  const unitLesson = kind === "path" && !review && unit && unit.lessonReady ? await api(`/api/lessons/${unit.lessonId}`).catch(() => null) : null;
  if (review && !data.exercises.length) { $("#sessBody").innerHTML = `<div class="empty">Nessun errore da ripassare. <a href="#/percorso">Torna al percorso</a></div>`; return; }
  P.s = {key, lang, path: kind === "path" ? path : null, kind, review, unit, lvl, live: !!opts.live, types: opts.live ? ["zero"] : null, adapt: review ? "" : data.adapt || "",
         en: /_en\//.test(key),
         label: review ? `Ripasso errori · ${PATHS[path].name}` : (opts.live ? data.label.replace("Logica", "Live coding") : data.label),
         exitHref: kind === "path" ? "#/percorso" : kind === "logic" && !opts.live ? "#/logica" : "#/colloquio",
         unitLesson, list: data.exercises.map(prepEx), i: 0, results: [], gained: 0,
         size: review ? data.exercises.length : data.size, done: false, poll: null};
  renderSession();
}
function prepEx(ex) {
  const e = JSON.parse(JSON.stringify(ex));
  e.state = {tries: 0, hints: 0, solved: false, revealed: false, wrong: [], t0: Date.now()};
  if (e.type === "quiz" || e.type === "logica") e.order = shuffled(e.options.length);
  if (e.type === "riordina") e.state.order = e.lines.map((_, i) => i);
  if (["completa", "bug", "zero"].includes(e.type)) e.state.code = e.starter || "";
  return e;
}

function sessCtx(ex) {
  const s = P.s;
  let c = `Sessione: ${s.label}${s.unit ? ` (${s.unit.concepts})` : ""}.\n`;
  if (s.kind === "interview") c += "È un allenamento per il colloquio tecnico: aiutalo come farebbe un mentore, senza dare la risposta modello finché non ha risposto.\n";
  if (!ex) return c;
  c += `Esercizio «${ex.title}» (${TYPES[ex.type] ? TYPES[ex.type].name : ex.type}).\n`;
  if (ex.statement) c += `Consegna: ${ex.statement}\n`;
  if (ex.question) c += `Domanda: ${ex.question}\n` + (ex.options ? `Opzioni: ${ex.options.join(" | ")}\n` : "");
  if (ex.code) c += `Codice:\n${ex.code}\n`;
  if (ex.state.code) c += `Codice attuale dello studente:\n${ex.state.code}\n`;
  if (ex.state.last) c += `Ultimo risultato:\n${ex.state.last}\n`;
  if (!ex.state.solved && !ex.state.revealed) c += "NON dare la risposta o la soluzione: guida con indizi e domande.\n";
  else c += `Soluzione/risposta: ${ex.solution || ex.model || ex.answer || (ex.answers ? ex.answers.join(", ") : "") || ex.output || (ex.options ? ex.options[ex.correct] : "")}\n`;
  return c;
}

function renderSession() {
  const s = P.s, body = $("#sessBody"); if (!body) return;
  clearTimeout(s.poll);
  if (s.done) return renderSummary();
  const ex = s.list[s.i];
  const segs = Array.from({length: s.size}, (_, k) => {
    const r = s.results[k];
    return `<span class="${r ? r.result : k === s.i ? "cur" : ""}"></span>`;
  }).join("");
  const head = `<div class="sess-head">
    <a class="btn small ghost" href="${s.exitHref}" title="Esci dalla sessione">Esci</a>
    <div class="sess-bar">${segs}</div>
    ${s.live ? `<span class="live-timer" id="liveTimer"></span>` : ""}
    <span class="sess-xp"><b>+${s.gained}</b> XP</span></div>
    <p class="eyebrow sess-sub">${esc(s.label)} · esercizio ${Math.min(s.i + 1, s.size)} di ${s.size}</p>`;
  if (!ex) {
    s.waitT0 = s.waitT0 || Date.now();
    body.innerHTML = head + `<div class="gen"><span class="spin"></span><div style="flex:1">
      <p><b>Qwen sta preparando il prossimo esercizio</b> <span class="timer" id="waitTimer">0:00</span></p>
      <p class="muted" style="font-size:13.5px" id="waitJob">Ricalco lo esegue per verificarlo prima di mostrartelo. Intanto puoi chiedere qualcosa al tutor: la preparazione si mette in pausa e riprende dopo.</p></div></div>`;
    timerEl($("#waitTimer"));
    pollMore();
    Tutor.setContext(sessCtx(null), "Sessione · in attesa del prossimo esercizio");
    return;
  }
  const adapt = s.adapt && s.i === 0 ? `<p class="adapt">Sessione adattata a te. ${esc(s.adapt)}</p>` : "";
  body.innerHTML = head + adapt + `<article class="exc sess-card">${exHead(ex)}${exBody(ex)}<div class="results" id="results">${ex.state.lastHtml || ""}</div><div id="feedback">${feedbackHtml(ex)}</div></article>`;
  afterRender(ex);
  if (!s.review && s.list.length < s.size) s.poll = setTimeout(() => pollMore(), 1500);
  if (s.live) liveTick(ex);
  Tutor.setContext(sessCtx(ex), `Esercizio «${ex.title}»`);
  Tutor.setQuick(ex.type === "orale" ? ["Da dove parto per rispondere?", "Fammi un esempio pratico"]
    : ex.type === "logica" ? ["Dammi un indizio senza la soluzione", "Come imposto il ragionamento?"]
    : ex.type === "quiz" ? ["Non capisco la domanda", "Dammi un indizio"]
    : ex.type === "predici" ? ["Seguiamo il codice riga per riga", "Cosa fa la riga che non capisco?"]
    : ["Dammi un indizio", "Spiegami la consegna", "Cosa significa questo errore?"]);
}

function exHead(ex) {
  const rev = ex.check === "review";
  return `<div class="exc-head"><span class="tag acc">${TYPES[ex.type] ? TYPES[ex.type].name : ex.type}</span>
    ${rev ? `<span class="tag wait" title="Il codice non viene eseguito: lo valuta il modello">valutato dal modello</span>` : ""}
    ${ex.check === "spring" ? `<span class="tag ok" title="Compilato ed eseguito con Maven e JUnit">test Spring reali</span>` : ""}
    ${ex.ripasso ? `<span class="tag wait" title="Un esercizio sbagliato in un livello precedente">ripasso</span>` : ""}
    <h2>${esc(ex.title)}</h2></div>`;
}

function exBody(ex) {
  const s = ex.state, locked = s.solved || s.revealed;
  const lang = ex.lang || P.s.lang;
  if (ex.type === "orale") {
    const j = s.judge;
    return `<p class="q">${inl(ex.question)}</p>
      <textarea class="open-ans big" id="oralAns" placeholder="Rispondi come faresti al colloquio: chiaro, con un esempio se serve." ${locked ? "readonly" : ""}>${esc(s.answer || "")}</textarea>
      ${!locked ? `<div class="row"><button class="btn primary" data-act="judgeAns">Valuta la risposta</button><span class="muted" style="font-size:12.5px">valutazione del modello</span>
        ${s.tries ? `<span class="spacer"></span><button class="btn ghost" data-act="reveal">Mostra la risposta modello</button>` : ""}</div>` : ""}
      ${j ? judgeHtml(j) : ""}`;
  }
  if (ex.type === "logica" && s.free) {
    return `<p class="q">${inl(ex.question)}</p>
      <div class="row"><input class="free-ans" id="freeAns" placeholder="La tua risposta" value="${esc(s.freeVal || "")}" ${locked ? "readonly" : ""} autocomplete="off">
      ${!locked ? `<button class="btn primary" data-act="checkFree">Verifica</button><button class="linkish" data-act="toggleFree">Mostra le opzioni</button>` : ""}</div>
      ${!locked && s.tries ? `<div class="row"><button class="btn ghost" data-act="reveal">Mostrami la risposta</button></div>` : ""}`;
  }
  if (ex.type === "quiz" || ex.type === "logica") {
    const L = "ABCDE";
    return `<p class="q">${inl(ex.question)}</p>${dbHtml(ex, false)}${ex.code ? `<pre class="ro askable">${esc(ex.code)}</pre>` : ""}
      <div class="opts">${ex.order.map((oi, k) => {
        const cls = locked && oi === ex.correct ? "right" : s.wrong.includes(oi) ? "wrong" : "";
        return `<button class="opt ${cls}" data-qopt="${oi}" ${locked || s.wrong.includes(oi) ? "disabled" : ""}><span class="k">${L[k]}</span><span>${inl(ex.options[oi])}</span></button>`;
      }).join("")}</div>
      <div class="row">${!locked && ex.type === "logica" && !s.tries ? `<button class="linkish" data-act="toggleFree">Rispondi senza vedere le opzioni</button>` : ""}
      ${!locked && s.tries ? `<button class="btn ghost" data-act="reveal">Mostrami la risposta</button>` : ""}</div>`;
  }
  if (ex.type === "riempi") {
    const parts = ex.code.split("___");
    let html = "";
    parts.forEach((p, k) => {
      html += esc(p);
      if (k < parts.length - 1) {
        const val = s.fill ? s.fill[k] || "" : "";
        const w = Math.max(3, (ex.answers[k] || "").length + 1);
        html += `<input class="blank ${s.badBlank && s.badBlank.includes(k) ? "bad" : ""} ${locked ? "okb" : ""}" data-blank="${k}" style="width:${w + 1}ch" value="${esc(locked ? (s.revealed && !s.solved ? ex.answers[k] : val) : val)}" ${locked ? "readonly" : ""} spellcheck="false" autocomplete="off" aria-label="Spazio ${k + 1}">`;
      }
    });
    return `${ex.statement ? `<p class="statement">${inl(ex.statement)}</p>` : ""}${dbHtml(ex, true)}<pre class="ro fill askable">${html}</pre>
      ${!locked ? `<div class="row"><button class="btn primary" data-act="checkFill">Verifica</button><span class="muted" style="font-size:12.5px"><kbd>Invio</kbd> per verificare</span>${s.tries ? `<span class="spacer"></span><button class="btn ghost" data-act="reveal">Mostra la risposta</button>` : ""}</div>` : ""}`;
  }
  if (ex.type === "predici" && ex.check === "sql") {
    return `<p class="statement">Leggi la query e scrivi le righe del risultato, <b>una per riga</b>, con i valori separati da <code>|</code>${ex.outCols && ex.outCols.length ? ` nell'ordine delle colonne <code>${esc(ex.outCols.join(" | "))}</code>` : ""}.</p>
      ${dbHtml(ex, true)}<pre class="ro askable">${esc(ex.code)}</pre>
      <textarea class="guess" id="guess" spellcheck="false" placeholder="Es. Ada | Roma" ${locked ? "readonly" : ""}>${esc(s.guess || "")}</textarea>
      ${!locked ? `<div class="row"><button class="btn primary" data-act="checkGuess">Verifica</button><span class="muted" style="font-size:12.5px">${/order\s+by/i.test(ex.code) ? "L'ordine delle righe conta." : "Senza ORDER BY l'ordine delle righe non conta."} Scrivi NULL per i valori mancanti.</span>${s.tries ? `<span class="spacer"></span><button class="btn ghost" data-act="reveal">Mostra il risultato</button>` : ""}</div>` : ""}`;
  }
  if (ex.type === "predici") {
    return `<p class="statement">Leggi il codice e scrivi <b>esattamente</b> cosa stampa.</p><pre class="ro askable">${esc(ex.code)}</pre>
      <textarea class="guess" id="guess" spellcheck="false" placeholder="Una riga per ogni riga stampata" ${locked ? "readonly" : ""}>${esc(s.guess || "")}</textarea>
      ${!locked ? `<div class="row"><button class="btn primary" data-act="checkGuess">Verifica</button>${s.tries ? `<span class="spacer"></span><button class="btn ghost" data-act="reveal">Mostra l'output</button>` : ""}</div>` : ""}`;
  }
  const tp = ex.check === "sql" ? dbHtml(ex, true) + (ex.expected ? `<details class="exp-out"><summary class="muted">Risultato atteso${ex.ordered ? " (in quest'ordine)" : ""}</summary>${sqlTable(ex.expected)}</details>` : "")
    : ex.check === "spring" ? `<details class="exp-out" open><summary class="muted">Test JUnit che il codice deve superare</summary><pre class="out askable">${esc(ex.tests_java || "")}</pre></details>`
    : ex.tests ? testsPreview(ex) : ex.check === "output" ? `<details class="exp-out"><summary class="muted">Output atteso</summary><pre class="out">${esc(ex.output)}</pre></details>` : "";
  const hints = ex.hints && ex.hints.length ? `<button class="btn" data-act="hint" ${s.hints >= ex.hints.length || locked ? "disabled" : ""}>Suggerimento ${Math.min(s.hints + 1, ex.hints.length)}/${ex.hints.length}</button>` : "";
  const shownHints = s.hints ? `<div><span class="eyebrow">Suggerimenti</span><ol class="hints">${ex.hints.slice(0, s.hints).map(h => `<li>${inl(h)}</li>`).join("")}</ol></div>` : "";
  const runLabel = ex.check === "sql" ? (ex.type === "riordina" ? "Verifica l'ordine" : "Esegui la query") : ex.check === "spring" ? "Esegui i test Spring" : ex.check === "review" ? "Fai valutare" : ex.type === "riordina" ? "Verifica l'ordine" : ex.check === "output" ? "Esegui" : "Esegui i test";
  const actions = locked ? "" : `<div class="row"><button class="btn primary" data-act="run" id="runBtn">${runLabel}</button>${ex.type !== "riordina" ? `<span class="muted" style="font-size:12.5px"><kbd>Ctrl</kbd>+<kbd>Invio</kbd></span>` : ""}<span class="spacer"></span>${hints}
      ${s.last ? `<button class="btn" data-act="explain">Spiega il mio errore</button>` : ""}<button class="btn ghost" data-act="reveal">Mostra la soluzione</button></div>`;
  if (ex.type === "riordina") {
    return `<p class="statement">${inl(ex.statement || "Rimetti le righe nell'ordine giusto.")}</p>${tp}
      <ol class="parsons askable" id="parsons">${s.order.map((li, pos) => `<li draggable="${!locked}" data-pos="${pos}"><span class="grip">⋮⋮</span><pre>${esc(ex.lines[li])}</pre><span class="mv">${locked ? "" : `<button data-mv="-1" data-pos="${pos}" aria-label="Sposta su">↑</button><button data-mv="1" data-pos="${pos}" aria-label="Sposta giù">↓</button>`}</span></li>`).join("")}</ol>
      ${shownHints}${actions}`;
  }
  return `<p class="statement">${inl(ex.statement)}</p>${tp}<div id="editorHost"></div>${shownHints}${actions}`;
}

function feedbackHtml(ex) {
  const s = ex.state;
  if (!s.solved && !s.revealed) return "";
  const good = s.solved && !s.revealed;
  const r = P.s.results[P.s.i];
  const label = good ? (r && r.result === "first" ? "Giusto al primo colpo." : "Giusto.") : "Ecco la soluzione.";
  let extra = "";
  if (ex.type === "predici") extra = good ? "" : ex.check === "sql" ? `<pre class="out">${esc((ex.outCols || []).join(" | ") + "\n" + ex.output)}</pre>` : `<pre class="out">${esc(ex.output)}</pre>`;
  if (ex.type === "logica") extra = `${good ? "" : `<p class="explain">Risposta: <b>${esc(ex.answer)}</b></p>`}<details><summary class="muted" style="cursor:pointer">Il programma che verifica la risposta</summary><pre class="out askable">${esc(ex.verify || "")}</pre></details>`;
  if (ex.type === "orale") extra = `<div><span class="eyebrow">Risposta modello</span><div class="th-text">${md(ex.model)}</div><button class="btn small" data-act="saveQ">Salva la domanda da rivedere</button></div>
    ${ex.followup ? `<div class="follow"><span class="eyebrow">Il selezionatore continua</span><p class="explain">${inl(ex.followup)}</p><button class="btn small" data-act="followTutor">Rispondi e discutine col tutor</button></div>` : ""}`;
  if (ex.type === "riempi" && !good) extra = `<p class="explain">Risposte: ${ex.answers.map(a => `<code>${esc(a)}</code>`).join(", ")}</p>`;
  if (["completa", "bug", "zero", "riordina"].includes(ex.type)) extra = `${ex.bugExplain ? `<p class="explain"><b>Il bug:</b> ${inl(ex.bugExplain)}</p>` : ""}<div class="rc-host" id="rcHost"></div><div class="fy-host" id="fyHost"></div>`;
  if (P.s.live && good && ["zero", "bug", "completa"].includes(ex.type)) extra += liveFollowHtml(ex);
  if (P.s.unitLesson && !(r && r.result === "first")) extra += `<div class="row"><button class="btn small" data-act="drill">Riscrivi a memoria il blocco della lezione su questo concetto</button></div><div id="drillBox"></div>`;
  return `<div class="${good ? "solved" : "banner"}"><b>${label}</b>${ex.explain ? `<p class="explain">${inl(ex.explain)}</p>` : ""}${extra}
    <div class="row"><button class="btn primary" data-act="next" id="nextBtn">Continua</button><span class="spacer"></span>
    <button class="linkish" data-act="flag" title="Toglie l'esercizio dal tuo archivio e non conta nel punteggio">L'esercizio è sbagliato? Segnalalo</button></div></div>`;
}

function afterRender(ex) {
  const s = ex.state;
  if (["completa", "bug", "zero"].includes(ex.type)) {
    App.editor = makeEditor($("#editorHost"), s.code, {
      onChange: v => { s.code = v; },
      onRun: () => { if (!s.solved && !s.revealed) runCode(ex); }
    });
    if (s.solved || s.revealed) App.editor.ta.readOnly = true;
  }
  if (ex.type === "riordina" && !(s.solved || s.revealed)) bindSessParsons(ex);
  if (ex.type === "riempi" && !(s.solved || s.revealed)) {
    const first = $$(".blank").find(i => !i.value) || $(".blank");
    if (first) first.focus();
  }
  const nb = $("#nextBtn"); if (nb) nb.focus();
  if (CODE_TYPES.includes(ex.type) && (s.solved || s.revealed) && ex.solution) {
    const r = P.s.results[P.s.i];
    startSolutionRicalco(ex, ex.lang || P.s.lang, !(r && r.result !== "miss"));
  }
}

function bindSessParsons(ex) {
  const ol = $("#parsons"); let from = null;
  ol.addEventListener("dragstart", e => { const li = e.target.closest("li"); if (!li) return; from = +li.dataset.pos; li.classList.add("drag"); e.dataTransfer.setData("text/plain", ""); });
  ol.addEventListener("dragend", () => $$("li", ol).forEach(li => li.classList.remove("drag", "over")));
  ol.addEventListener("dragover", e => { e.preventDefault(); const li = e.target.closest("li"); $$("li", ol).forEach(x => x.classList.toggle("over", x === li)); });
  ol.addEventListener("drop", e => {
    e.preventDefault(); const li = e.target.closest("li"); if (!li || from === null) return;
    const [it] = ex.state.order.splice(from, 1); ex.state.order.splice(+li.dataset.pos, 0, it); from = null; renderSession();
  });
}

function solve(ex, ok) {
  const s = P.s, st = ex.state;
  if (ok) st.solved = true; else st.revealed = true;
  const result = ok ? (st.tries === 0 ? "first" : "retry") : "miss";
  s.results[s.i] = {id: ex.id, result};
  LOG.ev("ex_result", {key: ex.key || s.key, type: ex.type, title: ex.title, result, tries: st.tries, hints: st.hints, secs: st.t0 ? secsSince(st.t0) : null});
  const key = ex.key || s.key;
  if (!ok && CODE_TYPES.includes(ex.type) && ex.solution) {
    api("/api/rewrite_card", {method: "POST", body: {title: ex.title, explain: ex.statement || "", code: ex.solution, lang: ex.lang || s.lang, path: s.path || ex.lang || s.lang, src: ex.id}}).catch(() => {});
  }
  api("/api/result", {method: "POST", body: {key, id: ex.id, result, review: !!s.review}})
    .then(r => { s.gained += r.gain; const x = $(".sess-xp b"); if (x) x.textContent = "+" + s.gained; }).catch(() => {});
  renderSession();
}
function fail(ex, html, text) {
  ex.state.tries++;
  ex.state.lastHtml = html; ex.state.last = text;
  renderSession();
}

function outputDiff(expected, got) {
  const a = normOut(got).split("\n"), b = normOut(expected).split("\n");
  const rows = Array.from({length: Math.max(a.length, b.length)}, (_, i) => ({g: a[i] ?? "", e: b[i] ?? ""}));
  return `<div class="cmp-wrap"><table class="cmp"><tr><th>#</th><th>Atteso</th><th>Il tuo output</th></tr>${rows.map((r, i) => `<tr class="${r.g === r.e ? "" : "bad"}"><td>${i + 1}</td><td>${esc(r.e)}</td><td>${esc(r.g) || "<span class='muted'>(vuota)</span>"}</td></tr>`).join("")}</table></div>`;
}

async function runCode(ex) {
  const st = ex.state, lang = ex.lang || P.s.lang;
  const code = ex.type === "riordina" ? st.order.map(i => ex.lines[i]).join("\n") : (App.editor ? App.editor.get() : st.code);
  const btn = $("#runBtn"); if (btn) { btn.disabled = true; btn.textContent = ex.check === "review" ? "Qwen sta leggendo il codice…" : ex.check === "spring" ? "Maven compila ed esegue i test (20-60 s)…" : "Eseguo…"; }
  try {
    if (ex.check === "sql") {
      const r = await api("/api/check_sql", {method: "POST", body: {setup: ex.setup, code, verify: ex.verify, expected: ex.expected, ordered: ex.ordered}});
      if (r.ok) return solve(ex, true);
      return fail(ex, sqlFailHtml(ex, r), sqlFailText(ex, r));
    }
    if (ex.check === "spring") {
      const r = await api("/api/run_spring", {method: "POST", body: {code, test: ex.tests_java, runner: ex.runner || ""}});
      if (r.all_ok) return solve(ex, true);
      return fail(ex, resultsHtml(r) + (r.secs ? `<small class="muted">Maven: ${r.secs} s</small>` : ""), resultsText(r));
    }
    if (ex.check === "review") {
      if (ex.type === "riordina") {
        const ok = normOut(code) === normOut(ex.solution);
        if (ok) return solve(ex, true);
        const sol = ex.solution.split("\n");
        const firstBad = code.split("\n").findIndex((l, i) => l !== sol[i]);
        return fail(ex, `<div class="res-err"><b>Ordine non giusto.</b><span>La prima riga fuori posto è la numero ${firstBad + 1}.</span></div>`, `Ordine sbagliato dalla riga ${firstBad + 1}`);
      }
      const r = await api("/api/review_code", {method: "POST", body: {lang, statement: ex.statement, solution: ex.solution, criteria: ex.criteria || [], code}});
      if (r.verdict === "giusto") { ex.explain = (r.comment ? r.comment + " " : "") + (ex.explain || ""); return solve(ex, true); }
      return fail(ex, `<div class="res-err"><b>${r.verdict === "parziale" ? "Quasi" : "Non ancora"}</b><span>${inl(r.comment)}</span>${r.problems.length ? `<ul>${r.problems.map(p => `<li>${inl(p)}</li>`).join("")}</ul>` : ""}<small class="muted">Valutazione del modello: il codice non è stato eseguito.</small></div>`,
        `Valutazione: ${r.verdict}. ${r.comment} ${r.problems.join("; ")}`);
    }
    if (ex.check === "output" || !ex.tests) {
      const r = await api("/api/check_output", {method: "POST", body: {lang, code, output: ex.output}});
      if (r.ok) return solve(ex, true);
      if (r.error) return fail(ex, `<div class="res-err"><b>${/^Tempo/.test(r.error) ? "Tempo scaduto" : "Il codice non si esegue"}</b><pre>${esc(r.error)}</pre></div>`, "Errore: " + r.error);
      return fail(ex, `<span class="eyebrow">L'output non è quello atteso</span>${outputDiff(ex.output, r.stdout)}`, `Output atteso:\n${ex.output}\nOutput ottenuto:\n${r.stdout}`);
    }
    const r = await api("/api/run", {method: "POST", body: {lang, mode: "tests", code, tests: ex.tests}});
    if (r.all_ok) return solve(ex, true);
    fail(ex, resultsHtml(r), resultsText(r));
  } catch (e) { toast(e.message); if (btn) { btn.disabled = false; btn.textContent = "Riprova"; } }
}

async function checkFill(ex) {
  const st = ex.state, vals = $$(".blank").map(i => i.value.trim());
  st.fill = vals;
  if (vals.some(v => !v)) { toast("Riempi tutti gli spazi."); return; }
  const squash = v => { v = String(v).replace(/\s+/g, ""); return ex.check === "sql" ? v.toLowerCase() : v; };
  const exact = vals.every((v, k) => squash(v) === squash(ex.answers[k]));
  if (exact) return solve(ex, true);
  const lang = ex.lang || P.s.lang;
  try {
    if (ex.check === "sql") {
      const filled = ex.code.split("___").reduce((a, p, k) => a + p + (k < vals.length ? vals[k] : ""), "");
      const r = await api("/api/check_sql", {method: "POST", body: {setup: ex.setup, code: filled, verify: ex.verify, expected: ex.expected, ordered: ex.ordered}});
      if (r.ok) return solve(ex, true);
      st.badBlank = vals.map((v, k) => v.replace(/\s+/g, "").toLowerCase() !== String(ex.answers[k]).replace(/\s+/g, "").toLowerCase() ? k : -1).filter(k => k >= 0);
      return fail(ex, sqlFailHtml(ex, r), sqlFailText(ex, r));
    }
    if (ex.check === "review") {
      const filled = ex.code.split("___").reduce((a, p, k) => a + p + (k < vals.length ? vals[k] : ""), "");
      const sol = ex.code.split("___").reduce((a, p, k) => a + p + (k < ex.answers.length ? ex.answers[k] : ""), "");
      const r = await api("/api/review_code", {method: "POST", body: {lang, statement: ex.statement, solution: sol, criteria: ["Le parti inserite devono essere equivalenti a quelle della soluzione"], code: filled}});
      if (r.verdict === "giusto") return solve(ex, true);
      st.badBlank = vals.map((v, k) => v !== ex.answers[k] ? k : -1).filter(k => k >= 0);
      return fail(ex, `<div class="res-err"><b>Non è giusto.</b><span>${inl(r.comment)}</span></div>`, r.comment);
    }
    const r = await api("/api/check_fill", {method: "POST", body: {lang, code: ex.code, answers: vals, output: ex.output}});
    if (r.ok) return solve(ex, true);
    st.badBlank = vals.map((v, k) => v.replace(/\s+/g, "") !== String(ex.answers[k]).replace(/\s+/g, "") ? k : -1).filter(k => k >= 0);
    fail(ex, r.error ? `<div class="res-err"><b>Con queste parole il codice non funziona</b><pre>${esc(r.error)}</pre></div>`
      : `<span class="eyebrow">Il programma stampa qualcosa di diverso</span>${outputDiff(ex.output, r.stdout)}`,
      r.error ? "Errore: " + r.error : `Atteso:\n${ex.output}\nOttenuto:\n${r.stdout}`);
  } catch (e) { toast(e.message); }
}

async function sessionClick(e) {
  const s = P.s; if (!s) return;
  const t = e.target.closest("button"); if (!t) return;
  const ex = s.list[s.i];
  if (t.dataset.act === "next") return nextEx();
  if (!ex) return;
  if (t.dataset.qopt !== undefined) {
    const oi = +t.dataset.qopt;
    if (oi === ex.correct) return solve(ex, true);
    ex.state.wrong.push(oi);
    return fail(ex, `<p class="fb bad"><b>Non è questa.</b> Ripensaci e scegli un'altra risposta.</p>`, `Ha scelto: ${ex.options[oi]}`);
  }
  const act = t.dataset.act;
  if (act === "checkFill") return checkFill(ex);
  if (act === "toggleFree") { ex.state.free = !ex.state.free; renderSession(); const f = $("#freeAns"); if (f) f.focus(); return; }
  if (act === "checkFree") return checkFree(ex);
  if (act === "judgeAns") return judgeOral(ex, t);
  if (act === "saveQ") { const tr = (P.s.key || "").split("/")[1] || ""; return saveQuestion(t, ex.question, tr, ex.model + (ex.points && ex.points.length ? "\n\nPunti chiave: " + ex.points.join("; ") : "")); }
  if (act === "followTutor") { openTutor(); const ti = $("#tutorIn"); ti.value = `Il selezionatore mi chiede: «${ex.followup}». La mia risposta: `; ti.focus(); return; }
  if (act === "followAns") return answerFollow(ex, t);
  if (act === "drill") { t.disabled = true; return openDrill(ex); }
  if (act === "checkGuess") {
    const g = $("#guess").value; ex.state.guess = g;
    if (!g.trim()) { toast("Scrivi cosa pensi che stampi."); return; }
    if (ex.check === "sql") {
      const ord = /order\s+by/i.test(ex.code);
      const mine = sqlLines(g, ex.outCols), real = sqlLines(ex.output);
      const same = ord ? mine.join("\n") === real.join("\n") : [...mine].sort().join("\n") === [...real].sort().join("\n");
      if (same) return solve(ex, true);
      const rs = new Set(real);
      return fail(ex, `<span class="eyebrow">Non ancora</span><div class="cmp-wrap"><table class="cmp"><tr><th>#</th><th>Le tue righe</th></tr>${mine.map((l, i) => `<tr class="${(ord ? l === real[i] : rs.has(l)) ? "" : "bad"}"><td>${i + 1}</td><td>${esc(l)}</td></tr>`).join("")}</table></div>
        <p class="muted" style="margin:0;font-size:13px">${mine.length !== real.length ? `Il risultato ha ${real.length} ${real.length === 1 ? "riga" : "righe"}, tu ne hai scritte ${mine.length}.` : "Il numero di righe è giusto: ricontrolla quelle evidenziate."}</p>`, `Ha previsto:\n${g}`);
    }
    if (normOut(g) === normOut(ex.output)) return solve(ex, true);
    const a = normOut(g).split("\n"), b = normOut(ex.output).split("\n");
    return fail(ex, `<span class="eyebrow">Non ancora</span><div class="cmp-wrap"><table class="cmp"><tr><th>#</th><th>Il tuo output</th></tr>${a.map((l, i) => `<tr class="${l === b[i] ? "" : "bad"}"><td>${i + 1}</td><td>${esc(l) || "<span class='muted'>(vuota)</span>"}</td></tr>`).join("")}</table></div>
      <p class="muted" style="margin:0;font-size:13px">${a.length !== b.length ? `Il programma stampa ${b.length} ${b.length === 1 ? "riga" : "righe"}, tu ne hai scritte ${a.length}.` : "Il numero di righe è giusto: ricontrolla le righe evidenziate."}</p>`, `Ha previsto:\n${g}`);
  }
  if (act === "run") { if (App.editor) ex.state.code = App.editor.get(); return runCode(ex); }
  if (act === "hint") { if (App.editor) ex.state.code = App.editor.get(); ex.state.hints++; return renderSession(); }
  if (act === "explain") { Tutor.ask("Perché la mia risposta non va? Spiegami l'errore e dammi un indizio, senza darmi la soluzione."); return; }
  if (act === "reveal") {
    if (!t.dataset.armed) { t.dataset.armed = "1"; t.textContent = "Sicuro? Conta come errore"; setTimeout(() => { if (t.isConnected) { delete t.dataset.armed; t.textContent = "Mostra la soluzione"; } }, 3500); return; }
    if (App.editor) ex.state.code = App.editor.get();
    return solve(ex, false);
  }
  if (act === "flag") {
    api("/api/flag", {method: "POST", body: {key: ex.key || s.key, id: ex.id}}).catch(() => {});
    s.results.splice(s.i, 1);
    s.list.splice(s.i, 1);
    toast("Esercizio segnalato e rimosso.");
    if (!s.review) { pollMore(true); }
    else s.size = Math.max(s.results.length, s.list.length);
    if (s.i >= s.size) return finishSession();
    return renderSession();
  }
  if (t.dataset.mv) {
    const pos = +t.dataset.pos, to = pos + +t.dataset.mv, o = ex.state.order;
    if (to < 0 || to >= o.length) return;
    [o[pos], o[to]] = [o[to], o[pos]];
    renderSession();
    const b = $(`#parsons [data-pos="${to}"][data-mv="${t.dataset.mv}"]`); if (b) b.focus();
  }
}
document.addEventListener("keydown", e => {
  if (App.view !== "session" || !P.s) return;
  const ex = P.s.list[P.s.i];
  if (e.key === "Enter" && e.target.classList && e.target.classList.contains("blank")) { e.preventDefault(); if (ex) checkFill(ex); }
  else if (e.key === "Enter" && e.target.id === "freeAns") { e.preventDefault(); if (ex) checkFree(ex); }
  else if (e.key === "Enter" && e.target.id === "guess" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); $("[data-act=checkGuess]") && $("[data-act=checkGuess]").click(); }
});

function nextEx() {
  const s = P.s;
  s.i++;
  if (s.i >= s.size) return finishSession();
  renderSession();
  $("#view").scrollTop = 0;
}

async function pollMore(once) {
  const s = P.s; if (!s || s.review || s.done) return;
  const have = s.list.map(e => e.id);
  if (s.list.length >= s.size && !once) return;
  try {
    const r = await api("/api/session/more", {method: "POST", body: {key: s.key, have, types: s.types}});
    if (P.s !== s) return;
    if (r.exercise && !s.list.find(e => e.id === r.exercise.id)) {
      s.list.push(prepEx(r.exercise));
      if (s.waitT0 && s.i === s.list.length - 1) { LOG.ev("wait", {what: "esercizio del percorso", secs: secsSince(s.waitT0), key: s.key}); s.waitT0 = null; }
      if (s.i === s.list.length - 1) return renderSession();
    }
    const job = $("#waitJob");
    if (job && r.worker && r.worker.job) job.textContent = `Qwen sta preparando: ${r.worker.job}. Ricalco lo esegue per verificarlo prima di mostrartelo.`;
    if (job && !r.model) job.textContent = "Ollama non risponde: accendilo per generare altri esercizi.";
  } catch (e) { /* riprova al prossimo giro */ }
  if (s.list.length < s.size && !s.done) s.poll = setTimeout(() => pollMore(), 3000);
}

async function finishSession() {
  const s = P.s;
  s.done = true;
  clearTimeout(s.poll);
  const total = s.results.length, first = s.results.filter(r => r.result === "first").length;
  s.summary = {total, first};
  if (!s.review && total) {
    try { s.level = await api("/api/level_done", {method: "POST", body: {key: s.key, first, total}}); } catch (e) { toast(e.message); }
  }
  renderSummary();
}

function renderSummary() {
  const s = P.s, L = s.level || {}, sum = s.summary;
  const nextHref = L.next && L.nextUnlocked ? `#/s/${L.next}` : null;
  const [nl, nu, nv] = L.next ? L.next.split("/") : [];
  const nextUnit = App.C && nu ? App.C.units.find(u => u.id === nu) : null;
  $("#sessBody").innerHTML = `<div class="summary-card">
    <p class="eyebrow">${esc(s.label)}</p>
    <h1>${s.review ? "Errori ripassati" : s.kind !== "path" ? (s.live ? "Live coding concluso" : "Sessione completata") : L.stars ? "Livello superato" : "Quasi: ripeti il livello"}</h1>
    ${s.review ? "" : `<div class="big-stars">${stars(L.stars || 0)}</div>`}
    <div class="sum">
      <div class="stat"><b>${sum.first}/${sum.total}</b><span>Giusti al primo colpo</span></div>
      <div class="stat"><b>+${s.gained + (L.bonus || 0)}</b><span>XP guadagnati</span></div>
      <div class="stat"><b>${s.results.filter(r => r.result === "miss").length}</b><span>Da ripassare</span></div>
    </div>
    <p class="explain">${s.review ? "Gli esercizi risolti al primo colpo escono dalla lista degli errori."
      : s.kind !== "path" ? "Le prossime sessioni avranno sempre esercizi nuovi: Qwen li prepara mentre ti alleni." + (s.kind === "logic" && !s.live ? " I problemi fatti sono finiti nel mazzo di flashcard «Logica»." : s.kind === "interview" ? " Le domande sono finite nelle flashcard del colloquio." : "")
      : L.stars ? (L.newlyUnlocked && nextUnit ? `Hai sbloccato: <b>${esc(nextUnit.title)} · ${LEVEL_NAMES[nv]}</b>.` : "Puoi ripeterlo per prendere più stelle: gli esercizi saranno nuovi.")
      : "Per superarlo servono almeno metà degli esercizi giusti al primo colpo. Gli esercizi della prossima volta saranno nuovi."}</p>
    <div class="row">
      ${nextHref && s.kind === "path" ? `<a class="btn primary" href="${nextHref}">Prossimo livello</a>` : ""}
      ${s.review ? "" : `<button class="btn ${nextHref && s.kind === "path" ? "" : "primary"}" data-act="again">${s.kind === "path" ? "Ripeti con esercizi nuovi" : s.live ? "Altri problemi" : "Altri " + s.size + " esercizi"}</button>`}
      <a class="btn" href="${s.exitHref}">${s.kind === "path" ? "Torna al percorso" : "Indietro"}</a>
    </div></div>`;
  const again = $("[data-act=again]");
  if (again) again.onclick = () => startSession(s.key, false, {live: s.live});
  Tutor.setContext(sessCtx(null) + `Ha finito la sessione: ${sum.first}/${sum.total} al primo colpo.`, "Sessione completata");
  Tutor.setQuick(["Su cosa dovrei esercitarmi di più?"]);
}

/* ================================================================ logica, colloquio orale, live coding */
function simple(x) {
  x = String(x ?? "").trim().replace(/^[`"']+|[`"']+$/g, "").toLowerCase().replace(/\.$/, "").replace(/\s+/g, " ");
  const m = x.match(/^(-?\d+)[.,](\d+)(.*)$/);
  if (m) { const dec = m[2].replace(/0+$/, ""); x = m[1] + (dec ? "," + dec : "") + m[3]; }
  return x;
}
function checkFree(ex) {
  const v = ($("#freeAns") || {}).value || "";
  ex.state.freeVal = v;
  if (!v.trim()) { toast("Scrivi la tua risposta."); return; }
  const a = simple(v), b = simple(ex.answer);
  const num = s => s.replace(/[^\d,.-]/g, "");
  if (a === b || (num(a) && num(a) === num(b) && /\d/.test(b))) return solve(ex, true);
  fail(ex, `<p class="fb bad"><b>Non è questa.</b> Ricontrolla il ragionamento, oppure guarda le opzioni.</p>`, `Ha risposto: ${v}`);
}
function judgeHtml(j) {
  return `<div class="judge ${j.score >= 4 ? "good" : j.score >= 3 ? "mid" : "bad"}">
    <div class="row"><b>Voto ${j.score}/5</b><span class="dots">${[1, 2, 3, 4, 5].map(i => `<i class="${i <= j.score ? "on" : ""}"></i>`).join("")}</span></div>
    ${j.comment ? `<p class="explain">${inl(j.comment)}</p>` : ""}
    ${j.covered.length ? `<ul class="ck">${j.covered.map(x => `<li class="y">${inl(x)}</li>`).join("")}</ul>` : ""}
    ${j.missing.length ? `<ul class="ck">${j.missing.map(x => `<li class="n">${inl(x)}</li>`).join("")}</ul>` : ""}
    ${j.language ? `<div class="lang-box"><span class="eyebrow">Il tuo inglese</span><p class="explain">${inl(j.language)}</p></div>` : ""}
    <small class="muted">Valutazione del modello.</small></div>`;
}
async function judgeOral(ex, btn) {
  const v = $("#oralAns").value.trim();
  ex.state.answer = v;
  if (v.length < 15) { toast("Scrivi una risposta un po' più completa."); return; }
  btn.disabled = true; btn.textContent = "Il selezionatore sta leggendo…";
  try {
    const j = await api("/api/judge_answer", {method: "POST", body: {question: ex.question, points: ex.points, model: ex.model, answer: v, en: P.s.en}});
    ex.state.judge = j;
    if (j.score >= 3) return solve(ex, true);
    fail(ex, "", `Voto ${j.score}/5. Mancava: ${j.missing.join("; ")}`);
  } catch (e) { toast(e.message); btn.disabled = false; btn.textContent = "Valuta la risposta"; }
}

const LIVE_MIN = {base: 20, pratica: 25, sfida: 35};
function liveTick(ex) {
  clearInterval(App.liveInt);
  const st = ex.state;
  st.t0 = st.t0 || Date.now();
  const lim = (LIVE_MIN[P.s.lvl] || 25) * 60;
  const draw = () => {
    const el = $("#liveTimer"); if (!el) return clearInterval(App.liveInt);
    const sec = Math.round(((st.tEnd || Date.now()) - st.t0) / 1000);
    el.textContent = `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, "0")} / ${lim / 60}:00`;
    el.classList.toggle("over", sec > lim);
  };
  draw();
  if (!st.tEnd) App.liveInt = setInterval(draw, 1000);
}
function liveFollowHtml(ex) {
  const st = ex.state, f = st.follow;
  st.tEnd = st.tEnd || Date.now();
  if (!f) { setTimeout(() => loadFollow(ex), 0); return `<div class="follow" id="followBox"><span class="eyebrow">Il selezionatore ha una domanda</span><p class="muted"><span class="spin small"></span> Sta leggendo il tuo codice…</p></div>`; }
  if (f.error) return `<div class="follow"><p class="muted">${esc(f.error)}</p></div>`;
  return `<div class="follow" id="followBox"><span class="eyebrow">Il selezionatore chiede</span><p class="explain"><b>${inl(f.question)}</b></p>
    ${f.res ? `<p class="explain">${esc(f.ans)}</p>${judgeHtml(f.res)}<details><summary class="muted" style="cursor:pointer">Risposta modello</summary><p class="explain">${inl(f.model)}</p></details>`
      : `<textarea class="open-ans" id="followAns" placeholder="Rispondi come al colloquio">${esc(f.ans || "")}</textarea><div class="row"><button class="btn" data-act="followAns">Rispondi</button></div>`}</div>`;
}
async function loadFollow(ex) {
  if (ex.state.followLoading) return;
  ex.state.followLoading = true;
  const code = App.editor ? App.editor.get() : ex.state.code;
  try { ex.state.follow = await api("/api/followup", {method: "POST", body: {lang: P.s.lang, statement: ex.statement, code, en: App.intLang === "en"}}); }
  catch (e) { ex.state.follow = {error: e.message}; }
  if (P.s && P.s.list[P.s.i] === ex) renderSession();
}
async function answerFollow(ex, btn) {
  const f = ex.state.follow, v = $("#followAns").value.trim();
  f.ans = v;
  if (v.length < 10) { toast("Scrivi la tua risposta."); return; }
  btn.disabled = true; btn.textContent = "Valuto…";
  try { f.res = await api("/api/judge_answer", {method: "POST", body: {question: f.question, points: f.points, model: f.model, answer: v, en: App.intLang === "en"}}); }
  catch (e) { toast(e.message); }
  renderSession();
}

/* ---- vista Logica */
async function showLogic() {
  App.view = "logic"; mainNav("logica");
  const v = $("#view");
  v.innerHTML = `<section class="path"><header class="path-head"><div><p class="eyebrow">Allenamento</p><h1>Logica e problem solving</h1>
    <p class="goal muted">Esercizi senza limite per ogni livello. Ogni rompicapo viene risolto anche da un programma: se il programma non conferma la risposta, il problema viene scartato.</p></div></header>
    <div id="logicBody"><div class="empty">Caricamento…</div></div></section>`;
  Tutor.setContext("Lo studente sta scegliendo un allenamento di logica e problem solving.", "Logica");
  Tutor.setQuick(["Come miglioro nel problem solving?", "Quali tecniche servono per i colloqui?"]);
  const d = await api("/api/logic");
  const w = d.worker || {};
  $("#logicBody").innerHTML = `<div class="cat-grid">${d.cats.map(c => `<article class="cat">
      <div class="u-title"><h3>${esc(c.title)}</h3>${c.code ? `<span class="tag acc">${LANG[c.lang]}</span>` : ""}</div>
      <p class="u-concepts">${esc(c.desc)}</p>
      <div class="u-levels">${c.levels.map(l => `<a class="lvl ${l.stars ? "done" : ""}" href="#/s/${l.key}"><b>${l.name}</b>${stars(l.stars)}<small>${l.done} fatti · ${l.ready ? l.ready + " pronti" : "in preparazione"}</small></a>`).join("")}</div>
    </article>`).join("")}</div>
    <p class="worker muted">${w.job ? `<span class="spin small"></span> In sottofondo Qwen prepara: ${esc(w.job)}` : "Apri un livello: Qwen inizia subito a preparare gli esercizi successivi."}</p>`;
}

/* ---- vista Colloquio */
async function showInterview() {
  App.view = "interview"; mainNav("colloquio");
  const v = $("#view");
  v.innerHTML = `<section class="path"><header class="path-head"><div><p class="eyebrow">Preparazione</p><h1>Colloquio tecnico</h1>
    <p class="goal muted">Tre modi per allenarti: domande a cui rispondere per scritto, live coding con il timer, e una simulazione completa con valutazione finale.</p></div></header>
    <div id="intBody"><div class="empty">Caricamento…</div></div></section>`;
  Tutor.setContext("Lo studente si prepara a un colloquio tecnico per una posizione junior.", "Colloquio tecnico");
  Tutor.setQuick(["Come si prepara un colloquio junior?", "Come rispondo quando non so una cosa?", "Come spiego un mio progetto?"]);
  const d = await api("/api/interview");
  App.intLang = App.intLang || localStorage.getItem("ricalco.intlang") || "it";
  const en = App.intLang === "en";
  const saved = simLoad();
  $("#intBody").innerHTML = (saved ? `<div class="banner"><b>Hai una simulazione in corso: ${esc(saved.title)} · ${esc(saved.levelName)}.</b><span>${saved.history.filter(m => m.role === "user").length} risposte date. Riprendila da dove eri rimasto.</span><div class="row"><a class="btn small primary" href="#/sim/${saved.track}/${saved.level}">Riprendi</a><button class="btn small ghost" id="simDrop">Lasciala perdere</button></div></div>` : "") +
    `<div class="row"><span class="muted">Lingua del colloquio</span><div class="seg" role="group" aria-label="Lingua del colloquio">
      <button type="button" data-il="it" aria-pressed="${!en}">Italiano</button><button type="button" data-il="en" aria-pressed="${en}">English</button></div>
      ${en ? `<span class="muted" style="font-size:13px">Domande e selezionatore in inglese. Dopo ogni risposta ti correggo l'inglese, senza togliere punti.</span>` : ""}</div>` +
    d.tracks.filter(t => !!t.en === en).map(t => `<article class="track">
      <div class="u-title"><h3>${esc(t.title)}</h3><span class="tag acc">${LANG[t.lang]}</span></div>
      <div class="modes">
        <div class="mode"><b>Domande</b><small>Rispondi per scritto: voto, punti mancati, risposta modello.</small>
          <div class="u-levels">${t.levels.map(l => `<a class="lvl ${l.stars ? "done" : ""}" href="#/s/${l.key}"><b>${l.name}</b>${stars(l.stars)}<small>${l.done} fatte</small></a>`).join("")}</div></div>
        <div class="mode"><b>Live coding</b><small>3 problemi con il timer, test veri, poi la domanda sul tuo codice.</small>
          <div class="u-levels">${t.live.map(l => `<a class="lvl" href="#/live/${l.key}"><b>${d.levelNames[l.id]}</b><small>${l.ready} pronti</small></a>`).join("")}</div></div>
        <div class="mode"><b>Simulazione</b><small>Colloquio in chat, una domanda alla volta, con scheda di valutazione finale.</small>
          <div class="u-levels">${Object.entries(d.levelNames).map(([k, n]) => `<a class="lvl" href="#/sim/${t.id}/${k}"><b>${n}</b><small>circa 8 domande</small></a>`).join("")}</div></div>
      </div></article>`).join("") +
    `<div class="row"><a class="btn small" href="#/carte/colloquio-salvate">Domande salvate</a><a class="btn small ghost" href="#/carte/punti-deboli">Punti da migliorare</a></div>` +
    (d.reports.length ? `<div><h2 class="section-title">Simulazioni fatte</h2><div class="reports">${d.reports.map(r => `<a class="lvl" href="#/report/${r.id}"><b>${esc(r.track)} · ${esc(r.level)}</b><small>${esc(r.date)} · voto ${r.score ?? "—"}/10</small></a>`).join("")}</div></div>` : "");
}

/* ---- simulazione: resta salvata se cambi pagina, e chiede di non cambiare scheda del browser */
function simLoad() { try { const s = JSON.parse(localStorage.getItem("ricalco.sim") || "null"); return s && s.history && s.history.some(m => m.role === "user") ? s : null; } catch (e) { return null; } }
function simSave() { const S = App.sim; if (!S) return; try { localStorage.setItem("ricalco.sim", JSON.stringify({track: S.track, level: S.level, title: S.title, levelName: S.levelName, history: S.history.filter(m => m.content), leaves: S.leaves || 0})); } catch (e) { /* niente */ } }
function simClear() { try { localStorage.removeItem("ricalco.sim"); } catch (e) { /* niente */ } }
document.addEventListener("visibilitychange", () => {
  const S = App.sim;
  if (!document.hidden || App.view !== "sim" || !S || S.ended) return;
  S.leaves = (S.leaves || 0) + 1; simSave();
  LOG.ev("sim_leave", {track: S.track, n: S.leaves});
  const w = $("#simWarn");
  if (w) w.innerHTML = `<div class="banner"><b>Hai cambiato scheda (${S.leaves} ${S.leaves === 1 ? "volta" : "volte"}).</b><span>In un colloquio vero non puoi cercare le risposte: resta qui. Lo segno nella valutazione.</span></div>`;
});
window.addEventListener("beforeunload", e => {
  if (App.view === "sim" && App.sim && !App.sim.ended && App.sim.history.some(m => m.role === "user")) { simSave(); e.preventDefault(); e.returnValue = ""; }
});
document.addEventListener("click", e => {
  const b = e.target.closest("#simDrop"); if (!b) return;
  simClear(); showInterview();
});
document.addEventListener("click", e => {
  const b = e.target.closest("[data-il]"); if (!b || App.view !== "interview") return;
  App.intLang = b.dataset.il; localStorage.setItem("ricalco.intlang", App.intLang); showInterview();
});
async function showSim(track, level) {
  App.view = "sim"; mainNav("colloquio");
  const d = App.intData || (App.intData = await api("/api/interview"));
  const t = d.tracks.find(x => x.id === track);
  const saved = simLoad();
  const resume = saved && saved.track === track && saved.level === level;
  App.sim = resume ? Object.assign(saved, {busy: false}) : {track, level, history: [], busy: false, leaves: 0, title: t ? t.title : track, levelName: d.levelNames[level]};
  $("#view").innerHTML = `<section class="sim"><div class="sim-head"><div><p class="eyebrow">Simulazione di colloquio</p><h1>${esc(App.sim.title)} · ${esc(App.sim.levelName)}</h1></div>
      <div class="row"><span class="muted" id="simCount"></span><button class="btn" id="simEnd">Termina e valuta</button></div></div>
    <div id="simWarn">${resume ? `<p class="muted" style="margin:0">Simulazione ripresa da dove eri rimasto.</p>` : ""}</div>
    <div class="sim-chat" id="simChat"></div>
    <form class="sim-form" id="simForm"><textarea id="simIn" rows="3" placeholder="${/_en$/.test(track) ? "Answer as you would in a real interview. Enter to send, Shift+Enter for a new line." : "Rispondi come faresti dal vivo. Invio per inviare, Maiusc+Invio per andare a capo."}"></textarea>
      <button class="btn primary" id="simSend">Rispondi</button></form>
    <p class="muted" style="font-size:12.5px;margin:0">Il selezionatore è il tuo modello locale. Scrivi FINE per chiudere prima. La valutazione si basa solo su quello che rispondi.</p></section>`;
  Tutor.setContext(`Lo studente sta facendo una simulazione di colloquio (${App.sim.title}). Non dargli le risposte alle domande del selezionatore.`, "Simulazione di colloquio");
  Tutor.setQuick([]);
  $("#simForm").onsubmit = e => { e.preventDefault(); simSend(); };
  $("#simIn").onkeydown = e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); simSend(); } };
  $("#simEnd").onclick = simEnd;
  $("#simIn").addEventListener("paste", e => { e.preventDefault(); toast("Al colloquio non si incolla: rispondi con parole tue."); });
  $("#simChat").onclick = e => { const b = e.target.closest("[data-saveq]"); if (b) saveQuestion(b, App.sim.history[+b.dataset.saveq].content, App.sim.track); };
  if (resume && App.sim.history.length && App.sim.history[App.sim.history.length - 1].role === "assistant") { simRender(); $("#simIn").focus(); }
  else simTurn();
}
async function saveQuestion(btn, question, track, model) {
  btn.disabled = true; btn.textContent = model ? "Salvo…" : "Qwen scrive la risposta modello…";
  try { const r = await api("/api/interview/save_question", {method: "POST", body: {question, track, model: model || ""}}); btn.textContent = r.added ? "Salvata ✓" : "Già salvata"; }
  catch (e) { toast(e.message); btn.disabled = false; btn.textContent = "Salva la domanda"; }
}
function simRender() {
  const S = App.sim, box = $("#simChat"); if (!box) return;
  box.innerHTML = S.history.map((m, i) => `<div class="msg ${m.role === "user" ? "user" : "bot"}">${m.role === "user" ? esc(m.content) : (m.content ? md(m.content) : `<span class="think">Il selezionatore sta scrivendo…</span>`)}${m.role !== "user" && m.content && !(S.busy && i === S.history.length - 1) ? `<button class="linkish msg-save" data-saveq="${i}">Salva la domanda</button>` : ""}</div>`).join("");
  box.scrollTop = box.scrollHeight;
  $("#simCount").textContent = `Risposte date: ${S.history.filter(m => m.role === "user").length}`;
}
async function simTurn() {
  const S = App.sim;
  S.busy = true; $("#simSend").disabled = true;
  const bot = {role: "assistant", content: ""};
  const hist = S.history.slice();
  S.history.push(bot); simRender();
  try {
    const r = await fetch("/api/interview/turn", {method: "POST", headers: {"X-Ricalco": "1", "Content-Type": "application/json"}, body: JSON.stringify({track: S.track, level: S.level, history: hist})});
    if (!r.ok) { const d = await r.json().catch(() => ({})); throw new Error(d.error || "Errore"); }
    const rd = r.body.getReader(), dec = new TextDecoder();
    for (;;) { const {done, value} = await rd.read(); if (done) break; bot.content += dec.decode(value, {stream: true}); if (App.sim === S) simRender(); }
  } catch (e) { bot.content = e.message; }
  S.busy = false; simSave();
  if (App.sim === S) { $("#simSend").disabled = false; simRender(); $("#simIn").focus(); }
}
function simSend() {
  const S = App.sim, v = $("#simIn").value.trim();
  if (!v || S.busy) return;
  $("#simIn").value = "";
  S.history.push({role: "user", content: v});
  if (/^(fine|end)\.?$/i.test(v)) { simRender(); return simEnd(); }
  simTurn();
}
async function simEnd() {
  const S = App.sim;
  if (!S.history.some(m => m.role === "user")) { toast("Rispondi ad almeno una domanda."); return; }
  const b = $("#simEnd"); b.disabled = true; b.textContent = "Scrivo la valutazione…";
  try {
    const rec = await api("/api/interview/report", {method: "POST", body: {track: S.track, level: S.level, history: S.history.filter(m => m.content), leaves: S.leaves || 0}});
    S.ended = true; simClear();
    App.intData = null;
    location.hash = `#/report/${rec.id}`;
  } catch (e) { toast(e.message); b.disabled = false; b.textContent = "Termina e valuta"; }
}
async function showReport(id) {
  App.view = "report"; mainNav("colloquio");
  const r = await api(`/api/interviews/${id}`), R = r.report || {};
  $("#view").innerHTML = `<section class="theory"><p class="eyebrow">Valutazione · ${esc(r.trackTitle)} · ${esc(r.levelName)} · ${esc(r.date)}</p>
    <h1>${R.voto ?? "—"}/10</h1><p class="explain"><b>${esc(R.esito || "")}</b></p>
    <div class="areas">${(R.aree || []).map(a => `<div class="area"><div class="row"><b>${esc(a.area)}</b><span class="spacer"></span><span>${a.voto}/10</span></div>
      <div class="bar"><i style="width:${Math.max(0, Math.min(10, a.voto)) * 10}%"></i></div><p class="muted">${inl(a.commento)}</p></div>`).join("")}</div>
    <div class="th-box"><span class="eyebrow">Punti forti</span><ul>${(R.punti_forti || []).map(x => `<li>${inl(x)}</li>`).join("")}</ul></div>
    ${r.leaves ? `<p class="explain"><b>Durante il colloquio hai cambiato scheda ${r.leaves} ${r.leaves === 1 ? "volta" : "volte"}.</b> In un colloquio vero non si può: la prossima volta resta sulla simulazione.</p>` : ""}
    <div class="th-box warnbox"><span class="eyebrow">Da migliorare</span><ul class="drill">${(R.da_migliorare || []).map((x, i) => `<li>${inl(x)} <button class="btn small" data-drill="${i}">Allenati su questo</button></li>`).join("")}</ul></div>
    <div class="th-box"><span class="eyebrow">Prossimi passi</span><ul>${(R.prossimi_passi || []).map(x => `<li>${inl(x)}</li>`).join("")}</ul></div>
    <details><summary class="muted" style="cursor:pointer">Trascrizione · salva le domande da rivedere</summary><div class="sim-chat static" id="repChat">${r.history.map((m, i) => `<div class="msg ${m.role === "user" ? "user" : "bot"}">${m.role === "user" ? esc(m.content) : md(m.content) + `<button class="linkish msg-save" data-saveq="${i}">Salva la domanda</button>`}</div>`).join("")}</div></details>
    <div class="row"><a class="btn primary" href="#/sim/${r.track}/${r.level}">Nuova simulazione</a><a class="btn" href="#/colloquio">Torna al colloquio</a></div></section>`;
  $("#view").onclick = async e => {
    if (App.view !== "report") return;
    const s = e.target.closest("[data-saveq]"); if (s) return saveQuestion(s, r.history[+s.dataset.saveq].content, r.track);
    const d = e.target.closest("[data-drill]"); if (!d) return;
    d.disabled = true; d.textContent = "Qwen prepara le domande…";
    try {
      const x = await api("/api/interview/drill", {method: "POST", body: {point: (R.da_migliorare || [])[+d.dataset.drill], track: r.track}});
      LOG.ev("interview_drill", {track: r.track, added: x.added});
      location.hash = "#/carte/punti-deboli";
    } catch (err) { toast(err.message); d.disabled = false; d.textContent = "Allenati su questo"; }
  };
  Tutor.setContext(`Valutazione di una simulazione di colloquio (${r.trackTitle}): voto ${R.voto}/10. Da migliorare: ${(R.da_migliorare || []).join("; ")}. Prossimi passi: ${(R.prossimi_passi || []).join("; ")}`, "Valutazione del colloquio");
  Tutor.setQuick(["Fammi un piano di studio di una settimana", "Rifammi la domanda su cui sono andato peggio"]);
}

/* ---- flashcard */
async function showCards() {
  App.view = "cards"; mainNav("carte");
  const d = await api("/api/cards");
  const due = d.decks.reduce((a, x) => a + x.due, 0);
  $("#view").innerHTML = `<section class="path"><header class="path-head"><div><p class="eyebrow">Ripasso</p><h1>Flashcard</h1>
      <p class="goal muted">Ripetizione dilazionata: le carte che sai tornano dopo giorni, quelle che sbagli tornano subito. Le carte di logica e colloquio si aggiungono da sole quando fai gli esercizi.</p></div>
      ${due ? `<a class="btn primary" href="#/carte/tutte">Ripassa tutto (${due})</a>` : ""}</header>
    ${d.decks.length ? `<div class="cat-grid">${d.decks.map(k => `<article class="cat"><div class="u-title"><h3>${esc(k.title)}</h3></div>
        <p class="u-concepts">${k.total} carte · ${k.learned} imparate · <b>${k.due}</b> da ripassare oggi</p>
        <div class="row">${k.due ? `<a class="btn primary small" href="#/carte/${encodeURIComponent(k.id)}">Studia (${k.due})</a>` : `<span class="tag ok">In pari</span>`}
          <button class="btn small ghost" data-gen="${esc(k.id)}">Aggiungi 10 carte</button></div></article>`).join("")}</div>`
      : `<div class="empty">Nessuna carta ancora. Fai qualche esercizio di logica o di colloquio, oppure genera un mazzo qui sotto.</div>`}
    <div class="gen-cards"><h2 class="section-title">Crea un mazzo</h2>
      <div class="row"><select id="genDeck">${d.generators.map(g => `<option value="${esc(g.id)}">${esc(g.title)}</option>`).join("")}</select>
      <button class="btn" id="genGo">Genera 10 carte</button><span class="muted" id="genMsg" style="font-size:13px"></span></div></div></section>`;
  Tutor.setContext("Lo studente gestisce i suoi mazzi di flashcard.", "Flashcard");
  Tutor.setQuick(["Come funziona la ripetizione dilazionata?"]);
  const gen = async deck => {
    $("#genMsg").innerHTML = `<span class="spin small"></span> Qwen scrive le carte…`;
    try { const r = await api("/api/cards/generate", {method: "POST", body: {deck}}); toast(`${r.added} carte aggiunte.`); showCards(); }
    catch (e) { $("#genMsg").textContent = e.message; }
  };
  $("#genGo").onclick = () => gen($("#genDeck").value);
  $("#view").onclick = e => { const b = e.target.closest("[data-gen]"); if (b) { b.disabled = true; gen(b.dataset.gen); } };
}
async function studyDeck(deck) {
  App.view = "study"; mainNav("carte");
  const d = await api("/api/cards/study", {method: "POST", body: {deck}});
  App.study = {deck, queue: d.cards, done: 0, again: 0, flipped: false};
  renderCard();
}
function studyHost() { return App.studyHome ? $("#quick") : $("#view"); }
function studyExit() { return App.studyHome ? `<button class="btn small ghost" data-q="endReview">Basta ripasso</button>` : `<a class="btn small ghost" href="#/carte">Esci</a>`; }
function renderCard() {
  const S = App.study, c = S.queue[0], v = studyHost();
  if (App.studyHome && !c) return endHomeReview();
  if (c && c.kind === "quick") return renderQuickCard(c);
  if (!c) {
    v.innerHTML = `<section class="theory"><h1>Fatto per oggi</h1><p class="explain">Hai ripassato ${S.done} carte${S.again ? `, ${S.again} da rivedere presto` : ""}. Le prossime torneranno quando sarà il momento giusto per ricordarle.</p>
      <div class="row"><a class="btn primary" href="#/carte">Torna ai mazzi</a></div></section>`;
    return;
  }
  if (c.kind === "rewrite") return renderRewriteCard(c);
  v.innerHTML = `<section class="study"><div class="sess-head">${studyExit()}<span class="muted">${esc(c.deckTitle)}</span><span class="spacer"></span><span class="sess-xp">${S.done} fatte · ${S.queue.length} rimaste</span></div>
    <div class="fc-stack"><article class="card fc ${S.flipped ? "flipped" : ""}"><span class="fc-side">${S.flipped ? "Retro" : "Fronte"} · carta ${S.done + 1} di ${S.done + S.queue.length}</span><div class="card-front askable">${md(c.front)}</div>
      ${S.flipped ? `<div class="card-back askable fc-in">${md(c.back)}</div>${S.ans ? `<div class="fc-you"><span class="eyebrow">La tua risposta</span><p class="explain">${esc(S.ans)}</p><div id="fcJudge">${S.judge ? judgeHtml(S.judge) : `<p class="muted"><span class="spin small"></span> Qwen confronta la tua risposta…</p>`}</div></div>` : ""}`
        : `<textarea class="open-ans fc-ans" id="cardAns" placeholder="Prima di girarla, spiegalo a parole tue (facoltativo). Ctrl+Invio per girare.">${esc(S.draft || "")}</textarea>`}</article></div>
    ${S.flipped ? `<div class="row grade"><button class="btn" data-g="0">Non lo sapevo <kbd>1</kbd></button><button class="btn" data-g="1">Difficile <kbd>2</kbd></button><button class="btn primary" data-g="2">Facile <kbd>3</kbd></button>
      <span class="spacer"></span><button class="linkish" data-del="${c.id}">Elimina carta</button></div>`
      : `<div class="row"><button class="btn primary" id="flip">Mostra la risposta <kbd>Spazio</kbd></button></div>`}</section>`;
  Tutor.setContext(`Flashcard. Fronte: ${c.front}` + (S.flipped ? `\nRetro: ${c.back}` : "\nLo studente non ha ancora visto la risposta: non dirgliela."), "Flashcard");
  Tutor.setQuick(S.flipped ? ["Spiegamelo meglio", "Fammi un esempio"] : ["Dammi un indizio"]);
  v.onclick = e => {
    const t = e.target.closest("button"); if (!t) return;
    if (t.id === "flip") flipCard();
    else if (t.dataset.g) gradeCard(+t.dataset.g);
    else if (t.dataset.del) { api("/api/cards/delete", {method: "POST", body: {id: t.dataset.del}}); S.queue.shift(); S.flipped = false; renderCard(); }
  };
}
function renderRewriteCard(c) {
  const S = App.study, v = studyHost();
  v.onclick = null;
  const [head, ...rest] = c.front.split("\n\n");
  v.innerHTML = `<section class="study"><div class="sess-head">${studyExit()}<span class="muted">Riscrivi a memoria · ${esc(head)}</span><span class="spacer"></span><span class="sess-xp">${S.done} fatte · ${S.queue.length} rimaste</span></div>
    <article class="card rw"><div class="card-front"><span class="eyebrow">Cosa deve fare</span>${md(rest.join("\n\n"))}</div>
      ${sheetHtml("Clicca sul foglio e riscrivi il blocco a memoria")}
      <div id="rwRes"></div></article>
    <div class="row" id="rwActs"><button class="btn ghost" id="rwShow">Non me lo ricordo: mostramelo</button><span class="muted" style="font-size:12.5px">Tre errori sullo stesso punto mostrano la parola.</span></div></section>`;
  Tutor.setContext(`Ripasso: lo studente deve riscrivere a memoria un blocco di codice. Descrizione: ${rest.join(" ")}. Non scrivergli il codice.`, "Ripasso a memoria");
  Tutor.setQuick(["Dammi un indizio senza il codice"]);
  let shown = false;
  const {tr} = rewriteTracer($(".card.rw"), c.lang || "python", c.back, st => {
    const tot = st.typed + st.errors, acc = tot ? Math.round(st.typed / tot * 100) : 100;
    const g = shown ? 0 : st.errors <= 1 && !st.hints ? 2 : acc >= 85 ? 1 : 0;
    S.rwGrade = g;
    $("#rwRes").innerHTML = `<p class="explain"><b>${g === 2 ? "Perfetto." : g === 1 ? "Ci sei quasi." : "Da rivedere."}</b> Precisione ${acc}%, ${st.errors} errori, ${st.hints} aiuti.
      ${g === 2 ? "Tornerà tra qualche giorno." : g === 1 ? "Tornerà presto." : "Lo rivedi tra poco, in questa stessa sessione."}</p>`;
    $("#rwActs").innerHTML = `<button class="btn primary" id="rwNext">Avanti <kbd>Invio</kbd></button>`;
    $("#rwNext").onclick = () => gradeCard(g);
    $("#rwNext").focus();
  });
  $("#rwShow").onclick = () => { shown = true; tr.setLevel(1); tr.focus(); $("#rwShow").disabled = true; };
}
function judgeHtml(r) {
  const lab = {giusto: "Giusto", parziale: "Quasi", sbagliato: "Non ancora"}[r.verdict] || r.verdict;
  return `<p class="explain fc-verdict ${r.verdict}"><b>${lab}.</b> ${inl(r.comment || "")}</p>`;
}
function flipCard() {
  const S = App.study, c = S.queue[0]; if (!S || !c) return;
  const ta = $("#cardAns");
  S.ans = ta ? ta.value.trim() : ""; S.judge = null; S.draft = "";
  S.flipped = true; renderCard();
  if (S.ans) {
    api("/api/judge", {method: "POST", body: {question: c.front, reference: c.back, why: "", answer: S.ans}})
      .then(r => { S.judge = r; LOG.ev("card_explain", {deck: c.deck, verdict: r.verdict}); const el = $("#fcJudge"); if (el && S.queue[0] === c) el.innerHTML = judgeHtml(r); })
      .catch(e => { const el = $("#fcJudge"); if (el) el.innerHTML = `<p class="muted">${esc(e.message)}</p>`; });
  }
}
/* esercizio passato in ripasso: prima una flashcard (spiegalo a parole), poi lo riscrivi a memoria */
function renderQuickCard(c) {
  const S = App.study, v = studyHost(), it = c.itemData;
  if (!it) { S.queue.shift(); return renderCard(); }
  const st = S.qc && S.qc.id === c.id ? S.qc : (S.qc = {id: c.id, phase: "front", ans: ""});
  const total = S.done + S.queue.length;
  v.onclick = null;
  v.innerHTML = `<section class="study fc-home"><div class="sess-head">${studyExit()}<span class="muted">Ripasso · esercizio passato</span><span class="spacer"></span><span class="sess-xp">carta ${S.done + 1} di ${total}</span></div>
    <div class="fc-stack"><article class="card fc ${st.phase === "back" ? "flipped" : ""}">
      <span class="fc-side">${st.phase === "back" ? "Retro" : "Fronte"} · ${esc(it.title)}</span>
      <div class="card-front">${it.problem ? inl(it.problem) : esc(it.title)}</div>
      ${st.phase === "front" ? `<p class="muted" style="margin:0;font-size:13.5px">${inl(it.plan ? it.plan.q : "Come lo risolvi?")}</p>
        <textarea class="open-ans fc-ans" id="qcAns" placeholder="Spiegalo a parole: che metodo usi, i passi, il caso limite. Ctrl+Invio per girare.">${esc(st.ans)}</textarea>`
      : `<div class="card-back fc-in"><span class="eyebrow">Il piano</span><p class="explain">${it.plan ? inl(it.plan.options[it.plan.correct]) + ". " + inl(it.plan.why || "") : ""}</p>
          ${it.steps && it.steps.length ? `<ol class="q-steps">${it.steps.map(x => `<li>${inl(x)}</li>`).join("")}</ol>` : ""}
          ${st.ans ? `<div class="fc-you"><span class="eyebrow">La tua spiegazione</span><p class="explain">${esc(st.ans)}</p><div id="qcJudge">${st.judge ? judgeHtml(st.judge) : `<p class="muted"><span class="spin small"></span> Qwen confronta la tua spiegazione…</p>`}</div></div>` : ""}</div>`}
    </article></div>
    <div class="row">${st.phase === "front"
      ? `<button class="btn primary" data-qc="flip">Gira la carta <kbd>Ctrl</kbd>+<kbd>Invio</kbd></button><button class="btn ghost" data-qc="plain">Non so spiegarlo: ragiono con le opzioni</button>`
      : `<button class="btn primary" data-qc="write">Ora riscrivilo a memoria</button>`}</div></section>`;
  Tutor.setContext(`Ripasso di un esercizio passato: «${it.title}». ${it.problem || ""} Lo studente deve prima spiegare il metodo a parole: non dirgli la soluzione.`, "Ripasso");
  const ta = $("#qcAns"); if (ta) { ta.focus(); ta.oninput = () => { st.ans = ta.value; }; ta.onkeydown = e => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); v.querySelector("[data-qc=flip]").click(); } }; }
  v.onclick = e => {
    const t = e.target.closest("button"); if (!t) return;
    const a = t.dataset.qc; if (!a) return;
    const start = plan => {
      S.qc = null;
      startQuick(it, {mode: "review", level: 3, card: c, hist: c.blockHist});
      if (plan) { App.Q.plan = plan; App.Q.phase = "scrivi"; App.Q.tWrite = Date.now(); renderQuick(); }
    };
    if (a === "plain") return start(null);
    if (a === "write") {
      const pl = st.judge ? {giusto: "free", parziale: "partial", sbagliato: "retry"}[st.judge.verdict] : st.ans ? "partial" : "shown";
      LOG.ev("plan_done", {id: it.id, title: it.title, plan: pl, how: "flashcard", secs: 0});
      return start(pl);
    }
    if (a === "flip") {
      st.ans = (st.ans || "").trim(); st.phase = "back"; renderQuickCard(c);
      if (st.ans && it.plan) api("/api/judge", {method: "POST", body: {question: `${it.problem || it.title} ${it.plan.q}`, reference: `${it.plan.options[it.plan.correct]}. Passi: ${(it.steps || []).join("; ")}`, why: it.plan.why || "", answer: st.ans}})
        .then(r => { st.judge = r; LOG.ev("plan_try", {id: it.id, title: it.title, how: "flashcard", ok: r.verdict === "giusto", verdict: r.verdict, answer: st.ans.slice(0, 300), comment: (r.comment || "").slice(0, 300)}); const el = $("#qcJudge"); if (el) el.innerHTML = judgeHtml(r); })
        .catch(e2 => { const el = $("#qcJudge"); if (el) el.innerHTML = `<p class="muted">${esc(e2.message)}</p>`; });
    }
  };
}
async function gradeCard(g) {
  const S = App.study, c = S.queue.shift();
  S.flipped = false; S.ans = ""; S.judge = null;
  api("/api/cards/grade", {method: "POST", body: {id: c.id, grade: g}}).catch(() => {});
  if (g === 0) { S.again++; S.queue.splice(Math.min(3, S.queue.length), 0, c); } else S.done++;
  renderCard();
}
document.addEventListener("keydown", e => {
  if (e.target.id === "cardAns" && e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); flipCard(); return; }
  if (!(App.view === "study" || (App.view === "start" && App.studyHome)) || !App.study || /INPUT|TEXTAREA/.test(e.target.tagName)) return;
  if (App.study.queue[0] && ["rewrite", "quick"].includes(App.study.queue[0].kind)) return;
  if (e.key === " " && !App.study.flipped) { e.preventDefault(); flipCard(); }
  else if (App.study.flipped && ["1", "2", "3"].includes(e.key)) { e.preventDefault(); gradeCard(+e.key - 1); }
});

/* ================================================================ prova del modello */
async function showSelftest() {
  App.view = "selftest"; mainNav("");
  const d = await api("/api/selftest");
  App.st = {d, res: [], running: false};
  const sp = d.spring;
  const TYPE_LABEL = t => (TYPES[t] ? TYPES[t].name : t);
  const stats = Object.entries(d.typestats || {}).filter(([, v]) => v.n);
  $("#view").innerHTML = `<section class="theory">
    <p class="eyebrow">Diagnostica</p><h1>Prova il modello</h1>
    <p class="explain">Genera un esercizio per ogni sezione con <code>${esc(d.model || "nessun modello")}</code>, lo verifica come fa l'app e misura quanto ci mette. Gli esercizi validi restano nel tuo archivio. Durata tipica: 5-15 minuti.</p>
    <div class="kpis" style="grid-template-columns:repeat(4,minmax(0,1fr))">
      <div class="stat"><b>${esc(d.model || "—")}</b><span>Modello</span></div><div class="stat"><b>${esc(d.python)}</b><span>Python</span></div>
      <div class="stat"><b>${esc(d.java || "—")}</b><span>Java</span></div><div class="stat"><b>${sp.ready ? "pronto" : "da preparare"}</b><span>Spring</span></div></div>
    <div class="row"><button class="btn primary" id="stGo" ${d.model ? "" : "disabled"}>Avvia la prova</button><span class="muted" id="stMsg"></span></div>
    <div class="cmp-wrap"><table class="cmp st"><tr><th>Sezione</th><th>Esito</th><th>Tempo</th><th>Note</th></tr>
      ${d.steps.map((s, i) => `<tr id="st-${i}"><td>${esc(s.label)}</td><td class="muted">—</td><td></td><td></td></tr>`).join("")}</table></div>
    <div id="stVerdict"></div>
    <div class="th-box"><span class="eyebrow">Spring con Maven</span>
      <p class="explain">${sp.ready ? `Pronto: le unità Java con Maven eseguono davvero i test JUnit (Spring Boot ${esc(sp.springBoot)}, H2, Spring Security, Spring AI con modelli finti). ${(sp.extras || []).filter(x => !x.ready).length ? ` Mancano ancora le librerie di ${sp.extras.filter(x => !x.ready).map(x => esc(x.label)).join(" e ")}: premi «Ripeti la prova Spring» per scaricarle (oppure si scaricano da sole al primo esercizio).` : ""}`
        : `Le unità Spring ora sono valutate dal modello. Preparando Spring, Ricalco ${sp.maven ? "usa il Maven che hai già" : "scarica Maven (9 MB)"} e le librerie di Spring Boot ${esc(sp.springBoot)} (circa 150 MB, solo la prima volta), poi esegue un test di prova.`}</p>
      <div class="row"><button class="btn ${sp.ready ? "" : "primary"}" id="spGo">${sp.ready ? "Ripeti la prova Spring" : "Prepara Spring"}</button><span class="muted" id="spMsg"></span></div>
      <pre class="out" id="spLog" ${sp.log && sp.log.length ? "" : "hidden"}>${esc((sp.log || []).join("\n"))}</pre></div>
    ${stats.length ? `<div class="th-box"><span class="eyebrow">I tuoi risultati per tipo di esercizio</span><ul>${stats.map(([k, v]) => `<li>${esc(k.split(":")[0])} · ${esc(TYPE_LABEL(k.split(":")[1]))}: ${Math.round(v.first / v.n * 100)}% al primo colpo su ${v.n}</li>`).join("")}</ul></div>` : ""}
    ${Object.keys(d.flags || {}).length ? `<div class="th-box warnbox"><span class="eyebrow">Esercizi che hai segnalato come sbagliati</span><ul>${Object.entries(d.flags).map(([t, n]) => `<li>${esc(TYPE_LABEL(t))}: ${n}</li>`).join("")}</ul></div>` : ""}
  </section>`;
  Tutor.setContext(`Lo studente sta provando il modello locale ${d.model} in Ricalco.`, "Prova il modello");
  Tutor.setQuick([]);
  $("#stGo").onclick = runSelftest;
  $("#spGo").onclick = setupSpring;
  if (sp.busy) pollSpring();
}
async function runSelftest() {
  const S = App.st; if (S.running) return;
  S.running = true; $("#stGo").disabled = true;
  const t0 = Date.now();
  for (let i = 0; i < S.d.steps.length; i++) {
    if (App.view !== "selftest") return;
    const row = $(`#st-${i}`);
    row.children[1].innerHTML = `<span class="spin small"></span>`;
    $("#stMsg").textContent = `${i + 1}/${S.d.steps.length} · ${Math.round((Date.now() - t0) / 1000)} s`;
    let r;
    try { r = await api("/api/selftest/step", {method: "POST", body: {i}}); } catch (e) { r = {ok: false, error: e.message, secs: 0}; }
    S.res[i] = r;
    if (!$(`#st-${i}`)) return;
    row.children[1].innerHTML = r.ok ? (r.attempts > 1 ? `<span class="okc">✓</span> dopo ${r.attempts} tentativi` : `<span class="okc">✓</span> al primo tentativo`) : `<span class="koc">✗</span> non riuscito`;
    row.children[2].textContent = r.secs + " s" + (r.first ? ` (prima parola ${r.first} s)` : "");
    row.children[3].textContent = r.error || r.title || r.sample || "";
  }
  S.running = false; $("#stGo").disabled = false; $("#stMsg").textContent = `Finito in ${Math.round((Date.now() - t0) / 60000)} min.`;
  const gen = S.res.slice(1), ok = gen.filter(r => r.ok), first = ok.filter(r => (r.attempts || 1) === 1);
  const avg = ok.length ? Math.round(ok.reduce((a, r) => a + r.secs, 0) / ok.length) : 0;
  const bad = gen.map((r, k) => r.ok ? null : S.d.steps[k + 1].label).filter(Boolean);
  let advice;
  if (ok.length === gen.length && first.length >= gen.length - 2) advice = "Il modello è affidabile per tutte le sezioni. Tienilo così.";
  else if (ok.length >= gen.length - 2) advice = "Funziona, ma a volte serve più di un tentativo: i tempi di attesa saranno più lunghi in quelle sezioni. Il lavoro in sottofondo compensa quasi sempre.";
  else advice = "Il modello sbaglia spesso. Prova un modello più forte per il codice (per esempio qwen2.5-coder:14b) oppure usa le sezioni che qui risultano affidabili.";
  if (avg > 90) advice += ` Tempo medio ${avg} s per esercizio: se è troppo, un 7B (qwen2.5-coder:7b) è circa due volte più veloce.`;
  $("#stVerdict").innerHTML = `<div class="th-box"><span class="eyebrow">Risultato</span>
    <p class="explain"><b>${ok.length}/${gen.length}</b> sezioni con esercizi validi, <b>${first.length}</b> al primo tentativo, tempo medio <b>${avg} s</b> per esercizio. Tutor: prima parola dopo ${S.res[0] && S.res[0].first || "—"} s.</p>
    ${bad.length ? `<p class="explain">Non riuscite: ${bad.map(esc).join(", ")}.</p>` : ""}<p class="explain">${advice}</p></div>`;
}
async function setupSpring() {
  $("#spGo").disabled = true;
  try { await api("/api/spring/setup", {method: "POST", body: {}}); } catch (e) { toast(e.message); }
  pollSpring();
}
async function pollSpring() {
  const st = await api("/api/spring").catch(() => null);
  if (!st || App.view !== "selftest") return;
  const log = $("#spLog"); log.hidden = false; log.textContent = st.log.join("\n"); log.scrollTop = log.scrollHeight;
  $("#spMsg").innerHTML = st.busy ? `<span class="spin small"></span> In corso…` : st.ready ? "Spring è pronto." : "Non riuscito: guarda il registro qui sotto.";
  if (st.busy) setTimeout(pollSpring, 2000);
  else { $("#spGo").disabled = false; if (st.ready) { $("#spGo").textContent = "Ripeti la prova Spring"; toast("Spring pronto: le unità Spring ora eseguono i test veri."); } }
}

/* ================================================================ riscrittura a memoria (esercizi sbagliati, ripasso) */
function sheetHtml(hint) {
  return `<div class="sheet drill"><pre class="code askable"></pre><textarea class="trap" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" aria-label="Scrivi qui il codice"></textarea><div class="miss-tag"></div><div class="sheet-hint when-blur">${esc(hint || "Clicca sul foglio e scrivi a memoria")}</div></div>`;
}
function rewriteTracer(host, lang, code, onDone, level = 3) {
  const stats = {typed: 0, errors: 0, hints: 0, blockErr: {}};
  const tr = new Tracer($(".sheet", host), {lang, blocks: [{code}]}, {
    level, stats,
    onLocked: () => {},
    onBlockDone: () => { const h = $(".sheet-hint", host); if (h) h.remove(); onDone(stats, tr); },
    onChange: () => {}
  });
  tr.setState(0, "scrivi");
  tr.focus();
  setTimeout(() => tr.focus(), 30);
  return {tr, stats};
}
function words(t) { return new Set(String(t || "").toLowerCase().match(/[a-z_][a-z0-9_]{2,}/g) || []); }
function bestBlock(L, ex) {
  const w = words([ex.statement, ex.question, ex.code, ex.solution, ex.starter, (ex.options || []).join(" ")].join(" "));
  let best = 0, score = -1;
  L.blocks.forEach((b, k) => {
    const bw = words(b.code + " " + (b.explain || ""));
    let sc = 0; bw.forEach(x => { if (w.has(x)) sc++; });
    sc = sc / Math.sqrt(bw.size || 1);
    if (sc > score) { score = sc; best = k; }
  });
  return best;
}
function openDrill(ex) {
  const L = P.s.unitLesson; if (!L) return;
  const k = bestBlock(L, ex), b = L.blocks[k];
  const box = $("#drillBox"); if (!box) return;
  box.innerHTML = `<div class="drill-box"><span class="eyebrow">Riscrivi a memoria · «${esc(L.title)}», blocco ${k + 1}</span>
    <p class="explain">${inl(b.explain || "")}</p>${sheetHtml()}<p class="muted" id="drillMsg" style="font-size:13px;margin:0">Dopo tre errori sullo stesso punto compare la parola.</p></div>`;
  rewriteTracer(box, P.s.lang, b.code, st => {
    const tot = st.typed + st.errors;
    $("#drillMsg").innerHTML = `<b>Fatto.</b> Precisione ${tot ? Math.round(st.typed / tot * 100) : 100}%, ${st.hints} aiuti. Questo blocco è già nel tuo ripasso.`;
    const nb = $("#nextBtn"); if (nb) nb.focus();
  });
  box.scrollIntoView({block: "nearest", behavior: "smooth"});
}

/* ================================================================ SQL: tabelle e confronti */
function sqlCell(v) { return v === null || v === undefined ? "NULL" : typeof v === "number" && !Number.isInteger(v) ? String(+v.toFixed(4)) : String(v); }
function sqlTable(res, cls = "") {
  if (!res || !res.cols) return `<p class="muted">(nessun risultato)</p>`;
  return `<div class="cmp-wrap"><table class="cmp sqlt ${cls}"><tr>${res.cols.map(c => `<th>${esc(c)}</th>`).join("")}</tr>${res.rows.length ? res.rows.map(r => `<tr>${r.map(v => `<td class="${v === null ? "null" : ""}">${esc(sqlCell(v))}</td>`).join("")}</tr>`).join("") : `<tr><td colspan="${res.cols.length}" class="muted">nessuna riga</td></tr>`}</table></div>`;
}
function dbHtml(ex, open) {
  if (ex.check !== "sql" || !ex.tables || !Object.keys(ex.tables).length) return "";
  const names = Object.keys(ex.tables);
  return `<details class="db" ${open ? "open" : ""}><summary><span class="eyebrow">Il database</span> <span class="muted">${names.map(esc).join(", ")}</span></summary>
    <div class="db-grid">${names.map(n => `<div><b class="db-name">${esc(n)}</b>${sqlTable(ex.tables[n])}${ex.tables[n].rows.length >= 12 ? `<small class="muted">prime 12 righe</small>` : ""}</div>`).join("")}</div></details>`;
}
function sqlFailHtml(ex, r) {
  if (r.error) return `<div class="res-err"><b>La query va in errore</b><pre>${esc(r.error)}</pre>${r.where && !/^(setup|check)$/.test(r.where) ? `<small class="muted">Nell'istruzione: ${esc(r.where)}</small>` : ""}</div>`;
  const got = r.result, exp = ex.expected || {cols: [], rows: []};
  let why = "";
  if (!got) why = "La query non restituisce nessuna tabella: manca una SELECT?";
  else if (got.cols.length !== exp.cols.length) why = `Il risultato ha ${got.cols.length} ${got.cols.length === 1 ? "colonna" : "colonne"}, ne ${exp.cols.length === 1 ? "serve 1" : `servono ${exp.cols.length}`}.`;
  else if (got.rows.length !== exp.rows.length) why = `Il risultato ha ${got.rows.length} ${got.rows.length === 1 ? "riga" : "righe"}, ne ${exp.rows.length === 1 ? "serve 1" : `servono ${exp.rows.length}`}.`;
  else why = ex.ordered ? "Stesse dimensioni, ma valori o ordine diversi." : "Stesse dimensioni, ma i valori sono diversi (l'ordine qui non conta).";
  return `<span class="eyebrow">Il risultato non è quello atteso</span><p class="muted" style="margin:0;font-size:13px">${why}</p>
    <div class="sql-cmp"><div><small class="muted">Atteso</small>${sqlTable(exp)}</div><div><small class="muted">Il tuo risultato</small>${sqlTable(got)}</div></div>`;
}
function sqlFailText(ex, r) {
  if (r.error) return "Errore: " + r.error;
  const t = res => res ? [res.cols.join(" | ")].concat(res.rows.map(x => x.map(sqlCell).join(" | "))).join("\n") : "(nessun risultato)";
  return `Risultato atteso:\n${t(ex.expected)}\nRisultato ottenuto:\n${t(r.result)}`;
}
function sqlLines(text, cols) {
  const norm = v => { v = v.trim().replace(/^['"]|['"]$/g, ""); if (/^null$/i.test(v)) return "NULL"; if (/^-?\d+([.,]\d+)?$/.test(v)) { const n = parseFloat(v.replace(",", ".")); return String(+n.toFixed(4)); } return v; };
  let lines = String(text || "").replace(/\r/g, "").split("\n").map(l => l.trim()).filter(Boolean).map(l => l.replace(/^\||\|$/g, "").split("|").map(norm).join(" | "));
  if (cols && cols.length && lines.length && lines[0].toLowerCase() === cols.map(c => c.toLowerCase()).join(" | ")) lines = lines.slice(1);
  return lines;
}

/* ================================================================ ricalco della soluzione (ogni volta che scrivi codice) */
const CODE_TYPES = ["completa", "bug", "zero", "riordina"];
function startSolutionRicalco(ex, lang, miss) {
  const host = $("#rcHost"); if (!host || !ex.solution) return;
  const st = ex.state.rc = ex.state.rc || {level: miss ? 1 : 2, best: 0};
  mountRicalco(host, {lang, code: ex.solution, st, label: miss ? "Ora ricalca la soluzione" : "Ricalca la soluzione di riferimento",
    note: miss ? "La soluzione è anche nel tuo ripasso: tornerà da riscrivere a memoria domani." : ""});
  feynmanFor(ex, lang);
}
function mountRicalco(host, o) {
  const st = o.st, lv = st.level;
  if (st.skipped) {
    host.innerHTML = `<div class="rc"><span class="eyebrow">Soluzione di riferimento</span><pre class="out askable">${esc(o.code)}</pre>
      <div class="row"><button class="btn small" data-rc="open">Ricalcala</button></div></div>`;
  } else {
    host.innerHTML = `<div class="rc">
      <div class="rc-head"><span class="eyebrow">${esc(o.label)}</span><span class="spacer"></span>
        <div class="seg small" role="group" aria-label="Livello">${[1, 2, 3].map(n => `<button type="button" data-rc="${n}" aria-pressed="${n === lv}" title="${LEVELS[n].desc}"><span class="num">${n}</span>${LEVELS[n].name}</button>`).join("")}</div>
        <button class="linkish" data-rc="skip">Salta</button></div>
      ${sheetHtml(lv === 1 ? "Clicca sul foglio e ricalca la soluzione" : lv === 2 ? "Clicca e ricostruisci nomi e valori" : "Clicca e riscrivila a memoria")}
      <p class="muted rc-msg">${o.note ? esc(o.note) + " " : ""}Si scrive come sul foglio della lezione: niente incolla, i commenti si scrivono da soli.</p></div>`;
    rewriteTracer(host, o.lang, o.code, stats => {
      const tot = stats.typed + stats.errors, acc = tot ? Math.round(stats.typed / tot * 100) : 100;
      st.best = Math.max(st.best, lv);
      const msg = $(".rc-msg", host);
      msg.innerHTML = `<b>Fatto al livello ${lv}.</b> Precisione ${acc}%, ${stats.hints} aiuti. ` +
        (lv < 3 ? `<button class="btn small primary" data-rc="${lv + 1}">Rifalla a livello ${lv + 1} · ${LEVELS[lv + 1].name}</button>` : "L'hai scritta a memoria.");
      const fy = $(".fy-ans");
      const b = fy && !fy.value ? fy : lv < 3 ? $(`[data-rc="${lv + 1}"].primary`, host) : ($("#nextBtn") || $("#nextEx"));
      if (b) b.focus();
    }, lv);
  }
  host.onclick = e => {
    const b = e.target.closest("[data-rc]"); if (!b) return;
    const a = b.dataset.rc;
    if (a === "skip") st.skipped = true;
    else if (a === "open") st.skipped = false;
    else { st.level = +a; st.skipped = false; }
    mountRicalco(host, o);
  };
}

/* ================================================================ pagina principale: Oggi */
const QL = {python: "Python", java: "Java", sql: "SQL"};
const PLAN_LABEL = {first: "piano giusto al primo colpo", free: "piano spiegato con parole tue", partial: "piano quasi giusto", retry: "piano giusto al secondo tentativo", shown: "piano visto senza risolverlo"};
function eloHtml(e) {
  if (!e) return "";
  return `<div class="elo" title="Il punteggio sale se risolvi bene esercizi del tuo livello e scende se sbagli: gli esercizi si scelgono vicino al tuo punteggio.">
    <div class="row"><b>Livello ${e.tier} · ${esc(e.tierName)}</b><span class="elo-r">${e.r}</span></div>
    <div class="bar"><i style="width:${e.pct}%"></i></div>
    <small class="muted">${e.n ? `${e.n} ${e.n === 1 ? "esercizio valutato" : "esercizi valutati"}` : "Si parte facile: il livello si adatta a come vai"}${e.nextName ? ` · ${esc(e.nextName)} a ${e.nextAt}` : ""}</small>
    ${e.unit ? `<small class="muted" style="display:block;margin-top:4px">Argomento: <b>${esc(e.unit)}</b>${e.unitNext ? ` · a ${e.unitNextAt}: ${esc(e.unitNext)}` : ""}</small>` : ""}</div>`;
}
async function showStart() {
  App.view = "start"; mainNav("home");
  if (!QL[App.qlang]) App.qlang = "python";
  App.study = null; App.studyHome = false;
  const v = $("#view");
  v.innerHTML = `<section class="start">
    <header class="path-head">
      <div><p class="eyebrow">Oggi</p><h1>Allenamento</h1>
        <p class="goal muted">Ragioni sul problema, poi riscrivi la soluzione blocco per blocco. La difficoltà segue il tuo livello.</p></div>
      <div class="start-tools">
        <div class="seg" role="group" aria-label="Linguaggio">${Object.keys(QL).map(k => `<button type="button" data-ql="${k}" aria-pressed="${App.qlang === k}">${QL[k]}</button>`).join("")}</div>
        <div id="eloBox"></div>
      </div>
    </header>
    <div id="warn">${ollamaBanner()}</div>
    <div id="reviewBox"></div>
    <article class="quick" id="quick"><div class="empty">Preparo l'esercizio…</div></article>
    <div id="startSide"></div>
  </section>`;
  v.onclick = startClick;
  await renderStartSide();
  loadQuick();
}
async function renderStartSide() {
  let H;
  try { H = await api("/api/home"); } catch (e) { return; }
  App.H = H;
  if (App.view !== "start") return;
  renderReviewBox();
  const box = $("#startSide"); if (!box) return;
  const order = ["python", "java", "sql", "algopy", "algojava"];
  const ps = order.map(id => H.paths.find(p => p.id === id)).filter(Boolean);
  box.innerHTML = `
    <div class="kpis home-kpis">
      <div class="stat"><b>${H.streak}</b><span>Giorni di fila${H.today ? "" : " · oggi no"}</span></div>
      <div class="stat"><b>${H.quick}</b><span>Esercizi fatti qui</span></div>
      <div class="stat"><b>${H.cardsDue}</b><span>Da ripassare oggi</span></div>
      <div class="stat"><b>${H.xp}</b><span>XP</span></div>
    </div>
    <div class="home-grid">
      <section class="cat"><div class="u-title"><h3>I tuoi schemi · ${QL[App.qlang]}</h3></div>${patternsHtml(H.patterns[App.qlang])}</section>
      <section class="cat"><div class="u-title"><h3>Prova settimanale · ${QL[App.qlang]}</h3></div>${weeklyHtml(H.weekly[App.qlang])}</section>
    </div>
    <h2 class="section-title">Percorsi</h2>
    <div class="cat-grid">${ps.map(p => `<article class="cat pcard ${p.algo ? "algo" : ""}">
        <div class="u-title"><h3>${esc(p.name)}</h3>${p.due ? `<span class="tag wait">${p.due} da ripassare</span>` : ""}</div>
        <p class="u-concepts">${esc(p.goal)}</p>
        <div class="bar" title="${p.fixed}/${p.units} unità fissate"><i style="width:${Math.round(p.fixed / p.units * 100)}%"></i></div>
        <p class="u-concepts">${p.unit ? `Unità ${p.unit.n}/${p.units} · ${esc(p.unit.title)} · ${p.unit.step === 1 ? "da imparare" : "da fissare"}` : "Percorso fissato"}</p>
        <div class="row"><a class="btn small ${p.started ? "primary" : ""}" href="#/percorso/${p.id}">${p.started ? "Continua" : "Inizia"}</a></div>
      </article>`).join("")}</div>
    <div class="row muted" style="font-size:13.5px">Altro: <a href="#/logica">Logica</a> · <a href="#/colloquio">Colloquio tecnico</a> · <a href="#/carte">Tutti i mazzi</a> · <a href="#/libere">Lezione libera su un argomento</a></div>`;
}
function renderReviewBox() {
  const box = $("#reviewBox"), H = App.H; if (!box || !H) return;
  if (App.studyHome || !H.cardsDue || App.reviewSkipped) { box.innerHTML = ""; return; }
  const q = H.reviewByKind.quick, rw = H.reviewByKind.rewrite, other = H.cardsDue - q - rw;
  const parts = [q ? `${q} ${q === 1 ? "esercizio passato" : "esercizi passati"}` : "", rw ? `${rw} ${rw === 1 ? "blocco" : "blocchi"} da riscrivere` : "", other > 0 ? `${other} ${other === 1 ? "carta" : "carte"}` : ""].filter(Boolean);
  box.innerHTML = `<div class="review-banner row-banner"><div><b>Prima il ripasso: ${parts.join(", ")}.</b><span>Gli esercizi passati tornano come flashcard: ragioni sul piano e li riscrivi a memoria.</span></div>
    <div class="row"><button class="btn primary" data-q="review">Inizia il ripasso</button><button class="btn ghost" data-q="skipReview">Più tardi</button></div></div>`;
}
async function loadQuick(skip) {
  const box = $("#quick"); if (!box) return;
  const lang = App.qlang;
  if (skip) App.qSkip = (App.qSkip || []).concat(skip).slice(-30);
  let d;
  const pat = App.qPattern || ""; App.qPattern = null;
  try { d = await api(`/api/quick?lang=${lang}&skip=${encodeURIComponent((App.qSkip || []).join(","))}&pattern=${pat}`); }
  catch (e) { box.innerHTML = `<div class="banner err">${esc(e.message)}</div>`; return; }
  if (App.view !== "start" || App.qlang !== lang || App.studyHome) return;
  $("#eloBox").innerHTML = eloHtml(d.elo);
  if (!d.item) { box.innerHTML = `<div class="empty">Nessun esercizio pronto. Accendi Ollama: Qwen ne prepara in sottofondo.</div>`; return; }
  startQuick(d.item, {mode: "new", level: d.startLevel, info: d, hist: d.blockHist});
}

/* ---- un esercizio: ragiona → scrivi (ricalco con «cosa fa») → fatto */
function startQuick(item, o) {
  const host = $("#quick"); host.onclick = null;
  const T = App.Q = {item, mode: o.mode, card: o.card || null, info: o.info || {}, level: o.level || 1,
    phase: item.plan || item.problem ? "ragiona" : "scrivi", plan: item.plan ? null : "none", tries: 0, wrong: [], free: true, judge: null, draft: "",
    order: item.plan ? shuffled(item.plan.options.length) : [], stats: {typed: 0, errors: 0, hints: 0, blockErr: {}, blockHint: {}}, k: 0, res: null,
    hist: o.hist || null, fromReview: !!o.fromReview, t0: Date.now(), tBlock: Date.now()};
  LOG.ev("quick_start", {id: item.id, title: item.title, tier: item.tier, lang: item.lang, mode: o.mode, level: T.level, pattern: item.pattern});
  T.free = !(App.status && !App.status.model);
  renderQuick();
  Tutor.reset();
  Tutor.setQuick(["Dammi un indizio sul metodo", "Qual è la complessità?", "Quando si usa nella pratica?"]);
}
function quickCtx() {
  const T = App.Q, it = T.item;
  let c = `Esercizio «${it.title}» (${QL[it.lang]}). Problema: ${it.problem}\n`;
  if (T.phase === "ragiona") c += "Lo studente deve ancora dire come lo risolverebbe: NON dargli il metodo né il codice, fai domande e dai indizi.\n";
  else c += `Piano: ${(it.steps || []).join(" ")}\nCodice:\n${it.blocks.map(b => b.code).join("\n")}\nCosa fa ogni blocco: ${it.blocks.map((b, i) => `${i + 1}) ${b.what}`).join(" ")}\n`;
  return c;
}
function quickHead() {
  const T = App.Q, it = T.item;
  const rev = T.mode === "review" || T.fromReview;
  return `<div class="q-head"><span class="tag acc">${it.kind === "query" ? "Query" : "Algoritmo"} · ${QL[it.lang]}</span><span class="tag">Livello ${it.tier}</span>${rev ? `<span class="tag wait">ripasso</span>` : ""}
    <h2>${esc(it.title)}</h2><span class="spacer"></span>
    ${rev && App.study ? `<span class="muted" style="font-size:12.5px">${App.study.done} fatte · ${App.study.queue.length} rimaste</span><button class="btn small ghost" data-q="endReview">Basta ripasso</button>`
      : T.phase !== "fatto" ? `<button class="btn small ghost" data-q="other" title="Passa a un altro esercizio: questo non conta">Salta</button>` : ""}</div>`;
}
function renderQuick() {
  const T = App.Q, it = T.item, box = $("#quick"); if (!box) return;
  Tutor.setContext(quickCtx(), `Oggi · ${it.title}`);
  if (T.phase === "ragiona") return renderRagiona();
  if (T.level === 4) return renderFree();
  const n = it.blocks.length;
  box.innerHTML = `${quickHead()}
    ${it.problem ? `<p class="q-problem">${inl(it.problem)}</p>` : ""}
    ${T.plan && T.plan !== "none" && it.steps && it.steps.length ? `<details class="q-plan"><summary class="muted">Il piano</summary><ol>${it.steps.map(x => `<li>${inl(x)}</li>`).join("")}</ol></details>` : ""}
    <div class="row q-levels"><span class="muted" style="font-size:13px">Aiuto</span>${levelSeg(T)}
      <span class="muted" style="font-size:12.5px">${LEVELS[T.level].desc}</span></div>
    <div class="strip" id="qStrip"></div>
    <div class="q-task" id="qTask" hidden></div>
    <div class="sheet" id="qSheet"><pre class="code askable" aria-label="Codice da riscrivere"></pre>
      <textarea class="trap" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" aria-label="Scrivi qui il codice"></textarea>
      <div class="miss-tag"></div><div class="sheet-hint when-blur">Clicca sul foglio e scrivi</div></div>
    <div class="sheet-foot"><p class="status" id="qStatus"></p><div class="acts"><button class="btn small" id="qHint">Mostra parola</button><button class="btn small ghost" data-q="restart">Ricomincia</button></div></div>
    <div id="qExplain" class="q-explain"></div>
    <div id="qEnd"></div>`;
  T.bl = blockLevels(T.hist, T.level, it.blocks.length);
  const tr = new Tracer($("#qSheet"), {lang: it.lang, blocks: it.blocks}, {
    level: T.level, stats: T.stats, blockLevel: T.bl,
    onLocked: ch => { if (T.phase === "fatto" && ch === "\n") { const b = $("#qEnd .btn.primary"); if (b) b.click(); } },
    onBlockDone: k => quickBlockDone(k),
    onChange: () => quickStatus()
  });
  T.tr = tr;
  tr.setState(0, "scrivi");
  quickStatus();
  tr.focus(); setTimeout(() => tr.focus(), 30);
}
function levelSeg(T) {
  return `<div class="seg small" role="group" aria-label="Livello di aiuto">${[1, 2, 3, 4].map(l => `<button type="button" data-qv="${l}" aria-pressed="${T.level === l}" title="${LEVELS[l].desc}" ${T.phase === "fatto" ? "disabled" : ""}><span class="num">${l}</span>${LEVELS[l].name}</button>`).join("")}</div>`;
}
/* ---- livello 4 «Scrivi tu»: niente foglio da ricalcare, solo il problema e il tuo codice */
function renderFree() {
  const T = App.Q, it = T.item, box = $("#quick");
  T.f4 = T.f4 || {code: it.lang === "python" ? "# Scrivi qui il tuo programma\n" : it.lang === "sql" ? "-- Scrivi qui la tua query\n" : "public class Main {\n    public static void main(String[] args) {\n        \n    }\n}\n", runs: 0, fails: 0, matched: false, reviewOk: false};
  box.innerHTML = `${quickHead()}
    ${it.problem ? `<p class="q-problem">${inl(it.problem)}</p>` : ""}
    ${T.plan && T.plan !== "none" && it.steps && it.steps.length ? `<details class="q-plan"><summary class="muted">Il piano</summary><ol>${it.steps.map(x => `<li>${inl(x)}</li>`).join("")}</ol></details>` : ""}
    <div class="row q-levels"><span class="muted" style="font-size:13px">Aiuto</span>${levelSeg(T)}<span class="muted" style="font-size:12.5px">${LEVELS[4].desc}</span></div>
    <p class="muted" style="margin:0;font-size:13px">Nomi, metodo e struttura li scegli tu. Conta che il programma dia lo stesso risultato della soluzione di riferimento${it.lang === "sql" ? "" : " sugli stessi casi di prova (stampali come vuoi: se il formato è diverso, Qwen lo valuta lo stesso)"}.</p>
    <div id="f4Ed"></div>
    <div class="row" id="f4Acts"><button class="btn primary" data-q="f4run" id="f4Run">Esegui e fai correggere</button><span class="muted" style="font-size:12.5px"><kbd>Ctrl</kbd>+<kbd>Invio</kbd></span><span class="spacer"></span>
      <button class="btn ghost" data-q="f4give">Mostrami la soluzione</button></div>
    <div id="f4Res"></div><div id="f4Rev"></div><div id="qEnd"></div>`;
  T.f4.ed = makeEditor($("#f4Ed"), T.f4.code, {onChange: v => { T.f4.code = v; }, onRun: () => freeRun()});
  T.f4.ed.focus();
}
async function freeRun() {
  const T = App.Q, it = T.item, F = T.f4, btn = $("#f4Run"); if (!F || F.done) return;
  btn.disabled = true; btn.textContent = "Eseguo…";
  try {
    const r = await api("/api/quick/free", {method: "POST", body: {lang: it.lang, id: it.id, code: F.code}});
    F.runs++; if (!r.match) F.fails++;
    F.matched = F.matched || r.match;
    LOG.ev("free_run", {id: it.id, title: it.title, ok: r.ok, match: r.match, run: F.runs});
    $("#f4Res").innerHTML = r.match ? `<div class="solved"><b>Il tuo programma dà lo stesso risultato della soluzione.</b><pre class="out">${esc(r.stdout)}</pre></div>`
      : !r.ok ? `<div class="res-err"><b>Il programma si ferma con un errore</b><pre>${esc(r.error || "")}</pre></div>`
      : `<div class="banner"><b>Gira, ma il risultato è diverso</b><div class="cmp2"><div><span class="eyebrow">Il tuo</span><pre class="out">${esc(r.stdout || "(niente)")}</pre></div><div><span class="eyebrow">Atteso</span><pre class="out">${esc(r.expected || "")}</pre></div></div></div>`;
    const rv = await mountReview($("#f4Rev"), {lang: it.lang, task: `${it.title}: ${it.problem || ""}`, code: F.code, reference: it.blocks.map(b => b.code).join("\n"),
      outcome: r.match ? "Stesso output della soluzione di riferimento." : r.ok ? `Gira ma stampa:\n${(r.stdout || "").slice(0, 600)}\nAtteso:\n${(r.expected || "").slice(0, 600)}` : `Errore: ${(r.error || "").slice(0, 600)}`});
    F.reviewOk = F.reviewOk || !!(rv && rv.ok && r.ok);
    if ((F.matched || F.reviewOk) && !$("#f4Done")) $("#f4Acts").insertAdjacentHTML("beforeend", `<button class="btn primary" data-q="f4done" id="f4Done">Concludi</button>`);
  } catch (e) { toast(e.message); }
  if (btn.isConnected) { btn.disabled = false; btn.textContent = "Esegui di nuovo"; }
}
async function freeFinish(gaveUp) {
  const T = App.Q, it = T.item, F = T.f4; F.done = true;
  const acc = gaveUp ? 0 : F.matched ? Math.max(40, 100 - 15 * Math.max(0, F.fails)) : Math.max(30, 70 - 15 * Math.max(0, F.fails - 1));
  $("#f4Acts").remove(); F.ed.ta.readOnly = true;
  let r = null;
  try { r = await api("/api/quick/done", {method: "POST", body: {lang: it.lang, id: it.id, level: 4, acc, hints: 0, plan: T.plan || "none", mode: T.mode, card: T.card ? T.card.id : null}}); }
  catch (e) { toast(e.message); }
  LOG.ev("quick_done", {id: it.id, title: it.title, tier: it.tier, lang: it.lang, mode: T.mode, level: 4, acc, hints: 0, plan: T.plan, s: r ? r.s : null, delta: r ? r.delta : null, runs: F.runs, gaveUp});
  T.phase = "fatto";
  if (r && r.elo && T.mode !== "review") $("#eloBox").innerHTML = eloHtml(r.elo);
  const rev = T.mode === "review" || T.fromReview;
  $("#qEnd").innerHTML = `<div class="${gaveUp ? "banner" : "solved"}"><b>${r ? `Punteggio ${Math.round(r.s * 100)}/100` : "Fatto"}${r && r.delta ? ` · livello ${r.delta > 0 ? "+" : ""}${r.delta}` : ""}</b>
    <span>${gaveUp ? "Ecco la soluzione di riferimento: ricalcala al livello 2 e poi riprova da solo." : `Scritto da te, ${F.runs} ${F.runs === 1 ? "esecuzione" : "esecuzioni"}.`}</span>
    ${gaveUp ? `<pre class="out">${esc(it.blocks.map(b => b.code).join("\n"))}</pre>` : ""}
    <div class="row">${gaveUp ? `<button class="btn primary" data-q="down">Ricalcalo al livello 2</button>` : ""}
      ${rev ? `<button class="btn ${gaveUp ? "" : "primary"}" data-q="nextCard">Avanti</button>` : `<button class="btn ${gaveUp ? "" : "primary"}" data-q="next">Prossimo esercizio</button>`}</div></div>`;
}
function rev2(T) { return T.mode === "review" || T.fromReview; }
function renderRagiona() {
  const T = App.Q, it = T.item, p = it.plan, box = $("#quick");
  const L = "ABCDE";
  let body;
  const solved = T.plan && T.plan !== "none";
  if (!p) body = "";
  else if (solved) {
    body = `<div class="${T.plan === "shown" ? "banner" : "solved"}"><b>${T.plan === "shown" ? "Ecco il piano." : T.plan === "partial" ? "Quasi: il piano completo è questo." : "Giusto."}</b>
      ${T.judge && T.judge.comment ? `<p class="explain">${inl(T.judge.comment)}</p>` : ""}
      <p class="explain">${inl(p.options[p.correct])}. ${inl(p.why)}</p>
      ${it.steps && it.steps.length ? `<span class="eyebrow">I passi</span><ol class="q-steps">${it.steps.map(x => `<li>${inl(x)}</li>`).join("")}</ol>` : ""}
      <div class="row"><button class="btn primary" data-q="write" id="qWrite">Ora scrivi il codice</button><span class="muted" style="font-size:12.5px">livello ${T.level} · ${LEVELS[T.level].name}</span></div></div>`;
  } else if (T.free) {
    body = `<p class="q">${inl(p.q)}</p><p class="muted" style="margin:0;font-size:13.5px">Scrivi i passi con parole tue: cosa ti serve e cosa fai. <kbd>Invio</kbd> per farlo valutare.</p>
      <textarea class="open-ans" id="qPlanAns" placeholder="Es. tengo una variabile con… scorro… se… alla fine restituisco…">${esc(T.draft)}</textarea>
      ${T.judge ? `<p class="fb ${T.judge.verdict === "parziale" ? "mid" : "bad"}"><b>${T.judge.verdict === "parziale" ? "Quasi." : "Non ancora."}</b> ${inl(T.judge.comment)}</p>` : ""}
      <div class="row"><button class="btn primary" data-q="judge" id="qJudge">Valuta il mio piano</button><button class="linkish" data-q="mc">Preferisco scegliere tra le opzioni</button>
        <span class="spacer"></span>${T.tries ? `<button class="btn ghost" data-q="showPlan">Mostrami il piano</button>` : ""}</div>`;
  } else {
    body = `<p class="q">${inl(p.q)}</p><div class="opts">${T.order.map((oi, k) => `<button class="opt ${T.wrong.includes(oi) ? "wrong" : ""}" data-qopt="${oi}" ${T.wrong.includes(oi) ? "disabled" : ""}><span class="k">${L[k]}</span><span>${inl(p.options[oi])}</span></button>`).join("")}</div>
      ${T.tries ? `<p class="fb bad"><b>Non è questo.</b> Ripensaci, oppure guarda il piano.</p>` : ""}
      <div class="row">${App.status && App.status.model ? `<button class="linkish" data-q="free">Preferisco spiegarlo con parole mie</button>` : ""}<span class="spacer"></span>${T.tries ? `<button class="btn ghost" data-q="showPlan">Mostrami il piano</button>` : ""}</div>`;
  }
  box.innerHTML = `${quickHead()}
    <div class="step-head"><span class="n">1</span><h2>Ragiona prima di scrivere</h2></div>
    ${T.info && T.info.repeatReason && !rev2(T) ? `<p class="fb mid" style="font-size:13px"><b>Ripresa.</b> ${esc(T.info.repeatReason)}</p>` : ""}
    <p class="q-problem">${inl(it.problem || "Leggi il problema e pensa a come lo risolveresti.")}</p>
    ${body}`;
  const f = $("#qWrite") || $("#qPlanAns"); if (f) f.focus();
  if ($("#qPlanAns")) $("#qPlanAns").oninput = e => { T.draft = e.target.value; };
}
function quickStatus() {
  const T = App.Q; if (!T || !$("#qStatus")) return;
  const it = T.item, n = it.blocks.length, s = T.stats, tot = s.typed + s.errors;
  $("#qStrip").innerHTML = it.blocks.map((b, k) => `<span class="${k < T.k || T.phase === "fatto" ? "done" : k === T.k ? "cur" : ""}"></span>`).join("");
  $("#qStatus").textContent = T.phase === "fatto" ? `Finito · precisione ${tot ? Math.round(s.typed / tot * 100) : 100}%` : `Blocco ${T.k + 1} di ${n} · precisione ${tot ? Math.round(s.typed / tot * 100) + "%" : "—"} · aiuti ${s.hints}`;
  const task = $("#qTask"), b = it.blocks[T.k];
  task.hidden = T.phase === "fatto" || !b;
  const bl = T.tr ? T.tr.lv(T.k) : T.level;
  $("#qHint").hidden = bl === 1 || T.phase === "fatto";
  if (!task.hidden && task.dataset.k !== `${T.k}-${bl}`) {
    task.dataset.k = `${T.k}-${bl}`;
    const what = b.what || (bl === 3 ? b.explain : "");
    const why = bl > T.level ? "l'ultima volta l'hai scritto bene: qui meno aiuto" : bl < T.level ? "l'ultima volta qui hai sbagliato: più aiuto" : "";
    task.innerHTML = `<span class="lbl">Blocco ${T.k + 1} · cosa fa${why ? ` · livello ${bl} ${LEVELS[bl].name}` : ""}</span>${why ? `<small class="muted">${why}</small>` : ""}<p class="explain">${what ? inl(what) : `<span class="muted">Ricalca il blocco: la spiegazione arriva quando lo finisci.</span>`}</p>`;
  }
  if (T.phase === "fatto") { const h = $("#qSheet .sheet-hint"); if (h) h.remove(); }
}
function quickBlockDone(k) {
  const T = App.Q, it = T.item, b = it.blocks[k];
  $("#qExplain").insertAdjacentHTML("beforeend", `<div class="q-ex"><span class="lbl">Blocco ${k + 1} · perché è scritto così</span>${b.what ? `<p class="explain"><b>${inl(b.what)}</b></p>` : ""}<p class="explain">${inl(b.explain || "")}</p></div>`);
  LOG.ev("block", {id: it.id, title: it.title, k, secs: secsSince(T.tBlock), err: T.stats.blockErr[k] || 0, hints: (T.stats.blockHint || {})[k] || 0, lvl: T.tr.lv(k)});
  T.tBlock = Date.now();
  if (k + 1 < it.blocks.length) { T.k = k + 1; T.tr.setState(k + 1, "scrivi"); quickStatus(); return; }
  T.phase = "fatto"; T.k = it.blocks.length;
  quickStatus();
  $$("[data-qv]").forEach(x => x.disabled = true);
  quickFinish();
}
async function quickFinish() {
  const T = App.Q, it = T.item, s = T.stats, tot = s.typed + s.errors, acc = tot ? Math.round(s.typed / tot * 100) : 100;
  const end = $("#qEnd");
  end.innerHTML = `<p class="muted"><span class="spin small"></span> Calcolo il punteggio…</p>`;
  let r = null;
  try { r = await api("/api/quick/done", {method: "POST", body: {lang: it.lang, id: it.id, level: T.level, acc, hints: s.hints, plan: T.plan || "none", mode: T.mode, card: T.card ? T.card.id : null,
    blocks: T.sent = it.blocks.map((b, k) => ({err: s.blockErr[k] || 0, hints: (s.blockHint || {})[k] || 0, lvl: T.tr.lv(k)}))}}); }
  catch (e) { toast(e.message); }
  T.res = r;
  LOG.ev("quick_done", {id: it.id, title: it.title, tier: it.tier, lang: it.lang, mode: T.mode, level: T.level, acc, hints: s.hints, plan: T.plan,
    s: r ? r.s : null, delta: r ? r.delta : null, secs: secsSince(T.tWrite || T.t0), total: secsSince(T.t0)});
  if (App.Q !== T || !$("#qEnd")) return;
  if (r && r.elo && T.mode !== "review") $("#eloBox").innerHTML = eloHtml(r.elo);
  const pct = r ? Math.round(r.s * 100) : null;
  const when = r ? (r.grade === 2 ? "tra qualche giorno" : r.grade === 1 ? "domani" : "tra poche ore") : "";
  const rev = T.mode === "review" || T.fromReview;
  const tooHard = !!(r && T.level === 3 && r.revealed >= 20);
  $("#qEnd").innerHTML = `<div class="${r && r.s >= 0.6 ? "solved" : "banner"}"><b>${pct !== null ? `Punteggio ${pct}/100` : "Fatto"}${r && r.delta ? ` · livello ${r.delta > 0 ? "+" : ""}${r.delta}` : ""}</b>
    <span>Scritto al livello ${T.level} · ${LEVELS[T.level].name}, precisione ${acc}%, ${s.hints} ${s.hints === 1 ? "aiuto" : "aiuti"}${r && s.hints ? ` (${r.revealed}% delle parole)` : ""}${T.plan && PLAN_LABEL[T.plan] ? `, ${PLAN_LABEL[T.plan]}` : ""}. ${r ? `Tornerà come ripasso ${when}.` : ""}</span>
    ${tooHard ? `<p class="explain" style="margin:0"><b>Ti sei fatto mostrare ${r.revealed}% delle parole: a memoria è ancora presto.</b> Rifallo ora al livello 2: vedi la struttura e scrivi tu nomi e valori. Poi ritenta a memoria.</p>`
      : !rev && r && r.help ? `<p class="muted" style="margin:0;font-size:13px">${r.help > T.level ? `<b>Bene: il prossimo esercizio parte dal livello ${r.help} · ${LEVELS[r.help].name}.</b> ` : r.help < T.level ? `Il prossimo esercizio parte dal livello ${r.help} · ${LEVELS[r.help].name}. ` : ""}${T.level < 3 ? "Più il livello è alto, più punti prendi." : ""}</p>` : ""}
    <div class="fy-host" id="qFy"></div>
    <div class="row">
      ${tooHard ? `<button class="btn primary" data-q="down">Rifallo a livello 2 · Struttura</button>${rev ? `<button class="btn" data-q="nextCard">Avanti</button>` : `<button class="btn" data-q="next">Prossimo esercizio</button>`}`
      : rev ? `<button class="btn primary" data-q="nextCard">Avanti <kbd>Invio</kbd></button>` : `<button class="btn primary" data-q="variant">Variante da zero <kbd>Invio</kbd></button><button class="btn" data-q="next">Prossimo esercizio</button>
      ${T.level < 3 ? `<button class="btn" data-q="up">Rifallo a livello ${T.level + 1} · ${LEVELS[T.level + 1].name}</button>` : ""}`}
      <button class="btn ghost" data-q="predict">Prevedi ed esegui</button>
    </div><p class="muted" style="margin:0;font-size:12.5px">${rev ? "" : "La variante è un problema gemello da scrivere da zero, con test veri: dimostra che hai capito lo schema e non solo questo codice."}</p><div id="qRun"></div></div>`;
  T.fy = T.fy || (App.fyDone && App.fyDone[it.id]) || {phase: "write"};
  (App.fyDone = App.fyDone || {})[it.id] = T.fy;
  mountFeynman($("#qFy"), {st: T.fy, lang: it.lang, title: it.title, problem: it.problem || "", code: it.blocks.map(b => b.code).join("\n")});
  const fyIn = $("#qFy .fy-ans");
  if (fyIn) fyIn.focus(); else T.tr.focus();
  if (!rev) renderStartSide();
}
async function quickJudge() {
  const T = App.Q, it = T.item, p = it.plan, v = ($("#qPlanAns") || {}).value || "";
  T.draft = v;
  if (v.trim().length < 8) { toast("Scrivi almeno un'idea di come lo risolveresti."); return; }
  const b = $("#qJudge"); b.disabled = true; b.textContent = "Qwen legge il tuo piano…";
  try {
    const r = await api("/api/judge", {method: "POST", body: {question: `${it.problem}\n${p.q}`, reference: `${p.options[p.correct]}. Passi: ${(it.steps || []).join(" ")}`, why: p.why, answer: v}});
    T.judge = r;
    LOG.ev("plan_try", {id: it.id, title: it.title, how: "free", verdict: r.verdict, len: v.length, answer: v.slice(0, 300), comment: (r.comment || "").slice(0, 300)});
    if (r.verdict === "giusto") T.plan = T.tries ? "retry" : "free";
    else if (r.verdict === "parziale" && T.tries) T.plan = "partial";
    else T.tries++;
  } catch (e) { toast(e.message); }
  renderRagiona();
}
async function startClick(e) {
  const t = e.target.closest("button"); if (!t) return;
  if (t.dataset.ql) { App.qlang = t.dataset.ql; localStorage.setItem("ricalco.qlang", App.qlang); $$("[data-ql]").forEach(b => b.setAttribute("aria-pressed", String(b === t))); App.qSkip = []; renderStartSide(); if (!App.studyHome) loadQuick(); return; }
  if (t.dataset.pat) { App.qPattern = t.dataset.pat; App.studyHome = false; App.study = null; $("#quick").scrollIntoView({block: "start", behavior: "smooth"}); return loadQuick(App.Q ? App.Q.item.id : null); }
  if (t.dataset.ct) return ctClick(t);
  if (t.dataset.q === "weekly") return startWeekly();
  if (t.id === "retryStatus") { await refreshStatus(); $("#warn").innerHTML = ollamaBanner(); return; }
  const a = t.dataset.q;
  if (a === "review") return startHomeReview();
  if (a === "skipReview") { App.reviewSkipped = true; renderReviewBox(); return; }
  if (a === "endReview") return endHomeReview();
  const T = App.Q; if (!T) return;
  if (t.dataset.qopt !== undefined && T.phase === "ragiona") {
    const oi = +t.dataset.qopt;
    LOG.ev("plan_try", {id: T.item.id, title: T.item.title, how: "mc", ok: oi === T.item.plan.correct, answer: oi === T.item.plan.correct ? "" : String(T.item.plan.options[oi] || "").slice(0, 200), comment: oi === T.item.plan.correct ? "" : `Giusto era: ${T.item.plan.options[T.item.plan.correct]}`.slice(0, 300)});
    if (oi === T.item.plan.correct) T.plan = T.tries ? "retry" : "first";
    else { T.tries++; T.wrong.push(oi); }
    return renderRagiona();
  }
  if (a === "f4run") return freeRun();
  if (a === "f4done") return freeFinish(false);
  if (a === "f4give") {
    if (!t.dataset.armed) { t.dataset.armed = "1"; t.textContent = "Sicuro?"; return; }
    return freeFinish(true);
  }
  if (t.dataset.qv && T.phase !== "fatto") {
    if (+t.dataset.qv === 4 || T.level === 4) {
      if (T.level === 4 && T.f4 && T.f4.runs) { toast("Hai già eseguito il tuo codice: concludi o chiedi la soluzione."); return; }
      if (+t.dataset.qv === 4 && T.phase === "scrivi" && (T.k > 0 || T.stats.typed > 0)) { toast("Hai già iniziato a ricalcare: «Scrivi tu» si sceglie all'inizio dell'esercizio."); return; }
      LOG.ev("level_change", {id: T.item.id, from: T.level, to: +t.dataset.qv, block: T.k});
      T.level = +t.dataset.qv; T.bl = null; renderQuick(); return;
    }
    // una volta iniziato a scrivere non si torna a un livello più facile per sbirciare: per un aiuto c'è «Mostra parola»
    if (+t.dataset.qv < T.level && T.phase === "scrivi" && (T.k > 0 || T.stats.typed > 0)) {
      LOG.ev("peek_blocked", {id: T.item.id, from: T.level, to: +t.dataset.qv, block: T.k});
      toast("Niente sbirciatine: hai già iniziato a questo livello. Se sei bloccato usa «Mostra parola», oppure «Ricomincia».");
      T.tr.focus(); return;
    }
    LOG.ev("level_change", {id: T.item.id, from: T.level, to: +t.dataset.qv, block: T.k});
    T.level = +t.dataset.qv; T.bl = null; T.tr.setLevel(T.level, null);  // scelto a mano: vale per tutti i blocchi, senza adattamenti
    $$("[data-qv]").forEach(b => b.setAttribute("aria-pressed", String(b === t)));
    quickStatus(); T.tr.focus(); return;
  }
  if (t.id === "qHint") { T.tr.reveal(true); T.tr.focus(); return; }
  if (a === "mc") { T.free = false; return renderRagiona(); }
  if (a === "free") { T.free = true; return renderRagiona(); }
  if (a === "judge") return quickJudge();
  if (a === "showPlan") { T.plan = "shown"; return renderRagiona(); }
  if (a === "write") { LOG.ev("plan_done", {id: T.item.id, title: T.item.title, plan: T.plan, tries: T.tries, secs: secsSince(T.t0)}); T.tWrite = Date.now(); T.phase = "scrivi"; return renderQuick(); }
  if (a === "other") LOG.ev("skip", {id: T.item.id, title: T.item.title, phase: T.phase, secs: secsSince(T.t0)});
  if (a === "other") return (T.mode === "review" || T.fromReview) ? nextHomeCard() : loadQuick(T.item.id);
  if (a === "next") return loadQuick(T.item.id);
  if (a === "nextCard") return nextHomeCard();
  if (a === "restart" || a === "up" || a === "down") {
    LOG.ev("redo", {id: T.item.id, how: a, from: T.level});
    const lvl = a === "up" ? Math.min(3, T.level + 1) : a === "down" ? 2 : T.level;
    const done = T.phase === "fatto";
    startQuick(T.item, {mode: done ? "repeat" : T.mode, fromReview: T.fromReview || T.mode === "review", level: lvl, card: T.card, info: T.info, hist: done ? T.sent : T.hist});
    App.Q.plan = T.plan || "none"; App.Q.phase = "scrivi"; renderQuick(); return;
  }
  if (a === "predict") {
    $("#qRun").innerHTML = `<div class="predict"><span class="eyebrow">Prima di eseguire: cosa ${T.item.lang === "sql" ? "restituiranno le query" : "stamperà"}?</span>
      <textarea class="guess" id="qGuess" spellcheck="false" placeholder="${T.item.lang === "sql" ? "Una riga per ogni riga del risultato, valori separati da |" : "Una riga per ogni riga stampata"}"></textarea>
      <div class="row"><button class="btn primary" data-q="runcmp">Esegui e confronta</button><button class="linkish" data-q="run">Esegui senza prevedere</button></div></div>`;
    $("#qGuess").focus(); return;
  }
  if (a === "run" || a === "runcmp") {
    const guess = a === "runcmp" ? ($("#qGuess") || {}).value || "" : null;
    if (guess !== null && !guess.trim()) { toast("Scrivi la tua previsione."); return; }
    const out = $("#qRun"); out.innerHTML = `<p class="muted">Eseguo…</p>`;
    try {
      const r = await api("/api/run", {method: "POST", body: {lang: T.item.lang, mode: "program", code: T.item.blocks.map(b => b.code).join("\n")}});
      let cmp = "";
      if (guess !== null && r.ok) {
        const sql = T.item.lang === "sql";
        const real = sql ? sqlLines(String(r.stdout).split(/\n\s*\n/).map(ch => ch.split("\n").slice(1).join("\n")).join("\n")) : normOut(r.stdout).split("\n");
        const mine = sql ? sqlLines(guess) : normOut(guess).split("\n");
        const ok = mine.join("\n") === real.join("\n");
        LOG.ev("predict", {id: T.item.id, ok});
        cmp = ok ? `<p class="fb"><b>Previsione giusta.</b> Hai seguito il codice a mente.</p>`
          : `<p class="fb bad"><b>Non proprio.</b> Le righe evidenziate sono diverse: rileggi il blocco che le produce.</p>${outputDiff(real.join("\n"), mine.join("\n")).replace("Il tuo output", "La tua previsione")}`;
      }
      out.innerHTML = `${cmp}<pre class="out askable">${esc(r.stdout || "(nessun output)")}</pre>${r.ok ? "" : `<div class="res-err"><pre>${esc(r.error)}</pre></div>`}`;
    } catch (err) { out.innerHTML = `<div class="res-err">${esc(err.message)}</div>`; }
    return;
  }
  if (a === "variant") return startVariant(T);
}
document.addEventListener("keydown", e => {
  if (App.view !== "start" || !App.Q || App.Q.phase !== "ragiona") return;
  if (e.key === "Enter" && e.target.id === "qPlanAns" && !e.shiftKey) { e.preventDefault(); quickJudge(); }
});

/* ---- aiuto per blocco: dove l'ultima volta sei andato bene, meno aiuto; dove hai sbagliato, di più */
function blockLevels(hist, base, n) {
  if (!hist || hist.length !== n) return null;
  return hist.map(h => {
    if (h.err >= 4 || h.hints >= 2) return Math.max(1, base - 1);
    if (h.err <= 1 && !h.hints && h.lvl >= base) return Math.min(3, base + 1);
    return base;
  });
}

/* ---- schemi e prova settimanale (colonna sotto l'esercizio) */
function patternsHtml(list) {
  if (!list || !list.length) return `<p class="u-concepts">Fai qualche esercizio: qui vedrai gli schemi (hash map, due puntatori, ricorsione…) in cui vai forte e quelli da allenare.</p>`;
  return `<ul class="pats">${list.slice(0, 7).map((x, i) => `<li><div class="row"><b>${esc(x.name)}</b><span class="spacer"></span><span class="muted">${x.avg}/100</span></div>
      <div class="bar ${x.avg < 60 ? "weak" : ""}" title="Media recente dei punteggi su ${x.n} esercizi"><i style="width:${x.avg}%"></i></div>
      <small class="muted">${x.n} ${x.n === 1 ? "esercizio" : "esercizi"}${x.vn ? ` · varianti risolte ${x.vok}/${x.vn}` : ""}</small>
      ${i === 0 && list.length > 1 ? `<button class="btn small" data-pat="${x.id}">Allenati su questo</button>` : ""}</li>`).join("")}</ul>
    <small class="muted">Dal più debole al più forte. La home continua a scegliere da sola: «Allenati» cambia solo il prossimo esercizio.</small>`;
}
function weeklyChart(hist) {
  if (!hist.length) return "";
  const W = 260, H = 70, bw = Math.min(26, (W - 8) / hist.length - 4);
  const max = Math.max(...hist.map(h => Math.max(h.secs / 60, h.minutes || 0)), 1);
  const bars = hist.map((h, i) => {
    const m = h.secs / 60, bh = Math.max(3, m / max * (H - 18)), x = 4 + i * (bw + 4), y = H - 14 - bh;
    const d = new Date(h.t * 1000).toLocaleDateString("it-IT", {day: "numeric", month: "short"});
    return `<g><title>${d}: ${h.ok ? "risolto" : "non risolto"} in ${Math.round(m)} min${h.minutes ? ` (tempo previsto ${h.minutes})` : ""}</title>
      <rect x="${x}" y="${y}" width="${bw}" height="${bh}" rx="3" class="${h.ok ? "wk-ok" : "wk-ko"}"/>
      <text x="${x + bw / 2}" y="${H - 2}" text-anchor="middle" class="wk-lbl">${h.ok ? "✓" : "✗"}</text></g>`;
  }).join("");
  return `<svg class="wk-chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Minuti impiegati nelle ultime prove settimanali">${bars}</svg>
    <small class="muted">Minuti per prova, dalla più vecchia. ✓ risolta, ✗ non risolta.</small>`;
}
function weeklyHtml(w) {
  if (!w) return "";
  const last = w.hist[w.hist.length - 1];
  const head = w.due
    ? `<p class="u-concepts">Un problema mai visto, da scrivere da zero, senza aiuti e con il tempo. È il modo per sapere se migliori davvero.</p>
       <div class="row"><button class="btn primary small" data-q="weekly">Inizia la prova</button><span class="muted" style="font-size:12.5px">${w.ready ? "pronta" : App.status && App.status.model ? "la prepara Qwen: la prima volta ci vuole circa un minuto" : "serve Ollama acceso"}</span></div>`
    : `<p class="u-concepts">Prossima prova tra ${w.nextDays} ${w.nextDays === 1 ? "giorno" : "giorni"}.${last ? ` L'ultima: ${last.ok ? "risolta" : "non risolta"} in ${Math.round(last.secs / 60)} min.` : ""}</p>`;
  return head + weeklyChart(w.hist);
}

/* ---- esercizio da zero dentro la home: variante e prova settimanale */
async function startVariant(T) {
  const it = T.item, box = $("#quick");
  box.innerHTML = `${quickHead()}<div class="gen"><span class="spin"></span><div><p><b>Preparo la variante</b> <span class="timer" id="vTimer">0:00</span></p>
    <p class="muted" style="font-size:13.5px">Un problema gemello di «${esc(it.title)}»: stesso schema, obiettivo diverso. Ricalco esegue la soluzione sui test prima di dartelo.</p></div></div>`;
  timerEl($("#vTimer"));
  let d;
  const tw = Date.now();
  try { d = await api(`/api/quick/variant?lang=${it.lang}&id=${it.id}`); LOG.ev("wait", {what: "variante", secs: secsSince(tw)}); }
  catch (e) { box.insertAdjacentHTML("beforeend", `<div class="banner err"><b>Variante non pronta.</b><span>${esc(e.message)}</span><div class="row"><button class="btn small" data-q="next">Prossimo esercizio</button></div></div>`); return; }
  if (App.Q !== T) return;
  codeTask(d.exercise, {kind: "variant", lang: it.lang, label: "Variante da zero", sub: `Stesso schema di «${it.title}»`, hints: true,
    done: (res, secs) => api("/api/quick/variant_done", {method: "POST", body: {lang: it.lang, id: it.id, result: res, secs}}).then(r => { renderStartSide(); return r; }),
    after: (T.mode === "review" || T.fromReview) ? `<button class="btn primary" data-q="nextCard">Avanti</button>` : `<button class="btn primary" data-q="next">Prossimo esercizio</button>`});
}
async function startWeekly() {
  const lang = App.qlang, box = $("#quick");
  App.study = null; App.studyHome = false;
  $("#quick").scrollIntoView({block: "start", behavior: "smooth"});
  box.innerHTML = `<div class="gen"><span class="spin"></span><div><p><b>Preparo la prova settimanale</b> <span class="timer" id="vTimer">0:00</span></p>
    <p class="muted" style="font-size:13.5px">Un problema nuovo al tuo livello. Ricalco ne verifica la soluzione sui test prima di dartelo.</p></div></div>`;
  timerEl($("#vTimer"));
  let d;
  const tw = Date.now();
  try { d = await api(`/api/weekly?lang=${lang}&start=1`); LOG.ev("wait", {what: "prova settimanale", secs: secsSince(tw)}); }
  catch (e) { box.innerHTML = `<div class="banner err"><b>Prova non pronta.</b><span>${esc(e.message)}</span><div class="row"><button class="btn small" data-q="next">Torna agli esercizi</button></div></div>`; App.Q = App.Q || {item: {id: ""}}; return; }
  if (!d.exercise) { toast("La prova di questa settimana l'hai già fatta."); return loadQuick(); }
  App.Q = {item: {id: d.exercise.id, lang}, mode: "weekly", phase: "fatto"};
  codeTask(d.exercise, {kind: "weekly", lang, label: "Prova settimanale", sub: `Tempo previsto: ${d.exercise.minutes} minuti · niente aiuti`, hints: false, limit: d.exercise.minutes,
    done: (res, secs, tries, revealed) => api("/api/weekly/done", {method: "POST", body: {lang, ok: res !== "miss", secs, tries, revealed}}).then(r => { renderStartSide(); return r; }),
    after: `<button class="btn primary" data-q="next">Torna agli esercizi</button>`});
}
function codeTask(ex, o) {
  const box = $("#quick");
  ex.state = {tries: 0, hints: 0, solved: false, revealed: false, code: ex.starter || ""};
  const C = App.CT = {ex, o, t0: Date.now(), done: false};
  const sql = ex.check === "sql";
  box.innerHTML = `<div class="q-head"><span class="tag acc">${esc(o.label)} · ${QL[o.lang]}</span><h2>${esc(ex.title)}</h2><span class="spacer"></span>
      <span class="live-timer" id="ctTimer"></span></div>
    <p class="muted" style="margin:0;font-size:13px">${esc(o.sub)}</p>
    <p class="q-problem">${inl(ex.statement || "")}</p>
    ${sql ? dbHtml(ex, true) + (ex.expected ? `<details class="exp-out"><summary class="muted">Risultato atteso${ex.ordered ? " (in quest'ordine)" : ""}</summary>${sqlTable(ex.expected)}</details>` : "") : ex.tests ? testsPreview(ex) : ""}
    <div id="ctEditor"></div>
    <div class="row" id="ctActs"><button class="btn primary" data-ct="run" id="ctRun">${sql ? "Esegui la query" : "Esegui i test"}</button><span class="muted" style="font-size:12.5px"><kbd>Ctrl</kbd>+<kbd>Invio</kbd></span><span class="spacer"></span>
      ${o.hints && ex.hints && ex.hints.length ? `<button class="btn" data-ct="hint" id="ctHint">Suggerimento 1/${ex.hints.length}</button>` : ""}
      <button class="btn ghost" data-ct="reveal">${o.kind === "weekly" ? "Mi arrendo" : "Mostra la soluzione"}</button>
      ${o.kind === "variant" ? `<button class="linkish" data-ct="skip">Salta</button>` : ""}</div>
    <div id="ctHints"></div><div class="results" id="ctRes"></div><div id="ctEnd"></div>`;
  C.editor = makeEditor($("#ctEditor"), ex.state.code, {onChange: v => { ex.state.code = v; }, onRun: () => ctRun()});
  C.editor.focus();
  const tick = () => {
    const el = $("#ctTimer"); if (!el || App.CT !== C) return clearInterval(C.int);
    const sec = Math.round(((C.tEnd || Date.now()) - C.t0) / 1000);
    el.textContent = `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, "0")}${o.limit ? ` / ${o.limit}:00` : ""}`;
    el.classList.toggle("over", !!o.limit && sec > o.limit * 60);
  };
  tick(); C.int = setInterval(tick, 1000);
  Tutor.reset();
  Tutor.setContext(o.kind === "weekly"
    ? `Lo studente sta facendo la PROVA SETTIMANALE: deve risolvere da solo. Non dare indizi, metodi né codice: rispondi che durante la prova il tutor non aiuta e che potrete parlarne alla fine.`
    : `Variante da zero, stesso schema dell'esercizio appena ricalcato. Consegna: ${ex.statement}\nNON dare la soluzione: guida con domande e indizi.`, o.label);
  Tutor.setQuick(o.kind === "weekly" ? [] : ["Dammi un indizio", "Che differenza c'è con l'esercizio di prima?"]);
}
async function ctRun() {
  const C = App.CT; if (!C || C.done) return;
  const ex = C.ex, code = C.editor.get(), btn = $("#ctRun");
  btn.disabled = true; btn.textContent = "Eseguo…";
  try {
    let ok, html;
    if (ex.check === "sql") {
      const r = await api("/api/check_sql", {method: "POST", body: {setup: ex.setup, code, verify: ex.verify, expected: ex.expected, ordered: ex.ordered}});
      ok = r.ok; html = ok ? "" : sqlFailHtml(ex, r);
    } else {
      const r = await api("/api/run", {method: "POST", body: {lang: C.o.lang, mode: "tests", code, tests: ex.tests, tolerant: true}});
      ok = r.all_ok; html = resultsHtml(r);
      C.adapted = r.adapted || null;
      if (r.adapted) html = `<p class="fb">${r.adapted.map(esc).join(" ")}</p>` + html;
    }
    if (ok) { $("#ctRes").innerHTML = ""; return ctFinish(ex.state.tries ? "retry" : "first"); }
    ex.state.tries++;
    $("#ctRes").innerHTML = html;
  } catch (e) { toast(e.message); }
  if (btn.isConnected) { btn.disabled = false; btn.textContent = ex.check === "sql" ? "Esegui la query" : "Esegui i test"; }
}
async function ctFinish(result) {
  const C = App.CT, ex = C.ex, o = C.o;
  C.done = true; C.tEnd = Date.now();
  const secs = Math.round((C.tEnd - C.t0) / 1000);
  LOG.ev("code_task", {kind: o.kind, title: ex.title, lang: o.lang, result, secs, tries: ex.state.tries, hints: ex.state.hints});
  C.editor.ta.readOnly = true;
  $("#ctActs").remove();
  const ok = result !== "miss";
  $("#ctEnd").innerHTML = `<div class="${ok ? "solved" : "banner"}"><b>${ok ? (result === "first" ? "Risolto al primo colpo" : `Risolto in ${ex.state.tries + 1} tentativi`) : "Ecco la soluzione"}</b>
    <span>Tempo: ${Math.floor(secs / 60)} min ${secs % 60} s${o.limit ? ` su ${o.limit} previsti` : ""}. <span id="ctGain"></span></span>
    ${C.adapted ? `<p class="muted" style="margin:0;font-size:13px">${C.adapted.map(esc).join(" ")}</p>` : ""}
    <div id="ctReview"></div>
    <div class="rc-host" id="rcHost"></div><div class="fy-host" id="fyHost"></div><div class="row">${o.after}</div></div>`;
  const mine = (ex.state.code || "").trim();
  if (mine && mine !== (ex.starter || "").trim())
    mountReview($("#ctReview"), {lang: o.lang, task: ex.statement || ex.title, code: mine, reference: ex.solution || "",
      outcome: ok ? "Supera tutti i test." : "Non supera i test: lo studente si è arreso."});
  startSolutionRicalco(ex, o.lang, !ok);
  if (!ok && ex.solution) api("/api/rewrite_card", {method: "POST", body: {title: ex.title, explain: ex.statement || "", code: ex.solution, lang: o.lang, path: o.lang, src: ex.id}}).catch(() => {});
  try { const r = await o.done(result, secs, ex.state.tries, !ok); const g = $("#ctGain"); if (g && r && r.gain) g.textContent = `+${r.gain} XP`; } catch (e) { toast(e.message); }
}
function ctClick(t) {
  const C = App.CT; if (!C || C.done) return;
  const a = t.dataset.ct, ex = C.ex;
  if (a === "run") return ctRun();
  if (a === "hint") {
    ex.state.hints++;
    $("#ctHints").innerHTML = `<span class="eyebrow">Suggerimenti</span><ol class="hints">${ex.hints.slice(0, ex.state.hints).map(h => `<li>${inl(h)}</li>`).join("")}</ol>`;
    if (ex.state.hints >= ex.hints.length) t.disabled = true; else t.textContent = `Suggerimento ${ex.state.hints + 1}/${ex.hints.length}`;
    return;
  }
  if (a === "reveal") {
    if (!t.dataset.armed) { t.dataset.armed = "1"; t.textContent = "Sicuro?"; setTimeout(() => { if (t.isConnected) { delete t.dataset.armed; t.textContent = C.o.kind === "weekly" ? "Mi arrendo" : "Mostra la soluzione"; } }, 3500); return; }
    return ctFinish("miss");
  }
  if (a === "skip") { LOG.ev("code_task", {kind: C.o.kind, title: ex.title, result: "skip", secs: secsSince(C.t0), tries: ex.state.tries}); clearInterval(C.int); return App.Q && (App.Q.mode === "review" || App.Q.fromReview) ? nextHomeCard() : loadQuick(App.Q ? App.Q.item.id : null); }
}

/* ---- revisione del tuo codice: cosa va, cosa migliorare, una versione migliore */
function reviewHtml(r, lang) {
  return `<div class="review"><span class="eyebrow">La revisione di Qwen</span>
    <p class="explain"><b>${r.ok ? "Funziona." : "Non funziona ancora."}</b> ${inl(r.verdict)}</p>
    ${r.good.length ? `<p class="muted" style="margin:0;font-size:13px">Fatto bene</p><ul class="rv-good">${r.good.map(x => `<li>${inl(x)}</li>`).join("")}</ul>` : ""}
    ${r.fix.length ? `<p class="muted" style="margin:0;font-size:13px">Da migliorare</p><ul class="rv-fix">${r.fix.map(x => `<li>${inl(x)}</li>`).join("")}</ul>` : ""}
    ${r.better ? `<details class="rv-better"><summary>Una versione migliore, partendo dalla tua</summary><pre class="out askable">${esc(r.better)}</pre><p class="explain">${inl(r.why)}</p></details>` : ""}</div>`;
}
async function mountReview(host, o) {
  if (!host) return;
  host.innerHTML = `<p class="muted"><span class="spin small"></span> Qwen legge il tuo codice…</p>`;
  try {
    const r = await api("/api/code_review", {method: "POST", body: o});
    LOG.ev("code_review", {lang: o.lang, ok: r.ok, fixes: r.fix.length});
    if (host.isConnected) host.innerHTML = reviewHtml(r, o.lang);
    return r;
  } catch (e) { if (host.isConnected) host.innerHTML = `<p class="muted">Revisione non disponibile: ${esc(e.message)}</p>`; }
}

/* ---- ripasso in home: gli esercizi passati tornano come flashcard */
async function startHomeReview() {
  const d = await api("/api/cards/study", {method: "POST", body: {deck: "tutte"}});
  App.study = {deck: "tutte", queue: d.cards, done: 0, again: 0, flipped: false};
  App.studyHome = true;
  LOG.ev("review_start", {n: d.cards.length});
  renderReviewBox();
  $("#quick").scrollIntoView({block: "start", behavior: "smooth"});
  renderCard();
}
function nextHomeCard() {
  const S = App.study; if (!S) return endHomeReview();
  S.queue.shift(); S.done++; S.flipped = false;
  renderCard();
}
function endHomeReview() {
  const S = App.study;
  App.study = null; App.studyHome = false;
  LOG.ev("review_end", {done: S ? S.done : 0, left: S ? S.queue.length : 0});
  if (S && S.done) toast(`Ripasso: ${S.done} fatte.`);
  renderStartSide().then(() => loadQuick());
}

/* ================================================================ metodo Feynman: dopo ogni codice, spiegalo a un principiante */
function mountFeynman(host, o) {
  if (!host) return;
  const st = o.st;
  const dots = n => `<span class="dots">${[1, 2, 3, 4, 5].map(i => `<i class="${i <= n ? "on" : ""}"></i>`).join("")}</span>`;
  const head = `<div class="fy-head"><span class="eyebrow">Spiegalo a un principiante</span><span class="spacer"></span>${["write", "answer"].includes(st.phase) ? `<button class="linkish" data-fy="skip">Salta</button>` : ""}</div>`;
  let body = "";
  if (st.phase === "skipped") body = `<p class="muted" style="margin:0;font-size:13px">Spiegazione saltata. <button class="linkish" data-fy="reopen">Spiegalo ora</button></p>`;
  else if (st.phase === "write") body = `<p class="explain" style="margin:0">Scrivi come funziona la soluzione a qualcuno che non sa programmare: l'idea, perché questa struttura, cosa succede nel caso limite${o.lang === "sql" ? "" : ", quanto costa"}. Niente codice.</p>
    <textarea class="open-ans fy-ans" data-fyin="expl" placeholder="L'idea è… Uso … perché … Se la lista è vuota…">${esc(st.expl || "")}</textarea>
    <div class="row"><button class="btn primary" data-fy="send">Spiega</button><span class="muted" style="font-size:12.5px">Il principiante (Qwen) leggerà e ti farà domande sui punti vaghi.</span></div>`;
  else if (st.phase === "asking" || st.phase === "judging") body = `<p class="muted"><span class="spin small"></span> ${st.phase === "asking" ? "Il principiante legge la tua spiegazione…" : "Valuto la spiegazione…"}</p>`;
  else if (st.phase === "answer") body = `<div class="fy-you"><b>Tu:</b> ${esc(st.expl)}</div>
    <div class="fy-q"><b>Il principiante chiede:</b><ol>${st.qs.map(q => `<li>${inl(q)}</li>`).join("")}</ol></div>
    <textarea class="open-ans fy-ans" data-fyin="ans" placeholder="Rispondi alle domande con parole semplici">${esc(st.ans || "")}</textarea>
    <div class="row"><button class="btn primary" data-fy="answer">Rispondi</button></div>`;
  else if (st.phase === "done" && st.res) {
    const r = st.res, tot = r.clarity + r.complete + r.correct;
    body = `<div class="fy-res ${tot >= 12 ? "good" : tot >= 9 ? "mid" : "bad"}">
      <div class="fy-scores"><span>Chiarezza ${dots(r.clarity)}</span><span>Completezza ${dots(r.complete)}</span><span>Correttezza ${dots(r.correct)}</span></div>
      ${r.comment ? `<p class="explain">${inl(r.comment)}</p>` : ""}
      ${r.missing ? `<p class="explain"><b>Ti mancava:</b> ${inl(r.missing)} <span class="muted">(torna nel ripasso)</span></p>` : ""}
      ${r.model ? `<details><summary class="muted" style="cursor:pointer">Come lo spiegherebbe il tutor</summary><p class="explain">${inl(r.model)}</p></details>` : ""}
      <small class="muted">Valutazione del modello.</small></div>`;
  } else if (st.phase === "error") body = `<div class="res-err"><span>${esc(st.err || "")}</span><div class="row"><button class="btn small" data-fy="retry">Riprova</button><button class="linkish" data-fy="skip">Salta</button></div></div>`;
  host.innerHTML = `<div class="fy">${head}${body}</div>`;
  host.oninput = e => { const k = e.target.dataset.fyin; if (k) st[k] = e.target.value; };
  host.onkeydown = e => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey) && e.target.dataset.fyin) { e.preventDefault(); const b = $(st.phase === "write" ? '[data-fy="send"]' : '[data-fy="answer"]', host); if (b) b.click(); }
  };
  host.onclick = async e => {
    const b = e.target.closest("[data-fy]"); if (!b) return;
    const a = b.dataset.fy;
    const call = (stage, qa) => api("/api/feynman", {method: "POST", body: {stage, lang: o.lang, title: o.title, problem: o.problem, code: o.code, explanation: st.expl, qa}});
    if (a === "skip") { st.phase = "skipped"; LOG.ev("feynman_skip", {title: o.title}); return mountFeynman(host, o); }
    if (a === "reopen") { st.phase = "write"; mountFeynman(host, o); const t = $(".fy-ans", host); if (t) t.focus(); return; }
    const judge = async qa => {
      st.phase = "judging"; mountFeynman(host, o);
      try { st.res = await call("judge", qa); st.phase = "done"; } catch (err) { st.phase = "error"; st.err = err.message; st.retry = "judge"; }
      mountFeynman(host, o);
      if (st.phase === "done" && o.onDone) o.onDone(st.res);
    };
    if (a === "send" || (a === "retry" && st.retry === "ask")) {
      if ((st.expl || "").trim().length < 20) { toast("Scrivi almeno un paio di frasi."); return; }
      st.phase = "asking"; mountFeynman(host, o);
      try { const r = await call("ask", []); st.qs = r.questions; }
      catch (err) { st.phase = "error"; st.err = err.message; st.retry = "ask"; return mountFeynman(host, o); }
      if (!st.qs.length) return judge([]);
      st.phase = "answer"; mountFeynman(host, o);
      const t = $(".fy-ans", host); if (t) t.focus();
      return;
    }
    if (a === "answer" || (a === "retry" && st.retry === "judge")) {
      if (a === "answer" && (st.ans || "").trim().length < 5) { toast("Rispondi alle domande."); return; }
      return judge(st.qs && st.qs.length ? [{q: st.qs.join(" / "), a: st.ans}] : []);
    }
  };
}
function feynmanFor(ex, lang) {
  const host = $("#fyHost"); if (!host || !ex.solution) return;
  ex.state.fy = ex.state.fy || {phase: "write"};
  mountFeynman(host, {st: ex.state.fy, lang, title: ex.title, problem: ex.statement || "", code: ex.solution});
}
/* ================================================================ progetti a tappe */
async function showProjects() {
  App.view = "projects"; mainNav("progetti");
  const d = await api("/api/projects");
  $("#view").innerHTML = `<section class="path"><header class="path-head"><div><p class="eyebrow">Costruisci qualcosa di intero</p><h1>Progetti</h1>
      <p class="goal muted">Un programma vero, una tappa alla volta: ragioni sulla tappa, ricalchi il codice nuovo, lo esegui sul tuo PC, lo spieghi e lo modifichi a modo tuo. I file finiscono in una cartella che puoi aprire con il tuo editor e mettere su GitHub.</p></div></header>
    <div class="cat-grid">${d.projects.map(p => `<article class="cat pcard">
      <div class="u-title"><h3>${esc(p.title)}</h3><span class="tag acc">${LANG[p.lang]}</span></div>
      <p class="u-concepts">${esc(p.desc)}</p>
      <div class="bar" title="${p.done}/${p.steps} tappe"><i style="width:${Math.round(p.done / p.steps * 100)}%"></i></div>
      <p class="u-concepts">${p.done ? `${p.done} tappe su ${p.steps}` : `${p.steps} tappe`}${p.ready ? "" : p.kind === "maven" ? ` · serve Spring (Prova il modello → Prepara Spring)` : ` · serve <code>${esc(p.requires.join(" "))}</code>`}</p>
      <div class="row"><a class="btn small primary" href="#/progetto/${p.id}">${p.done ? (p.done >= p.steps ? "Rivedi" : "Continua") : "Inizia"}</a></div></article>`).join("")}</div></section>`;
  Tutor.setContext("Lo studente sceglie un progetto da costruire a tappe.", "Progetti");
  Tutor.setQuick([]);
}
async function showProject(id, step) {
  App.view = "project"; mainNav("progetti");
  const v = $("#view");
  v.innerHTML = `<section class="project"><div class="empty">Carico il progetto…</div></section>`;
  const d = await api(`/api/project?id=${id}${step !== undefined ? `&step=${step}` : ""}`);
  const S = d.step;
  const PR = App.PR = {d, S, k: S.n - 1, phase: "ragiona", tries: 0, wrong: [], order: shuffled(S.plan.options.length), op: 0,
    level: +(localStorage.getItem("ricalco.plevel") || 1), stats: {typed: 0, errors: 0, hints: 0}, t0: Date.now(), fy: {phase: "write"}};
  LOG.ev("project_step", {project: id, step: S.n, title: S.title});
  v.innerHTML = `<section class="project">
    <header class="path-head"><div><p class="eyebrow"><a href="#/progetti">Progetti</a> · ${esc(d.title)} · ${LANG[d.lang]}</p><h1>Tappa ${S.n} · ${esc(S.title)}</h1>
      <p class="goal">${inl(S.goal)}</p></div>
      <div class="seg small" role="group" aria-label="Livello di aiuto">${[1, 2, 3].map(l => `<button type="button" data-plv="${l}" aria-pressed="${PR.level === l}" title="${LEVELS[l].desc}"><span class="num">${l}</span>${LEVELS[l].name}</button>`).join("")}</div></header>
    <ol class="steps-strip">${d.titles.map((t, i) => `<li class="${i < d.done ? "done" : ""} ${i === PR.k ? "cur" : ""}">${i <= d.done ? `<a href="#/progetto/${id}/${i + 1}" title="${esc(t)}">${i + 1}</a>` : `<span title="${esc(t)}">${i + 1}</span>`}</li>`).join("")}</ol>
    ${d.ready ? "" : d.kind === "maven" ? `<div class="banner"><b>Per eseguire i test di questo progetto serve Spring preparato sul tuo PC.</b><span>Una volta sola: <a href="#/prova">Prova il modello → Prepara Spring</a>. Intanto puoi scrivere le tappe.</span></div>` : `<div class="banner"><b>Per eseguire questo progetto serve <code>${esc(d.requires.join(" "))}</code>.</b><span>Puoi installarlo da qui (una volta sola) oppure da terminale con <code>pip install ${esc(d.requires.join(" "))}</code>.</span><div class="row"><button class="btn small" data-pj="install">Installa ${esc(d.requires.join(" "))}</button><span class="muted" id="pjInstall"></span></div></div>`}
    <article class="quick" id="pjBox"></article>
  </section>`;
  v.onclick = projectClick;
  Tutor.reset();
  Tutor.setContext(`Progetto «${d.title}», tappa ${S.n}: ${S.title}. Obiettivo: ${S.goal}\nModifiche della tappa:\n${S.ops.map(o => `${o.file} (${o.where}): ${o.what}\n${o.code}`).join("\n\n")}`, `Progetto · tappa ${S.n}`);
  Tutor.setQuick(["Come si collega questa tappa alle precedenti?", "Cosa succederebbe se togliessi questa parte?"]);
  renderProject();
}
function renderProject() {
  const PR = App.PR, S = PR.S, box = $("#pjBox"); if (!box) return;
  if (PR.phase === "ragiona") {
    const p = S.plan, L = "ABCDE", solved = PR.plan;
    box.innerHTML = `<div class="step-head"><span class="n">1</span><h2>Ragiona sulla tappa</h2></div>
      <p class="q">${inl(p.q)}</p>
      ${solved ? `<div class="solved"><b>${PR.plan === "shown" ? "Ecco la risposta." : "Giusto."}</b><p class="explain">${inl(p.options[p.correct])}. ${inl(p.why)}</p>
          <div class="row"><button class="btn primary" data-pj="write" id="pjWrite">Scrivi il codice della tappa</button><span class="muted" style="font-size:12.5px">${S.ops.length} modifiche in ${[...new Set(S.ops.map(o => o.file))].length} file</span></div></div>`
        : `<div class="opts">${PR.order.map((oi, k) => `<button class="opt ${PR.wrong.includes(oi) ? "wrong" : ""}" data-pjopt="${oi}" ${PR.wrong.includes(oi) ? "disabled" : ""}><span class="k">${L[k]}</span><span>${inl(p.options[oi])}</span></button>`).join("")}</div>
          ${PR.tries ? `<div class="row"><p class="fb bad" style="flex:1"><b>Non è questa.</b> Ripensaci.</p><button class="btn ghost" data-pj="showPlan">Mostrami la risposta</button></div>` : ""}`}`;
    const w = $("#pjWrite"); if (w) w.focus();
    return;
  }
  if (PR.phase === "scrivi") {
    const o = S.ops[PR.op];
    box.innerHTML = `<div class="step-head"><span class="n">2</span><h2>Modifica ${PR.op + 1} di ${S.ops.length}</h2></div>
      <div class="strip">${S.ops.map((x, i) => `<span class="${i < PR.op ? "done" : i === PR.op ? "cur" : ""}"></span>`).join("")}</div>
      <div class="pj-where"><span class="tag acc" title="${esc(o.file)}">${esc(o.file.split("/").pop())}</span><span class="muted">${esc(o.where)}</span></div>
      ${o.before.length || o.removed.length ? `<pre class="pj-ctx">${o.before.map(l => `<span class="ctx">${esc(l) || " "}</span>`).join("\n")}${o.removed.length ? (o.before.length ? "\n" : "") + o.removed.map(l => `<span class="del">${esc(l) || " "}</span>`).join("\n") : ""}</pre>` : ""}
      <div class="q-task"><span class="lbl">Cosa fa</span><p class="explain">${inl(o.what)}</p></div>
      <div id="pjSheet"></div>
      <div id="pjWhy"></div>`;
    $("#pjSheet").innerHTML = sheetHtml(PR.level === 1 ? "Clicca sul foglio e ricalca" : PR.level === 2 ? "Clicca e ricostruisci nomi e valori" : "Clicca e scrivi a memoria");
    const tp = Date.now();
    rewriteTracer($("#pjSheet"), o.lang || PR.d.lang, o.code, st => {
      PR.stats.typed += st.typed; PR.stats.errors += st.errors; PR.stats.hints += st.hints;
      LOG.ev("project_op", {project: PR.d.id, step: S.n, op: PR.op + 1, file: o.file, secs: secsSince(tp), err: st.errors, hints: st.hints, level: PR.level});
      $("#pjWhy").innerHTML = `<div class="q-ex"><span class="lbl">Perché è scritto così</span><p class="explain">${inl(o.why)}</p></div>
        <div class="row"><button class="btn primary" data-pj="nextop" id="pjNext">${PR.op + 1 < S.ops.length ? "Prossima modifica" : "Concludi la tappa"} <kbd>Invio</kbd></button></div>`;
      $("#pjNext").focus();
    }, PR.level);
    return;
  }
  // fatto
  const tot = PR.stats.typed + PR.stats.errors, acc = tot ? Math.round(PR.stats.typed / tot * 100) : 100;
  const last = PR.k + 1 >= PR.d.titles.length, mvn = PR.d.kind === "maven";
  box.innerHTML = `<div class="step-head"><span class="n">3</span><h2>Tappa completata</h2></div>
    <p class="explain">Precisione ${acc}%, ${PR.stats.hints} aiuti, livello ${PR.level} · ${LEVELS[PR.level].name}. <span id="pjSaved" class="muted"><span class="spin small"></span> Salvo i file…</span></p>
    <div class="row">${mvn ? `<button class="btn primary" data-pj="run">Esegui i test</button><button class="btn" data-pj="start">Avvia l'API</button>` : PR.d.kind === "sql" ? `<button class="btn primary" data-pj="run">Esegui gli script</button>` : `<button class="btn primary" data-pj="run">Esegui sul tuo PC</button>`}<button class="btn" data-pj="open">Apri la cartella</button>
      ${last ? "" : `<a class="btn" href="#/progetto/${PR.d.id}/${PR.k + 2}">Prossima tappa</a>`}</div>
    <div id="pjRun"></div>
    <div class="fy-host" id="pjFy"></div>
    <div class="th-box"><span class="eyebrow">Tocca a te</span><p class="explain">${inl(S.challenge)}</p>
      <p class="muted" style="font-size:13px;margin:0">Lavora su una copia, così le tappe successive non toccano le tue modifiche: aprila con il tuo editor (per esempio VS Code), cambia il codice e premi «${mvn ? "Testa la tua copia" : "Esegui la tua copia"}».</p>
      <div class="row"><button class="btn" data-pj="copy">${PR.d.copyExists ? "Ricrea la copia da questa tappa" : "Crea la tua copia"}</button><button class="btn" data-pj="opencopy">Apri la copia</button><button class="btn" data-pj="runcopy">${mvn ? "Testa la tua copia" : "Esegui la tua copia"}</button></div>
      <div id="pjCopy" class="muted" style="font-size:13px"></div></div>
    <details class="pj-files"><summary class="muted">Tutti i file del progetto dopo questa tappa</summary>${Object.entries(S.files).map(([n, src]) => `<div><b class="db-name">${esc(n)}</b><pre class="out askable">${esc(src)}</pre></div>`).join("")}</details>`;
  mountFeynman($("#pjFy"), {st: PR.fy, lang: PR.d.lang, title: `${PR.d.title}, tappa ${S.n}: ${S.title}`, problem: S.goal, code: S.ops.map(o => `${o.lang === "python" ? "#" : o.lang === "sql" ? "--" : "//"} ${o.file}\n${o.code}`).join("\n\n")});
  api("/api/project/step_done", {method: "POST", body: {id: PR.d.id, step: PR.k, acc, level: PR.level}})
    .then(r => { PR.d.done = r.done; const el = $("#pjSaved"); if (el) el.innerHTML = `File salvati in <code>${esc(r.folder)}</code>.`; })
    .catch(e => { const el = $("#pjSaved"); if (el) el.textContent = e.message; });
  LOG.ev("project_step_done", {project: PR.d.id, step: S.n, acc, hints: PR.stats.hints, level: PR.level, secs: secsSince(PR.t0)});
  const f = $("#pjFy .fy-ans"); if (f) f.focus();
}
function sqlProjectHtml(r) {
  const one = o => `<div class="pj-out">${o.title ? `<b class="db-name">${esc(o.title)}</b>` : ""}${sqlTable(o)}${o.rows.length >= 200 ? `<small class="muted">prime 200 righe</small>` : ""}</div>`;
  const outs = r.outputs.map(one).join(""), old = r.outputs.slice(0, -3), last = r.outputs.slice(-3);
  if (!r.ok) return `<div class="res-err"><b>Errore${r.file ? ` in <code>${esc(r.file)}</code>` : ""}</b><pre>${esc(r.error)}</pre>${r.where ? `<small class="muted">Nell'istruzione:</small><pre class="out">${esc(r.where)}</pre>` : ""}</div>${outs ? `<details><summary class="muted" style="font-size:13px;cursor:pointer">I risultati prima dell'errore</summary>${outs}</details>` : ""}`;
  return `<p class="fb"><b>Eseguiti ${r.files.map(esc).join(", ")}.</b> ${r.outputs.length} ${r.outputs.length === 1 ? "risultato" : "risultati"}${r.db ? `, database salvato in <code>${esc(r.db)}</code> (si apre con DB Browser for SQLite o DBeaver)` : ""}.</p>${r.dbError ? `<p class="muted">${esc(r.dbError)}</p>` : ""}${old.length ? `<details><summary class="muted" style="font-size:13px;cursor:pointer">Le ${old.length} query precedenti</summary>${old.map(one).join("")}</details>` : ""}${last.map(one).join("")}`;
}
async function projectClick(e) {
  const PR = App.PR; if (!PR) return;
  const t = e.target.closest("button"); if (!t) return;
  if (t.dataset.plv) {
    PR.level = +t.dataset.plv; localStorage.setItem("ricalco.plevel", PR.level);
    $$("[data-plv]").forEach(b => b.setAttribute("aria-pressed", String(b === t)));
    if (PR.phase === "scrivi") renderProject();
    return;
  }
  if (t.dataset.pjopt !== undefined) {
    const oi = +t.dataset.pjopt;
    if (oi === PR.S.plan.correct) PR.plan = PR.tries ? "retry" : "first"; else { PR.tries++; PR.wrong.push(oi); }
    return renderProject();
  }
  const a = t.dataset.pj;
  if (a === "showPlan") { PR.plan = "shown"; return renderProject(); }
  if (a === "write") { PR.phase = "scrivi"; PR.op = 0; return renderProject(); }
  if (a === "nextop") { PR.op++; if (PR.op >= PR.S.ops.length) PR.phase = "fatto"; return renderProject(); }
  if (a === "install") {
    t.disabled = true; $("#pjInstall").innerHTML = `<span class="spin small"></span> Installo (può volerci un minuto)…`;
    try { const r = await api("/api/project/install", {method: "POST", body: {id: PR.d.id}}); $("#pjInstall").textContent = r.ok ? "Installato." : "Non riuscito: " + r.output.slice(-300); if (r.ok) PR.d.ready = true; }
    catch (err) { $("#pjInstall").textContent = err.message; }
    t.disabled = false; return;
  }
  if (a === "run" || a === "runcopy") {
    const out = $("#pjRun");
    out.innerHTML = PR.d.kind === "sql" ? `<p class="muted"><span class="spin small"></span> Eseguo gli script su SQLite…</p>`
      : PR.d.kind === "maven" ? `<p class="muted"><span class="spin small"></span> Maven compila ed esegue i test (la prima volta anche un paio di minuti)…</p>`
      : `<p class="muted"><span class="spin small"></span> Avvio il programma: si apre una finestra sul tuo PC…</p>`;
    t.disabled = true;
    try {
      const r = await api("/api/project/run", {method: "POST", body: {id: PR.d.id, copy: a === "runcopy"}});
      LOG.ev("project_run", {project: PR.d.id, step: PR.S.n, copy: a === "runcopy", ok: r.ok, running: r.running});
      out.innerHTML = r.kind === "sql" ? sqlProjectHtml(r)
        : r.kind === "maven" && r.missing ? `<div class="banner"><b>Spring non è ancora pronto sul tuo PC.</b><span><a href="#/prova">Prova il modello → Prepara Spring</a> (una volta sola).</span></div>`
        : r.kind === "maven" ? `${r.ok ? `<p class="fb"><b>Tutti i test passano.</b> ${r.result.tests.length} test in ${r.result.secs}s.</p>` : ""}${resultsHtml(r.result)}`
        : r.missing ? `<div class="banner"><b>Manca ${esc(r.missing.join(" "))}.</b><span>Installalo con il pulsante in alto oppure con <code>pip install ${esc(r.missing.join(" "))}</code>.</span></div>`
        : r.running ? `<p class="fb"><b>Il gioco è aperto in un'altra finestra.</b> Chiudila (o premi Q dalla tappa 6) per tornare qui.</p>${r.output ? `<pre class="out">${esc(r.output)}</pre>` : ""}`
        : r.ok ? `<p class="fb"><b>Il programma è terminato senza errori.</b></p>${r.output ? `<pre class="out">${esc(r.output)}</pre>` : ""}`
        : `<div class="res-err"><b>Il programma si è fermato con un errore</b><pre>${esc(r.error)}</pre><small class="muted">Selezionalo e premi «Cosa fa?» oppure chiedi al tutor di aiutarti a leggerlo.</small></div>`;
    } catch (err) { out.innerHTML = `<div class="res-err">${esc(err.message)}</div>`; }
    t.disabled = false;
    return;
  }
  if (a === "start") {
    try {
      const r = await api("/api/project/start", {method: "POST", body: {id: PR.d.id}});
      LOG.ev("project_start", {project: PR.d.id, step: PR.S.n});
      $("#pjRun").innerHTML = `<p class="fb"><b>L'API si sta avviando in una finestra a parte</b> (Maven, circa 10-20 secondi). Poi apri <a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.url)}</a>. Per fermarla premi Ctrl+C in quella finestra.</p>`;
    } catch (err) { toast(err.message); }
    return;
  }
  if (a === "open" || a === "opencopy") {
    try { const r = await api("/api/project/open", {method: "POST", body: {id: PR.d.id, copy: a === "opencopy"}}); toast("Cartella: " + r.path); }
    catch (err) { toast(err.message); }
    return;
  }
  if (a === "copy") {
    if (PR.d.copyExists && !t.dataset.armed) { t.dataset.armed = "1"; t.textContent = "Sicuro? Sovrascrive la tua copia"; return; }
    try { const r = await api("/api/project/copy", {method: "POST", body: {id: PR.d.id, force: true}}); PR.d.copyExists = true; $("#pjCopy").innerHTML = `La tua copia è in <code>${esc(r.path)}</code>.`; t.textContent = "Ricrea la copia da questa tappa"; delete t.dataset.armed; }
    catch (err) { toast(err.message); }
  }
}
document.addEventListener("keydown", e => {
  if (App.view !== "project" || !App.PR) return;
  if (e.key === "Enter" && e.target.id === "pjNext") return;
});
/* ================================================================ diario d'uso */
$("#noteBtn").onclick = () => { const f = $("#notePop"); f.hidden = !f.hidden; if (!f.hidden) $("#noteText").focus(); };
$("#noteClose").onclick = () => { $("#notePop").hidden = true; };
$("#notePop").onsubmit = e => {
  e.preventDefault();
  const v = $("#noteText").value.trim(); if (!v) return;
  const it = App.Q && App.view === "start" ? App.Q.item : null;
  LOG.ev("note", {text: v, where: $("#tutorCtx").textContent.replace(/^Contesto: /, "").slice(0, 100) || App.view, hash: location.hash, item: it ? it.title : null});
  LOG.flush();
  $("#noteText").value = ""; $("#notePop").hidden = true; toast("Nota salvata nel diario.");
};
async function showDiary() {
  App.view = "diary"; mainNav("");
  $("#view").innerHTML = `<section class="theory"><p class="eyebrow">Ultimi 14 giorni</p><h1>Diario d'uso</h1><div id="diaryBody"><div class="empty">Leggo i log…</div></div></section>`;
  Tutor.setContext("Lo studente guarda il diario d'uso di Ricalco: statistiche su come si allena.", "Diario d'uso");
  Tutor.setQuick([]);
  const d = await api("/api/logs/summary?days=14");
  const T = d.totals, L = d.llm, P = d.phases;
  const pct = (a, b) => b ? Math.round(a / b * 100) + "%" : "—";
  const n = v => v === null || v === undefined ? "—" : v;
  $("#diaryBody").innerHTML = `
    <p class="explain">Tutto quello che fai in Ricalco viene registrato in <code>data/logs/</code>, solo sul tuo PC. Qui sotto c'è il riassunto: serve a capire dove ti blocchi, dove perdi tempo e quanto è lento il modello. Con il pulsante <b>Nota</b> in alto puoi annotare al volo cosa non va.</p>
    <div class="kpis diary-kpis">
      <div class="stat"><b>${T.activeDays}</b><span>Giorni attivi</span></div>
      <div class="stat"><b>${T.activeMin}</b><span>Minuti di lavoro</span></div>
      <div class="stat"><b>${T.done}</b><span>Esercizi di Oggi</span></div>
      <div class="stat"><b>${n(T.avg)}</b><span>Punteggio medio</span></div>
      <div class="stat"><b>${pct(T.variantsOk, T.variants)}</b><span>Varianti risolte (${T.variants})</span></div>
      <div class="stat"><b>${pct(T.predictOk, T.predict)}</b><span>Previsioni giuste (${T.predict})</span></div>
      <div class="stat"><b>${T.skips}</b><span>Esercizi saltati</span></div>
      <div class="stat"><b>${T.tutor}</b><span>Domande al tutor</span></div>
    </div>
    ${d.days.length ? `<div class="cmp-wrap"><table class="cmp st"><tr><th>Giorno</th><th>Minuti</th><th>Esercizi Oggi</th><th>Media</th><th>Saltati</th><th>Aiuti</th><th>Varianti</th><th>Esercizi percorso</th></tr>
      ${d.days.slice().reverse().map(r => `<tr><td>${esc(r.day)}</td><td>${r.min}</td><td>${r.done}</td><td>${n(r.avg)}</td><td>${r.skips}</td><td>${r.hints}</td><td>${r.variants}</td><td>${r.exercises}</td></tr>`).join("")}</table></div>`
      : `<div class="empty">Ancora nessun dato: torna qui dopo qualche esercizio.</div>`}
    <div class="home-grid">
      <div class="th-box"><span class="eyebrow">Dove passi il tempo</span><ul>
        <li>Ragionare sul piano: in media ${n(P.ragiona)} s per esercizio${P.plans ? ` · piano giusto da solo ${pct(P.planFirst, P.plans)}, piano guardato ${pct(P.planShown, P.plans)}` : ""}.</li>
        <li>Scrivere il codice: in media ${n(P.scrivi)} s per esercizio.</li>
        ${d.waits.map(w => `<li>Attesa per ${esc(w.what)}: ${w.n} ${w.n === 1 ? "volta" : "volte"}, in media ${w.avg} s (al massimo ${w.max} s).</li>`).join("")}</ul></div>
      <div class="th-box"><span class="eyebrow">Il modello (${esc((App.status && App.status.model) || "")})</span><ul>
        <li>${L.n} richieste, ${L.fail} non riuscite. Tempo medio ${n(L.avg)} s, il 90% sotto ${n(L.p90)} s.</li>
        <li>Quando aspetti tu: in media ${n(L.fgAvg)} s. Tutor: prima parola dopo ${n(L.tutorFirst)} s.</li>
        <li>Esercizi preparati in sottofondo: ${L.gen}, in media ${n(L.genAvg)} s l'uno, ${L.genFail} falliti.</li></ul>
        ${L.kinds.length ? `<details><summary class="muted" style="cursor:pointer">Per tipo di richiesta</summary><ul>${L.kinds.map(k => `<li>${esc(k.what)}… · ${k.n} · ${n(k.avg)} s${k.fail ? ` · ${k.fail} fallite` : ""}</li>`).join("")}</ul></details>` : ""}</div>
    </div>
    <div class="th-box warnbox"><span class="eyebrow">Errori di ragionamento · prima di scrivere il codice</span>
      ${d.reasoning && d.reasoning.length ? `<p class="muted" style="margin:0;font-size:13px">Il metodo sbagliato o incompleto, le spiegazioni deboli, le domande di ragionamento sbagliate: sono gli errori che contano di più al colloquio.</p>
      <ul class="reason">${d.reasoning.slice(0, 20).map(r => `<li><b>«${esc(r.title)}»</b> · ${esc(r.kind)}: ${esc(r.what)} <span class="muted">${esc(r.t)}</span>
        ${r.answer ? `<div class="muted">Hai risposto: «${esc(r.answer)}»</div>` : ""}${r.comment ? `<div>${inl(r.comment)}</div>` : ""}</li>`).join("")}</ul>`
      : `<p class="muted" style="margin:0">Nessun errore di ragionamento in questi giorni.</p>`}</div>
    ${d.hardBlocks.length ? `<div class="th-box warnbox"><span class="eyebrow">Blocchi più difficili · errori di battitura</span><ul>${d.hardBlocks.map(b => `<li>«${esc(b.title)}», blocco ${b.k + 1}: ${b.err} errori, ${b.hints} aiuti${b.secs ? `, ${b.secs} s` : ""}</li>`).join("")}</ul></div>` : ""}
    ${d.skipped.length ? `<div class="th-box"><span class="eyebrow">Esercizi saltati</span><ul>${d.skipped.map(x => `<li>${esc(x.title)}${x.n > 1 ? ` (${x.n} volte)` : ""}</li>`).join("")}</ul></div>` : ""}
    <div class="th-box"><span class="eyebrow">Le tue note</span>${d.notes.length ? `<ul>${d.notes.map(x => `<li><b>${esc(x.t)}</b> · <span class="muted">${esc(x.where)}</span><br>${esc(x.text)}</li>`).join("")}</ul>` : `<p class="explain">Nessuna nota. Quando qualcosa ti blocca o ti annoia, premi <b>Nota</b> in alto e scrivilo in una riga.</p>`}</div>
    ${d.errors.length ? `<div class="th-box warnbox"><span class="eyebrow">Errori dell'app</span><ul>${d.errors.map(x => `<li>${esc(x.t)} · ${esc(x.msg)}</li>`).join("")}</ul></div>` : ""}
    <div class="row"><button class="btn primary" id="logExport">Esporta i log</button><span class="muted" style="font-size:13px">Un file .jsonl degli ultimi 30 giorni: puoi mandarmelo per analizzarlo insieme.</span></div>`;
  $("#logExport").onclick = async () => {
    LOG.flush();
    const r = await fetch("/api/logs/export", {headers: {"X-Ricalco": "1"}});
    const blob = await r.blob(), a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = `ricalco-log-${new Date().toISOString().slice(0, 10)}.jsonl`; a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  };
}
/* ================================================================ avvio */
Tutor.render();
refreshStatus().then(() => { if ($("#warn")) $("#warn").innerHTML = ollamaBanner(); if (App.view === "path") refreshPath(true); if (App.view === "start" && App.Q) quickStatus(); });
route();
