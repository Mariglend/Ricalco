"""Generazione degli esercizi SQL, verificati su SQLite."""

import json
import uuid

from .sql_runner import as_text as sql_as_text, is_ordered, run_sql, same_result
from .config import LLMError
from .llm import llm_json
from .esecuzione import norm_code
from .generazione import ARR, DIFF_TEXT, EX_TYPES, STR, SYS_GEN, fill_blanks, shuffled_lines


# ---------------------------------------------------------------- SQL
SQL_SETUP_RULE = ("Database SQLite. In \"setup\" scrivi CREATE TABLE e INSERT con dati realistici in italiano (al massimo 3 tabelle "
                  "e 12 righe per tabella), coerenti con l'ambientazione; inserisci qualche NULL o caso particolare se serve all'esercizio. "
                  "Usa solo SQL supportato da SQLite (niente funzioni di MySQL o PostgreSQL). ")


def sql_schema(kind):
    props = {"titolo": STR, "setup": STR}
    if kind == "quiz":
        props.update(domanda=STR, codice=STR, opzioni=ARR, corretta={"type": "integer"}, spiegazione=STR)
    elif kind == "predici":
        props.update(codice=STR, spiegazione=STR)
    elif kind == "riempi":
        props.update(consegna=STR, codice=STR, risposte=ARR, spiegazione=STR)
    else:
        props.update(consegna=STR, soluzione=STR, verifica=STR, suggerimenti=ARR)
        if kind in ("completa", "zero"):
            props["codice_iniziale"] = STR
        if kind == "bug":
            props.update(codice_con_bug=STR, spiegazione_bug=STR)
    return {"type": "object", "properties": props, "required": list(props)}


def sql_prompt(kind, diff, topic, avoid):
    avoid_txt = ("\nNon ripetere questi esercizi già presenti: " + "; ".join(avoid[-12:]) + ".") if avoid else ""
    head = f"Argomento: {topic}\nLinguaggio: SQL (SQLite). Difficoltà {DIFF_TEXT[diff]}.{avoid_txt}\n\n" + SQL_SETUP_RULE
    verifica = ("\"verifica\": se la soluzione modifica dati o tabelle (INSERT, UPDATE, DELETE, CREATE...), una SELECT con ORDER BY che mostra "
                "lo stato finale da confrontare; se la soluzione è una SELECT, stringa vuota. ")
    hints = "\"suggerimenti\": 3 indizi progressivi senza scrivere la query completa. \"titolo\": massimo 5 parole."
    if kind == "predici":
        return head + ("Esercizio «prevedi il risultato»: in \"codice\" una query di 2-10 righe il cui risultato ha da 1 a 6 righe e al massimo "
                       "4 colonne. Lo studente deve prevedere esattamente le righe. Inserisci un dettaglio che richieda ragionamento "
                       "(un filtro, un raggruppamento, un NULL, una join). Se il risultato ha più righe usa ORDER BY. "
                       "\"spiegazione\": perché il risultato è quello. \"titolo\": massimo 5 parole.")
    if kind == "quiz":
        return head + ("Esercizio a scelta multipla sulla COMPRENSIONE (cosa fa una clausola, quale query è giusta, cosa succede con i NULL...). "
                       "\"codice\": una query a cui la domanda si riferisce, oppure stringa vuota. \"opzioni\": 4 risposte brevi, una sola giusta. "
                       "\"corretta\": indice 0-3. \"spiegazione\": 1-2 frasi. \"titolo\": massimo 5 parole.")
    if kind == "riempi":
        return head + ("Esercizio «completa gli spazi»: in \"codice\" una query di 2-10 righe in cui da 1 a 3 parti brevi (una parola chiave, "
                       "una funzione, un operatore, un nome di colonna) sono sostituite da ___ (tre trattini bassi). \"risposte\": le parti mancanti "
                       "in ordine. Con le risposte la query deve funzionare e restituire almeno una riga. \"consegna\": cosa deve restituire. "
                       "\"spiegazione\": perché quelle risposte. \"titolo\": massimo 5 parole.")
    base = ("\"consegna\": cosa deve restituire o fare la query, citando colonne e ordinamento del risultato atteso. "
            "\"soluzione\": la query (o le istruzioni) corretta, che restituisce almeno una riga. " + verifica)
    if kind == "riordina":
        extra = "Esercizio «riordina le righe»: la soluzione ha 4-10 righe, una clausola per riga (SELECT, FROM, JOIN, WHERE, GROUP BY, HAVING, ORDER BY...)."
    elif kind == "zero":
        extra = "Esercizio da scrivere da zero: \"codice_iniziale\" contiene solo il commento `-- scrivi qui la query`."
    elif kind == "completa":
        extra = ("Esercizio «completa la query»: in \"codice_iniziale\" la soluzione con 1-2 parti importanti sostituite da un commento "
                 "`-- TODO: ...` che dice cosa manca, in modo che il risultato NON sia quello giusto.")
    else:
        extra = ("Esercizio «trova il bug»: in \"codice_con_bug\" la soluzione con UN errore logico realistico (INNER al posto di LEFT JOIN, "
                 "WHERE al posto di HAVING, condizione sbagliata, COUNT(*) al posto di COUNT(colonna), ordinamento invertito...) che cambia "
                 "il risultato senza errori di sintassi. \"spiegazione_bug\": spiega il bug.")
    return head + extra + " " + base + hints


