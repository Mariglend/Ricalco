"use strict";

/* ================================================================ motore di ricalco */
const KW = new Set(("and as assert async await break class continue def del elif else except False finally for from global if import in is lambda None nonlocal not or pass raise return True try while with yield print self len range " +
  "abstract boolean byte case catch char const default do double enum extends final float goto implements instanceof int interface long native new null package private protected public short static super switch synchronized this throw throws transient void volatile var record true false String System").split(" "));

const SQL_KW = new Set(("SELECT FROM WHERE AND OR NOT IN IS NULL AS ON JOIN LEFT RIGHT INNER OUTER FULL CROSS GROUP BY ORDER HAVING LIMIT OFFSET " +
  "DISTINCT INSERT INTO VALUES UPDATE SET DELETE CREATE TABLE VIEW INDEX DROP ALTER ADD PRIMARY KEY FOREIGN REFERENCES UNIQUE DEFAULT CHECK " +
  "INTEGER TEXT REAL BLOB NUMERIC CASE WHEN THEN ELSE END EXISTS BETWEEN LIKE ASC DESC UNION ALL WITH RECURSIVE OVER PARTITION BEGIN COMMIT " +
  "ROLLBACK TRANSACTION CASCADE IF COUNT SUM AVG MIN MAX ROUND COALESCE UPPER LOWER LENGTH SUBSTR ABS RANK DENSE_RANK ROW_NUMBER LAG LEAD " +
  "EXPLAIN QUERY PLAN AUTOINCREMENT TRUE FALSE").split(" "));
function tokenize(t, lang) {
  const ty = new Array(t.length).fill("pun");
  const hash = lang === "python", slash = lang === "java", sql = lang === "sql";
  const fill = (a, b, v) => { for (let k = a; k < b; k++) ty[k] = v; };
  let i = 0;
  while (i < t.length) {
    const c = t[i], n = t[i + 1];
    if (c === " " || c === "\n") { ty[i] = "ws"; i++; continue; }
    if ((c === "#" && hash) || (c === "/" && n === "/" && slash) || (c === "-" && n === "-" && sql)) { let j = t.indexOf("\n", i); if (j < 0) j = t.length; fill(i, j, "com"); i = j; continue; }
    if (c === "/" && n === "*" && (slash || sql)) { let j = t.indexOf("*/", i + 2); j = j < 0 ? t.length : j + 2; fill(i, j, "com"); for (let k = i; k < j; k++) if (t[k] === "\n") ty[k] = "ws"; i = j; continue; }
    if (c === '"' || c === "'") {
      const triple = hash && t.slice(i, i + 3) === c.repeat(3);
      let j = i + (triple ? 3 : 1);
      while (j < t.length) {
        if (t[j] === "\\") { j += 2; continue; }
        if (triple ? t.slice(j, j + 3) === c.repeat(3) : t[j] === c) break;
        if (!triple && t[j] === "\n") break;
        j++;
      }
      const end = Math.min(j + (triple ? 3 : 1), t.length);
      fill(i, end, "str"); ty[i] = "q"; if (end - 1 > i && t[end - 1] === c) ty[end - 1] = "q";
      for (let k = i; k < end; k++) if (t[k] === "\n") ty[k] = "ws";
      i = end; continue;
    }
    if (/[0-9]/.test(c)) { let j = i; while (j < t.length && /[0-9._xa-fA-FlLdD]/.test(t[j])) j++; fill(i, j, "num"); i = j; continue; }
    if (/[A-Za-z_$]/.test(c)) { let j = i; while (j < t.length && /[\w$]/.test(t[j])) j++; fill(i, j, (sql ? SQL_KW.has(t.slice(i, j).toUpperCase()) : KW.has(t.slice(i, j))) ? "kw" : "id"); i = j; continue; }
    i++;
  }
  return ty;
}

