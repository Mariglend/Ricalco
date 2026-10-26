"use strict";

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
