"""Metodo Feynman: spiega la soluzione a un principiante."""

from .config import LANGNAME
from .llm import llm_json
from .generazione import ARR, STR, SYS_GEN


# ---- metodo Feynman: spiega la soluzione a un principiante
FY_ASK = {"type": "object", "properties": {"domande": ARR}, "required": ["domande"]}
FY_JUDGE = {"type": "object", "properties": {"chiarezza": {"type": "integer"}, "completezza": {"type": "integer"}, "correttezza": {"type": "integer"},
                                             "commento": STR, "mancava": STR, "spiegazione_semplice": STR},
            "required": ["chiarezza", "completezza", "correttezza", "commento", "mancava", "spiegazione_semplice"]}


def feynman(stage, lang, title, problem, code, explanation, qa):
    from .flashcard import card_add
    head = (f"Esercizio «{title}» ({LANGNAME.get(lang, lang)}). Problema: {problem}\nSoluzione:\n{code[:3500]}\n\n"
            f"Lo studente ha spiegato la soluzione con parole sue, come a un principiante:\n«{explanation}»\n")
    if qa:
        head += "".join(f"\nDomanda del principiante: {x.get('q')}\nRisposta dello studente: «{x.get('a')}»" for x in qa) + "\n"
    if stage == "ask":
        prompt = head + ("\nFai la parte di un PRINCIPIANTE curioso che non sa programmare bene. Hai letto la spiegazione: individua al massimo 2 punti "
                         "vaghi, saltati o sbagliati (il perché di una scelta, cosa succede in un caso limite, perché quella struttura dati, la complessità) "
                         "e fai una domanda breve per ciascuno, in italiano, dando del tu. Le domande devono costringere a spiegare meglio, "
                         "non rivelare la risposta. Se la spiegazione è già chiara e completa, \"domande\" è una lista vuota.")
        d = llm_json([{"role": "system", "content": SYS_GEN}, {"role": "user", "content": prompt}], FY_ASK, temperature=0.3, num_ctx=4096)
        return {"questions": [str(x).strip() for x in (d.get("domande") or []) if str(x).strip()][:2]}
    prompt = head + ("\nOra fai il tutor. Valuta la spiegazione dello studente (comprese le risposte) da 1 a 5 su: "
                     "\"chiarezza\" (parole semplici, ordine logico), \"completezza\" (idea, scelte, casi limite), \"correttezza\" (niente errori). "
                     "Sii esigente ma giusto: 5 solo se la capirebbe davvero un principiante. "
                     "\"commento\": 1-2 frasi rivolte allo studente. \"mancava\": il punto più importante che non ha spiegato bene, in una frase "
                     "(stringa vuota se non manca nulla). \"spiegazione_semplice\": come lo spiegheresti tu a un principiante, in 3-4 frasi senza codice.")
    d = llm_json([{"role": "system", "content": SYS_GEN}, {"role": "user", "content": prompt}], FY_JUDGE, temperature=0.1, num_ctx=4096)
    clamp = lambda v: max(1, min(5, int(v))) if isinstance(v, (int, float)) else 3
    res = {"clarity": clamp(d.get("chiarezza")), "complete": clamp(d.get("completezza")), "correct": clamp(d.get("correttezza")),
           "comment": str(d.get("commento") or ""), "missing": str(d.get("mancava") or "").strip(), "model": str(d.get("spiegazione_semplice") or "")}
    if res["missing"]:
        card_add("spiega", f"Spiega a un principiante: «{title}»\n\nIl punto che ti era sfuggito: {res['missing']}",
                 res["model"] or res["missing"], "feynman")
    return res
