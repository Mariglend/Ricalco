"""Generazione con il modello: lezioni ed esercizi verificati eseguendoli, giudizi, revisione del codice."""

import json
import random
import re
import time
import uuid

from .config import LANGNAME, LLMError, RUNNERS, SPRING
from .llm import llm_json
from .esecuzione import failing_summary, norm_code, norm_tests, run_program, run_tests


# ---------------------------------------------------------------- generazione
SYS_GEN = ("Sei un insegnante di programmazione che prepara materiale per studenti junior italiani. "
           "Scrivi codice corretto, semplice e idiomatico, con nomi di variabili e funzioni in italiano senza accenti. "
           "Tutti i testi sono in italiano. Rispondi solo con JSON valido.")

STR = {"type": "string"}
LESSON_SCHEMA = {
    "type": "object",
    "properties": {
        "titolo": STR, "obiettivo": STR,
        "concetti": {"type": "array", "items": STR},
        "blocchi": {"type": "array", "items": {
            "type": "object",
            "properties": {"codice": STR, "domanda": STR, "opzioni": {"type": "array", "items": STR},
                           "corretta": {"type": "integer"}, "perche": STR, "spiegazione": STR},
            "required": ["codice", "domanda", "opzioni", "corretta", "perche", "spiegazione"]}}},
    "required": ["titolo", "obiettivo", "concetti", "blocchi"]}


def lang_rules_program(lang):
    if lang == "sql":
        return ("Il codice è uno script SQLite completo: crea le tabelle con CREATE TABLE, inserisce pochi dati realistici con INSERT, "
                "poi esegue le query che mostrano i concetti, ciascuna preceduta da un commento -- che dice cosa fa. Solo SQL supportato da SQLite.")
    if lang == "python":
        return ("Il codice è uno script Python 3 completo ed eseguibile: definisce funzioni o classi e in fondo le usa "
                "con alcuni print che mostrano i risultati. Niente input(), file esterni, librerie esterne o numeri casuali.")
    return ("Il codice è un programma Java completo con una sola classe `public class Main` che contiene "
            "`public static void main(String[] args)` e, se servono, altri metodi static o classi annidate static. "
            "Il main usa il codice e stampa i risultati con System.out.println. Solo librerie standard "
            "(gli import vanno all'inizio). Niente Scanner, file o numeri casuali.")


def lesson_prompt(req, lang, level):
    size = ("principiante: concetti base, 15-35 righe in tutto" if level == "base"
            else "intermedio: 30-60 righe, gestisci anche i casi limite")
    return f"""Lo studente vuole imparare: «{req}»
Linguaggio: {LANGNAME[lang]}. Livello: {size}.

Prepara una lezione. {lang_rules_program(lang)}

Dividi il programma in 4-7 blocchi CONSECUTIVI: concatenandoli in ordine si ottiene il programma completo, con l'indentazione corretta. Ogni blocco è un'idea (una funzione, un controllo, un ciclo, la parte che stampa...).
Per ogni blocco:
- "codice": le righe del blocco.
- "domanda": una domanda di RAGIONAMENTO che lo studente affronta PRIMA di vedere il blocco. Deve farlo pensare alla logica: cosa serve fare, cosa succede in un caso limite, quale scelta è giusta e perché. Non chiedere sintassi a memoria e non mostrare il codice del blocco.
- "opzioni": 4 risposte brevi, una sola giusta, le altre plausibili ma sbagliate.
- "corretta": indice (0-3) della risposta giusta; non metterla sempre nella stessa posizione.
- "perche": 1-2 frasi che spiegano perché la risposta è giusta.
- "spiegazione": 2-4 frasi sul PERCHÉ il blocco è scritto così: il concetto chiave, cosa succederebbe senza, l'errore tipico di chi inizia.
"titolo": massimo 6 parole. "obiettivo": una frase su cosa saprà fare lo studente. "concetti": 2-5 concetti chiave in poche parole."""


def build_lesson(data):
    blocks = []
    for b in data.get("blocchi") or []:
        if not isinstance(b, dict):
            continue
        code = norm_code(b.get("codice"))
        if not code.strip():
            continue
        opts = [str(o).strip() for o in (b.get("opzioni") or []) if str(o).strip()]
        c = b.get("corretta")
        q = None
        if str(b.get("domanda") or "").strip() and len(opts) >= 2 and isinstance(c, int) and 0 <= c < len(opts):
            q = {"q": str(b["domanda"]), "options": opts, "correct": c, "why": str(b.get("perche") or "")}
        blocks.append({"code": code, "question": q, "explain": str(b.get("spiegazione") or "")})
    return blocks


