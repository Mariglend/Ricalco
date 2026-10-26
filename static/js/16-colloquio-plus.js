"use strict";

/* ================================================================ colloquio approfondito
   Domande a catena (il selezionatore scava finché trova il limite), system design, code review, domande comportamentali.
   I contenuti sono fissi e controllati; Qwen valuta solo le risposte. */
const intEn = () => (App.intLang || localStorage.getItem("ricalco.intlang") || "it") === "en";
const verdictCls = s => s >= 4 ? "" : s >= 3 ? "mid" : "bad";
function listHtml(title, xs, cls = "") { return xs && xs.length ? `<div class="jl ${cls}"><span class="lbl">${title}</span><ul>${xs.map(x => `<li>${inl(x)}</li>`).join("")}</ul></div>` : ""; }
function intHead(eyebrow, title, goal) {
  return `<header class="path-head"><div><p class="eyebrow"><a href="#/colloquio">Colloquio</a> · ${eyebrow}</p><h1>${title}</h1><p class="goal muted">${goal}</p></div></header>`;
}

/* ---- domande a catena */
async function showBank() {
  App.view = "bank"; mainNav("c-domande");
  const v = $("#view");
  v.innerHTML = `<section class="path">${intHead("Domande a catena", "Domande a catena",
    "Come in un colloquio vero: rispondi, e se la risposta regge il selezionatore scava con un «perché?» o un «e se…?», finché trova il tuo limite. Le domande dove ti fermi presto tornano prima.")}
    <div id="bankBody"><div class="empty">Caricamento…</div></div></section>`;
  Tutor.setContext("Lo studente si allena con le domande a catena del colloquio tecnico.", "Domande a catena");
  Tutor.setQuick(["Come rispondo quando non so una cosa?", "Come strutturo una risposta tecnica?"]);
  const d = await api("/api/bank");
  if (App.view !== "bank") return;
  $("#bankBody").innerHTML = `<div class="kpis home-kpis"><div class="stat"><b>${d.fatte}</b><span>Domande fatte</span></div><div class="stat"><b>${d.totale}</b><span>Nella banca</span></div>
      <div class="stat"><b>${d.aree.reduce((s, a) => s + a.due, 0)}</b><span>Da ripassare</span></div></div>
    <div class="cat-grid">${d.aree.map(a => `<article class="cat">
      <div class="u-title"><h3>${esc(a.name)}</h3>${a.due ? `<span class="tag wait">${a.due} da ripassare</span>` : ""}</div>
      <div class="bar"><i style="width:${Math.round(a.fatte / a.n * 100)}%"></i></div>
      <p class="u-concepts">${a.fatte} di ${a.n} fatte${a.media !== null ? ` · arrivi in media a ${a.media}/5 della catena` : ""}</p>
      <div class="u-levels">${a.livelli.map(l => `<a class="lvl ${l.fatte ? "done" : ""}" href="#/colloquio/domande/${a.id}/${l.id}"><b>${l.name}</b><small>${l.fatte}/${l.n}</small></a>`).join("")}</div>
      <div class="row"><a class="btn small primary" href="#/colloquio/domande/${a.id}">Allenati su ${esc(a.name)}</a></div></article>`).join("")}</div>
    ${d.deboli.length ? `<h2 class="section-title">Dove ti fermi presto</h2><ol class="weak">${d.deboli.map(w => `<li><a href="#/colloquio/domande/q/${w.id}"><span class="tag">${esc(w.area)}</span> ${inl(w.q)}</a> <span class="muted">· ${w.score}/5</span></li>`).join("")}</ol>` : ""}`;
}
async function bankSession(area, level, qid) {
  App.view = "bankq"; mainNav("c-domande");
  App.B = {area, level, skip: [], qid};
  Tutor.setQuick(["Come rispondo quando non so una cosa?", "Come strutturo una risposta tecnica?"]);
  $("#view").innerHTML = `<section class="path bank">${intHead("Domande a catena", "Domande a catena", "Rispondi come faresti a voce: frasi complete, un esempio se ti viene. <b>Non lo so</b> è una risposta onesta: chiude la catena e ti mostra quella giusta.")}
    <article class="quick" id="bankBox"><div class="empty">Scelgo la domanda…</div></article></section>`;
  $("#view").onclick = bankClick;
  await bankNext();
}
async function bankNext() {
  const B = App.B, box = $("#bankBox"); if (!box) return;
  box.innerHTML = `<div class="empty">Scelgo la domanda…</div>`;
  let q;
  try { q = await api(`/api/bank/next?area=${B.area || ""}${B.level ? `&level=${B.level}` : ""}&skip=${B.skip.join(",")}${B.qid ? `&id=${B.qid}` : ""}`); B.qid = null; }
  catch (e) { box.innerHTML = `<div class="banner err">${esc(e.message)}</div>`; return; }
  if (App.view !== "bankq") return;
  B.q = q; B.step = 0; B.chain = [{q: q.q}]; B.skip.push(q.id); B.skip = B.skip.slice(-20);
  Tutor.setContext(`Colloquio, domanda: «${q.q}». NON dare la risposta: se lo studente chiede aiuto, fai domande che lo guidino.`, `Domanda · ${q.area}`);
  renderBank();
}
function renderBank() {
  const B = App.B, q = B.q, box = $("#bankBox"); if (!box) return;
  const dots = Array.from({length: q.catena + 1}, (_, i) => `<span class="${i < B.step ? "done" : i === B.step && !B.ended ? "cur" : B.chain[i] && B.chain[i].r ? (B.chain[i].r.score >= 3 ? "done" : "bad") : ""}"></span>`).join("");
  const past = B.chain.map((c, i) => c.r ? `<div class="chain-step">
      <p class="q"><span class="tag ${i ? "wait" : "acc"}">${i ? "Approfondimento " + i : "Domanda"}</span> ${inl(c.q)}</p>
      <p class="your muted"><b>Tu:</b> ${esc(c.a || "(non lo so)")}</p>
      <p class="fb ${verdictCls(c.r.score)}"><b>${c.r.score}/5.</b> ${inl(c.r.comment)}</p>
      ${listHtml("Hai toccato", c.r.covered, "ok")}${listHtml("Mancava", c.r.missing, "miss")}
      ${c.r.language ? `<p class="fb mid"><b>Inglese:</b> ${inl(c.r.language)}</p>` : ""}
      <details><summary class="muted">Risposta modello</summary><p class="explain">${inl(c.r.model)}</p>${c.r.trap ? `<p class="muted"><b>Trappola tipica:</b> ${inl(c.r.trap)}</p>` : ""}</details>
    </div>` : "").join("");
  const cur = B.ended ? "" : `<div class="chain-step now">
      <p class="q"><span class="tag ${B.step ? "wait" : "acc"}">${B.step ? "Il selezionatore scava · " + B.step : "Domanda"}</span> ${inl(B.chain[B.step].q)}</p>
      <textarea class="open-ans" id="bankAns" placeholder="${intEn() ? "Answer in English…" : "Rispondi come a voce…"}"></textarea>
      <div class="row"><button class="btn primary" data-b="answer">Rispondi</button><button class="btn ghost" data-b="dunno">Non lo so</button>
        <span class="muted" style="font-size:12.5px"><kbd>Ctrl</kbd>+<kbd>Invio</kbd> per inviare</span></div></div>`;
  const end = B.ended ? `<div class="unit-next ${B.reached === B.total ? "ok" : B.reached ? "" : "warn"}"><b>Sei arrivato a ${B.reached} su ${B.total} nella catena.</b>
      ${B.reached === B.total ? "Hai retto fino all'ultimo approfondimento: tornerà fra qualche settimana." : B.reached ? "Ti sei fermato a metà: rileggi la risposta modello del punto dove hai ceduto, tornerà presto." : "Ti sei fermato alla prima domanda: leggi bene la risposta modello, tornerà domani."}
      <div class="row"><button class="btn primary" data-b="next">Prossima domanda</button><a class="btn" href="#/colloquio/domande">Torna alle aree</a></div></div>` : "";
  box.innerHTML = `<div class="q-head"><span class="tag acc">${esc(q.area)}</span><span class="tag">${esc(q.livello)}</span>${q.motivo !== "nuova" ? `<span class="tag wait">${esc(q.motivo)}</span>` : ""}
      <h2>${esc(q.argomento || "Domanda")}</h2><span class="spacer"></span><button class="btn small ghost" data-b="skip">Salta</button></div>
    <div class="strip chain-dots" title="Profondità della catena">${dots}</div>${past}${cur}${end}`;
  const ta = $("#bankAns");
  if (ta) { ta.focus(); ta.onkeydown = ev => { if (ev.key === "Enter" && (ev.ctrlKey || ev.metaKey)) { ev.preventDefault(); bankAnswer(ta.value); } }; }
}
async function bankAnswer(text) {
  const B = App.B; if (B.busy) return;
  B.busy = true;
  const btn = $("[data-b=answer]"); if (btn) { btn.disabled = true; btn.innerHTML = `<span class="spin small"></span> Il selezionatore valuta…`; }
  try {
    const r = await api("/api/bank/answer", {method: "POST", body: {id: B.q.id, step: B.step, answer: text, en: intEn()}});
    B.chain[B.step].a = text; B.chain[B.step].r = r;
    if (r.next) { B.step = r.next.step; B.chain.push({q: r.next.q}); }
    else { B.ended = true; B.reached = r.reached; B.total = r.total; }
  } catch (e) { toast(e.message); }
  B.busy = false;
  if (App.view === "bankq") renderBank();
}
function bankClick(e) {
  const t = e.target.closest("button"); if (!t || !App.B) return;
  const a = t.dataset.b;
  if (a === "answer") { const ta = $("#bankAns"); if (!ta.value.trim()) { toast("Scrivi la risposta, oppure premi «Non lo so»."); return; } bankAnswer(ta.value); }
  if (a === "dunno") bankAnswer("");
  if (a === "next" || a === "skip") { App.B.ended = false; bankNext(); }
}

