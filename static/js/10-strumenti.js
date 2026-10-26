"use strict";

/* ================================================================ prova del modello */
async function showSelftest() {
  App.view = "selftest"; mainNav("prova");
  const d = await api("/api/selftest");
  App.st = {d, res: [], running: false};
  const sp = d.spring;
  const TYPE_LABEL = t => (TYPES[t] ? TYPES[t].name : t);
  const stats = Object.entries(d.typestats || {}).filter(([, v]) => v.n);
  $("#view").innerHTML = `<section class="theory">
    <p class="eyebrow">Diagnostica</p><h1>Prova il modello</h1>
    <p class="explain">Genera un esercizio per ogni sezione con <code>${esc(d.model || "nessun modello")}</code>, lo verifica come fa l'app e misura quanto ci mette. Gli esercizi validi restano nel tuo archivio. Durata tipica: 5-15 minuti.</p>
    <div class="kpis" style="grid-template-columns:repeat(4,minmax(0,1fr))">
      <div class="stat"><b>${esc(d.model || "—")}</b><span>Modello</span></div><div class="stat"><b>${esc(d.python)}</b><span>Python</span></div>
      <div class="stat"><b>${esc(d.java || "—")}</b><span>Java</span></div><div class="stat"><b>${sp.ready ? "pronto" : "da preparare"}</b><span>Spring</span></div></div>
    <div class="row"><button class="btn primary" id="stGo" ${d.model ? "" : "disabled"}>Avvia la prova</button><span class="muted" id="stMsg"></span></div>
    <div class="cmp-wrap"><table class="cmp st"><tr><th>Sezione</th><th>Esito</th><th>Tempo</th><th>Note</th></tr>
      ${d.steps.map((s, i) => `<tr id="st-${i}"><td>${esc(s.label)}</td><td class="muted">—</td><td></td><td></td></tr>`).join("")}</table></div>
    <div id="stVerdict"></div>
    <div class="th-box"><span class="eyebrow">Spring con Maven</span>
      <p class="explain">${sp.ready ? `Pronto: le unità Java con Maven eseguono davvero i test JUnit (Spring Boot ${esc(sp.springBoot)}, H2, Spring Security, Spring AI con modelli finti). ${(sp.extras || []).filter(x => !x.ready).length ? ` Mancano ancora le librerie di ${sp.extras.filter(x => !x.ready).map(x => esc(x.label)).join(" e ")}: premi «Ripeti la prova Spring» per scaricarle (oppure si scaricano da sole al primo esercizio).` : ""}`
        : `Le unità Spring ora sono valutate dal modello. Preparando Spring, Ricalco ${sp.maven ? "usa il Maven che hai già" : "scarica Maven (9 MB)"} e le librerie di Spring Boot ${esc(sp.springBoot)} (circa 150 MB, solo la prima volta), poi esegue un test di prova.`}</p>
      <div class="row"><button class="btn ${sp.ready ? "" : "primary"}" id="spGo">${sp.ready ? "Ripeti la prova Spring" : "Prepara Spring"}</button><span class="muted" id="spMsg"></span></div>
      <pre class="out" id="spLog" ${sp.log && sp.log.length ? "" : "hidden"}>${esc((sp.log || []).join("\n"))}</pre></div>
    ${stats.length ? `<div class="th-box"><span class="eyebrow">I tuoi risultati per tipo di esercizio</span><ul>${stats.map(([k, v]) => `<li>${esc(k.split(":")[0])} · ${esc(TYPE_LABEL(k.split(":")[1]))}: ${Math.round(v.first / v.n * 100)}% al primo colpo su ${v.n}</li>`).join("")}</ul></div>` : ""}
    ${Object.keys(d.flags || {}).length ? `<div class="th-box warnbox"><span class="eyebrow">Esercizi che hai segnalato come sbagliati</span><ul>${Object.entries(d.flags).map(([t, n]) => `<li>${esc(TYPE_LABEL(t))}: ${n}</li>`).join("")}</ul></div>` : ""}
  </section>`;
  Tutor.setContext(`Lo studente sta provando il modello locale ${d.model} in Ricalco.`, "Prova il modello");
  Tutor.setQuick([]);
  $("#stGo").onclick = runSelftest;
  $("#spGo").onclick = setupSpring;
  if (sp.busy) pollSpring();
}
async function runSelftest() {
  const S = App.st; if (S.running) return;
  S.running = true; $("#stGo").disabled = true;
  const t0 = Date.now();
  for (let i = 0; i < S.d.steps.length; i++) {
    if (App.view !== "selftest") return;
    const row = $(`#st-${i}`);
    row.children[1].innerHTML = `<span class="spin small"></span>`;
    $("#stMsg").textContent = `${i + 1}/${S.d.steps.length} · ${Math.round((Date.now() - t0) / 1000)} s`;
    let r;
    try { r = await api("/api/selftest/step", {method: "POST", body: {i}}); } catch (e) { r = {ok: false, error: e.message, secs: 0}; }
    S.res[i] = r;
    if (!$(`#st-${i}`)) return;
    row.children[1].innerHTML = r.ok ? (r.attempts > 1 ? `<span class="okc">✓</span> dopo ${r.attempts} tentativi` : `<span class="okc">✓</span> al primo tentativo`) : `<span class="koc">✗</span> non riuscito`;
    row.children[2].textContent = r.secs + " s" + (r.first ? ` (prima parola ${r.first} s)` : "");
    row.children[3].textContent = r.error || r.title || r.sample || "";
  }
  S.running = false; $("#stGo").disabled = false; $("#stMsg").textContent = `Finito in ${Math.round((Date.now() - t0) / 60000)} min.`;
  const gen = S.res.slice(1), ok = gen.filter(r => r.ok), first = ok.filter(r => (r.attempts || 1) === 1);
  const avg = ok.length ? Math.round(ok.reduce((a, r) => a + r.secs, 0) / ok.length) : 0;
  const bad = gen.map((r, k) => r.ok ? null : S.d.steps[k + 1].label).filter(Boolean);
  let advice;
  if (ok.length === gen.length && first.length >= gen.length - 2) advice = "Il modello è affidabile per tutte le sezioni. Tienilo così.";
  else if (ok.length >= gen.length - 2) advice = "Funziona, ma a volte serve più di un tentativo: i tempi di attesa saranno più lunghi in quelle sezioni. Il lavoro in sottofondo compensa quasi sempre.";
  else advice = "Il modello sbaglia spesso. Prova un modello più forte per il codice (per esempio qwen2.5-coder:14b) oppure usa le sezioni che qui risultano affidabili.";
  if (avg > 90) advice += ` Tempo medio ${avg} s per esercizio: se è troppo, un 7B (qwen2.5-coder:7b) è circa due volte più veloce.`;
  $("#stVerdict").innerHTML = `<div class="th-box"><span class="eyebrow">Risultato</span>
    <p class="explain"><b>${ok.length}/${gen.length}</b> sezioni con esercizi validi, <b>${first.length}</b> al primo tentativo, tempo medio <b>${avg} s</b> per esercizio. Tutor: prima parola dopo ${S.res[0] && S.res[0].first || "—"} s.</p>
    ${bad.length ? `<p class="explain">Non riuscite: ${bad.map(esc).join(", ")}.</p>` : ""}<p class="explain">${advice}</p></div>`;
}
async function setupSpring() {
  $("#spGo").disabled = true;
  try { await api("/api/spring/setup", {method: "POST", body: {}}); } catch (e) { toast(e.message); }
  pollSpring();
}
async function pollSpring() {
  const st = await api("/api/spring").catch(() => null);
  if (!st || App.view !== "selftest") return;
  const log = $("#spLog"); log.hidden = false; log.textContent = st.log.join("\n"); log.scrollTop = log.scrollHeight;
  $("#spMsg").innerHTML = st.busy ? `<span class="spin small"></span> In corso…` : st.ready ? "Spring è pronto." : "Non riuscito: guarda il registro qui sotto.";
  if (st.busy) setTimeout(pollSpring, 2000);
  else { $("#spGo").disabled = false; if (st.ready) { $("#spGo").textContent = "Ripeti la prova Spring"; toast("Spring pronto: le unità Spring ora eseguono i test veri."); } }
}

