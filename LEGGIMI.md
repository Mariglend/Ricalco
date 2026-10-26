# Ricalco

App locale per imparare a programmare **senza copiare codice**. Il motore è il tuo modello Qwen su Ollama: nessun dato esce dal PC.

## Requisiti

- **Python 3.9+**. Il server usa solo la libreria standard, quindi non serve `pip install`.
- **Ollama** acceso, con un modello. Consigliato `qwen3:14b` (GPU con circa 10-12 GB di memoria video); su PC meno potenti `qwen3:8b`:
  ```
  ollama pull qwen3:14b
  ```
  Funziona anche con altri modelli (Llama, Gemma…): lo scegli dal menu in alto a destra. Con Qwen3 l'italiano e le risposte strutturate vengono meglio.
- **JDK 17 o più recente** (per esempio Eclipse Temurin), solo per gli esercizi in Java. Ricalco cerca da solo il JDK più recente installato e salta i vecchi Java 8 e i JRE senza compilatore.

## Avvio

Doppio clic su `avvia.bat` (Windows) o `./avvia.sh` (macOS e Linux), oppure da terminale:

```
python server.py
```

Si apre il browser su http://127.0.0.1:8765. Per chiudere l'app chiudi la finestra nera (o premi Ctrl+C).

## Oggi (pagina principale)

Le sezioni sono nella barra a sinistra, raggruppate per quello che fai: **Impara** (percorsi, progetti, lezioni libere), **Allenati** (algoritmi, logica, flashcard), **Colloquio**, **Strumenti** (diario, prova del modello). Su schermi stretti la barra si apre con **Menu**.

In cima a Oggi c'è **il piano di oggi**: il ripasso da fare, la prossima unità del percorso, il prossimo algoritmo del catalogo e le domande del colloquio da ripassare.

Appena apri Ricalco trovi l'allenamento del giorno: un esercizio alla volta, quasi sempre un algoritmo classico (in SQL una query), scelto in base al tuo livello. Scegli il linguaggio: **Python**, **Java** o **SQL**.

Ogni esercizio ha tre passi:

1. **Ragiona.** Leggi il problema e, prima di vedere il codice, scrivi con parole tue come lo risolveresti: Qwen valuta il tuo piano. Se preferisci, scegli tra quattro metodi. Se sbagli puoi riprovare o farti mostrare il piano. Poi vedi i passi della soluzione.
2. **Scrivi.** Riscrivi la soluzione blocco per blocco al livello che scegli: **1 Ricalco** (codice in trasparenza), **2 Struttura** (solo parole chiave e punteggiatura) o **3 Memoria** (codice nascosto). Sopra il foglio vedi sempre **cosa fa** il blocco che stai scrivendo; finito il blocco, compare **perché** è scritto così. Una volta iniziato a scrivere non puoi tornare a un livello più facile per sbirciare: per un aiuto c'è «Mostra parola».

   C'è anche il livello **4 Scrivi tu**: niente foglio da ricalcare, scrivi il programma come vuoi tu, con i tuoi nomi e il tuo metodo. Ricalco lo esegue e confronta il risultato con quello della soluzione di riferimento; poi Qwen ti fa una revisione da collega (cosa va, cosa migliorare) e ti propone una versione migliore partendo dal tuo codice.
3. **Punteggio.** Conta il piano (40%) e come hai scritto il codice (60%): livello di aiuto, precisione e parole che ti sei fatto mostrare, in proporzione alla lunghezza del codice. Il punteggio pieno si prende a memoria. Se a memoria ti fai mostrare troppe parole, Ricalco ti propone di rifarlo subito al livello 2.

**Il livello si adatta come l'Elo degli scacchi.** Hai un punteggio per linguaggio (si parte da 800, «Primi passi»). Gli esercizi vengono scelti solo in base all'Elo: di solito un po' sotto il tuo punteggio, così hai buone probabilità di farli bene, mai più di 100 punti sopra. Il livello sale perché sale il tuo punteggio. Anche ogni esercizio ha il suo punteggio, che si aggiusta da solo: se ti va male sale, se ti va bene scende. Se vicino al tuo punteggio non ci sono esercizi nuovi, ne riprendi uno già fatto mentre Qwen ne prepara altri. Il punteggio sale se fai bene esercizi del tuo livello e scende se sbagli. Così non salti avanti dopo un solo esercizio e non resti bloccato sugli stessi. I livelli sono cinque: Primi passi, Base, Intermedio, Avanzato, Da colloquio difficile. Qwen prepara in sottofondo nuovi esercizi al tuo livello e uno al livello sopra, e Ricalco li esegue per controllarli. Se Ollama è spento ci sono comunque alcuni esercizi già pronti.