# Errori che Qwen ripete spesso: oltre al messaggio gli diciamo la causa e come si corregge.
ERROR_HINTS = [
    (r"stream has already been operated upon or closed",
     "CAUSA: uno stream Java si può usare UNA SOLA VOLTA. Non salvare mai uno stream in una variabile (Stream<...> s = lista.stream()) "
     "per riusarlo: per ogni operazione crea un nuovo stream partendo dalla collezione, per esempio lista.stream().filter(...) "
     "e poi di nuovo lista.stream().anyMatch(...). Se ti serve riusare dei dati, salva il RISULTATO in una List con .toList()."),
    (r"ConcurrentModificationException",
     "CAUSA: stai modificando una collezione mentre la scorri con for-each. Usa un Iterator con remove(), removeIf, oppure una copia."),
    (r"UnsupportedOperationException",
     "CAUSA: List.of, Map.of, Arrays.asList e .toList() restituiscono collezioni immutabili. Se devi aggiungere o togliere elementi "
     "usa new ArrayList<>(...) o new HashMap<>(...)."),
    (r"NullPointerException",
     "CAUSA: usi un valore null. Inizializza le variabili e controlla i get() delle mappe (usa getOrDefault)."),
    (r"(IndexOutOfBounds|ArrayIndexOutOfBounds)",
     "CAUSA: un indice fuori dai limiti. Controlla i cicli: l'ultimo indice valido è length-1 / size()-1."),
    (r"NoSuchElementException",
     "CAUSA: get() su un Optional vuoto o next() su un iteratore finito. Usa orElse/orElseThrow con un controllo, o hasNext()."),
    (r"IllegalStateException: Duplicate key",
     "CAUSA: Collectors.toMap con chiavi ripetute. Passa una funzione di unione come terzo argomento, per esempio (a, b) -> a + b."),
    (r"(KeyError|IndexError|TypeError|AttributeError|NameError)",
     "Leggi la riga indicata nel traceback e correggi la causa: la soluzione deve girare senza eccezioni dall'inizio alla fine."),
]


def error_hint(err):
    hints = [h for pat, h in ERROR_HINTS if re.search(pat, err or "")]
    return ("\n" + "\n".join(hints[:2])) if hints else ""


def generate_lesson(req, lang, level, extra="", run_check=True):
    msgs = [{"role": "system", "content": SYS_GEN}, {"role": "user", "content": lesson_prompt(req, lang, level) + ("\n\n" + extra if extra else "")}]
    last = None
    for attempt in range(3):
        data = llm_json(msgs, LESSON_SCHEMA, temperature=0.35 if attempt == 0 else 0.2)
        blocks = build_lesson(data)
        if len(blocks) < 2:
            feedback = "Servono almeno 3 blocchi con codice. Restituisci di nuovo tutto il JSON."
        else:
            code = "\n".join(b["code"] for b in blocks)
            run = run_program(lang, code) if run_check else {"ok": True, "stdout": "", "error": None, "skipped": True}
            last = (data, blocks, run)
            if run["ok"]:
                break
            feedback = ("Eseguendo il programma ottenuto concatenando i blocchi c'è questo errore:\n"
                        + (run["error"] or "")[:1200] + error_hint(run["error"])
                        + "\nCorreggi il codice (attenzione all'indentazione tra un blocco e l'altro) "
                          "e restituisci di nuovo tutto il JSON.")
        msgs = msgs[:2] + [{"role": "assistant", "content": json.dumps(data, ensure_ascii=False)},
                           {"role": "user", "content": feedback}]
    if not last:
        raise LLMError("Il modello non è riuscito a preparare la lezione. Riprova o riformula la richiesta.")
    data, blocks, run = last
    now = time.time()
    return {
        "id": "l" + uuid.uuid4().hex[:10], "kind": "lesson", "request": req, "lang": lang, "level": level,
        "title": str(data.get("titolo") or req)[:80], "goal": str(data.get("obiettivo") or ""),
        "concepts": [str(c) for c in (data.get("concetti") or [])][:6],
        "blocks": blocks, "verified": None if run.get("skipped") else run["ok"], "output": run["stdout"] if run["ok"] else "",
        "runError": None if run["ok"] else run["error"],
        "progress": {"block": 0, "phase": "ragiona", "done": False, "stats": {}},
        "exercises": [], "created": now, "updated": now}


TEST_ITEMS = {"type": "array", "items": {"type": "object", "properties": {
    "descrizione": STR, "chiamata": STR, "atteso": STR}, "required": ["chiamata", "atteso"]}}

EX_TYPES = {
    "logica": "Problema di logica",
    "orale": "Domanda da colloquio",
    "quiz": "Domanda",
    "riempi": "Completa gli spazi",
    "predici": "Prevedi l'output",
    "riordina": "Riordina le righe",
    "completa": "Completa il codice",
    "bug": "Trova il bug",
    "zero": "Scrivi da zero",
}
DIFF_TEXT = {
    "facile": "FACILE: un solo concetto, soluzione di 3-8 righe, nessun caso limite complicato",
    "medio": "MEDIA: uno o due concetti, soluzione di 6-15 righe, almeno un caso limite (vuoto, zero, negativo...)",
    "difficile": "DIFFICILE: combina più concetti, soluzione di 12-30 righe, più casi limite",
}
ARR = {"type": "array", "items": STR}
LOGIC_DIFF = {"facile": "FACILE: si risolve con uno o due passaggi di ragionamento",
              "medio": "MEDIA: servono 3-4 passaggi o un piccolo conteggio",
              "difficile": "DIFFICILE: bisogna combinare più vincoli o trovare un'idea non ovvia"}