/* ---- system design */
async function showDesignList() {
  App.view = "designs"; mainNav("c-design");
  $("#view").innerHTML = `<section class="path">${intHead("System design", "System design junior",
    "Ti danno un sistema da progettare: scrivi entità, endpoint, casi limite e come cresce. Qwen ti valuta con una griglia, poi ti fa le domande di approfondimento.")}
    <div id="dsBody"><div class="empty">Caricamento…</div></div></section>`;
  Tutor.setContext("Lo studente si allena con esercizi di system design per junior.", "System design");
  Tutor.setQuick(["Da dove parto in un system design?", "Come scelgo tra SQL e NoSQL?", "Cosa vuol dire che un sistema scala?"]);
  const d = await api("/api/design");
  if (App.view !== "designs") return;
  $("#dsBody").innerHTML = `<div class="cat-grid">${d.items.map(x => `<a class="cat cat-link" href="#/colloquio/design/${x.id}">
      <div class="u-title"><h3>${esc(x.titolo)}</h3><span class="tag">${esc(x.livello)}</span></div>
      <p class="u-concepts">${inl(x.brief)}</p>${x.voto != null ? `<span class="tag ok">migliore ${x.voto}/10</span>` : ""}</a>`).join("")}</div>`;
}
async function showDesign(id) {
  App.view = "design"; mainNav("c-design");
  const d = await api(`/api/design?id=${id}`);
  App.D = {d, fu: {}};
  $("#view").innerHTML = `<section class="path design">${intHead("System design", esc(d.titolo), inl(d.brief))}
    <div class="ds-req"><span class="lbl">Requisiti</span><ul>${d.requisiti.map(r => `<li>${inl(r)}</li>`).join("")}</ul></div>
    <form id="dsForm" class="ds-form">${d.sezioni.map((s, i) => `<label><b>${esc(s)}</b><textarea class="open-ans" data-sez="${i}" rows="4"></textarea></label>`).join("")}
      <div class="row"><button class="btn primary" type="submit">Fai valutare la proposta</button><span class="muted" style="font-size:12.5px">Scrivi per punti: conta il ragionamento, non la forma.</span></div></form>
    <div id="dsRes"></div></section>`;
  Tutor.setContext(`System design: ${d.brief}\nRequisiti: ${d.requisiti.join("; ")}. NON dare la soluzione completa: fai domande e suggerisci cosa considerare.`, `System design · ${d.titolo}`);
  $("#dsForm").onsubmit = async ev => {
    ev.preventDefault();
    const text = d.sezioni.map((s, i) => `## ${s}\n${$(`[data-sez="${i}"]`).value.trim()}`).join("\n\n");
    if (text.replace(/##.*\n/g, "").trim().length < 40) { toast("Scrivi qualcosa in più prima di farla valutare."); return; }
    const b = ev.submitter || $("#dsForm button"); b.disabled = true; b.innerHTML = `<span class="spin small"></span> Il selezionatore legge…`;
    try { App.D.r = await api("/api/design/judge", {method: "POST", body: {id, text}}); renderDesignRes(); }
    catch (e) { toast(e.message); }
    b.disabled = false; b.textContent = "Fai valutare di nuovo";
  };
  $("#view").onclick = designClick;
}
function renderDesignRes() {
  const r = App.D.r, id = App.D.d.id;
  $("#dsRes").innerHTML = `<div class="ds-score"><b>${r.voto}/10</b><p class="explain">${inl(r.commento)}</p></div>
    <table class="grid-tab"><thead><tr><th>Criterio</th><th>Voto</th><th>Commento</th></tr></thead><tbody>${r.criteri.map(c => `<tr>
      <td><b>${esc(c.criterio)}</b><small class="muted">${inl(c.atteso)}</small></td><td class="v v${c.voto}">${c.voto}/3</td><td>${inl(c.commento)}</td></tr>`).join("")}</tbody></table>
    ${listHtml("Punti forti", r.forti, "ok")}${listHtml("Da aggiungere", r.mancanze, "miss")}
    <details class="ds-sol"><summary>Una soluzione di riferimento</summary><div class="explain pre-wrap">${inl(r.soluzione)}</div></details>
    <h2 class="section-title">Il selezionatore approfondisce</h2>
    ${r.approfondimenti.map((q, i) => `<div class="chain-step"><p class="q">${inl(q)}</p>
      <textarea class="open-ans" data-fu="${i}" rows="3"></textarea><div class="row"><button class="btn small" data-fub="${i}">Rispondi</button></div><div data-fur="${i}"></div></div>`).join("")}`;
}
async function designClick(e) {
  const t = e.target.closest("[data-fub]"); if (!t) return;
  const i = +t.dataset.fub, D = App.D, ans = $(`[data-fu="${i}"]`).value.trim();
  if (!ans) { toast("Scrivi la risposta."); return; }
  t.disabled = true; t.innerHTML = `<span class="spin small"></span>`;
  try {
    const r = await api("/api/design/followup", {method: "POST", body: {id: D.d.id, question: D.r.approfondimenti[i], answer: ans, en: intEn()}});
    $(`[data-fur="${i}"]`).innerHTML = `<p class="fb ${verdictCls(r.score)}"><b>${r.score}/5.</b> ${inl(r.comment)}</p>${listHtml("Mancava", r.missing, "miss")}`;
  } catch (err) { toast(err.message); }
  t.disabled = false; t.textContent = "Rispondi";
}

/* ---- code review */
async function showReviewList() {
  App.view = "reviews"; mainNav("c-review");
  $("#view").innerHTML = `<section class="path">${intHead("Code review", "Code review",
    "Come nei colloqui veri: ti danno codice di una pull request e devi trovare bug, problemi di sicurezza, di prestazioni e di leggibilità. Poi vedi cosa ti è sfuggito.")}
    <div id="rvBody"><div class="empty">Caricamento…</div></div></section>`;
  Tutor.setContext("Lo studente si allena a fare code review per i colloqui.", "Code review");
  Tutor.setQuick(["Cosa guardo per primo in una code review?", "Quali sono gli errori di sicurezza più comuni?"]);
  const d = await api("/api/review_ex");
  if (App.view !== "reviews") return;
  const byLang = ["java", "python", "sql"].map(l => [l, d.items.filter(x => x.lang === l)]).filter(([, xs]) => xs.length);
  $("#rvBody").innerHTML = byLang.map(([l, xs]) => `<h2 class="section-title">${LANG[l] || l}</h2><div class="cat-grid">${xs.map(x => `<a class="cat cat-link" href="#/colloquio/review/${x.id}">
      <div class="u-title"><h3>${esc(x.titolo)}</h3><span class="tag">${esc(x.livello)}</span></div>
      <p class="u-concepts">${inl(x.contesto)}</p>${x.trovati != null ? `<span class="tag ${x.trovati === x.n ? "ok" : "wait"}">${x.trovati}/${x.n} trovati</span>` : `<span class="tag">${x.n} problemi</span>`}</a>`).join("")}</div>`).join("");
}
async function showReviewEx(id) {
  App.view = "review"; mainNav("c-review");
  const d = await api(`/api/review_ex?id=${id}`);
  App.RV = {d};
  const lines = d.codice.split("\n");
  $("#view").innerHTML = `<section class="path review-ex">${intHead("Code review", esc(d.titolo), inl(d.contesto) + ` Ci sono <b>${d.n}</b> problemi da trovare.`)}
    <pre class="out numbered askable" id="rvCode">${lines.map((l, i) => `<span class="ln" data-ln="${i + 1}"><i>${i + 1}</i>${esc(l) || " "}</span>`).join("")}</pre>
    <label class="ds-form"><b>La tua review</b><textarea class="open-ans" id="rvText" rows="7" placeholder="Un problema per riga: riga, cosa non va, come lo sistemi. Es. «riga 12: la query concatena l'input, rischio di SQL injection → PreparedStatement»"></textarea></label>
    <div class="row"><button class="btn primary" id="rvGo">Consegna la review</button></div>
    <div id="rvRes"></div></section>`;
  Tutor.setQuick(["Cosa guardo per primo in una code review?", "Dammi un indizio su dove guardare"]);
  Tutor.setContext(`Code review di questo codice (${LANG[d.lang] || d.lang}):\n${d.codice}\nNON elencare i problemi: guida lo studente con domande.`, `Code review · ${d.titolo}`);
  $("#rvGo").onclick = async () => {
    const text = $("#rvText").value.trim();
    if (text.length < 10) { toast("Scrivi almeno un problema."); return; }
    const b = $("#rvGo"); b.disabled = true; b.innerHTML = `<span class="spin small"></span> Il selezionatore confronta…`;
    try {
      const r = await api("/api/review_ex/judge", {method: "POST", body: {id, text}});
      $$("#rvCode .ln").forEach(el => el.classList.remove("hit", "miss"));
      r.problemi.forEach(p => { const el = $(`#rvCode [data-ln="${p.riga}"]`); if (el) el.classList.add(p.trovato ? "hit" : "miss"); });
      $("#rvRes").innerHTML = `<div class="ds-score"><b>${r.trovati}/${r.n}</b><p class="explain">${inl(r.commento)}</p></div>
        <ol class="rv-list">${r.problemi.map(p => `<li class="${p.trovato ? "hit" : "miss"}"><span class="tag ${p.trovato ? "ok" : "err"}">${p.trovato ? "trovato" : "sfuggito"}</span>
          <span class="tag">riga ${p.riga}</span><span class="tag">${esc(p.tipo)}</span><span class="tag ${p.gravita === "alta" ? "err" : p.gravita === "media" ? "wait" : ""}">${esc(p.gravita)}</span>
          <p><b>${inl(p.problema)}</b> ${inl(p.correzione)}</p></li>`).join("")}</ol>
        ${r.extra.length ? `<div class="jl"><span class="lbl">Altre tue osservazioni</span><ul>${r.extra.map(x => `<li>${inl(x.osservazione)} — <span class="${x.valida ? "" : "muted"}">${x.valida ? "giusta" : "non convince"}: ${inl(x.commento)}</span></li>`).join("")}</ul></div>` : ""}
        ${r.domanda_finale ? `<div class="chain-step"><p class="q"><span class="tag wait">E ora</span> ${inl(r.domanda_finale)}</p><p class="muted">Rispondi a voce o chiedilo al tutor.</p></div>` : ""}`;
    } catch (e) { toast(e.message); }
    b.disabled = false; b.textContent = "Consegna di nuovo";
  };
}

/* ---- domande comportamentali */
async function showSoft() {
  App.view = "soft"; mainNav("c-soft");
  $("#view").innerHTML = `<section class="path">${intHead("Comportamentali", "Domande comportamentali",
    "«Raccontami un bug difficile», «un conflitto nel team»… Si risponde con il metodo STAR: Situazione, Compito, Azione, Risultato. Puoi allenarti in italiano o in inglese.")}
    <div class="row"><span class="muted">Lingua</span><div class="seg" role="group" aria-label="Lingua">
      <button type="button" data-sl="it" aria-pressed="${!intEn()}">Italiano</button><button type="button" data-sl="en" aria-pressed="${intEn()}">English</button></div></div>
    <div id="softBody"><div class="empty">Caricamento…</div></div></section>`;
  Tutor.setContext("Lo studente si allena con le domande comportamentali (metodo STAR).", "Comportamentali");
  Tutor.setQuick(["Come funziona il metodo STAR?", "Cosa racconto se non ho esperienza di lavoro?"]);
  const d = await api("/api/soft");
  if (App.view !== "soft") return;
  App.SOFT = d.items;
  $("#softBody").innerHTML = `<ol class="soft-list">${d.items.map(s => `<li><button class="soft-q" data-sq="${s.id}"><span>${esc(intEn() ? s.q_en : s.q_it)}</span>${s.voto ? `<span class="tag ok">${s.voto}/5</span>` : ""}</button><div class="soft-box" data-sb="${s.id}"></div></li>`).join("")}</ol>`;
  $("#view").onclick = softClick;
}
async function softClick(e) {
  const l = e.target.closest("[data-sl]");
  if (l) { App.intLang = l.dataset.sl; localStorage.setItem("ricalco.intlang", App.intLang); showSoft(); return; }
  const q = e.target.closest("[data-sq]");
  if (q) {
    const id = q.dataset.sq, box = $(`[data-sb="${id}"]`);
    if (box.innerHTML) { box.innerHTML = ""; return; }
    box.innerHTML = `<textarea class="open-ans" rows="6" data-sa="${id}" placeholder="${intEn() ? "Situation, Task, Action, Result…" : "Situazione, Compito, Azione, Risultato…"}"></textarea>
      <div class="row"><button class="btn small primary" data-sg="${id}">Fai valutare</button></div><div data-sr="${id}"></div>`;
    box.querySelector("textarea").focus();
    return;
  }
  const g = e.target.closest("[data-sg]"); if (!g) return;
  const id = g.dataset.sg, ans = $(`[data-sa="${id}"]`).value.trim();
  if (ans.length < 20) { toast("Racconta un po' di più: almeno qualche frase."); return; }
  g.disabled = true; g.innerHTML = `<span class="spin small"></span>`;
  try {
    const r = await api("/api/soft/judge", {method: "POST", body: {id, answer: ans, en: intEn()}});
    const S = [["situazione", "Situazione"], ["compito", "Compito"], ["azione", "Azione"], ["risultato", "Risultato"]];
    $(`[data-sr="${id}"]`).innerHTML = `<p class="fb ${verdictCls(r.voto)}"><b>${r.voto}/5.</b> ${inl(r.commento)}</p>
      <div class="star">${S.map(([k, n]) => `<span class="tag ${r.star[k] ? "ok" : "err"}">${r.star[k] ? "✓" : "✗"} ${n}</span>`).join("")}</div>
      ${listHtml("Funziona", r.forti, "ok")}${listHtml("Da cambiare", r.migliorare, "miss")}
      ${r.lingua ? `<p class="fb mid"><b>Inglese:</b> ${inl(r.lingua)}</p>` : ""}
      <details><summary class="muted">Consigli e un esempio di risposta</summary><p class="explain">${inl(r.consigli)}</p><p class="explain">${inl(r.esempio)}</p></details>`;
  } catch (err) { toast(err.message); }
  g.disabled = false; g.textContent = "Fai valutare di nuovo";
}