def sql_tables(setup):
    r = run_sql(setup, "", tables=True)
    return r.get("tables") or {}


def prep_sql(ex):
    """Completa un esercizio SQL (seed o generato) con anteprima tabelle e risultato atteso."""
    setup = ex.get("setup", "")
    ex["check"] = ex.get("check") or "sql"
    if ex["check"] == "sql" and "tables" not in ex:
        ex["tables"] = sql_tables(setup)
    t = ex["type"]
    if t == "predici" and "output" not in ex:
        r = run_sql(setup, ex["code"])
        ex["output"] = sql_as_text(r.get("result"))
        ex["outCols"] = (r.get("result") or {}).get("cols", [])
    elif t == "riempi" and "expected" not in ex:
        r = run_sql(setup, fill_blanks(ex["code"], ex["answers"]), ex.get("verify"))
        ex["expected"], ex["ordered"] = r.get("result"), is_ordered(ex["code"])
    elif t in ("riordina", "completa", "bug", "zero") and "expected" not in ex:
        r = run_sql(setup, ex["solution"], ex.get("verify"))
        ex["expected"], ex["ordered"] = r.get("result"), is_ordered(ex.get("verify") or ex["solution"])
        if t == "riordina" and "lines" not in ex:
            lines, mixed = shuffled_lines(ex["solution"])
            ex["solution"], ex["lines"] = "\n".join(lines), mixed
    return ex