def ex_schema(kind, mode="tests"):
    if kind == "predici":
        props = {"titolo": STR, "codice": STR, "spiegazione": STR}
    elif kind == "logica":
        props = {"titolo": STR, "problema": STR, "opzioni": ARR, "risposta": STR, "spiegazione": STR, "codice_verifica": STR}
    elif kind == "orale":
        props = {"titolo": STR, "domanda": STR, "punti_chiave": ARR, "risposta_modello": STR, "domanda_approfondimento": STR}
    elif kind == "quiz":
        props = {"titolo": STR, "domanda": STR, "codice": STR, "opzioni": ARR, "corretta": {"type": "integer"}, "spiegazione": STR}
    elif kind == "riempi":
        props = {"titolo": STR, "consegna": STR, "codice": STR, "risposte": ARR, "spiegazione": STR}
    else:
        props = {"titolo": STR, "consegna": STR, "soluzione": STR}
        if mode == "tests":
            props["test"] = TEST_ITEMS
        if mode == "spring":
            props["test_junit"] = STR
        if mode == "review":
            props["criteri"] = ARR
        props["suggerimenti"] = ARR
        if kind in ("completa", "zero"):
            props["codice_iniziale"] = STR
        if kind == "bug":
            props["codice_con_bug"] = STR
            props["spiegazione_bug"] = STR
    return {"type": "object", "properties": props, "required": list(props)}


def program_rule(lang):
    if lang == "python":
        return "script Python 3 completo ed eseguibile"
    return "programma Java completo con `public class Main` e `public static void main(String[] args)`"


def lang_rules_tests(lang):
    if lang == "python":
        return ("La soluzione definisce funzioni (ed eventualmente classi) Python 3 che RESTITUISCONO un valore: niente input(), niente print obbligatori, "
                "niente eccezioni non gestite. Ogni test ha \"chiamata\": un'espressione Python come `conta_vocali(\"ciao\")` "
                "o `Punto(3, 4).distanza()`, e \"atteso\": il valore atteso come letterale Python, per esempio `2`, `\"abc\"`, `[1, 2]`, `True`, `None`.")
    return ("La soluzione è codice Java SENZA main e senza la parola public davanti alle classi: una `class Soluzione { ... }` con metodi `static` "
            "che RESTITUISCONO un valore (niente void, niente Scanner), più eventuali altre classi o interfacce (anche loro senza public). "
            "Eventuali import (es. `import java.util.*;`) vanno in cima. Ogni test ha \"chiamata\": un'espressione Java come "
            "`Soluzione.contaVocali(\"ciao\")` o `new Punto(3, 4).getX()`, e \"atteso\": il valore atteso come espressione Java dello stesso tipo, "
            "per esempio `2`, `\"abc\"`, `true`, `new int[]{1, 2}`, `List.of(1, 2)`, `2.5`.")


