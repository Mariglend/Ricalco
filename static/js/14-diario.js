"use strict";

/* ================================================================ diario d'uso */
$("#noteBtn").onclick = () => { const f = $("#notePop"); f.hidden = !f.hidden; if (!f.hidden) $("#noteText").focus(); };
$("#noteClose").onclick = () => { $("#notePop").hidden = true; };
$("#notePop").onsubmit = e => {
  e.preventDefault();
  const v = $("#noteText").value.trim(); if (!v) return;
  const it = App.Q && App.view === "start" ? App.Q.item : null;
  LOG.ev("note", {text: v, where: $("#tutorCtx").textContent.replace(/^Contesto: /, "").slice(0, 100) || App.view, hash: location.hash, item: it ? it.title : null});
  LOG.flush();
  $("#noteText").value = ""; $("#notePop").hidden = true; toast("Nota salvata nel diario.");
};
async function showDiary() {
  App.view = "diary"; mainNav("diario");
  $("#view").innerHTML = `<section class="theory"><p class="eyebrow">Ultimi 14 giorni</p><h1>Diario d'uso</h1><div id="diaryBody"><div class="empty">Leggo i log…</div></div></section>`;
  Tutor.setContext("Lo studente guarda il diario d'uso di Ricalco: statistiche su come si allena.", "Diario d'uso");
  Tutor.setQuick([]);
  const d = await api("/api/logs/summary?days=14");
  const T = d.totals, L = d.llm, P = d.phases;
  const pct = (a, b) => b ? Math.round(a / b * 100) + "%" : "—";
  const n = v => v === null || v === undefined ? "—" : v;
  $("#diaryBody").innerHTML = `
    <p class="explain">Tutto quello che fai in Ricalco viene registrato in <code>data/logs/</code>, solo sul tuo PC. Qui sotto c'è il riassunto: serve a capire dove ti blocchi, dove perdi tempo e quanto è lento il modello. Con il pulsante <b>Nota</b> in alto puoi annotare al volo cosa non va.</p>
    <div class="kpis diary-kpis">
      <div class="stat"><b>${T.activeDays}</b><span>Giorni attivi</span></div>
      <div class="stat"><b>${T.activeMin}</b><span>Minuti di lavoro</span></div>
      <div class="stat"><b>${T.done}</b><span>Esercizi di Oggi</span></div>
      <div class="stat"><b>${n(T.avg)}</b><span>Punteggio medio</span></div>
      <div class="stat"><b>${pct(T.variantsOk, T.variants)}</b><span>Varianti risolte (${T.variants})</span></div>
      <div class="stat"><b>${pct(T.predictOk, T.predict)}</b><span>Previsioni giuste (${T.predict})</span></div>
      <div class="stat"><b>${T.skips}</b><span>Esercizi saltati</span></div>
      <div class="stat"><b>${T.tutor}</b><span>Domande al tutor</span></div>
    </div>
    ${d.days.length ? `<div class="cmp-wrap"><table class="cmp st"><tr><th>Giorno</th><th>Minuti</th><th>Esercizi Oggi</th><th>Media</th><th>Saltati</th><th>Aiuti</th><th>Varianti</th><th>Esercizi percorso</th></tr>
      ${d.days.slice().reverse().map(r => `<tr><td>${esc(r.day)}</td><td>${r.min}</td><td>${r.done}</td><td>${n(r.avg)}</td><td>${r.skips}</td><td>${r.hints}</td><td>${r.variants}</td><td>${r.exercises}</td></tr>`).join("")}</table></div>`
      : `<div class="empty">Ancora nessun dato: torna qui dopo qualche esercizio.</div>`}
    <div class="home-grid">
      <div class="th-box"><span class="eyebrow">Dove passi il tempo</span><ul>
        <li>Ragionare sul piano: in media ${n(P.ragiona)} s per esercizio${P.plans ? ` · piano giusto da solo ${pct(P.planFirst, P.plans)}, piano guardato ${pct(P.planShown, P.plans)}` : ""}.</li>
        <li>Scrivere il codice: in media ${n(P.scrivi)} s per esercizio.</li>
        ${d.waits.map(w => `<li>Attesa per ${esc(w.what)}: ${w.n} ${w.n === 1 ? "volta" : "volte"}, in media ${w.avg} s (al massimo ${w.max} s).</li>`).join("")}</ul></div>
      <div class="th-box"><span class="eyebrow">Il modello (${esc((App.status && App.status.model) || "")})</span><ul>
        <li>${L.n} richieste, ${L.fail} non riuscite. Tempo medio ${n(L.avg)} s, il 90% sotto ${n(L.p90)} s.</li>
        <li>Quando aspetti tu: in media ${n(L.fgAvg)} s. Tutor: prima parola dopo ${n(L.tutorFirst)} s.</li>
        <li>Esercizi preparati in sottofondo: ${L.gen}, in media ${n(L.genAvg)} s l'uno, ${L.genFail} falliti.</li></ul>
        ${L.kinds.length ? `<details><summary class="muted" style="cursor:pointer">Per tipo di richiesta</summary><ul>${L.kinds.map(k => `<li>${esc(k.what)}… · ${k.n} · ${n(k.avg)} s${k.fail ? ` · ${k.fail} fallite` : ""}</li>`).join("")}</ul></details>` : ""}</div>
    </div>
    <div class="th-box warnbox"><span class="eyebrow">Errori di ragionamento · prima di scrivere il codice</span>
      ${d.reasoning && d.reasoning.length ? `<p class="muted" style="margin:0;font-size:13px">Il metodo sbagliato o incompleto, le spiegazioni deboli, le domande di ragionamento sbagliate: sono gli errori che contano di più al colloquio.</p>
      <ul class="reason">${d.reasoning.slice(0, 20).map(r => `<li><b>«${esc(r.title)}»</b> · ${esc(r.kind)}: ${esc(r.what)} <span class="muted">${esc(r.t)}</span>
        ${r.answer ? `<div class="muted">Hai risposto: «${esc(r.answer)}»</div>` : ""}${r.comment ? `<div>${inl(r.comment)}</div>` : ""}</li>`).join("")}</ul>`
      : `<p class="muted" style="margin:0">Nessun errore di ragionamento in questi giorni.</p>`}</div>
    ${d.hardBlocks.length ? `<div class="th-box warnbox"><span class="eyebrow">Blocchi più difficili · errori di battitura</span><ul>${d.hardBlocks.map(b => `<li>«${esc(b.title)}», blocco ${b.k + 1}: ${b.err} errori, ${b.hints} aiuti${b.secs ? `, ${b.secs} s` : ""}</li>`).join("")}</ul></div>` : ""}
    ${d.skipped.length ? `<div class="th-box"><span class="eyebrow">Esercizi saltati</span><ul>${d.skipped.map(x => `<li>${esc(x.title)}${x.n > 1 ? ` (${x.n} volte)` : ""}</li>`).join("")}</ul></div>` : ""}
    <div class="th-box"><span class="eyebrow">Le tue note</span>${d.notes.length ? `<ul>${d.notes.map(x => `<li><b>${esc(x.t)}</b> · <span class="muted">${esc(x.where)}</span><br>${esc(x.text)}</li>`).join("")}</ul>` : `<p class="explain">Nessuna nota. Quando qualcosa ti blocca o ti annoia, premi <b>Nota</b> in alto e scrivilo in una riga.</p>`}</div>
    ${d.errors.length ? `<div class="th-box warnbox"><span class="eyebrow">Errori dell'app</span><ul>${d.errors.map(x => `<li>${esc(x.t)} · ${esc(x.msg)}</li>`).join("")}</ul></div>` : ""}
    <div class="row"><button class="btn primary" id="logExport">Esporta i log</button><span class="muted" style="font-size:13px">Un file .jsonl degli ultimi 30 giorni: puoi mandarmelo per analizzarlo insieme.</span></div>`;
  $("#logExport").onclick = async () => {
    LOG.flush();
    const r = await fetch("/api/logs/export", {headers: {"X-Ricalco": "1"}});
    const blob = await r.blob(), a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = `ricalco-log-${new Date().toISOString().slice(0, 10)}.jsonl`; a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  };
}