**Gli argomenti seguono il percorso.** Gli esercizi di Oggi vanno in ordine sulle unità del percorso, ognuna trasformata in un piccolo problema algoritmico. Ogni 30 punti si passa all'unità successiva. Dopo le unità che si possono eseguire (Java 1-17, Python 1-17, senza file, test e HTTP) si prosegue con il percorso Algoritmi. Le unità Spring restano nei Percorsi. Nel riquadro del livello vedi l'argomento di adesso e a che punteggio arriva il prossimo. Un esercizio rifatto conta per il punteggio, a metà peso e solo se fai meglio dell'ultima volta.

**Quanto si sale.** Un esercizio fatto bene vale circa +15/+25 punti: Base (875) si raggiunge in 4-5 esercizi puliti, Intermedio in una decina. Anche il livello di aiuto con cui parte l'esercizio si adatta: sale di uno dopo un esercizio pulito (precisione almeno 90%, quasi nessun aiuto, piano giusto) e scende dopo uno andato male. Lo puoi sempre cambiare a mano. Più il livello di aiuto è alto, più punti prendi: a memoria il punteggio pieno, al livello 1 tre quarti.

**Ripasso come flashcard.** Ogni esercizio fatto torna in home: tra qualche ora se è andato male, il giorno dopo se è andato così così, tra qualche giorno se è andato bene, poi a intervalli sempre più lunghi. Nel ripasso rispondi di nuovo sul piano e riscrivi tutto a memoria. Nello stesso ripasso tornano anche i blocchi delle lezioni e le altre flashcard.

**Aiuto diverso per ogni blocco.** Quando un esercizio torna (ripasso o «Rifallo»), Ricalco ricorda come è andato ogni blocco: dove l'ultima volta hai sbagliato hai un livello di aiuto in più, dove sei andato liscio uno in meno. Sopra il foglio vedi il livello del blocco e il perché.

**Variante da zero.** Finito un esercizio, il pulsante principale è «Variante da zero»: un problema gemello (stesso schema, obiettivo diverso) da scrivere senza codice in trasparenza, con test veri. Qwen la prepara in sottofondo mentre fai l'esercizio. Dopo la variante ricalchi la soluzione di riferimento; se l'hai dovuta vedere, finisce nel ripasso.

**Spiegalo a un principiante (metodo Feynman).** Dopo ogni codice che scrivi (esercizi di Oggi, varianti, prova settimanale, esercizi dei percorsi e delle lezioni libere) spieghi la soluzione in poche righe, senza codice, a qualcuno che non sa programmare. Qwen fa il principiante: legge e ti fa 1-2 domande sui punti vaghi. Rispondi, poi ricevi un voto da 1 a 5 su chiarezza, completezza e correttezza, il punto che ti mancava e come lo spiegherebbe il tutor. Il punto mancante finisce nel mazzo «Spiegalo con parole tue» e torna nel ripasso. Puoi saltare, e riprenderla con «Spiegalo ora». La valutazione è del modello: indicativa.

**Prevedi ed esegui.** Prima di eseguire il programma scrivi cosa stamperà; Ricalco confronta la tua previsione con l'output vero riga per riga.

**I tuoi schemi.** Sotto l'esercizio vedi gli schemi (accumulatori, hash map, due puntatori, ricorsione, JOIN…) dal più debole al più forte, con la media dei punteggi e le varianti risolte. «Allenati su questo» cambia solo il prossimo esercizio: per il resto la home continua a scegliere da sola.

**Prova settimanale.** Una volta a settimana per linguaggio: un problema mai visto al tuo livello, da zero, senza suggerimenti e con un tempo previsto. Il tutor non aiuta durante la prova. Il grafico mostra i minuti e l'esito di ogni prova: è il modo per vedere se migliori davvero.