def exercise_prompt(kind, lang, diff, topic, avoid, mode="tests"):
    avoid_txt = ("\nNon ripetere questi esercizi già presenti: " + "; ".join(avoid[-12:]) + ".") if avoid else ""
    if kind == "logica":
        return (f"Tema: {topic}\nDifficoltà {LOGIC_DIFF[diff]}.{avoid_txt}\n\n"
                "Scrivi UN problema di logica originale, in italiano, con una sola risposta corretta e breve (un numero, un nome, una parola). "
                "\"problema\": testo completo e autosufficiente, senza ambiguità. \"opzioni\": 4 risposte brevi e plausibili, una è quella giusta. "
                "\"risposta\": la risposta corretta, scritta ESATTAMENTE come nella sua opzione. \"spiegazione\": il ragionamento passo per passo. "
                "\"codice_verifica\": uno script Python 3 che risolve il problema da zero, in modo indipendente (calcolo diretto o forza bruta, "
                "per esempio con itertools), e stampa SOLO la risposta, scritta esattamente come in \"risposta\". Non scrivere la risposta già pronta "
                "dentro il print: il codice deve calcolarla. \"titolo\": massimo 4 parole.")
    if kind == "orale":
        return (f"Contesto: {topic}.{avoid_txt}\n\n"
                "Prepara UNA domanda da colloquio tecnico, come la farebbe un selezionatore, su un argomento diverso da quelli già presenti. "
                "\"domanda\": chiara e concreta. \"punti_chiave\": 3-6 punti che una buona risposta deve toccare. "
                "\"risposta_modello\": la risposta ideale di un candidato preparato, 60-150 parole, con nomi e frammenti di codice tra backtick. "
                "\"domanda_approfondimento\": la domanda successiva che farebbe il selezionatore. \"titolo\": massimo 4 parole.")
    head = f"Argomento: {topic}\nLinguaggio: {LANGNAME[lang]}. Difficoltà {DIFF_TEXT[diff]}.{avoid_txt}\n\n"
    prog = program_rule(lang)
    if kind == "predici":
        return head + (f"Scrivi un esercizio «prevedi l'output»: un breve {prog} (4-18 righe) che lo studente deve leggere "
                       "per prevedere ESATTAMENTE cosa stampa. Deve stampare da 1 a 6 righe, senza input e senza numeri casuali. "
                       "Inserisci un dettaglio che richieda ragionamento (un ciclo, una condizione, un indice, un aggiornamento di variabile, una conversione). "
                       "In \"codice\" il programma completo. In \"spiegazione\" spiega passo per passo perché stampa quello. "
                       "\"titolo\": massimo 5 parole.")
    if kind == "quiz":
        return head + ("Scrivi una domanda a scelta multipla che verifica la COMPRENSIONE di un concetto (cosa succede, perché, quale scelta è giusta), "
                       f"non la memoria di un nome. Se serve, in \"codice\" metti un frammento di codice (al massimo 8 righe) a cui la domanda si riferisce, "
                       f"altrimenti una stringa vuota. Se la domanda chiede cosa stampa, il frammento deve essere un {prog} e una delle opzioni "
                       "deve essere ESATTAMENTE l'output. \"opzioni\": 4 risposte brevi, una sola giusta, le altre basate su errori tipici. "
                       "\"corretta\": indice 0-3 della giusta (varia la posizione). \"spiegazione\": 1-2 frasi. \"titolo\": massimo 5 parole.")
    if kind == "riempi":
        return head + (f"Scrivi un esercizio «completa gli spazi»: un {prog} di 3-14 righe che stampa qualcosa, in cui da 1 a 3 parti brevi "
                       "(una parola chiave, un operatore, un nome di metodo o di variabile, un valore) sono sostituite da ___ (tre trattini bassi). "
                       "\"risposte\": le parti mancanti, nell'ordine in cui compaiono. Inserendo le risposte il programma deve funzionare. "
                       "\"consegna\": in una frase, cosa deve stampare o fare il programma. \"spiegazione\": perché quelle risposte. "
                       "\"titolo\": massimo 5 parole.")
    if mode == "spring" and kind in ("completa", "bug", "zero", "riordina"):
        return head + spring_prompt(kind)
    if mode in ("review", "spring"):
        return head + review_prompt(kind, lang)
    hints = ("In \"suggerimenti\" 3 indizi progressivi, dal più vago al quasi-soluzione, senza mai scrivere il codice completo. "
             "\"titolo\": massimo 5 parole.")
    if mode == "output":
        common = (f"La soluzione è un {prog} che stampa il risultato (niente input, niente numeri casuali, da 1 a 10 righe di output). "
                  "I dati di partenza sono già scritti nel codice. In \"consegna\" spiega cosa deve fare il programma e cosa deve stampare. " + hints)
        if kind == "zero":
            extra = ("Esercizio da risolvere da zero. In \"codice_iniziale\" metti solo il punto di partenza: i dati già assegnati alle variabili "
                     + ("e un commento `# TODO`." if lang == "python" else "dentro il main e un commento `// TODO`, con la classe Main completa."))
        elif kind == "completa":
            extra = ("Esercizio «completa il codice». In \"codice_iniziale\" metti la soluzione con 1-3 parti importanti sostituite da un commento "
                     + ("`# TODO: ...`" if lang == "python" else "`// TODO: ...`") + " in modo che il programma giri ma NON stampi il risultato giusto. "
                     "Il commento dice cosa manca, non come farlo.")
        elif kind == "bug":
            extra = ("Esercizio «trova il bug». In \"codice_con_bug\" metti la soluzione con UN solo errore logico realistico "
                     "(off-by-one, condizione invertita, variabile non aggiornata, operatore sbagliato...) che cambia l'output, senza errori di sintassi. "
                     "La \"consegna\" descrive cosa DOVREBBE stampare il programma, senza dire dov'è il bug. In \"spiegazione_bug\" spiega il bug.")
        else:
            extra = ("Esercizio «riordina le righe»: la soluzione deve avere 5-14 righe non vuote, una istruzione per riga, senza righe vuote né commenti: "
                     "lo studente riceverà le righe mescolate e dovrà rimetterle in ordine.")
        return head + extra + "\n" + common
    common = lang_rules_tests(lang) + " Scrivi 3-6 test. In \"consegna\" spiega cosa deve fare il codice, con un esempio. " + hints
    if kind == "zero":
        extra = ("Esercizio da risolvere da zero. In \"codice_iniziale\" metti SOLO la firma della funzione/metodo con un commento TODO "
                 + ("e `pass` come corpo." if lang == "python" else "dentro `class Soluzione { }` e un return provvisorio (es. `return 0;`, `return \"\";`, `return null;`)."))
    elif kind == "completa":
        extra = ("Esercizio «completa il codice». In \"codice_iniziale\" metti la soluzione con 1-3 parti importanti sostituite da un commento "
                 + ("`# TODO: ...` seguito da `pass` dove serve," if lang == "python" else "`// TODO: ...` (lascia un return provvisorio se serve),")
                 + " in modo che il codice compili ma NON superi i test. Il commento dice cosa manca, non come farlo.")
    elif kind == "bug":
        extra = ("Esercizio «trova il bug». In \"codice_con_bug\" metti la soluzione con UN solo errore logico realistico "
                 "(off-by-one, condizione invertita, variabile non aggiornata, return nel posto sbagliato...) che fa fallire almeno un test "
                 "senza errori di sintassi. La \"consegna\" descrive cosa DOVREBBE fare il codice, senza dire dov'è il bug. "
                 "In \"spiegazione_bug\" spiega il bug.")
    else:
        extra = ("Esercizio «riordina le righe»: la soluzione deve avere 5-12 righe non vuote, una istruzione per riga, "
                 "senza righe vuote né commenti: lo studente riceverà le righe mescolate e dovrà rimetterle in ordine.")
    return head + extra + "\n" + common


