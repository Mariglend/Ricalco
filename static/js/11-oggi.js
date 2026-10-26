"use strict";

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
async function showStart(opts = {}) {
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
    <div id="planBox"></div>
    <div id="reviewBox"></div>
    <article class="quick" id="quick"><div class="empty">Preparo l'esercizio…</div></article>
    <div id="startSide"></div>
  </section>`;
  v.onclick = startClick;
  await renderStartSide();
  if (!opts.noPick) loadQuick();
}
async function renderStartSide() {
  let H;
  try { H = await api("/api/home"); } catch (e) { return; }
  App.H = H;
  navBadge("carte", H.cardsDue);
  if (App.view !== "start") return;
  renderReviewBox();
  const box = $("#startSide"); if (!box) return;
  const order = ["python", "java", "sql", "algopy", "algojava"];
  const ps = order.map(id => H.paths.find(p => p.id === id)).filter(Boolean);
  const pl = H.plan || {}, cur = ps.find(p => p.started && p.unit) || ps.find(p => p.unit), al = pl.algo && (pl.algo[App.qlang] || pl.algo.python);
  const plan = [
    H.cardsDue ? {h: "#/carte", k: "Ripasso", t: `${H.cardsDue} ${H.cardsDue === 1 ? "carta" : "carte"} da ripassare`, d: "Prima il ripasso: è quello che ti fa ricordare."} : null,
    cur ? {h: `#/percorso/${cur.id}`, k: "Percorso", t: `${esc(cur.name)} · ${esc(cur.unit.title)}`, d: cur.unit.step === 1 ? "La lezione da imparare." : "Da riscrivere a memoria per fissarla."} : null,
    al ? {h: `#/oggi/${pl.algo[App.qlang] ? App.qlang : "python"}/${al.id}`, k: "Algoritmo", t: esc(al.title), d: `Il prossimo del catalogo · livello ${al.tier}`} : null,
    {h: "#/colloquio/domande", k: "Colloquio", t: pl.bankDue ? `${pl.bankDue} domande da ripassare` : "Una domanda a catena", d: pl.bankDone ? "Dove ti eri fermato presto." : "Scopri fin dove reggi."},
  ].filter(Boolean);
  const pb = $("#planBox");
  if (pb) pb.innerHTML = `<h2 class="section-title">Il piano di oggi</h2>
    <div class="plan">${plan.map(x => `<a class="plan-item" href="${x.h}"><span class="eyebrow">${x.k}</span><b>${x.t}</b><small class="muted">${x.d}</small></a>`).join("")}</div>
    <h2 class="section-title">Allenamento</h2>`;
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