Sotto trovi i percorsi, ciascuno con l'unità a cui sei arrivato.

## Ricalco anche negli esercizi

Ogni volta che in un esercizio scrivi codice (completa, trova il bug, scrivi da zero, riordina, live coding), alla fine riscrivi la soluzione di riferimento:

- se l'hai risolto, al livello 2;
- se hai visto la soluzione, al livello 1, e la soluzione finisce anche nel ripasso: torna da riscrivere a memoria il giorno dopo.

Puoi cambiare livello o saltare.

## Percorsi

Cinque percorsi, nel menu **Percorsi**:

- **Python**: 24 unità, da zero fino a FastAPI e SQLAlchemy.
- **Java**: 33 unità, allineate al programma «Java & AI»:
  - **OOP:** i quattro pilastri, interfacce contro classi astratte e accoppiamento debole, eccezioni custom, SOLID e Singleton.
  - **Collezioni e Java moderno:** ArrayList contro LinkedList e prestazioni, interfacce funzionali (Function, Predicate, Consumer, Supplier…), lambda e Stream API, record, sealed e pattern matching.
  - **Spring:** DI e IoC, API REST, JPA con JPQL, MVC con Thymeleaf, validazione ed errori.
  - **Spring Security:** filter chain, ruoli, JWT, @PreAuthorize, CORS e CSRF.
  - **Spring AI:** ChatClient e prompt, risposte tipizzate, tool calling, RAG e streaming.

  Le unità Spring eseguono test veri con Maven. Security e AI usano un progetto Maven separato con le loro librerie; nei test di Spring AI il modello è finto, così il risultato è sempre lo stesso e Ollama non serve. Se hai preparato Spring prima di questo aggiornamento, premi «Ripeti la prova Spring» in «Prova il modello» per scaricare anche queste librerie.
- **SQL**: 17 unità, da SELECT a JOIN, sottoquery, progettazione, indici, transazioni, CTE, window function e query da colloquio. Tutto viene eseguito davvero su SQLite, che è già dentro Python: non serve installare niente.
- **Algoritmi e strutture dati**: 30 unità, in **Python** o in **Java** (scegli tu, i progressi sono separati). Complessità, hash map, due puntatori, finestra scorrevole, pile e code, ricerca binaria, ricorsione, ordinamenti, liste collegate, alberi, heap, grafi (BFS, DFS, Dijkstra, ordinamento topologico), programmazione dinamica, greedy e backtracking. Gli esercizi sono verificati con test veri.

**Ripreparare un'unità.** Sotto ogni unità c'è «↻ Riprepara l'unità»: Qwen rifà la lezione, la scheda di teoria e gli esercizi di Base, Pratica e Sfida. Puoi tenere i tuoi progressi o azzerarli. I file vecchi restano accanto con estensione `.bak`. Se una lezione dà un errore quando viene eseguita, nell'avviso c'è anche «Fai riscrivere la lezione a Qwen», che rifà solo la lezione.

Il cuore è il **ricalco**: ogni unità segue quattro passi.

1. **Impara:** una lezione da ricalcare. Prima rispondi a una domanda di ragionamento, poi riscrivi il codice blocco per blocco con il codice visibile in trasparenza (livello 1). Dopo ogni blocco puoi riscriverlo subito al livello 2 o 3.
2. **Fissa:** riscrivi tutta la lezione **a memoria** (livello 3), senza domande e senza codice visibile. Con almeno l'85% di precisione e al massimo 2 aiuti l'unità è «fissata» e si apre la successiva.
3. **Usa:** esercizi sugli stessi concetti, a tre livelli (**Base**, **Pratica**, **Sfida**), 8 per sessione, di sette tipi: domanda, completa gli spazi, prevedi l'output, riordina, completa il codice, trova il bug, scrivi da zero. Se sbagli, puoi riscrivere a memoria il blocco della lezione che usa quel concetto.
4. **Ripassa:** i blocchi delle lezioni tornano da riscrivere a memoria il giorno dopo e poi a intervalli sempre più lunghi. Il voto lo dà la precisione con cui li riscrivi. Il percorso ti mostra ogni giorno quanti blocchi hai da ripassare.

