"use strict";

/* ================================================================ percorso */
const LEVEL_NAMES = {base: "Base", pratica: "Pratica", sfida: "Sfida"};
const MODE_NOTE = {
  output: "Si esegue il programma e si confronta l'output.",
  tests: "Il tuo codice viene eseguito contro dei test.",
  review: "Codice non eseguibile qui: lo valuta il modello."
};
const stars = n => `<span class="stars" aria-label="${n} stelle su 3">${[1, 2, 3].map(i => `<i class="${i <= n ? "on" : ""}">★</i>`).join("")}</span>`;
let pathTimer = null;

/* Barra laterale: le sezioni raggruppate per quello che fai (imparare, allenarti, prepararti al colloquio). */
const NAV = [
  [null, [["home", "#/", "Oggi"]]],
  ["Impara", [["percorso", "#/percorso", "Percorsi"], ["progetti", "#/progetti", "Progetti"], ["libere", "#/libere", "Lezioni libere"]]],
  ["Allenati", [["algoritmi", "#/algoritmi", "Algoritmi"], ["logica", "#/logica", "Logica"], ["carte", "#/carte", "Flashcard"]]],
  ["Colloquio", [["colloquio", "#/colloquio", "Panoramica"], ["c-domande", "#/colloquio/domande", "Domande a catena"], ["c-design", "#/colloquio/design", "System design"],
                 ["c-review", "#/colloquio/review", "Code review"], ["c-soft", "#/colloquio/soft", "Comportamentali"]]],
  ["Strumenti", [["diario", "#/diario", "Diario"], ["prova", "#/prova", "Prova il modello"]]],
];
function mainNav(active) {
  const side = $("#side");
  if (!side.dataset.ready) {
    side.innerHTML = NAV.map(([g, items]) => `<div class="side-group">${g ? `<p class="side-label">${g}</p>` : ""}${items.map(([id, h, l]) =>
      `<a href="${h}" data-nav="${id}"><span>${l}</span><i class="side-badge" data-badge="${id}" hidden></i></a>`).join("")}</div>`).join("");
    side.dataset.ready = "1";
  }
  side.querySelectorAll("[data-nav]").forEach(a => { if (a.dataset.nav === active) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current"); });
  $("#crumbs").innerHTML = "";
  document.body.classList.remove("side-open"); $("#sideBtn").setAttribute("aria-expanded", "false");
}
function navBadge(id, n) {
  const b = document.querySelector(`[data-badge="${id}"]`); if (!b) return;
  b.hidden = !n; b.textContent = n > 99 ? "99+" : String(n || "");
}
document.addEventListener("click", e => {
  if (document.body.classList.contains("side-open") && !e.target.closest("#side, #sideBtn")) { document.body.classList.remove("side-open"); return; }
  if (!e.target.closest("#sideBtn")) return;
  const open = document.body.classList.toggle("side-open");
  $("#sideBtn").setAttribute("aria-expanded", String(open));
});
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