def spring_prompt(kind):
    base = ("Questo esercizio viene ESEGUITO DAVVERO con Maven: Spring Boot 3 (Java 17, import jakarta.*), JUnit 5, database H2 in memoria. "
            "La classe @SpringBootApplication esiste già (si chiama App, package com.ricalco.app): NON scriverla e NON scrivere la riga package. "
            "In \"soluzione\" metti tutte le classi necessarie (entity, repository, service, controller...) con gli import completi; "
            "più classi possono stare nello stesso testo, una dopo l'altra. "
            "In \"test_junit\" una classe `class EsercizioTest` JUnit 5 con 2-4 metodi @Test e import completi: per le API usa @SpringBootTest "
            "e @AutoConfigureMockMvc con MockMvc (status(), jsonPath(), content()); per repository e service @SpringBootTest con @Autowired; "
            "per codice senza Spring bastano test JUnit semplici. Nomi dei metodi di test descrittivi in camelCase italiano. "
            "I test devono passare con la soluzione. Mantieni il codice breve e concentrato sul concetto. ")
    hints = ("In \"suggerimenti\" 3 indizi progressivi, senza scrivere il codice completo. \"titolo\": massimo 5 parole. "
             "\"consegna\": cosa deve fare il codice, citando endpoint, classi e metodi che i test usano.")
    if kind == "zero":
        extra = ("Esercizio da scrivere da zero: in \"codice_iniziale\" lo scheletro con i nomi delle classi e dei metodi che i test usano, "
                 "un commento TODO e corpi provvisori (return null; o simili) in modo che compili ma i test falliscano.")
    elif kind == "completa":
        extra = ("Esercizio «completa il codice»: in \"codice_iniziale\" la soluzione con 1-3 parti importanti sostituite da un commento TODO "
                 "(lascia return provvisori), in modo che compili ma i test falliscano.")
    else:
        extra = ("Esercizio «trova il bug»: in \"codice_con_bug\" la soluzione con UN errore realistico che compila ma fa fallire almeno un test "
                 "(annotazione sbagliata, mapping HTTP sbagliato, query derivata con nome errato, condizione invertita...). "
                 "La consegna dice cosa DOVREBBE fare il codice. In \"spiegazione_bug\" spiega il bug.")
    return base + extra + " " + hints


def review_prompt(kind, lang):
    base = ("Questo codice NON verrà eseguito (usa framework o librerie esterne): deve essere corretto, realistico e completo di import "
            "e annotazioni, come in un progetto vero. Mantienilo breve e concentrato sul concetto. ")
    hints = ("In \"suggerimenti\" 3 indizi progressivi, dal più vago al quasi-soluzione, senza scrivere il codice completo. "
             "In \"criteri\" 2-5 controlli concreti che una soluzione corretta deve rispettare (per esempio «usa @PathVariable per l'id»). "
             "\"titolo\": massimo 5 parole.")
    if kind == "riempi":
        return base + ("Esercizio «completa gli spazi»: in \"codice\" un frammento di 4-16 righe in cui da 1 a 3 parti brevi "
                       "(un'annotazione, un nome di metodo, un tipo, una parola chiave) sono sostituite da ___ (tre trattini bassi). "
                       "\"risposte\": le parti mancanti in ordine. \"consegna\": cosa fa il codice. \"spiegazione\": perché quelle risposte. "
                       "\"titolo\": massimo 5 parole.")
    if kind == "zero":
        extra = "Esercizio da scrivere da zero: in \"codice_iniziale\" metti solo lo scheletro (classe, firma, import) con un commento TODO."
    elif kind == "completa":
        extra = "Esercizio «completa il codice»: in \"codice_iniziale\" la soluzione con 1-3 parti importanti sostituite da un commento TODO che dice cosa manca."
    elif kind == "bug":
        extra = ("Esercizio «trova il bug»: in \"codice_con_bug\" la soluzione con UN errore realistico (annotazione sbagliata o mancante, "
                 "metodo HTTP sbagliato, query errata, dipendenza non iniettata...). La consegna dice cosa DOVREBBE fare il codice. "
                 "In \"spiegazione_bug\" spiega il bug.")
    else:
        extra = "Esercizio «riordina le righe»: la soluzione ha 5-14 righe non vuote, senza righe vuote né commenti; lo studente le rimetterà in ordine."
    return base + extra + " In \"soluzione\" il codice di riferimento completo. In \"consegna\" cosa deve fare il codice. " + hints


def norm_out(s):
    return "\n".join(l.rstrip() for l in str(s or "").replace("\r", "").split("\n")).strip("\n")


def simple(x):
    """Normalizza una risposta breve: minuscole, spazi, virgola decimale, punto finale."""
    x = str(x).strip().strip("`\"'").lower().rstrip(".")
    x = re.sub(r"\s+", " ", x)
    m = re.fullmatch(r"(-?\d+)[.,](\d+)(.*)", x)
    if m:
        dec = m.group(2).rstrip("0")
        x = m.group(1) + ("," + dec if dec else "") + m.group(3)
    return x