def generate_sql_exercise(kind, diff, topic, avoid, attempts=4):
    msgs = [{"role": "system", "content": SYS_GEN}, {"role": "user", "content": sql_prompt(kind, diff, topic, avoid)}]
    schema = sql_schema(kind)
    base = {"id": "e" + uuid.uuid4().hex[:10], "type": kind, "difficulty": diff, "lang": "sql", "check": "sql"}
    for attempt in range(attempts):
        data = llm_json(msgs, schema, temperature=0.6 if attempt == 0 else 0.35)
        problem, ex = None, None
        title = str(data.get("titolo") or EX_TYPES[kind])[:70]
        setup = str(data.get("setup") or "").strip()
        rs = run_sql(setup, "")
        if not setup:
            problem = "Manca il setup con CREATE TABLE e INSERT."
        elif rs.get("error"):
            problem = "Il setup va in errore: " + rs["error"][:500]
        elif kind == "quiz":
            opts = [str(o).strip() for o in (data.get("opzioni") or []) if str(o).strip()][:5]
            c = data.get("corretta")
            if not data.get("domanda") or len(opts) < 3 or not isinstance(c, int) or not 0 <= c < len(opts):
                problem = "Servono domanda, 4 opzioni e l'indice della risposta giusta."
            else:
                ex = dict(base, title=title, setup=setup, question=str(data["domanda"]), code=norm_code(data.get("codice")),
                          options=opts, correct=c, explain=str(data.get("spiegazione") or ""))
        elif kind == "predici":
            code = norm_code(data.get("codice"))
            r = run_sql(setup, code)
            res = r.get("result")
            if r.get("error") or not res:
                problem = "La query non funziona o non restituisce righe: " + str(r.get("error") or "nessun risultato")[:500]
            elif not 1 <= len(res["rows"]) <= 6 or len(res["cols"]) > 4:
                problem = f"Il risultato ha {len(res['rows'])} righe e {len(res['cols'])} colonne: servono 1-6 righe e al massimo 4 colonne."
            else:
                ex = dict(base, title=title, setup=setup, code=code, explain=str(data.get("spiegazione") or ""))
        elif kind == "riempi":
            code = norm_code(data.get("codice"))
            ans = [str(a).strip().strip("`") for a in (data.get("risposte") or []) if str(a).strip()]
            n = code.count("___")
            if not 1 <= n <= 3 or n != len(ans):
                problem = f"Servono da 1 a 3 spazi ___ e altrettante risposte (ora {n} spazi e {len(ans)} risposte)."
            else:
                r = run_sql(setup, fill_blanks(code, ans))
                if r.get("error") or not r.get("result") or not r["result"]["rows"]:
                    problem = "Con le risposte la query non funziona o non restituisce righe: " + str(r.get("error") or "")[:400]
                else:
                    ex = dict(base, title=title, setup=setup, code=code, answers=ans, statement=str(data.get("consegna") or ""),
                              explain=str(data.get("spiegazione") or ""))
        else:
            sol = norm_code(data.get("soluzione"))
            verify = norm_code(data.get("verifica")) or None
            r = run_sql(setup, sol, verify)
            res = r.get("result")
            if r.get("error") or not res or not res["rows"]:
                problem = "La soluzione non funziona o non restituisce righe: " + str(r.get("error") or "nessun risultato")[:500]
            else:
                ex = dict(base, title=title, setup=setup, solution=sol, verify=verify, statement=str(data.get("consegna") or ""),
                          hints=[str(h) for h in (data.get("suggerimenti") or []) if str(h).strip()][:4])
                if kind in ("completa", "zero", "bug"):
                    start = norm_code(data.get("codice_con_bug" if kind == "bug" else "codice_iniziale"))
                    rr = run_sql(setup, start, verify) if start else {"error": "vuoto"}
                    if not start:
                        problem = "Manca il codice di partenza."
                    elif kind == "bug" and rr.get("error"):
                        problem = "La query con il bug va in errore: il bug deve essere logico. " + rr["error"][:300]
                    elif not rr.get("error") and same_result(res, rr.get("result"), is_ordered(verify or sol)):
                        problem = "Il codice di partenza restituisce già il risultato giusto: deve essere diverso."
                    ex["starter"] = start
                    if kind == "bug":
                        ex["bugExplain"] = str(data.get("spiegazione_bug") or "")
                if kind == "riordina" and not problem:
                    lines = [l for l in sol.split("\n") if l.strip()]
                    if not 3 <= len(lines) <= 12:
                        problem = "La soluzione deve avere 4-10 righe, una clausola per riga."
        if ex and not problem:
            ex = prep_sql(ex)
            ex["state"] = {"solved": False, "attempts": 0, "hints": 0, "revealed": False}
            ex["genAttempts"] = attempt + 1
            return ex
        msgs = msgs[:2] + [{"role": "assistant", "content": json.dumps(data, ensure_ascii=False)},
                           {"role": "user", "content": (problem or "Errore") + "\nRestituisci di nuovo tutto il JSON corretto."}]
    raise LLMError("Il modello non è riuscito a creare un esercizio SQL che funzioni. Riprova o scegli un altro tipo.")