**Esercizi SQL.** Ogni esercizio ha il suo piccolo database: le tabelle sono mostrate sopra la consegna. La tua query viene eseguita e il risultato confrontato con quello atteso. Se è diverso vedi le due tabelle una accanto all'altra. L'ordine delle righe conta solo se la consegna chiede un ORDER BY. In «prevedi il risultato» scrivi una riga per ogni riga del risultato, con i valori separati da `|`.

Ogni volta che ripeti un livello di esercizi, gli esercizi sono nuovi. Ci sono anche una scheda di teoria per ogni unità, XP e giorni di fila. Se conosci già le basi puoi sbloccare tutte le unità.

**Esercizi in sottofondo.** Mentre ti eserciti, Qwen prepara gli esercizi dei livelli successivi e Ricalco li esegue per controllarli. Quando chiedi qualcosa al tutor, la preparazione si mette in pausa.

**Spring eseguito davvero.** Le unità Java 18 e 20-24 (JUnit, JDBC, Spring Core, Spring Boot REST, Spring Data JPA, Spring avanzato) possono girare con Maven e JUnit 5 sul tuo PC. Per attivarle vai su **Prova il modello → Prepara Spring**, una volta sola: se Maven manca Ricalco lo scarica, poi scarica Spring Boot 3.5 (circa 150 MB) ed esegue un test di prova. Ogni verifica richiede 20-60 secondi. Finché Spring non è preparato, e per l'unità su Maven, il codice lo valuta Qwen e l'app lo segna «valutato dal modello».

**Difficoltà adattiva.** Ricalco tiene conto di quanto spesso fai giusto al primo colpo ogni tipo di esercizio. Nelle sessioni del percorso aumenta gli esercizi del tipo in cui sbagli di più e inserisce fino a 2 esercizi che hai sbagliato nei livelli precedenti, segnati «ripasso».

**FastAPI e SQLAlchemy.** Le unità Python con FastAPI e SQLAlchemy si eseguono davvero se installi i pacchetti: lancia `installa_extra.bat` e poi riavvia Ricalco. Senza i pacchetti, anche quelle unità vengono valutate da Qwen.

Gli esercizi generati sono salvati in `data/pool/`, i programmi della pagina principale in `data/quick/`, la teoria in `data/theory/`, i progressi in `data/progress.json`.

## Progetti

Un programma vero costruito a tappe, come nei libri «crash course». Il primo è **Invasione aliena** in Python con pygame: una navicella che spara a una flotta di alieni, in 15 tappe. Si parte da una finestra vuota e si arriva a collisioni, vite, punteggio e difficoltà crescente.

Ogni tappa:

