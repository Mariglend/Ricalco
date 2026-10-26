"use strict";

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
        <button class="btn small" id="skipBlockBtn" title="Il blocco resta nel programma: passi solo al blocco dopo">Salta il blocco</button>
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
  const nSkip = Object.keys(p.skipped || {}).length, skipTxt = nSkip ? ` · ${nSkip} ${nSkip === 1 ? "blocco saltato" : "blocchi saltati"}` : "";
  $("#lstatus").textContent = p.done ? `Lezione completata · precisione ${acc}${skipTxt}` :
    `Blocco ${p.block + 1} di ${n} · ${p.phase === "ragiona" ? "ragiona" : p.phase === "rivedi" ? "scritto" : "scrivi"} · precisione ${acc} · aiuti ${s.hints}`;
  $("#sheet").classList.toggle("compact", p.phase !== "scrivi");
  const hint = $("#sheetHint");
  hint.className = "sheet-hint" + (p.phase === "scrivi" ? " when-blur" : "");
  hint.textContent = p.done ? "Lezione completata" : p.phase === "ragiona" ? "Rispondi alla domanda qui sotto per sbloccare il blocco" : p.phase === "rivedi" ? "Riscrivilo più difficile o premi Invio per andare avanti" : "Clicca sul foglio e scrivi";
  $("#hintBtn").hidden = (p.redoLevel || App.traceLevel) === 1 || p.phase !== "scrivi";
  // saltare un blocco si può quando impari (livelli 1 e 2), non nella riscrittura a memoria che fissa l'unità
  const sk = $("#skipBlockBtn"), cur = L.blocks[p.block];
  sk.hidden = p.done || !cur || !["ragiona", "scrivi"].includes(p.phase) || App.traceLevel >= 3 || !!p.redoLevel;
  if (cur && !sk.hidden) {
    const nl = cur.code.split("\n").length;
    sk.textContent = `Salta il blocco (${nl} ${nl === 1 ? "riga" : "righe"})`;
    sk.classList.toggle("ghost", nl <= 15);
  }
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
  if (t.id === "skipBlockBtn") {
    p.skipped = p.skipped || {}; p.skipped[k] = true;
    LOG.ev("lesson_skip", {lesson: L.id, title: L.title, k, lines: L.blocks[k].code.split("\n").length});
    advanceBlock(k); return;
  }
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
