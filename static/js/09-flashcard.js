"use strict";

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