1. **Ragiona:** una domanda sul perché della tappa.
2. **Scrivi:** ricalchi ogni modifica (file nuovo, righe da aggiungere o da sostituire). Vedi il contesto del file, «cosa fa» la modifica e, finita, il «perché». Il livello di aiuto (1, 2, 3) lo scegli tu. Se una modifica è lunga o già nota (pom.xml, configurazioni) premi **Salta questa modifica**: il codice finisce lo stesso nei file e passi alla modifica dopo.
3. **Esegui:** i file vengono salvati in `progetti/invasione-aliena/` (accanto all'app) e «Esegui sul tuo PC» apre la finestra del gioco.
4. **Spiegalo** a un principiante, come dopo ogni codice.
5. **Tocca a te:** una modifica da fare da solo su una tua copia (`progetti/invasione-aliena-mia/`), con il tuo editor. Le tappe successive non la toccano.

Serve pygame: si installa dalla pagina del progetto oppure con `installa_extra.bat`. Le tappe le ho scritte e verificate io, non Qwen, così il progetto resta coerente dall'inizio alla fine. Qwen risponde alle domande e valuta le spiegazioni.

Il secondo è **API prenotazioni palestra** in Java con Spring Boot, in 12 tappe: pom.xml, primo endpoint, entità JPA su H2, repository, service, controller REST, 404, validazione, prenotazioni con la regola dei posti esauriti (409), gestione degli errori in JSON con `@RestControllerAdvice`. Ogni tappa ha i suoi test (MockMvc, `@DataJpaTest`).

- I file vanno in `progetti/prenotazioni-api/`: è un progetto Maven normale, lo apri anche con IntelliJ o VS Code.
- **Esegui i test** lancia `mvn test` e mostra quali test passano. La prima volta Maven scarica i pezzi che mancano (un paio di minuti).
- **Avvia l'API** apre una console con `mvn spring-boot:run`. Poi vai su http://localhost:8080/api/corsi. Si ferma con Ctrl+C.
- Serve Spring preparato una volta da «Prova il modello → Prepara Spring».

**Web app palestra (MVC)** è sempre in Java, ma con Spring MVC, Thymeleaf e Bootstrap 5, in 11 tappe:
- prima pagina con `@Controller` e Model
- corsi su JPA/H2 caricati all'avvio, e un service
- elenco con `th:each`, dettaglio con link `@{...}`
- pagina 404 con `@ControllerAdvice`
- layout comune con frammenti e Bootstrap
- form con `th:object`/`th:field` e `@Valid`, salvataggio con Post/Redirect/Get e messaggi flash
- prenotazione di un posto con la regola dei posti esauriti nell'entità

Ogni tappa ha i suoi test MockMvc su vista, model e HTML. I file vanno in `progetti/palestra-web/`. «Avvia l'API» apre l'app su http://localhost:8080/corsi.

Il terzo è **Database biblioteca** in SQL (SQLite), in 13 tappe: tabelle e chiavi esterne, INSERT, WHERE e ORDER BY, JOIN, soci e prestiti, IS NULL, GROUP BY e HAVING, LEFT JOIN, date con `julianday`, sottoquery ed EXISTS, viste, CTE e funzioni finestra (`RANK`), trigger, indici e transazioni.

- I file sono `schema.sql`, `dati.sql`, `viste.sql` e `query.sql` in `progetti/biblioteca-sql/`.
- **Esegui gli script** li lancia in quest'ordine su un database nuovo e mostra il risultato di ogni SELECT con il titolo del suo commento. Se c'è un errore ti dice in quale file e in quale istruzione.
- Ogni esecuzione ricrea anche `biblioteca.db`, che puoi aprire con DB Browser for SQLite o DBeaver.
- Non serve installare niente: SQLite è già dentro Python.

## Logica

Cinque categorie, ciascuna con livelli Facile, Medio e Difficile, ed esercizi senza limite:

- rompicapo
- sequenze e numeri
- algoritmi in Python
- algoritmi in Java
- query SQL da colloquio

Per ogni rompicapo Qwen scrive anche un programma che lo risolve da solo. Ricalco lo esegue e scarta il problema se il programma non conferma la risposta. Puoi rispondere scegliendo tra le opzioni oppure senza vederle.

## Flashcard

Le flashcard usano la ripetizione dilazionata (sistema Leitner): una carta che sai torna dopo giorni, una che sbagli torna subito.

- I problemi di logica e le domande di colloquio diventano carte in automatico.
- Per ogni unità del percorso puoi generare un mazzo di 10 carte.
- Prima di girare la carta puoi **spiegare la risposta a parole tue**: Qwen la confronta con il retro e ti dice se è giusta, quasi o da rivedere.
- Gli esercizi passati che tornano in Oggi sono flashcard vere: sul fronte il problema, spieghi a parole come lo risolvi, giri la carta, vedi il piano e il giudizio di Qwen, poi lo riscrivi a memoria.
- Tasti: `Spazio` gira la carta (`Ctrl+Invio` se stai scrivendo la spiegazione); `1` = non lo sapevo, `2` = difficile, `3` = facile.

## Algoritmi

Un catalogo di oltre 150 problemi da colloquio, in **Python** e in **Java**, divisi per schema: accumulatori, stringhe, hash map, due puntatori, finestra scorrevole, somme prefisse, pile e code, ricerca binaria, ricorsione, ordinamenti, intervalli, matrici, bit, liste collegate, alberi, trie, heap, grafi, union-find, programmazione dinamica, backtracking e greedy, classi. Li ho scritti e verificati io (ogni programma è stato eseguito e l'output controllato), non Qwen, quindi non c'è da aspettare.

Ogni problema si apre come un esercizio di **Oggi**: ragioni sul metodo, poi riscrivi la soluzione. **Il prossimo da fare** ti porta al primo non ancora risolto, dal più facile. I problemi del catalogo entrano anche in Oggi: il punteggio Elo li propone quando sono al tuo livello.

## Colloquio tecnico

La sezione ha cinque parti, nella barra laterale:

- **Domande a catena:** circa 240 domande vere su Java, Spring, SQL, web e strumenti, Python, fondamenti e OOP, ognuna con 2-3 approfondimenti. Rispondi per scritto; se la risposta regge (voto 3 o più) il selezionatore scava con un «perché?» o un «e se…?», fino a trovare il tuo limite. Vedi punti toccati, punti mancanti, risposta modello e la trappola tipica. Le domande dove ti fermi presto tornano dopo un giorno, quelle che reggi fino in fondo dopo settimane.
- **System design junior:** 14 scenari (accorciatore di URL, prenotazioni, carrello, rate limiter…). Scrivi entità, endpoint, casi limite e come cresce; Qwen ti valuta con una griglia di criteri, ti mostra una soluzione di riferimento e ti fa le domande di approfondimento.
- **Code review:** 24 pezzi di codice Java, Python e SQL con problemi nascosti (bug, sicurezza, prestazioni, leggibilità). Scrivi la tua review e vedi, riga per riga, cosa hai trovato e cosa ti è sfuggito.
- **Comportamentali:** 26 domande come «raccontami un bug difficile», in italiano o in inglese. Qwen controlla la struttura STAR (situazione, compito, azione, risultato) e ti mostra un esempio di risposta.
- **Panoramica:** le modalità di prima, generate da Qwen per ogni percorso.

Nella panoramica ci sono quattro percorsi: Java backend junior (fino a Spring), Python backend junior (fino a FastAPI), SQL e database, fondamenti di informatica. Ognuno ha tre modalità:

Quattro percorsi: Java backend junior (fino a Spring), Python backend junior (fino a FastAPI), SQL e database, fondamenti di informatica. Ognuno ha tre modalità:

- **Domande:** rispondi per scritto. Qwen ti dà un voto da 1 a 5 e ti mostra i punti che hai toccato, quelli che mancano, la risposta modello e la domanda di approfondimento.
- **Live coding:** 3 problemi con il timer e test eseguiti davvero. Poi il selezionatore ti fa una domanda sul tuo codice, per esempio sulla complessità.
- **Simulazione:** colloquio in chat, una domanda alla volta, di circa 8 domande. Alla fine ricevi una scheda con il voto, il punteggio per area, i punti forti, cosa migliorare e i prossimi passi. Le schede restano salvate.

Durante la simulazione:

- se cambi pagina dentro Ricalco o chiudi il browser, la simulazione resta salvata e la riprendi da dove eri;
- se passi a un'altra scheda del browser, Ricalco te lo fa notare (in un colloquio vero non puoi cercare) e lo scrive nella valutazione;
- ogni domanda del selezionatore si può **salvare**: diventa una flashcard nel mazzo «Colloquio · domande salvate», con la risposta modello scritta da Qwen. Lo stesso vale per le domande della modalità Domande.

Nella valutazione finale, accanto a ogni punto «Da migliorare» c'è **Allenati su questo**: Qwen prepara domande mirate su quel punto nel mazzo «Colloquio · punti da migliorare», a cui rispondi per scritto.

Puoi scegliere la **lingua del colloquio**: in inglese le domande, il selezionatore e la simulazione sono in inglese. Dopo ogni risposta ricevi 1-3 correzioni del tuo inglese, che non abbassano il voto, e la scheda finale ha un'area «Comunicazione in inglese».

## Prova il modello

La pagina in alto a destra genera un esercizio per ogni sezione con il tuo modello e lo verifica come fa l'app. Per ognuno ti dice se è valido al primo tentativo, quanto ci ha messo, e ti dà un consiglio sul modello da usare. Mostra anche le tue percentuali per tipo di esercizio e quanti esercizi hai segnalato come sbagliati. Da qui si prepara anche Spring.

## Lezioni libere

1. **Chiedi cosa vuoi imparare.** Qwen scrive un programma diviso in blocchi. Ricalco lo **esegue davvero**: se va in errore, glielo rimanda da correggere (fino a 3 volte).
2. **Ogni blocco segue tre passi:**
   - **Ragiona**: una domanda di logica *prima* di vedere il codice. Puoi rispondere a scelta multipla o con parole tue (in quel caso giudica il modello). Se sbagli puoi riprovare, oppure andare avanti e vedere la risposta.
   - **Scrivi**: riscrivi il blocco su un foglio. Ci sono 3 livelli:
     1. *Ricalco*: il codice si vede in trasparenza.
     2. *Struttura*: si vedono solo parole chiave e punteggiatura.
     3. *Memoria*: il codice non si vede.

     Incolla e backspace sono disattivati.
   - **Capisci**: la spiegazione del perché il blocco è scritto così.
   - **Rifallo più difficile**: finito un blocco, puoi riscriverlo al livello 2 o 3, oppure andare avanti con `Invio`.
3. **Esercizi a tre difficoltà**, cinque tipi:
   - prevedi l'output
   - riordina le righe
   - completa il codice
   - trova il bug
   - scrivi da zero

   Prima di mostrarti un esercizio, Ricalco esegue la soluzione del modello sui test. Se non passa, lo fa rifare. Anche i tuoi test girano davvero sul PC (Python o Java).
4. **Tutor sempre aperto a destra.** Sa cosa stai guardando. Selezioni del codice e premi **Cosa fa?**. Negli esercizi ti guida senza darti la soluzione.

## Prova settimanale e varianti

Sono problemi da scrivere da zero, controllati con test veri. Se chiami la funzione o la classe con un nome diverso da quello che usano i test, va bene lo stesso: Ricalco collega il tuo nome a quello atteso e te lo dice. Alla fine Qwen fa la revisione del tuo codice e ti propone una versione migliore.

## Diario d'uso e log

Ricalco registra cosa fai (esercizi, tempi per blocco, errori, aiuti, salti, attese, domande al tutor) e quanto ci mette il modello, in `data/logs/`, un file al giorno. I log restano sul tuo PC.

- **Diario** (in alto): il riassunto degli ultimi 14 giorni. Mostra minuti di lavoro, punteggi, dove passi il tempo, gli **errori di ragionamento** (piani sbagliati o incompleti, spiegazioni deboli, domande di ragionamento sbagliate) separati dagli errori di battitura nei blocchi, gli esercizi saltati, le attese e la velocità del modello.
- **Nota** (in alto): scrivi in una riga cosa ti blocca, ti annoia o ti piace. La nota viene salvata insieme a dove ti trovi.
- **Esporta i log** (nel Diario): scarica un file con gli ultimi 30 giorni, utile per analizzarli.

## Lingua

Il selettore **IT / EN** in alto cambia la lingua dell'app. In inglese sono tradotti l'interfaccia, i percorsi, i progetti e gli esercizi già pronti, e Qwen scrive lezioni, esercizi e risposte in inglese. I contenuti generati in inglese stanno in `data/en/`, separati da quelli italiani; progressi, punteggio, flashcard e diario sono condivisi.

## Dati e sicurezza

- Lezioni e progressi sono salvati in `data/lessons/` come file JSON.
- Il server ascolta solo su `127.0.0.1` e accetta richieste solo dalla sua pagina: altri siti non possono fargli eseguire codice.
- Il codice (tuo e del modello) gira sul tuo PC in una cartella temporanea, con un limite di 10 secondi (25 secondi per Java). Il server esegue gli esercizi senza nessun isolamento: vale come lanciarli tu da terminale.

## Opzioni

Variabili d'ambiente:

| Variabile | Predefinito | A cosa serve |
|---|---|---|
| `RICALCO_OLLAMA` | `http://127.0.0.1:11434` | Indirizzo di Ollama |
| `RICALCO_PORT` | `8765` | Porta dell'app |
| `RICALCO_MODEL` | primo modello "qwen" installato | Modello da usare |