/* ================================================================ riscrittura a memoria (esercizi sbagliati, ripasso) */
function sheetHtml(hint) {
  return `<div class="sheet drill"><pre class="code askable"></pre><textarea class="trap" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" aria-label="Scrivi qui il codice"></textarea><div class="miss-tag"></div><div class="sheet-hint when-blur">${esc(hint || "Clicca sul foglio e scrivi a memoria")}</div></div>`;
}
function rewriteTracer(host, lang, code, onDone, level = 3) {
  const stats = {typed: 0, errors: 0, hints: 0, blockErr: {}};
  const tr = new Tracer($(".sheet", host), {lang, blocks: [{code}]}, {
    level, stats,
    onLocked: () => {},
    onBlockDone: () => { const h = $(".sheet-hint", host); if (h) h.remove(); onDone(stats, tr); },
    onChange: () => {}
  });
  tr.setState(0, "scrivi");
  tr.focus();
  setTimeout(() => tr.focus(), 30);
  return {tr, stats};
}
function words(t) { return new Set(String(t || "").toLowerCase().match(/[a-z_][a-z0-9_]{2,}/g) || []); }
function bestBlock(L, ex) {
  const w = words([ex.statement, ex.question, ex.code, ex.solution, ex.starter, (ex.options || []).join(" ")].join(" "));
  let best = 0, score = -1;
  L.blocks.forEach((b, k) => {
    const bw = words(b.code + " " + (b.explain || ""));
    let sc = 0; bw.forEach(x => { if (w.has(x)) sc++; });
    sc = sc / Math.sqrt(bw.size || 1);
    if (sc > score) { score = sc; best = k; }
  });
  return best;
}
function openDrill(ex) {
  const L = P.s.unitLesson; if (!L) return;
  const k = bestBlock(L, ex), b = L.blocks[k];
  const box = $("#drillBox"); if (!box) return;
  box.innerHTML = `<div class="drill-box"><span class="eyebrow">Riscrivi a memoria · «${esc(L.title)}», blocco ${k + 1}</span>
    <p class="explain">${inl(b.explain || "")}</p>${sheetHtml()}<p class="muted" id="drillMsg" style="font-size:13px;margin:0">Dopo tre errori sullo stesso punto compare la parola.</p></div>`;
  rewriteTracer(box, P.s.lang, b.code, st => {
    const tot = st.typed + st.errors;
    $("#drillMsg").innerHTML = `<b>Fatto.</b> Precisione ${tot ? Math.round(st.typed / tot * 100) : 100}%, ${st.hints} aiuti. Questo blocco è già nel tuo ripasso.`;
    const nb = $("#nextBtn"); if (nb) nb.focus();
  });
  box.scrollIntoView({block: "nearest", behavior: "smooth"});
}

