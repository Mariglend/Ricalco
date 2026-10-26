"use strict";

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