def fill_blanks(code, answers):
    for a in answers:
        code = code.replace("___", str(a), 1)
    return code


def shuffled_lines(sol):
    lines = [l for l in sol.split("\n") if l.strip()]
    order = list(range(len(lines)))
    if len(lines) > 1:
        while order == sorted(order):
            random.shuffle(order)
    return lines, [lines[i] for i in order]


def generate_exercise(kind, lang, diff, topic, avoid, mode="tests", attempts=4, runner=""):
    from .generazione_sql import generate_sql_exercise
    if kind not in EX_TYPES or diff not in DIFF_TEXT or lang not in LANGNAME:
        raise ValueError("parametri non validi")
    if lang == "sql" and kind not in ("logica", "orale"):
        return generate_sql_exercise(kind, diff, topic, avoid, attempts)
    msgs = [{"role": "system", "content": SYS_GEN},
            {"role": "user", "content": exercise_prompt(kind, lang, diff, topic, avoid, mode)}]
    schema = ex_schema(kind, mode)
    base = {"id": "e" + uuid.uuid4().hex[:10], "type": kind, "difficulty": diff, "lang": lang}
    RUN = RUNNERS.get(runner) or SPRING
    if mode == "spring" and runner:
        base["runner"] = runner
    for attempt in range(attempts):
        data = llm_json(msgs, schema, temperature=0.6 if attempt == 0 else 0.35)
        problem, ex = None, None
        title = str(data.get("titolo") or EX_TYPES[kind])[:70]
        if kind == "logica":
            opts = [str(o).strip() for o in (data.get("opzioni") or []) if str(o).strip()][:5]
            ans = str(data.get("risposta") or "").strip()
            code = norm_code(data.get("codice_verifica"))
            low = [simple(o) for o in opts]
            if not data.get("problema") or len(opts) < 3 or not ans or not code:
                problem = "Servono problema, 4 opzioni, risposta e codice_verifica."
            elif simple(ans) not in low:
                problem = "La risposta deve essere scritta esattamente come una delle opzioni."
            elif len(set(low)) < len(low):
                problem = "Le opzioni devono essere tutte diverse."
            elif re.fullmatch(r"\s*print\(\s*[\"'].*[\"']\s*\)\s*", code, re.S):
                problem = "Il codice_verifica deve CALCOLARE la risposta, non stamparla già pronta."
            else:
                run = run_program("python", code)
                out = norm_out(run.get("stdout")).split("\n")[-1] if run.get("stdout") else ""
                if not run["ok"]:
                    problem = "Il codice_verifica va in errore:\n" + (run.get("error") or "")[:700]
                elif simple(out) != simple(ans):
                    problem = (f"Il codice_verifica stampa «{out}» ma la risposta indicata è «{ans}». Controlla il problema: "
                               "se il codice ha ragione, correggi risposta e opzioni; se il problema è ambiguo, riscrivilo.")
                else:
                    ex = dict(base, title=title, question=str(data["problema"]), options=opts, correct=low.index(simple(ans)),
                              answer=ans, explain=str(data.get("spiegazione") or ""), verify=code)
        elif kind == "orale":
            pts = [str(x).strip() for x in (data.get("punti_chiave") or []) if str(x).strip()]
            if not data.get("domanda") or len(pts) < 2 or not data.get("risposta_modello"):
                problem = "Servono domanda, almeno 3 punti chiave e la risposta modello."
            else:
                ex = dict(base, title=title, question=str(data["domanda"]), points=pts[:6], model=str(data["risposta_modello"]),
                          followup=str(data.get("domanda_approfondimento") or ""))
        elif kind == "predici":
            code = norm_code(data.get("codice"))
            run = run_program(lang, code) if code else {"ok": False, "error": "codice vuoto", "stdout": ""}
            out = norm_out(run.get("stdout"))
            if not run["ok"]:
                problem = "Il programma non funziona:\n" + (run.get("error") or "")[:1000] + error_hint(run.get("error"))
            elif not out:
                problem = "Il programma non stampa nulla: deve stampare da 1 a 6 righe."
            elif out.count("\n") > 11:
                problem = "Il programma stampa troppe righe: al massimo 6."
            else:
                ex = dict(base, title=title, code=code, output=out, explain=str(data.get("spiegazione") or ""))
        elif kind == "quiz":
            opts = [str(o).strip() for o in (data.get("opzioni") or []) if str(o).strip()][:5]
            c = data.get("corretta")
            code = norm_code(data.get("codice"))
            q = str(data.get("domanda") or "").strip()
            if not q or len(opts) < 3 or not isinstance(c, int) or not 0 <= c < len(opts):
                problem = "Servono una domanda, 4 opzioni e l'indice della risposta corretta."
            elif len(set(o.lower() for o in opts)) < len(opts):
                problem = "Le opzioni devono essere tutte diverse."
            else:
                if code and mode not in ("review", "spring") and re.search(r"stamp|output|print", q, re.I):
                    run = run_program(lang, code)
                    out = norm_out(run.get("stdout"))
                    match = [i for i, o in enumerate(opts) if norm_out(o.strip("`")) == out]
                    if run["ok"] and out and match:
                        c = match[0]          # la risposta giusta è quella che il programma stampa davvero
                    elif run["ok"] and out:
                        problem = f"Il programma stampa:\n{out}\nma nessuna opzione è uguale a questo output. Una opzione deve esserlo esattamente."
                    else:
                        problem = "La domanda chiede l'output ma il codice non è un programma eseguibile:\n" + (run.get("error") or "")[:600]
                if not problem:
                    ex = dict(base, title=title, question=q, code=code, options=opts, correct=c, explain=str(data.get("spiegazione") or ""))
        elif kind == "riempi":
            code = norm_code(data.get("codice"))
            ans = [str(a).strip().strip("`") for a in (data.get("risposte") or []) if str(a).strip()]
            n = code.count("___")
            if not 1 <= n <= 3 or n != len(ans):
                problem = f"Il codice deve avere da 1 a 3 spazi ___ e lo stesso numero di risposte (ora: {n} spazi, {len(ans)} risposte)."
            elif mode in ("review", "spring"):
                ex = dict(base, title=title, statement=str(data.get("consegna") or ""), code=code, answers=ans,
                          output="", check="review", explain=str(data.get("spiegazione") or ""))
            else:
                run = run_program(lang, fill_blanks(code, ans))
                out = norm_out(run.get("stdout"))
                if not run["ok"] or not out:
                    problem = "Con le risposte inserite il programma non funziona o non stampa nulla:\n" + (run.get("error") or "")[:800]
                else:
                    ex = dict(base, title=title, statement=str(data.get("consegna") or ""), code=code, answers=ans,
                              output=out, explain=str(data.get("spiegazione") or ""))
        else:
            sol = norm_code(data.get("soluzione"))
            hints = [str(h) for h in (data.get("suggerimenti") or []) if str(h).strip()][:4]
            ex = dict(base, title=title, statement=str(data.get("consegna") or ""), solution=sol, hints=hints, check=mode)
            if not sol:
                problem = "Manca la soluzione."
            elif mode == "spring":
                test = norm_code(data.get("test_junit"))
                ex["check"], ex["tests_java"] = "spring", test
                if "@Test" not in test:
                    problem = "Manca test_junit con almeno un metodo @Test."
                else:
                    r = RUN.run(sol, test)
                    if not r.get("all_ok"):
                        problem = "Eseguendo i test con la soluzione:\n" + failing_summary(r) + "\nCorreggi soluzione o test."
                if not problem:
                    start = norm_code(data.get("codice_con_bug" if kind == "bug" else "codice_iniziale"))
                    if not start:
                        problem = "Manca il codice di partenza."
                    else:
                        rs = RUN.run(start, test)
                        if rs.get("all_ok"):
                            problem = "Il codice di partenza supera già i test: deve farne fallire almeno uno."
                        elif kind == "bug" and rs.get("error"):
                            problem = "Il codice_con_bug non compila: il bug deve essere logico.\n" + rs["error"][:500]
                        ex["starter"] = start
                        if kind == "bug":
                            ex["bugExplain"] = str(data.get("spiegazione_bug") or "")
            elif mode == "review":
                ex["criteria"] = [str(c) for c in (data.get("criteri") or []) if str(c).strip()][:6]
                if kind in ("completa", "zero", "bug"):
                    start = norm_code(data.get("codice_con_bug" if kind == "bug" else "codice_iniziale"))
                    if not start or start == sol:
                        problem = "Il codice di partenza manca o è identico alla soluzione."
                    ex["starter"] = start
                    if kind == "bug":
                        ex["bugExplain"] = str(data.get("spiegazione_bug") or "")
            elif mode == "output":
                run = run_program(lang, sol)
                out = norm_out(run.get("stdout"))
                if not run["ok"] or not out:
                    problem = "La soluzione non funziona o non stampa nulla:\n" + (run.get("error") or "")[:800]
                elif out.count("\n") > 15:
                    problem = "La soluzione stampa troppe righe: al massimo 10."
                else:
                    ex["output"] = out

                    def same(code):
                        r = run_program(lang, code)
                        return r["ok"] and norm_out(r.get("stdout")) == out, r
                    if kind in ("completa", "zero"):
                        start = norm_code(data.get("codice_iniziale"))
                        if not start:
                            problem = "Manca codice_iniziale."
                        elif same(start)[0]:
                            problem = "Il codice_iniziale stampa già il risultato giusto: togli le parti da completare."
                        ex["starter"] = start
                    elif kind == "bug":
                        bug = norm_code(data.get("codice_con_bug"))
                        ok, rb = same(bug) if bug else (True, {})
                        if not bug or ok:
                            problem = "Il codice_con_bug stampa lo stesso risultato della soluzione: il bug deve cambiare l'output."
                        elif not rb.get("ok"):
                            problem = "Il codice_con_bug va in errore: il bug deve essere logico, non di sintassi.\n" + (rb.get("error") or "")[:500]
                        ex["starter"] = bug
                        ex["bugExplain"] = str(data.get("spiegazione_bug") or "")
            else:
                tests = norm_tests(data.get("test"))
                ex["tests"] = tests
                if len(tests) < 2:
                    problem = "Servono almeno 3 test."
                else:
                    r = run_tests(lang, sol, tests)
                    if not r["all_ok"]:
                        problem = "La soluzione non supera i test:\n" + failing_summary(r) + "\nCorreggi soluzione o test."
                if not problem and kind in ("completa", "zero"):
                    start = norm_code(data.get("codice_iniziale"))
                    if not start:
                        problem = "Manca codice_iniziale."
                    elif run_tests(lang, start, tests)["all_ok"]:
                        problem = "Il codice_iniziale supera già tutti i test: togli le parti da completare."
                    ex["starter"] = start
                elif not problem and kind == "bug":
                    bug = norm_code(data.get("codice_con_bug"))
                    rb = run_tests(lang, bug, tests) if bug else {"all_ok": True, "error": None}
                    if not bug or rb["all_ok"]:
                        problem = "Il codice_con_bug supera tutti i test: il bug deve far fallire almeno un test."
                    elif rb.get("error"):
                        problem = "Il codice_con_bug non compila o va in errore: il bug deve essere logico, non di sintassi.\n" + rb["error"][:500]
                    ex["starter"] = bug
                    ex["bugExplain"] = str(data.get("spiegazione_bug") or "")
            if not problem and kind == "riordina":
                lines, mixed = shuffled_lines(sol)
                if not 3 <= len(lines) <= 18:
                    problem = "La soluzione deve avere tra 5 e 12 righe non vuote."
                else:
                    ex["solution"] = "\n".join(lines)
                    ex["lines"] = mixed
        if ex and not problem:
            ex["state"] = {"solved": False, "attempts": 0, "hints": 0, "revealed": False}
            ex["genAttempts"] = attempt + 1
            return ex
        msgs = msgs[:2] + [{"role": "assistant", "content": json.dumps(data, ensure_ascii=False)},
                           {"role": "user", "content": (problem or "Errore") + "\nRestituisci di nuovo tutto il JSON corretto."}]
    raise LLMError("Il modello non è riuscito a creare un esercizio che funzioni. Riprova o scegli un altro tipo.")


