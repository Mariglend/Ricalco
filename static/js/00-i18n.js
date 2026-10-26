"use strict";
/* Lingua dell'interfaccia. L'italiano è la lingua di partenza: le pagine sono scritte in italiano e, se è scelto
   l'inglese, questo file traduce i testi mentre compaiono (dizionario in /i18n/en.js, condiviso con il server).
   Il codice non si traduce mai: pre, code, textarea, editor e messaggi scritti dallo studente restano come sono. */
const UI_LANG = document.documentElement.lang === "en" ? "en" : "it";
const I18N = UI_LANG === "en" ? Object.assign({}, window.I18N_EN, window.I18N_EN_UI) : {};
const I18N_PATTERNS = Object.keys(I18N)
  .filter(k => k.includes("{}") && k.replace(/\{\}/g, "").length >= 3 && /[a-zà-ù]/i.test(k.replace(/\{\}/g, "")))
  .sort((a, b) => b.replace(/\{\}/g, "").length - a.replace(/\{\}/g, "").length)
  .map(k => [k.replace(/\{\}/g, "").length, new RegExp("^" + k.split("{}").map(p => p.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("(.+?)") + "$", "s"), I18N[k]]);

function t(s, depth = 0) {
  if (UI_LANG !== "en" || typeof s !== "string") return s;
  const core = s.trim();
  if (!core) return s;
  if (I18N[s] !== undefined) return I18N[s];
  if (I18N[core] !== undefined) return s.replace(core, I18N[core]);
  if (depth > 3 || core.length > 600) return s;
  // prima i modelli lunghi (specifici), poi gli elenchi «13 esercizi passati, 33 carte» pezzo per pezzo, poi i modelli corti
  const byPattern = long => {
    for (const [len, rx, v] of I18N_PATTERNS) {
      if (long !== len >= 14) continue;
      const m = core.match(rx);
      if (!m) continue;
      let out = v;
      for (const g of m.slice(1)) out = out.replace("{}", t(g, depth + 1));
      return out;
    }
    return null;
  };
  let hit = byPattern(true);
  if (hit !== null) return s.replace(core, hit);
  for (const sep of [" · ", ", "]) {
    if (!core.includes(sep)) continue;
    const parts = core.split(sep), tr = parts.map(p => t(p, depth + 1));
    if (tr.every((x, i) => x !== parts[i] || /^[\d\s.,%/+−-]*$/.test(parts[i]))) return s.replace(core, tr.join(sep));
  }
  hit = byPattern(false);
  if (hit !== null) return s.replace(core, hit);
  // testi composti da più pezzi: «13 esercizi valutati · Avanzato a 1175»
  if (core.includes(" · ")) {
    const out = core.split(" · ").map(p => t(p, depth + 1)).join(" · ");
    if (out !== core) return s.replace(core, out);
  }
  const num = core.match(/^([\d.,%+−-]+\s+)(\D.*)$/s);
  if (num) {
    const w = t(num[2], depth + 1);
    if (w !== num[2]) return s.replace(core, num[1] + w);
  }
  return s;
}

if (UI_LANG === "en") {
  const SKIP = "pre, code, textarea, script, style, .sheet, .ed, .out, .msg.user, [data-noi18n]";
  const SKIP_ATTR = "pre, code, .sheet, .ed, .out, .msg.user, [data-noi18n]";
  const ATTRS = ["placeholder", "title", "aria-label"];
  const fixText = n => {
    const p = n.parentElement;
    if (!p || p.closest(SKIP)) return;
    const v = n.nodeValue, w = t(v);
    if (w !== v) n.nodeValue = w;
  };
  const fixEl = el => {
    if (el.closest(SKIP_ATTR)) return;
    for (const a of ATTRS) {
      const v = el.getAttribute(a);
      if (v) { const w = t(v); if (w !== v) el.setAttribute(a, w); }
    }
    if (el.tagName === "INPUT" && (el.type === "button" || el.type === "submit") && el.value) el.value = t(el.value);
  };
  const walk = root => {
    if (root.nodeType === 3) return fixText(root);
    if (root.nodeType !== 1) return;
    fixEl(root);
    if (root.closest(SKIP)) return;
    root.querySelectorAll("[placeholder],[title],[aria-label],input[type=button],input[type=submit]").forEach(fixEl);
    const it = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    for (let n = it.nextNode(); n; n = it.nextNode()) fixText(n);
  };
  new MutationObserver(list => {
    for (const m of list) {
      if (m.type === "characterData") fixText(m.target);
      else if (m.type === "attributes") fixEl(m.target);
      else m.addedNodes.forEach(walk);
    }
  }).observe(document.documentElement, {childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ATTRS});
  document.addEventListener("DOMContentLoaded", () => walk(document.body));
  for (const f of ["alert", "confirm", "prompt"]) {
    const orig = window[f].bind(window);
    window[f] = (msg, ...rest) => orig(t(msg), ...rest);
  }
}

/* Selettore IT/EN nella barra in alto: cambia la lingua sul server (anche Qwen scriverà in quella lingua) e ricarica. */
document.addEventListener("DOMContentLoaded", () => {
  const box = document.getElementById("langSel");
  if (!box) return;
  box.querySelectorAll("button").forEach(b => {
    b.setAttribute("aria-pressed", String(b.dataset.lang === UI_LANG));
    b.addEventListener("click", async () => {
      if (b.dataset.lang === UI_LANG) return;
      try {
        await fetch("/api/config", {method: "POST", headers: {"Content-Type": "application/json", "X-Ricalco": "1"},
                                     body: JSON.stringify({lang: b.dataset.lang})});
      } catch (e) { /* il server non risponde: la pagina ricaricata lo mostrerà */ }
      location.reload();
    });
  });
});