/* ================================================================ SQL: tabelle e confronti */
function sqlCell(v) { return v === null || v === undefined ? "NULL" : typeof v === "number" && !Number.isInteger(v) ? String(+v.toFixed(4)) : String(v); }
function sqlTable(res, cls = "") {
  if (!res || !res.cols) return `<p class="muted">(nessun risultato)</p>`;
  return `<div class="cmp-wrap"><table class="cmp sqlt ${cls}"><tr>${res.cols.map(c => `<th>${esc(c)}</th>`).join("")}</tr>${res.rows.length ? res.rows.map(r => `<tr>${r.map(v => `<td class="${v === null ? "null" : ""}">${esc(sqlCell(v))}</td>`).join("")}</tr>`).join("") : `<tr><td colspan="${res.cols.length}" class="muted">nessuna riga</td></tr>`}</table></div>`;
}
function dbHtml(ex, open) {
  if (ex.check !== "sql" || !ex.tables || !Object.keys(ex.tables).length) return "";
  const names = Object.keys(ex.tables);
  return `<details class="db" ${open ? "open" : ""}><summary><span class="eyebrow">Il database</span> <span class="muted">${names.map(esc).join(", ")}</span></summary>
    <div class="db-grid">${names.map(n => `<div><b class="db-name">${esc(n)}</b>${sqlTable(ex.tables[n])}${ex.tables[n].rows.length >= 12 ? `<small class="muted">prime 12 righe</small>` : ""}</div>`).join("")}</div></details>`;
}
function sqlFailHtml(ex, r) {
  if (r.error) return `<div class="res-err"><b>La query va in errore</b><pre>${esc(r.error)}</pre>${r.where && !/^(setup|check)$/.test(r.where) ? `<small class="muted">Nell'istruzione: ${esc(r.where)}</small>` : ""}</div>`;
  const got = r.result, exp = ex.expected || {cols: [], rows: []};
  let why = "";
  if (!got) why = "La query non restituisce nessuna tabella: manca una SELECT?";
  else if (got.cols.length !== exp.cols.length) why = `Il risultato ha ${got.cols.length} ${got.cols.length === 1 ? "colonna" : "colonne"}, ne ${exp.cols.length === 1 ? "serve 1" : `servono ${exp.cols.length}`}.`;
  else if (got.rows.length !== exp.rows.length) why = `Il risultato ha ${got.rows.length} ${got.rows.length === 1 ? "riga" : "righe"}, ne ${exp.rows.length === 1 ? "serve 1" : `servono ${exp.rows.length}`}.`;
  else why = ex.ordered ? "Stesse dimensioni, ma valori o ordine diversi." : "Stesse dimensioni, ma i valori sono diversi (l'ordine qui non conta).";
  return `<span class="eyebrow">Il risultato non è quello atteso</span><p class="muted" style="margin:0;font-size:13px">${why}</p>
    <div class="sql-cmp"><div><small class="muted">Atteso</small>${sqlTable(exp)}</div><div><small class="muted">Il tuo risultato</small>${sqlTable(got)}</div></div>`;
}
function sqlFailText(ex, r) {
  if (r.error) return "Errore: " + r.error;
  const t = res => res ? [res.cols.join(" | ")].concat(res.rows.map(x => x.map(sqlCell).join(" | "))).join("\n") : "(nessun risultato)";
  return `Risultato atteso:\n${t(ex.expected)}\nRisultato ottenuto:\n${t(r.result)}`;
}
function sqlLines(text, cols) {
  const norm = v => { v = v.trim().replace(/^['"]|['"]$/g, ""); if (/^null$/i.test(v)) return "NULL"; if (/^-?\d+([.,]\d+)?$/.test(v)) { const n = parseFloat(v.replace(",", ".")); return String(+n.toFixed(4)); } return v; };
  let lines = String(text || "").replace(/\r/g, "").split("\n").map(l => l.trim()).filter(Boolean).map(l => l.replace(/^\||\|$/g, "").split("|").map(norm).join(" | "));
  if (cols && cols.length && lines.length && lines[0].toLowerCase() === cols.map(c => c.toLowerCase()).join(" | ")) lines = lines.slice(1);
  return lines;
}

/* ================================================================ ricalco della soluzione (ogni volta che scrivi codice) */
const CODE_TYPES = ["completa", "bug", "zero", "riordina"];
function startSolutionRicalco(ex, lang, miss) {
  const host = $("#rcHost"); if (!host || !ex.solution) return;
  const st = ex.state.rc = ex.state.rc || {level: miss ? 1 : 2, best: 0};
  mountRicalco(host, {lang, code: ex.solution, st, label: miss ? "Ora ricalca la soluzione" : "Ricalca la soluzione di riferimento",
    note: miss ? "La soluzione è anche nel tuo ripasso: tornerà da riscrivere a memoria domani." : ""});
  feynmanFor(ex, lang);
}
function mountRicalco(host, o) {
  const st = o.st, lv = st.level;
  if (st.skipped) {
    host.innerHTML = `<div class="rc"><span class="eyebrow">Soluzione di riferimento</span><pre class="out askable">${esc(o.code)}</pre>
      <div class="row"><button class="btn small" data-rc="open">Ricalcala</button></div></div>`;
  } else {
    host.innerHTML = `<div class="rc">
      <div class="rc-head"><span class="eyebrow">${esc(o.label)}</span><span class="spacer"></span>
        <div class="seg small" role="group" aria-label="Livello">${[1, 2, 3].map(n => `<button type="button" data-rc="${n}" aria-pressed="${n === lv}" title="${LEVELS[n].desc}"><span class="num">${n}</span>${LEVELS[n].name}</button>`).join("")}</div>
        <button class="linkish" data-rc="skip">Salta</button></div>
      ${sheetHtml(lv === 1 ? "Clicca sul foglio e ricalca la soluzione" : lv === 2 ? "Clicca e ricostruisci nomi e valori" : "Clicca e riscrivila a memoria")}
      <p class="muted rc-msg">${o.note ? esc(o.note) + " " : ""}Si scrive come sul foglio della lezione: niente incolla, i commenti si scrivono da soli.</p></div>`;
    rewriteTracer(host, o.lang, o.code, stats => {
      const tot = stats.typed + stats.errors, acc = tot ? Math.round(stats.typed / tot * 100) : 100;
      st.best = Math.max(st.best, lv);
      const msg = $(".rc-msg", host);
      msg.innerHTML = `<b>Fatto al livello ${lv}.</b> Precisione ${acc}%, ${stats.hints} aiuti. ` +
        (lv < 3 ? `<button class="btn small primary" data-rc="${lv + 1}">Rifalla a livello ${lv + 1} · ${LEVELS[lv + 1].name}</button>` : "L'hai scritta a memoria.");
      const fy = $(".fy-ans");
      const b = fy && !fy.value ? fy : lv < 3 ? $(`[data-rc="${lv + 1}"].primary`, host) : ($("#nextBtn") || $("#nextEx"));
      if (b) b.focus();
    }, lv);
  }
  host.onclick = e => {
    const b = e.target.closest("[data-rc]"); if (!b) return;
    const a = b.dataset.rc;
    if (a === "skip") st.skipped = true;
    else if (a === "open") st.skipped = false;
    else { st.level = +a; st.skipped = false; }
    mountRicalco(host, o);
  };
}