JUDGE_SCHEMA = {"type": "object", "properties": {
    "esito": {"type": "string", "enum": ["giusto", "parziale", "sbagliato"]}, "commento": STR},
    "required": ["esito", "commento"]}


def judge(question, reference, why, answer):
    prompt = (f"Domanda di ragionamento: {question}\nRisposta corretta di riferimento: {reference}\nMotivo: {why}\n\n"
              f"Risposta dello studente, scritta con parole sue: «{answer}»\n\n"
              "Valuta il ragionamento, non la forma né l'ortografia. \"esito\": giusto, parziale o sbagliato. "
              "\"commento\": 1-2 frasi rivolte allo studente (dagli del tu). Se è parziale o sbagliata, NON rivelare la risposta: "
              "dai un indizio che lo faccia ragionare.")
    d = llm_json([{"role": "system", "content": SYS_GEN}, {"role": "user", "content": prompt}], JUDGE_SCHEMA, temperature=0.1, num_ctx=3072)
    esito = d.get("esito") if d.get("esito") in ("giusto", "parziale", "sbagliato") else "parziale"
    return {"verdict": esito, "comment": str(d.get("commento") or "")}


REVIEW_SCHEMA = {"type": "object", "properties": {
    "esito": {"type": "string", "enum": ["giusto", "parziale", "sbagliato"]}, "commento": STR, "problemi": ARR},
    "required": ["esito", "commento", "problemi"]}


