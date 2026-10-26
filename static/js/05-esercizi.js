"use strict";

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
