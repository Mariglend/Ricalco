"use strict";

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
    level: +(localStorage.getItem("ricalco.plevel") || 1), stats: {typed: 0, errors: 0, hints: 0}, skipped: [], t0: Date.now(), fy: {phase: "write"}};
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
    const o = S.ops[PR.op], nl = o.code.split("\n").length, long = nl > 20;
    box.innerHTML = `<div class="step-head"><span class="n">2</span><h2>Modifica ${PR.op + 1} di ${S.ops.length}</h2>
        <span class="spacer"></span><button class="btn small ${long ? "" : "ghost"}" data-pj="skipop" title="Il codice viene scritto lo stesso nei file del progetto: passi solo alla modifica dopo">${PR.op + 1 < S.ops.length ? "Salta questa modifica" : "Salta e concludi la tappa"}</button></div>
      <div class="strip">${S.ops.map((x, i) => `<span class="${PR.skipped.includes(i) ? "skip" : i < PR.op ? "done" : i === PR.op ? "cur" : ""}"></span>`).join("")}</div>
      <div class="pj-where"><span class="tag acc" title="${esc(o.file)}">${esc(o.file.split("/").pop())}</span><span class="muted">${esc(o.where)} · ${nl} ${nl === 1 ? "riga" : "righe"}</span></div>
      ${long ? `<p class="muted pj-long">Codice lungo: se è una parte che conosci già o solo da copiare, puoi saltarla. Nei file del progetto finisce lo stesso.</p>` : ""}
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
    <p class="explain">Precisione ${acc}%, ${PR.stats.hints} aiuti, livello ${PR.level} · ${LEVELS[PR.level].name}${PR.skipped.length ? ` · ${PR.skipped.length} ${PR.skipped.length === 1 ? "modifica saltata" : "modifiche saltate"}` : ""}. <span id="pjSaved" class="muted"><span class="spin small"></span> Salvo i file…</span></p>
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
  if (a === "skipop") {
    const o = PR.S.ops[PR.op];
    PR.skipped.push(PR.op);
    LOG.ev("project_skip", {project: PR.d.id, step: PR.S.n, op: PR.op + 1, file: o.file, lines: o.code.split("\n").length});
    PR.op++; if (PR.op >= PR.S.ops.length) PR.phase = "fatto";
    return renderProject();
  }
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