def review_code(lang, statement, solution, criteria, code):
    prompt = (f"Sei un revisore di codice {LANGNAME[lang]} per uno studente. Il codice non può essere eseguito: valutalo leggendolo.\n"
              f"Consegna: {statement}\nCriteri da rispettare:\n" + "\n".join("- " + c for c in criteria) +
              f"\n\nSoluzione di riferimento (solo per te, non mostrarla):\n{solution}\n\nCodice dello studente:\n{code}\n\n"
              "Una soluzione diversa da quella di riferimento è GIUSTA se fa la stessa cosa e rispetta i criteri. "
              "Ignora differenze di stile, nomi, spazi e commenti. \"esito\": giusto, parziale o sbagliato. "
              "\"commento\": 1-3 frasi rivolte allo studente (dagli del tu), senza scrivere la soluzione. "
              "\"problemi\": elenco breve dei problemi concreti (vuoto se giusto).")
    d = llm_json([{"role": "system", "content": SYS_GEN}, {"role": "user", "content": prompt}], REVIEW_SCHEMA, temperature=0.1)
    v = d.get("esito") if d.get("esito") in ("giusto", "parziale", "sbagliato") else "parziale"
    return {"verdict": v, "comment": str(d.get("commento") or ""), "problems": [str(x) for x in (d.get("problemi") or [])][:6]}


TUTOR_SYS = ("Sei il tutor di Ricalco, un'app che insegna a programmare a studenti junior facendo riscrivere il codice invece di copiarlo. "
             "Rispondi in italiano, dando del tu, in modo concreto e breve (massimo 150 parole, salvo richiesta). "
             "Usa piccoli esempi di codice tra backtick o in blocchi ```. "
             "Se lo studente sta svolgendo un esercizio NON dargli la soluzione completa: guidalo con indizi e domande, "
             "a meno che non chieda esplicitamente la soluzione.")
