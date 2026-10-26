"use strict";

/* ================================================================ catalogo di algoritmi
   I problemi da colloquio divisi per schema. Ognuno si apre come un esercizio di «Oggi» (ragiona, poi riscrivi). */
async function showCatalog() {
  App.view = "catalog"; mainNav("algoritmi");
  const lang = App.catLang = App.catLang || localStorage.getItem("ricalco.catlang") || "python";
  const v = $("#view");
  v.innerHTML = `<section class="path catalog"><header class="path-head"><div><p class="eyebrow">Allenati</p><h1>Algoritmi</h1>
      <p class="goal muted">I problemi che tornano nei colloqui, divisi per schema e già verificati. Scegli uno schema e risolvili in ordine: prima ragioni sul metodo, poi riscrivi la soluzione.</p></div>
      <div class="seg" role="group" aria-label="Linguaggio">${["python", "java"].map(k => `<button type="button" data-cl="${k}" aria-pressed="${lang === k}">${QL[k]}</button>`).join("")}</div></header>
    <div id="catBody"><div class="empty">Caricamento…</div></div></section>`;
  v.onclick = catalogClick;
  Tutor.setContext("Lo studente sceglie un problema di algoritmi da allenare, diviso per schema (due puntatori, finestra scorrevole, grafi…).", "Algoritmi");
  Tutor.setQuick(["Da quale schema conviene partire?", "Come riconosco lo schema giusto?", "Quali schemi chiedono di più ai colloqui?"]);
  const d = await api(`/api/algoritmi?lang=${lang}`);
  if (App.view !== "catalog") return;
  App.cat = d;
  renderCatalog();
}
function renderCatalog() {
  const d = App.cat, f = App.catFilter || "tutti";
  const body = $("#catBody"); if (!body) return;
  if (!d.n) { body.innerHTML = `<div class="empty">Il catalogo non è ancora installato.</div>`; return; }
  const open = App.catOpen || {};
  body.innerHTML = `<div class="cat-top">
      <div class="cat-prog"><b>${d.done}</b> di ${d.n} risolti<div class="bar"><i style="width:${Math.round(d.done / d.n * 100)}%"></i></div></div>
      <div class="seg small" role="group" aria-label="Filtro">${[["tutti", "Tutti"], ["dafare", "Da fare"], ["fatti", "Fatti"]].map(([k, l]) => `<button type="button" data-cf="${k}" aria-pressed="${f === k}">${l}</button>`).join("")}</div>
      <button class="btn small" data-cat="next">Il prossimo da fare</button>
    </div>
    <div class="cat-list">${d.patterns.map(g => {
      const items = g.items.filter(x => f === "tutti" || (f === "fatti") === x.done);
      if (!items.length) return "";
      const isOpen = open[g.id] ?? (g.done < g.items.length && !Object.keys(open).length && g === d.patterns.find(p => p.done < p.items.length));
      return `<details class="cat-group" data-pat="${g.id}" ${isOpen ? "open" : ""}>
        <summary><b>${esc(g.name)}</b><span class="muted">${g.done}/${g.items.length}</span><span class="bar"><i style="width:${Math.round(g.done / g.items.length * 100)}%"></i></span></summary>
        <ol class="cat-items">${items.map(x => `<li><a href="#/oggi/${d.lang}/${x.id}" class="${x.done ? "done" : ""}">
          <span class="ck" aria-hidden="true">${x.done ? "✓" : ""}</span>
          <span class="t"><b>${esc(x.title)}</b><small class="muted">${inl(x.problem)}</small></span>
          <span class="tag">Livello ${x.tier}</span>${x.done ? `<span class="tag ok">${x.best}%</span>` : ""}</a></li>`).join("")}</ol>
      </details>`;
    }).join("")}</div>`;
}
function catalogClick(e) {
  const t = e.target.closest("button, summary"); if (!t) return;
  if (t.tagName === "SUMMARY") {
    const g = t.parentElement; App.catOpen = App.catOpen || {};
    setTimeout(() => { App.catOpen[g.dataset.pat] = g.open; }, 0);
    return;
  }
  if (t.dataset.cl) { App.catLang = t.dataset.cl; localStorage.setItem("ricalco.catlang", App.catLang); App.catOpen = null; showCatalog(); return; }
  if (t.dataset.cf) { App.catFilter = t.dataset.cf; renderCatalog(); return; }
  if (t.dataset.cat === "next") {
    const d = App.cat;
    const x = d.patterns.flatMap(g => g.items).filter(i => !i.done).sort((a, b) => a.tier - b.tier)[0];
    if (x) location.hash = `#/oggi/${d.lang}/${x.id}`; else toast("Li hai fatti tutti: ripassali con le flashcard.");
  }
}

/* Apre un esercizio preciso in «Oggi» (dal catalogo o da un link). */
async function openQuickItem(lang, id) {
  App.qlang = lang; localStorage.setItem("ricalco.qlang", lang);
  await showStart({noPick: true});
  const box = $("#quick"); if (!box) return;
  let d;
  try { d = await api(`/api/quick/item?lang=${lang}&id=${encodeURIComponent(id)}`); }
  catch (e) { box.innerHTML = `<div class="banner err">${esc(e.message)}</div>`; return; }
  if (App.view !== "start") return;
  $("#eloBox").innerHTML = eloHtml(d.elo);
  startQuick(d.item, {mode: "new", level: d.startLevel || 1, info: d, hist: d.blockHist});
}
