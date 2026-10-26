"use strict";

/* ================================================================ metodo Feynman: dopo ogni codice, spiegalo a un principiante */
function mountFeynman(host, o) {
  if (!host) return;
  const st = o.st;
  const dots = n => `<span class="dots">${[1, 2, 3, 4, 5].map(i => `<i class="${i <= n ? "on" : ""}"></i>`).join("")}</span>`;
  const head = `<div class="fy-head"><span class="eyebrow">Spiegalo a un principiante</span><span class="spacer"></span>${["write", "answer"].includes(st.phase) ? `<button class="linkish" data-fy="skip">Salta</button>` : ""}</div>`;
  let body = "";
  if (st.phase === "skipped") body = `<p class="muted" style="margin:0;font-size:13px">Spiegazione saltata. <button class="linkish" data-fy="reopen">Spiegalo ora</button></p>`;
  else if (st.phase === "write") body = `<p class="explain" style="margin:0">Scrivi come funziona la soluzione a qualcuno che non sa programmare: l'idea, perché questa struttura, cosa succede nel caso limite${o.lang === "sql" ? "" : ", quanto costa"}. Niente codice.</p>
    <textarea class="open-ans fy-ans" data-fyin="expl" placeholder="L'idea è… Uso … perché … Se la lista è vuota…">${esc(st.expl || "")}</textarea>
    <div class="row"><button class="btn primary" data-fy="send">Spiega</button><span class="muted" style="font-size:12.5px">Il principiante (Qwen) leggerà e ti farà domande sui punti vaghi.</span></div>`;
  else if (st.phase === "asking" || st.phase === "judging") body = `<p class="muted"><span class="spin small"></span> ${st.phase === "asking" ? "Il principiante legge la tua spiegazione…" : "Valuto la spiegazione…"}</p>`;
  else if (st.phase === "answer") body = `<div class="fy-you"><b>Tu:</b> ${esc(st.expl)}</div>
    <div class="fy-q"><b>Il principiante chiede:</b><ol>${st.qs.map(q => `<li>${inl(q)}</li>`).join("")}</ol></div>
    <textarea class="open-ans fy-ans" data-fyin="ans" placeholder="Rispondi alle domande con parole semplici">${esc(st.ans || "")}</textarea>
    <div class="row"><button class="btn primary" data-fy="answer">Rispondi</button></div>`;
  else if (st.phase === "done" && st.res) {
    const r = st.res, tot = r.clarity + r.complete + r.correct;
    body = `<div class="fy-res ${tot >= 12 ? "good" : tot >= 9 ? "mid" : "bad"}">
      <div class="fy-scores"><span>Chiarezza ${dots(r.clarity)}</span><span>Completezza ${dots(r.complete)}</span><span>Correttezza ${dots(r.correct)}</span></div>
      ${r.comment ? `<p class="explain">${inl(r.comment)}</p>` : ""}
      ${r.missing ? `<p class="explain"><b>Ti mancava:</b> ${inl(r.missing)} <span class="muted">(torna nel ripasso)</span></p>` : ""}
      ${r.model ? `<details><summary class="muted" style="cursor:pointer">Come lo spiegherebbe il tutor</summary><p class="explain">${inl(r.model)}</p></details>` : ""}
      <small class="muted">Valutazione del modello.</small></div>`;
  } else if (st.phase === "error") body = `<div class="res-err"><span>${esc(st.err || "")}</span><div class="row"><button class="btn small" data-fy="retry">Riprova</button><button class="linkish" data-fy="skip">Salta</button></div></div>`;
  host.innerHTML = `<div class="fy">${head}${body}</div>`;
  host.oninput = e => { const k = e.target.dataset.fyin; if (k) st[k] = e.target.value; };
  host.onkeydown = e => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey) && e.target.dataset.fyin) { e.preventDefault(); const b = $(st.phase === "write" ? '[data-fy="send"]' : '[data-fy="answer"]', host); if (b) b.click(); }
  };
  host.onclick = async e => {
    const b = e.target.closest("[data-fy]"); if (!b) return;
    const a = b.dataset.fy;
    const call = (stage, qa) => api("/api/feynman", {method: "POST", body: {stage, lang: o.lang, title: o.title, problem: o.problem, code: o.code, explanation: st.expl, qa}});
    if (a === "skip") { st.phase = "skipped"; LOG.ev("feynman_skip", {title: o.title}); return mountFeynman(host, o); }
    if (a === "reopen") { st.phase = "write"; mountFeynman(host, o); const t = $(".fy-ans", host); if (t) t.focus(); return; }
    const judge = async qa => {
      st.phase = "judging"; mountFeynman(host, o);
      try { st.res = await call("judge", qa); st.phase = "done"; } catch (err) { st.phase = "error"; st.err = err.message; st.retry = "judge"; }
      mountFeynman(host, o);
      if (st.phase === "done" && o.onDone) o.onDone(st.res);
    };
    if (a === "send" || (a === "retry" && st.retry === "ask")) {
      if ((st.expl || "").trim().length < 20) { toast("Scrivi almeno un paio di frasi."); return; }
      st.phase = "asking"; mountFeynman(host, o);
      try { const r = await call("ask", []); st.qs = r.questions; }
      catch (err) { st.phase = "error"; st.err = err.message; st.retry = "ask"; return mountFeynman(host, o); }
      if (!st.qs.length) return judge([]);
      st.phase = "answer"; mountFeynman(host, o);
      const t = $(".fy-ans", host); if (t) t.focus();
      return;
    }
    if (a === "answer" || (a === "retry" && st.retry === "judge")) {
      if (a === "answer" && (st.ans || "").trim().length < 5) { toast("Rispondi alle domande."); return; }
      return judge(st.qs && st.qs.length ? [{q: st.qs.join(" / "), a: st.ans}] : []);
    }
  };
}
function feynmanFor(ex, lang) {
  const host = $("#fyHost"); if (!host || !ex.solution) return;
  ex.state.fy = ex.state.fy || {phase: "write"};
  mountFeynman(host, {st: ex.state.fy, lang, title: ex.title, problem: ex.statement || "", code: ex.solution});
}