// Accenti: nel foglio da ricalcare la «è» diventa «é», e scrivendo valgono tutte e due (anche per à/á, ì/í, ò/ó, ù/ú).
const ACC_FOLD = {"è": "e", "é": "e", "È": "E", "É": "E", "à": "a", "á": "a", "ì": "i", "í": "i", "ò": "o", "ó": "o", "ù": "u", "ú": "u"};
const sameChar = (a, b) => a === b || (ACC_FOLD[a] !== undefined && ACC_FOLD[a] === ACC_FOLD[b]);
class Tracer {
  constructor(sheet, L, opts) {
    this.sheet = sheet; this.pre = $(".code", sheet); this.trap = $(".trap", sheet); this.opts = opts;
    this.L = L; this.level = opts.level || 1; this.blockLevel = opts.blockLevel || null;
    const B = L.blocks;
    this.text = B.map(b => b.code).join("\n").replace(/è/g, "é").replace(/È/g, "É");
    this.ty = tokenize(this.text, L.lang);
    this.bi = new Array(this.text.length).fill(0);
    this.B = [];
    let off = 0;
    B.forEach((b, k) => {
      const from = off, to = off + b.code.length;
      for (let i = from; i < Math.min(to + 1, this.text.length); i++) this.bi[i] = k;
      let e = to;
      while (e > from && !this.real(e - 1)) e--;
      this.B.push({from, to, effEnd: e});
      off = to + 1;
    });
    this.revealed = new Set(); this.missStreak = 0;
    this.pre.textContent = "";
    const frag = document.createDocumentFragment();
    this.spans = [];
    for (let i = 0; i < this.text.length; i++) { const s = document.createElement("span"); s.textContent = this.text[i]; frag.appendChild(s); this.spans.push(s); }
    this.pre.appendChild(frag);
    this.bind();
  }
  real(i) { const c = this.text[i]; return c !== " " && c !== "\n" && this.ty[i] !== "com"; }
  setState(k, phase) {
    this.cur = k; this.phase = phase; this.revealed.clear(); this.missStreak = 0;
    if (k >= this.B.length) this.pos = this.text.length;
    else { let p = this.B[k].from; while (p < this.text.length && !this.real(p)) p++; this.pos = p; }
    this.paint(); this.follow();
  }
  setLevel(n, blockLevel) { this.level = n; if (blockLevel !== undefined) this.blockLevel = blockLevel; this.paint(); }
  lv(k) { return (this.blockLevel && this.blockLevel[k]) || this.level; }
  paint() {
    const {text, ty, spans, pos, bi} = this;
    const vis = this.phase === "scrivi" ? this.cur : this.cur - 1;
    for (let i = 0; i < spans.length; i++) {
      const t = ty[i];
      let cls = "t-" + t + (text[i] === "\n" ? " nl" : "");
      if (i < pos) cls += " ok" + (this.revealed.has(i) ? " rev" : "");
      else if (bi[i] > vis) cls += " gone";
      else if (t === "com") cls += " gh";
      else if (this.lv(bi[i]) === 1) cls += " gh";
      else if (this.lv(bi[i]) === 2) cls += ((t === "id" || t === "num" || t === "str") && !this.revealed.has(i)) ? " mk" : " gh";
      else cls += this.revealed.has(i) ? " gh rev" : " gone";
      if (i === pos && this.phase === "scrivi") cls += " cur";
      if (spans[i].className !== cls) spans[i].className = cls;
      // i caratteri nascosti non restano nella pagina: selezionandoli o copiandoli non si leggono
      const hide = / (mk|gone)\b/.test(cls) && text[i] !== "\n";
      const ch = hide ? " " : text[i];
      if (spans[i].textContent !== ch) spans[i].textContent = ch;
    }
  }
  follow() {
    const sh = this.sheet;
    const c = this.spans[Math.min(this.pos, this.spans.length - 1)];
    if (!c) return;
    if (this.phase !== "scrivi") { sh.scrollTop = Math.max(0, (this.spans[Math.max(0, this.pos - 1)] || c).offsetTop - sh.clientHeight + 80); return; }
    const top = c.offsetTop, left = c.offsetLeft, lh = c.offsetHeight || 24;
    this.trap.style.top = top + "px"; this.trap.style.left = Math.min(left, this.pre.scrollWidth - 4) + "px";
    if (top < sh.scrollTop + lh) sh.scrollTop = Math.max(0, top - lh * 2);
    else if (top + lh * 2 > sh.scrollTop + sh.clientHeight) sh.scrollTop = top - sh.clientHeight / 2;
    if (left < sh.scrollLeft + 20) sh.scrollLeft = Math.max(0, left - 60);
    else if (left + 40 > sh.scrollLeft + sh.clientWidth) sh.scrollLeft = left - sh.clientWidth + 120;
  }
  skipComment() { while (this.pos < this.text.length && this.ty[this.pos] === "com") this.pos++; }
  skipAll() { while (this.pos < this.text.length && !this.real(this.pos)) this.pos++; }
  input(ch) {
    if (this.phase !== "scrivi") { this.opts.onLocked && this.opts.onLocked(ch); return; }
    const t = this.text, exp = t[this.pos], st = this.opts.stats;
    let ok = false;
    if (ch === "\n") {
      let j = this.pos;
      while (j < t.length && (t[j] === " " || this.ty[j] === "com")) j++;
      if (j >= t.length || t[j] === "\n") { this.pos = j; this.skipAll(); ok = true; }
    } else if (ch === " " || ch === "\t") {
      if (exp === " ") { while (this.pos < t.length && t[this.pos] === " ") this.pos++; this.skipComment(); ok = true; }
    } else if (sameChar(ch, exp)) { this.pos++; this.skipComment(); ok = true; }
    if (ok) {
      st.typed++; this.missStreak = 0;
      if (this.pos >= this.B[this.cur].effEnd) {
        this.phase = "wait"; this.paint();
        this.opts.onBlockDone(this.cur);
        return;
      }
    } else {
      st.errors++; this.missStreak++;
      st.blockErr[this.cur] = (st.blockErr[this.cur] || 0) + 1;
      if (this.lv(this.cur) > 1 && this.missStreak >= 3) { this.reveal(false); this.missStreak = 0; }
      this.miss(ch);
    }
    this.paint(); this.follow(); this.opts.onChange && this.opts.onChange();
  }
  reveal(manual) {
    if (this.phase !== "scrivi") return;
    if (this.lv(this.cur) === 1) { toast("Al livello 1 il blocco è già visibile."); return; }
    let i = this.pos, added = 0;
    while (i < this.text.length && this.text[i] !== " " && this.text[i] !== "\n") { if (!this.revealed.has(i)) { this.revealed.add(i); added++; } i++; }
    if (!added) return;
    this.opts.stats.hints++;
    const bh = this.opts.stats.blockHint = this.opts.stats.blockHint || {};
    bh[this.cur] = (bh[this.cur] || 0) + 1;
    if (!manual) toast("Tre errori di fila: ecco la parola.");
    this.paint(); this.opts.onChange && this.opts.onChange();
  }
  miss(ch) {
    const c = this.spans[this.pos]; if (!c) return;
    c.classList.add("miss");
    const tag = $(".miss-tag", this.sheet);
    tag.textContent = ch === " " ? "spazio" : ch === "\n" ? "invio" : ch === "\t" ? "tab" : ch;
    tag.style.left = c.offsetLeft + "px"; tag.style.top = c.offsetTop + "px";
    tag.classList.add("show");
    clearTimeout(this.missT);
    this.missT = setTimeout(() => { tag.classList.remove("show"); c.classList.remove("miss"); }, 450);
  }
  focus() { this.trap.focus({preventScroll: true}); }
  bind() {
    const trap = this.trap, sh = this.sheet;
    sh.addEventListener("mouseup", () => setTimeout(() => { if (!String(getSelection()).trim()) this.focus(); }, 0));
    trap.addEventListener("focus", () => sh.classList.add("focused"));
    trap.addEventListener("blur", () => sh.classList.remove("focused"));
    trap.addEventListener("keydown", e => {
      if (e.isComposing) return;
      if (e.key === "Enter") { e.preventDefault(); this.input("\n"); }
      else if (e.key === "Tab") { e.preventDefault(); this.input("\t"); }
      else if (e.key === "Backspace") e.preventDefault();
      else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "v") { e.preventDefault(); toast("Niente incolla: il punto è scriverlo."); }
    });
    trap.addEventListener("paste", e => { e.preventDefault(); toast("Niente incolla: il punto è scriverlo."); });
    trap.addEventListener("drop", e => e.preventDefault());
    trap.addEventListener("input", e => {
      if (e.isComposing) return;
      const v = trap.value; trap.value = "";
      for (const ch of v) this.input(ch === "\r" ? "\n" : ch);
    });
    trap.addEventListener("compositionend", () => { const v = trap.value; trap.value = ""; for (const ch of v) this.input(ch); });
  }
}
