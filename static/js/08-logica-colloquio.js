"use strict";

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
    <p class="goal muted">Un colloquio tecnico ha più parti: domande di teoria che scavano, problemi di codice, progettazione, lettura del codice altrui e domande su di te. Allenale una per una, poi mettile insieme in una simulazione.</p></div></header>
    <div class="int-modes">
      <a class="cat cat-link" href="#/colloquio/domande"><h3>Domande a catena</h3><p class="u-concepts">Domande vere su Java, Spring, SQL, web, Python e fondamenti. Se rispondi bene il selezionatore scava, finché trova il tuo limite.</p></a>
      <a class="cat cat-link" href="#/algoritmi"><h3>Algoritmi</h3><p class="u-concepts">I problemi che tornano nei colloqui, divisi per schema, in Python e Java.</p></a>
      <a class="cat cat-link" href="#/colloquio/design"><h3>System design</h3><p class="u-concepts">Progetta un piccolo sistema: entità, endpoint, casi limite. Valutazione con una griglia e domande di approfondimento.</p></a>
      <a class="cat cat-link" href="#/colloquio/review"><h3>Code review</h3><p class="u-concepts">Trova bug, falle di sicurezza e problemi di prestazioni in codice Java, Python e SQL.</p></a>
      <a class="cat cat-link" href="#/colloquio/soft"><h3>Comportamentali</h3><p class="u-concepts">«Raccontami un bug difficile»: risposte con il metodo STAR, in italiano o in inglese.</p></a>
    </div>
    <h2 class="section-title">Simulazione completa, live coding e domande generate</h2>
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
