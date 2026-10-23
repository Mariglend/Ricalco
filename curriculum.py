"""Percorsi di Ricalco: unità, livelli, mix di esercizi ed esercizi iniziali."""

LEVELS = [
    {"id": "base", "name": "Base", "diff": "facile"},
    {"id": "pratica", "name": "Pratica", "diff": "medio"},
    {"id": "sfida", "name": "Sfida", "diff": "difficile"},
]
SESSION_SIZE = 8

# Quanti esercizi di ogni tipo in una sessione da 8, per livello.
MIX = {
    "base":    {"quiz": 2, "riempi": 3, "predici": 2, "riordina": 1},
    "pratica": {"riempi": 1, "predici": 1, "quiz": 1, "completa": 2, "bug": 2, "riordina": 1},
    "sfida":   {"predici": 1, "completa": 2, "bug": 2, "zero": 3},
}
# Unità in "review": niente "prevedi l'output", perché il codice non si esegue.
MIX_REVIEW = {
    "base":    {"quiz": 3, "riempi": 3, "riordina": 2},
    "pratica": {"quiz": 2, "riempi": 2, "completa": 2, "bug": 2},
    "sfida":   {"quiz": 1, "completa": 2, "bug": 2, "zero": 3},
}
# Unità Spring/JUnit/JDBC eseguite davvero con Maven (se preparato), altrimenti valutate dal modello.
MIX_SPRING = {
    "base":    {"quiz": 3, "riempi": 3, "completa": 2},
    "pratica": {"quiz": 1, "riempi": 1, "completa": 2, "bug": 2, "zero": 2},
    "sfida":   {"completa": 2, "bug": 3, "zero": 3},
}
# Ordine in cui compaiono nella sessione: dal più rapido al più impegnativo.
TYPE_ORDER = ["logica", "orale", "quiz", "riempi", "predici", "riordina", "completa", "bug", "zero"]

THEMES = ["un negozio di alimentari", "i voti di una classe", "una playlist musicale", "il meteo della settimana",
          "una squadra di calcio", "un magazzino", "le ricette di cucina", "un viaggio in treno", "un conto in banca",
          "una biblioteca", "un videogioco", "una palestra", "le spese del mese", "un parcheggio", "un cinema",
          "un orto", "le temperature di una città", "un registro presenze", "un'agenda", "un e-commerce"]

# exec = come si verificano gli esercizi di codice:
#   "output": si esegue il programma e si confronta l'output (unità prima delle funzioni)
#   "tests":  si eseguono test su funzioni/metodi/classi
#   "spring": progetto Spring Boot eseguito con Maven e test JUnit 5 (serve la preparazione una tantum)
#   "sql":    SQLite: si esegue la query su un database di prova e si confronta il risultato
#   "review": il codice non è eseguibile qui: lo valuta il modello rispetto alla soluzione
# requires (solo Python): pacchetti necessari; se mancano, l'unità passa in "review".
CURRICULUM = {
    "python": [
        {"id": "u1", "title": "Output e variabili", "exec": "output",
         "concepts": "print(), variabili, assegnazione e riassegnazione, nomi validi, f-string semplici, commenti"},
        {"id": "u2", "title": "Numeri e operatori", "exec": "output",
         "concepts": "int e float, + - * /, divisione intera //, resto %, potenza **, precedenza, round(), int() e float()"},
        {"id": "u3", "title": "Stringhe", "exec": "output",
         "concepts": "indici, slicing, len(), upper/lower/strip/replace/split, concatenazione, ripetizione con *, in"},
        {"id": "u4", "title": "Condizioni", "exec": "output",
         "concepts": "if/elif/else, operatori di confronto, and/or/not, valori booleani, condizioni annidate"},
        {"id": "u5", "title": "Cicli", "exec": "output",
         "concepts": "for con range(), for su stringhe, while, break, continue, accumulatori e contatori"},
        {"id": "u6", "title": "Liste", "exec": "output",
         "concepts": "creare liste, indici, append/insert/remove/pop, len, in, sum/min/max, slicing, scorrere una lista"},
        {"id": "u7", "title": "Funzioni", "exec": "tests",
         "concepts": "def, parametri, return, valori di default, variabili locali, funzioni che chiamano funzioni"},
        {"id": "u8", "title": "Dizionari e set", "exec": "tests",
         "concepts": "dizionari, chiavi e valori, get, items, contare occorrenze, set, operazioni tra set"},
        {"id": "u9", "title": "Tuple e comprehension", "exec": "tests",
         "concepts": "tuple, unpacking, enumerate, zip, list comprehension con e senza condizione, sorted con key"},
        {"id": "u10", "title": "Classi e oggetti", "exec": "tests",
         "concepts": "class, __init__, self, attributi, metodi, __str__, più oggetti della stessa classe"},
        {"id": "u11", "title": "Eccezioni", "exec": "tests",
         "concepts": "try/except, except specifici (ValueError, ZeroDivisionError, KeyError), else/finally, raise"},
        {"id": "u12", "title": "Ricorsione e algoritmi", "exec": "tests",
         "concepts": "ricorsione con caso base, ricerca lineare e binaria, ordinamento semplice, massimo e minimo"},
        {"id": "u13", "title": "Moduli e libreria standard", "exec": "output",
         "concepts": "import, from ... import, alias, if __name__ == \"__main__\", math, datetime, collections (Counter, defaultdict), pip e ambienti virtuali (concetti)"},
        {"id": "u14", "title": "File e JSON", "exec": "output",
         "concepts": "open con with, leggere e scrivere file di testo, righe e split, json.dumps/json.loads, pathlib.Path, file CSV con il modulo csv"},
        {"id": "u15", "title": "OOP avanzata", "exec": "tests",
         "concepts": "ereditarietà, super(), override, @property, @classmethod e @staticmethod, dataclass, __eq__/__repr__/__len__"},
        {"id": "u16", "title": "Iteratori, generatori e decoratori", "exec": "tests",
         "concepts": "iter e next, yield, generator expression, decoratori con functools.wraps, context manager con with"},
        {"id": "u17", "title": "Type hint e codice pulito", "exec": "tests",
         "concepts": "annotazioni di tipo, Optional, list[int] e dict[str, int], docstring, nomi chiari, funzioni piccole, PEP 8"},
        {"id": "u18", "title": "Testare il codice", "exec": "tests",
         "concepts": "assert, unittest.TestCase e assertEqual, casi limite, test prima del codice (TDD), struttura dei test con pytest (concetti)"},
        {"id": "u19", "title": "SQL con sqlite3", "exec": "tests",
         "concepts": "CREATE TABLE, INSERT, SELECT con WHERE e ORDER BY, JOIN, GROUP BY, parametri ? contro la SQL injection, sqlite3 in memoria"},
        {"id": "u20", "title": "HTTP e API REST", "exec": "tests",
         "concepts": "metodi HTTP, codici di stato, JSON nelle richieste e risposte, URL e query string con urllib.parse, progettare risorse REST"},
        {"id": "u21", "title": "FastAPI: le basi", "exec": "tests", "requires": ["fastapi", "httpx"],
         "concepts": "FastAPI(), route GET e POST, parametri di percorso e query, modelli Pydantic, risposte JSON, TestClient per provare le route"},
        {"id": "u22", "title": "FastAPI: validazione ed errori", "exec": "tests", "requires": ["fastapi", "httpx"],
         "concepts": "validazione con Pydantic (Field, tipi), HTTPException e codici di stato, Depends per le dipendenze, response_model"},
        {"id": "u23", "title": "SQLAlchemy ORM", "exec": "tests", "requires": ["sqlalchemy"],
         "concepts": "DeclarativeBase e modelli, colonne e chiavi primarie, Session, select, insert/update/delete, relationship uno-a-molti, SQLite in memoria"},
        {"id": "u24", "title": "Progetto: API completa", "exec": "tests", "requires": ["fastapi", "httpx", "sqlalchemy"],
         "concepts": "API CRUD con FastAPI e SQLAlchemy, separare modelli/schemi/route, sessione del database come dipendenza, test end-to-end con TestClient"},
    ],
    "sql": [
        {"id": "u1", "title": "SELECT e FROM", "exec": "sql",
         "concepts": "SELECT, FROM, scegliere le colonne, *, alias con AS, espressioni nelle colonne, punto e virgola"},
        {"id": "u2", "title": "Filtrare con WHERE", "exec": "sql",
         "concepts": "WHERE, = <> < >, AND, OR, NOT, IN, BETWEEN, LIKE con % e _, IS NULL"},
        {"id": "u3", "title": "Ordinare e limitare", "exec": "sql",
         "concepts": "ORDER BY ASC e DESC, ordinamento su più colonne, LIMIT e OFFSET, DISTINCT"},
        {"id": "u4", "title": "Funzioni su testo, numeri e date", "exec": "sql",
         "concepts": "UPPER, LOWER, LENGTH, SUBSTR, ||, ROUND, ABS, COALESCE, date() e strftime() di SQLite"},
        {"id": "u5", "title": "Aggregazioni", "exec": "sql",
         "concepts": "COUNT(*) e COUNT(colonna), SUM, AVG, MIN, MAX, aggregazioni con WHERE, NULL nelle aggregazioni"},
        {"id": "u6", "title": "GROUP BY e HAVING", "exec": "sql",
         "concepts": "GROUP BY su una e più colonne, HAVING contro WHERE, contare per gruppo, ordinare i gruppi"},
        {"id": "u7", "title": "JOIN", "exec": "sql",
         "concepts": "INNER JOIN con ON, alias di tabella, join su più tabelle, chiavi primarie e chiavi esterne nelle join"},
        {"id": "u8", "title": "LEFT JOIN e dati mancanti", "exec": "sql",
         "concepts": "LEFT JOIN, righe senza corrispondenza, trovare chi non ha ordini con IS NULL, COUNT con LEFT JOIN, RIGHT JOIN e FULL OUTER JOIN (SQLite 3.39 o successivo)"},
        {"id": "u9", "title": "Sottoquery", "exec": "sql",
         "concepts": "sottoquery in WHERE con IN, sottoquery scalari, confronto con la media, EXISTS e NOT EXISTS, sottoquery in FROM"},
        {"id": "u10", "title": "CASE e logica condizionale", "exec": "sql",
         "concepts": "CASE WHEN THEN ELSE END, classificare righe, CASE dentro SUM e COUNT, ordinamenti personalizzati"},
        {"id": "u11", "title": "Creare tabelle", "exec": "sql",
         "concepts": "CREATE TABLE, tipi in SQLite, PRIMARY KEY, NOT NULL, UNIQUE, DEFAULT, CHECK, DROP TABLE"},
        {"id": "u12", "title": "INSERT, UPDATE e DELETE", "exec": "sql",
         "concepts": "INSERT INTO con colonne, inserimenti multipli, UPDATE con WHERE, DELETE con WHERE, il pericolo di dimenticare WHERE"},
        {"id": "u13", "title": "Chiavi esterne e relazioni", "exec": "sql",
         "concepts": "FOREIGN KEY e REFERENCES, relazioni uno-a-molti, tabella ponte per molti-a-molti, ON DELETE CASCADE"},
        {"id": "u14", "title": "Progettare un database", "exec": "sql",
         "concepts": "analisi dei requisiti, modello E-R (entità, attributi, relazioni e cardinalità), dal modello E-R alle tabelle, normalizzazione (1NF, 2NF, 3NF), eliminare dati duplicati, scegliere le chiavi, schema di un caso reale"},
        {"id": "u15", "title": "Indici e transazioni", "exec": "sql",
         "concepts": "CREATE INDEX, quando un indice aiuta, EXPLAIN QUERY PLAN, BEGIN, COMMIT, ROLLBACK, proprietà ACID"},
        {"id": "u16", "title": "CTE e window function", "exec": "sql",
         "concepts": "WITH (CTE), CTE ricorsive semplici, ROW_NUMBER, RANK, SUM e AVG OVER con PARTITION BY, totali progressivi"},
        {"id": "u17", "title": "Query da colloquio", "exec": "sql",
         "concepts": "secondo valore più alto, top N per gruppo, trovare duplicati, differenza tra righe consecutive con LAG, viste con CREATE VIEW"},
    ],
    "java": [
        {"id": "u1", "title": "Output e variabili", "exec": "output",
         "concepts": "System.out.println e print, tipi int double boolean char String, dichiarazione e assegnazione"},
        {"id": "u2", "title": "Operatori e Math", "exec": "output",
         "concepts": "operatori aritmetici, divisione tra interi, resto %, cast (int) e (double), ++ e +=, Math.max/min/abs/pow/sqrt"},
        {"id": "u3", "title": "Stringhe", "exec": "output",
         "concepts": "length, charAt, substring, indexOf, equals invece di ==, toUpperCase, concatenazione, String.valueOf"},
        {"id": "u4", "title": "Condizioni", "exec": "output",
         "concepts": "if/else if/else, operatori di confronto, && || !, switch, operatore ternario"},
        {"id": "u5", "title": "Cicli", "exec": "output",
         "concepts": "for, while, do-while, break, continue, accumulatori, cicli annidati semplici"},
        {"id": "u6", "title": "Array", "exec": "output",
         "concepts": "dichiarare e inizializzare array, length, indici, scorrere con for e for-each, Arrays.toString"},
        {"id": "u7", "title": "Metodi", "exec": "tests",
         "concepts": "metodi static, parametri, tipo di ritorno, return, overloading, metodi che usano array e stringhe"},
        {"id": "u8", "title": "ArrayList e HashMap", "exec": "tests",
         "concepts": "ArrayList add/get/set/remove/size/contains, HashMap put/get/getOrDefault/containsKey, scorrere keySet ed entrySet"},
        {"id": "u9", "title": "Classi, oggetti e incapsulamento", "exec": "tests",
         "concepts": "classe e oggetto, campi privati, costruttore e this, getter e setter con controlli, toString, incapsulamento: proteggere lo stato dell'oggetto"},
        {"id": "u10", "title": "Ereditarietà, polimorfismo e astrazione", "exec": "tests",
         "concepts": "extends e super, @Override, classi e metodi abstract, polimorfismo con una lista del tipo padre, upcasting, i quattro pilastri dell'OOP"},
        {"id": "u25", "title": "Interfacce e accoppiamento debole", "exec": "tests",
         "concepts": "interface e implements, più interfacce nella stessa classe, metodi default e static, interfaccia o classe astratta (quando usare cosa), programmare verso l'interfaccia, passare le dipendenze nel costruttore (loose coupling)"},
        {"id": "u11", "title": "Eccezioni", "exec": "tests",
         "concepts": "try/catch/finally, più catch, throw e throws, eccezioni checked e unchecked, eccezioni custom (extends Exception e RuntimeException) con messaggio, try-with-resources"},
        {"id": "u26", "title": "Principi SOLID e Singleton", "exec": "tests",
         "concepts": "Single responsibility, Open/closed, Liskov, Interface segregation, Dependency inversion con esempi piccoli prima/dopo, pattern Singleton (istanza unica, costruttore privato, versione con enum), perché il Singleton complica i test"},
        {"id": "u12", "title": "Ricorsione e algoritmi", "exec": "tests",
         "concepts": "ricorsione con caso base, ricerca lineare e binaria, bubble sort, massimo e minimo in un array"},
        {"id": "u13", "title": "Generics", "exec": "tests",
         "concepts": "classi generiche <T>, metodi generici, tipi limitati <T extends Comparable<T>>, wildcard ?, perché i generics evitano i cast"},
        {"id": "u15", "title": "Collection Framework: scelte e prestazioni", "exec": "tests",
         "concepts": "List, Set e Map come interfacce, ArrayList contro LinkedList (accesso per indice, inserimenti in testa), HashSet, LinkedHashSet e TreeSet, HashMap e TreeMap, complessità delle operazioni, equals e hashCode, Comparable e Comparator, Deque come pila e coda"},
        {"id": "u27", "title": "Interfacce funzionali", "exec": "tests",
         "concepts": "@FunctionalInterface e interfacce funzionali scritte da te, Function, BiFunction, Predicate, Consumer, Supplier, UnaryOperator, BinaryOperator, lambda e method reference al posto delle classi anonime, comporre con andThen, compose, and, or, negate, variabili effectively final",
         "notes": "Se usi uno stream, non salvarlo in una variabile per riusarlo: uno stream si consuma una sola volta."},
        {"id": "u14", "title": "Lambda e Stream API", "exec": "tests",
         "concepts": "stream da liste e mappe, filter, map, flatMap, sorted con Comparator.comparing, distinct, limit, anyMatch e allMatch, reduce, collect con toList, toMap, groupingBy, counting, partitioningBy, joining, IntStream e sum/average, Optional",
         "notes": "Uno stream si consuma una sola volta: non salvarlo mai in una variabile Stream per riusarlo, ma crea ogni volta un nuovo stream da lista.stream() o mappa.entrySet().stream(). Usa nomi di variabili senza accenti."},
        {"id": "u16", "title": "File e I/O", "exec": "output",
         "concepts": "java.nio.file Files e Path, leggere e scrivere righe, try-with-resources, BufferedReader, IOException"},
        {"id": "u17", "title": "Java moderno: record, enum, sealed e pattern", "exec": "tests",
         "concepts": "record, enum con campi e metodi, switch con frecce e come espressione, var, text block, instanceof con pattern, sealed interface con permits, switch con pattern sui record (Java 21), package e modificatori di accesso",
         "notes": "Lo switch con pattern sui tipi e sui record richiede Java 21: usalo solo negli esercizi di livello difficile."},
        {"id": "u18", "title": "Test con JUnit", "exec": "spring",
         "concepts": "JUnit 5: @Test, assertEquals, assertThrows, @BeforeEach, nomi dei test, casi limite, mock (concetti)"},
        {"id": "u19", "title": "Maven e struttura del progetto", "exec": "review",
         "concepts": "pom.xml, groupId/artifactId/version, dipendenze e scope, ciclo di vita (compile, test, package), struttura src/main/java e src/test/java"},
        {"id": "u20", "title": "Database con JDBC e SQL", "exec": "spring",
         "concepts": "SQL di base, Connection, PreparedStatement, ResultSet, transazioni, try-with-resources con JDBC"},
        {"id": "u21", "title": "Spring Core: IoC e Dependency Injection", "exec": "spring",
         "concepts": "container IoC, bean, @Component/@Service/@Repository, iniezione nel costruttore, @Configuration e @Bean, scope dei bean, ciclo di vita (@PostConstruct)"},
        {"id": "u22", "title": "Spring Boot: API REST", "exec": "spring",
         "concepts": "@SpringBootApplication, @RestController, @GetMapping/@PostMapping/@PutMapping/@DeleteMapping, @PathVariable, @RequestParam, @RequestBody, JSON con i record, ResponseEntity e codici di stato (200, 201, 204, 400, 404)"},
        {"id": "u23", "title": "Spring Data JPA e Hibernate", "exec": "spring",
         "concepts": "ORM, @Entity, @Id e @GeneratedValue, JpaRepository, query derivate dal nome, @Query con JPQL e parametri (@Param), @OneToMany/@ManyToOne, @Transactional, configurazione MySQL in application.properties",
         "notes": "Negli esercizi il database è H2 in memoria: MySQL compare solo come configurazione in application.properties o nella teoria."},
        {"id": "u28", "title": "Spring MVC con Thymeleaf", "exec": "review",
         "concepts": "@Controller contro @RestController, Model e addAttribute, restituire il nome della vista, template in src/main/resources/templates, th:text, th:each, th:if, th:href con @{...}, form con th:object e th:field, @ModelAttribute, redirect dopo il POST",
         "notes": "Mostra sia la classe @Controller sia il template HTML Thymeleaf corrispondente (in un commento o come secondo blocco)."},
        {"id": "u24", "title": "Spring Boot avanzato", "exec": "spring",
         "concepts": "validazione con @Valid, @NotBlank e @Size, gestione errori con @RestControllerAdvice e @ExceptionHandler, application.properties e profili, test con MockMvc e jsonPath"},
        {"id": "u29", "title": "Spring Security: autenticazione e ruoli", "exec": "spring", "runner": "security",
         "concepts": "autenticazione contro autorizzazione, Security Filter Chain, bean SecurityFilterChain con authorizeHttpRequests, requestMatchers, permitAll, authenticated, hasRole, httpBasic, utenti con InMemoryUserDetailsManager, PasswordEncoder BCrypt, 401 contro 403",
         "notes": ("Spring Security 6 (Spring Boot 3): configurazione SOLO con il DSL a lambda, per esempio "
                   "`http.authorizeHttpRequests(a -> a.requestMatchers(\"/admin/**\").hasRole(\"ADMIN\").anyRequest().authenticated()).httpBasic(Customizer.withDefaults());` "
                   "in un metodo `@Bean SecurityFilterChain filtri(HttpSecurity http) throws Exception` dentro una classe `@Configuration` (niente WebSecurityConfigurerAdapter, niente antMatchers). "
                   "Per le API stateless aggiungi `.csrf(c -> c.disable())` se il test fa POST. "
                   "Nei test usa `@SpringBootTest` e `@AutoConfigureMockMvc`, e per l'utente `@WithMockUser(roles = \"ADMIN\")` "
                   "(import org.springframework.security.test.context.support.WithMockUser) oppure "
                   "`.with(httpBasic(\"mario\", \"segreta\"))` (import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic). "
                   "Senza login la risposta è 401, con l'utente sbagliato 403.")},
        {"id": "u30", "title": "JWT, sicurezza dei metodi, CORS e CSRF", "exec": "spring", "runner": "security",
         "concepts": "autenticazione stateless con JSON Web Token, sessione STATELESS, resource server con JwtDecoder, emettere un token con JwtEncoder, ruoli nel token, @EnableMethodSecurity, @PreAuthorize e @PostAuthorize, CORS con CorsConfigurationSource, cos'è il CSRF e perché si disattiva per le API con token",
         "notes": ("Usa il resource server di Spring (spring-boot-starter-oauth2-resource-server, già presente), non la libreria jjwt. "
                   "Chiave HMAC: `SecretKey chiave = new SecretKeySpec(\"una-chiave-segreta-lunga-almeno-32-byte!!\".getBytes(), \"HmacSHA256\");` "
                   "decoder: `NimbusJwtDecoder.withSecretKey(chiave).build()` come @Bean JwtDecoder; "
                   "encoder: `new NimbusJwtEncoder(new ImmutableSecret<>(chiave))` e per firmare "
                   "`encoder.encode(JwtEncoderParameters.from(JwsHeader.with(MacAlgorithm.HS256).build(), claims)).getTokenValue()`. "
                   "Nella SecurityFilterChain: `.csrf(c -> c.disable()).sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))"
                   ".oauth2ResourceServer(o -> o.jwt(Customizer.withDefaults()))`. Per @PreAuthorize metti @EnableMethodSecurity sulla classe @Configuration. "
                   "Nei test simula il token con `.with(jwt().authorities(new SimpleGrantedAuthority(\"ROLE_ADMIN\")))` "
                   "(import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt): "
                   "senza token 401, con il ruolo sbagliato 403.")},
        {"id": "u31", "title": "Spring AI: ChatClient e prompt", "exec": "spring", "runner": "ai",
         "concepts": "un'astrazione per molti modelli (OpenAI, Anthropic, Ollama in locale), ChatModel e ChatClient, prompt fluente con system e user, PromptTemplate e parametri nel testo, defaultSystem nel builder, configurazione di Ollama in application.properties",
         "notes": ("Spring AI 1.0. I test NON chiamano un modello vero: usa una classe `ModelloFinto implements ChatModel` con "
                   "`public ChatResponse call(Prompt prompt)` che restituisce `new ChatResponse(List.of(new Generation(new AssistantMessage(testo))))` "
                   "e può leggere `prompt.getContents()` o `prompt.getInstructions()` (lista di Message, con getText()). "
                   "Import: org.springframework.ai.chat.client.ChatClient, org.springframework.ai.chat.model.ChatModel, org.springframework.ai.chat.model.ChatResponse, "
                   "org.springframework.ai.chat.model.Generation, org.springframework.ai.chat.messages.AssistantMessage, org.springframework.ai.chat.prompt.Prompt, "
                   "org.springframework.ai.chat.prompt.PromptTemplate. "
                   "API: `ChatClient.builder(modello).defaultSystem(\"...\").build()`, `chat.prompt().system(\"...\").user(u -> u.text(\"Traduci {testo}\").param(\"testo\", t)).call().content()`, "
                   "`new PromptTemplate(\"Ciao {nome}\").render(Map.of(\"nome\", \"Ada\"))`. "
                   "I test sono JUnit semplici, senza @SpringBootTest: creano il servizio passandogli il modello finto.")},
        {"id": "u32", "title": "Spring AI: risposte tipizzate e tool calling", "exec": "spring", "runner": "ai",
         "concepts": "structured output: risposta JSON mappata su un record con entity(), BeanOutputConverter e le istruzioni di formato, tool calling: metodi Java annotati con @Tool che il modello può decidere di chiamare, descrizioni dei tool e dei parametri, tools() nel prompt",
         "notes": ("Spring AI 1.0, modello finto come nell'unità precedente (`ModelloFinto implements ChatModel`). "
                   "Risposte tipizzate: il modello finto restituisce un JSON, per esempio `{\"titolo\":\"Dune\",\"anno\":1965}`, e il codice fa "
                   "`chat.prompt().user(\"...\").call().entity(Libro.class)` con `record Libro(String titolo, int anno) {}`. "
                   "Tool: `class Strumenti { @Tool(description = \"...\") String meteo(@ToolParam(description = \"la città\") String citta) { ... } }` "
                   "(import org.springframework.ai.tool.annotation.Tool e ToolParam); per provarli senza modello: "
                   "`ToolCallback[] t = ToolCallbacks.from(new Strumenti());` (import org.springframework.ai.support.ToolCallbacks e org.springframework.ai.tool.ToolCallback), "
                   "`t[0].getToolDefinition().name()` e `t[0].call(\"{\\\"citta\\\":\\\"Roma\\\"}\")` che restituisce il risultato serializzato in JSON (una stringa tra virgolette): "
                   "nei test controllalo con contains. Nel prompt i tool si passano con `.tools(new Strumenti())`.")},
        {"id": "u33", "title": "Spring AI: RAG e streaming", "exec": "spring", "runner": "ai",
         "concepts": "RAG: dividere i documenti, embeddings come vettori, vector store e ricerca per somiglianza, mettere i pezzi trovati nel prompt, PGVector e Milvus in produzione, streaming della risposta con Flux e stream().content()",
         "notes": ("Spring AI 1.0. Embeddings finti, deterministici: `class EmbeddingFinto implements EmbeddingModel` con "
                   "`public EmbeddingResponse call(EmbeddingRequest r)` che per ogni testo di `r.getInstructions()` crea `new Embedding(vettore(testo), indice)` "
                   "e `public float[] embed(Document d) { return vettore(d.getText()); }`, dove `vettore` conta alcune parole chiave (es. 3-4 dimensioni). "
                   "Import: org.springframework.ai.embedding.EmbeddingModel, EmbeddingRequest, EmbeddingResponse, Embedding; org.springframework.ai.document.Document. "
                   "Vector store in memoria: `SimpleVectorStore store = SimpleVectorStore.builder(new EmbeddingFinto()).build(); store.add(List.of(new Document(\"testo\")));` "
                   "e `store.similaritySearch(SearchRequest.builder().query(\"domanda\").topK(2).build())` (import org.springframework.ai.vectorstore.SimpleVectorStore e SearchRequest); "
                   "poi i testi trovati (`doc.getText()`) vanno nel messaggio system o user del ChatClient. "
                   "Streaming: il modello finto implementa anche `public Flux<ChatResponse> stream(Prompt p)` restituendo `Flux.just(...)` di più ChatResponse, "
                   "il codice usa `chat.prompt().user(\"...\").stream().content()` (Flux<String>) e il test lo raccoglie con "
                   "`collectList().block()` o con StepVerifier (reactor-test, già presente). Import reactor.core.publisher.Flux.")},
    ],
}


# Algoritmi e strutture dati: le stesse unità in Python (algopy) e in Java (algojava).
ALGO = [
    {"id": "u1", "title": "Complessità e O-grande", "exec": "tests",
     "concepts": "contare le operazioni, O(1), O(n), O(n²), O(log n), cicli annidati, confrontare due soluzioni dello stesso problema, spazio usato"},
    {"id": "u2", "title": "Array e stringhe: tecniche base", "exec": "tests",
     "concepts": "scorrere con l'indice, contatori, minimo e massimo in un passaggio, somme prefisse, invertire, ruotare un array"},
    {"id": "u3", "title": "Hash map e set", "exec": "tests",
     "concepts": "contare le frequenze, two sum con una mappa, anagrammi, primo elemento ripetuto, set per togliere i duplicati, ricerca in O(1)"},
    {"id": "u4", "title": "Due puntatori", "exec": "tests",
     "concepts": "puntatori ai due estremi, palindromi, coppie con somma data in un array ordinato, togliere i duplicati sul posto, unire due array ordinati"},
    {"id": "u5", "title": "Finestra scorrevole", "exec": "tests",
     "concepts": "finestra di dimensione fissa, somma massima di k elementi, finestra variabile, sottostringa più lunga senza ripetizioni"},
    {"id": "u6", "title": "Pile", "exec": "tests",
     "concepts": "push e pop, parentesi bilanciate, annullare operazioni, valutare un'espressione in notazione polacca inversa, prossimo elemento maggiore"},
    {"id": "u7", "title": "Code e deque", "exec": "tests",
     "concepts": "coda FIFO, deque con aggiunte e rimozioni ai due lati, simulare una fila, processare richieste in ordine, coda circolare"},
    {"id": "u8", "title": "Ricerca binaria", "exec": "tests",
     "concepts": "ricerca binaria iterativa, prima e ultima occorrenza, punto di inserimento, ricerca binaria sulla risposta (radice intera)"},
    {"id": "u9", "title": "Ricorsione", "exec": "tests",
     "concepts": "caso base e passo ricorsivo, pila delle chiamate, potenza, somma delle cifre, invertire una stringa, ricorsione su liste"},
    {"id": "u10", "title": "Ordinamenti", "exec": "tests",
     "concepts": "selection sort, insertion sort, merge sort, quick sort, stabilità, complessità, ordinare con una chiave personalizzata"},
    {"id": "u11", "title": "Liste collegate", "exec": "tests",
     "concepts": "classe Nodo, scorrere una lista, inserire in testa e in coda, rimuovere un nodo, invertire una lista, trovare un ciclo con lento e veloce"},
    {"id": "u12", "title": "Alberi binari", "exec": "tests",
     "concepts": "classe Nodo con sinistro e destro, visite preorder, inorder, postorder, altezza, contare i nodi, visita per livelli"},
    {"id": "u13", "title": "Alberi binari di ricerca", "exec": "tests",
     "concepts": "proprietà del BST, inserire, cercare, minimo e massimo, verificare se un albero è un BST, inorder che dà i valori ordinati"},
    {"id": "u14", "title": "Heap e code di priorità", "exec": "tests",
     "concepts": "min-heap e max-heap (heapq in Python, PriorityQueue in Java), i k elementi più grandi, unire liste ordinate, mediana corrente"},
    {"id": "u15", "title": "Grafi: BFS e DFS", "exec": "tests",
     "concepts": "lista di adiacenza, BFS con una coda, DFS ricorsiva e con pila, visitati, componenti connesse, cammino minimo in una griglia"},
    {"id": "u16", "title": "Grafi: algoritmi classici", "exec": "tests",
     "concepts": "ordinamento topologico, rilevare un ciclo, Dijkstra con una coda di priorità, union-find per le componenti"},
    {"id": "u17", "title": "Programmazione dinamica", "exec": "tests",
     "concepts": "sottoproblemi sovrapposti, memoization, tabulazione, Fibonacci, salire le scale, resto minimo di monete, zaino 0/1, sottosequenza comune più lunga"},
    {"id": "u18", "title": "Greedy e backtracking", "exec": "tests",
     "concepts": "scelta greedy e quando funziona, intervalli non sovrapposti, generare sottoinsiemi e permutazioni, backtracking con vincoli, N regine piccolo"},
]
CURRICULUM["algopy"] = ALGO
CURRICULUM["algojava"] = ALGO

# Percorsi mostrati nell'app: id → linguaggio in cui si esegue il codice.
PATHS = {
    "python": {"lang": "python", "name": "Python", "goal": "Da zero a FastAPI", "pre": "p"},
    "java": {"lang": "java", "name": "Java", "goal": "Da zero a Spring Boot", "pre": "j"},
    "sql": {"lang": "sql", "name": "SQL", "goal": "Da zero a SQL da colloquio", "pre": "s"},
    "algopy": {"lang": "python", "name": "Algoritmi · Python", "goal": "Algoritmi e strutture dati", "pre": "ap", "algo": True},
    "algojava": {"lang": "java", "name": "Algoritmi · Java", "goal": "Algoritmi e strutture dati", "pre": "aj", "algo": True},
}


def _main(body):
    lines = ["public class Main {", "    public static void main(String[] args) {"]
    lines += ["        " + l if l else "" for l in body.split("\n")]
    lines += ["    }", "}"]
    return "\n".join(lines)


SEEDS = {
    "python/u1/base": [
        {"type": "quiz", "title": "Cosa stampa print", "question": "Cosa stampa questa riga?", "code": "print(3 + 4)",
         "options": ["7", "3 + 4", "34", "Errore"], "correct": 0,
         "explain": "Senza virgolette `3 + 4` è un'espressione: Python la calcola e stampa il risultato."},
        {"type": "predici", "title": "Copia di una variabile", "code": "x = 5\ny = x\nx = 10\nprint(y)", "output": "5",
         "explain": "`y = x` copia il valore che `x` ha in quel momento (5). Cambiare `x` dopo non tocca `y`."},
        {"type": "riempi", "title": "Saluta con il nome", "statement": "Completa in modo che stampi `Ciao Ada`.",
         "code": "nome = \"Ada\"\n___(\"Ciao\", nome)", "answers": ["print"], "output": "Ciao Ada",
         "explain": "`print` stampa i suoi argomenti separati da uno spazio."},
        {"type": "quiz", "title": "Nomi di variabile", "question": "Quale nome di variabile NON è valido in Python?", "code": "",
         "options": ["2numero", "numero2", "_numero", "numero_due"], "correct": 0,
         "explain": "Un nome non può iniziare con una cifra. Può contenere lettere, cifre e underscore."},
        {"type": "riempi", "title": "Compleanno", "statement": "Aumenta l'età di un anno: deve stampare `21`.",
         "code": "eta = 20\neta = eta ___ 1\nprint(eta)", "answers": ["+"], "output": "21",
         "explain": "`eta = eta + 1` legge il valore attuale, aggiunge 1 e lo riassegna alla stessa variabile."},
        {"type": "predici", "title": "Testo più testo", "code": "a = \"3\"\nb = \"4\"\nprint(a + b)", "output": "34",
         "explain": "Con le virgolette sono stringhe: `+` le unisce invece di sommarle."},
        {"type": "predici", "title": "f-string", "code": "nome = \"Luca\"\nanni = 30\nprint(f\"{nome} ha {anni} anni\")",
         "output": "Luca ha 30 anni", "explain": "In una f-string le parentesi graffe vengono sostituite dal valore della variabile."},
        {"type": "riempi", "title": "Scambio di valori", "statement": "Scambia i valori di `x` e `y`: deve stampare `3 2`.",
         "code": "x = 2\ny = 3\nx, y = y, ___\nprint(x, y)", "answers": ["x"], "output": "3 2",
         "explain": "A destra Python prima legge `y, x` (3, 2), poi li assegna a `x, y`: lo scambio avviene senza variabile d'appoggio."},
    ],
    "java/u1/base": [
        {"type": "quiz", "title": "Il tipo giusto", "question": "Quale tipo usi per memorizzare il valore 3.14?", "code": "",
         "options": ["double", "int", "boolean", "char"], "correct": 0,
         "explain": "`double` contiene numeri con la virgola; `int` solo interi."},
        {"type": "predici", "title": "Copia di una variabile", "code": _main("int a = 5;\nint b = a;\na = 10;\nSystem.out.println(b);"),
         "output": "5", "explain": "`b = a` copia il valore 5. Cambiare `a` dopo non modifica `b`."},
        {"type": "riempi", "title": "Stampa a capo", "statement": "Completa in modo che stampi `Ciao Ada` e vada a capo.",
         "code": _main("String nome = \"Ada\";\nSystem.out.___(\"Ciao \" + nome);"), "answers": ["println"], "output": "Ciao Ada",
         "explain": "`println` stampa e va a capo; `print` stampa senza andare a capo."},
        {"type": "quiz", "title": "Decimale in un int", "question": "Cosa succede compilando questa riga?", "code": "int x = 3.5;",
         "options": ["Errore di compilazione", "x vale 3", "x vale 4", "x vale 3.5"], "correct": 0,
         "explain": "Java non converte da solo un `double` in `int`, perché perderebbe informazioni: serve un cast esplicito `(int) 3.5`."},
        {"type": "predici", "title": "Stringa più numeri", "code": _main("System.out.println(\"3\" + 4 + 5);"), "output": "345",
         "explain": "Si valuta da sinistra: `\"3\" + 4` dà la stringa \"34\", poi `+ 5` la allunga in \"345\"."},
        {"type": "predici", "title": "Numeri più stringa", "code": _main("System.out.println(3 + 4 + \"5\");"), "output": "75",
         "explain": "Da sinistra: `3 + 4` sono due int e fanno 7, poi `7 + \"5\"` diventa la stringa \"75\"."},
        {"type": "riempi", "title": "Vero o falso", "statement": "Dichiara la variabile con il tipo giusto.",
         "code": _main("___ attivo = true;\nSystem.out.println(attivo);"), "answers": ["boolean"], "output": "true",
         "explain": "`true` e `false` sono valori di tipo `boolean`."},
        {"type": "predici", "title": "Lettera più uno", "code": _main("char c = 'A';\nSystem.out.println(c + 1);"), "output": "66",
         "explain": "Un `char` è un numero (il codice di 'A' è 65): `c + 1` è un'operazione tra interi e dà 66."},
    ],
}


# ---------------------------------------------------------------- logica
# Ogni livello ha esercizi illimitati: si generano finché ti alleni.
LOGIC = [
    {"id": "rompicapo", "title": "Rompicapo", "lang": "python", "mode": "logic",
     "desc": "Deduzione, chi dice il vero, ordinamenti, pesate, età, orologi, combinatoria.",
     "topic": "rompicapo di logica e deduzione (chi mente e chi dice il vero, ordinare persone o oggetti da indizi, pesate, età, "
              "orologi e calendari, combinatoria semplice, incroci di informazioni)",
     "mix": {"base": {"logica": 8}, "pratica": {"logica": 8}, "sfida": {"logica": 8}}},
    {"id": "sequenze", "title": "Sequenze e numeri", "lang": "python", "mode": "logic",
     "desc": "Successioni, pattern, aritmetica ragionata, probabilità semplice.",
     "topic": "successioni numeriche e di lettere, pattern, aritmetica ragionata, percentuali, divisibilità, probabilità semplice, conteggi",
     "mix": {"base": {"logica": 8}, "pratica": {"logica": 8}, "sfida": {"logica": 8}}},
    {"id": "algoritmi_python", "title": "Algoritmi in Python", "lang": "python", "mode": "tests",
     "desc": "Problemi da colloquio: stringhe, array, hash map, due puntatori, ricorsione.",
     "topic": "problemi algoritmici da colloquio tecnico (stringhe, array, dizionari come hash map, due puntatori, finestra scorrevole, "
              "pile e code, ricorsione, ordinamento, ricerca binaria); scegli un problema classico con un nome chiaro",
     "mix": {"base": {"predici": 2, "zero": 4, "bug": 2}, "pratica": {"predici": 1, "zero": 5, "bug": 2}, "sfida": {"zero": 6, "bug": 2}}},
    {"id": "sql_query", "title": "Query SQL da colloquio", "lang": "sql", "mode": "sql",
     "desc": "JOIN, aggregazioni, sottoquery e window function come nei colloqui tecnici.",
     "topic": "query SQL da colloquio tecnico (top N, secondo valore più alto, duplicati, clienti senza ordini, totali per gruppo, "
              "confronti con la media, ranking con window function)",
     "mix": {"base": {"predici": 2, "zero": 4, "bug": 2}, "pratica": {"predici": 1, "zero": 5, "bug": 2}, "sfida": {"zero": 6, "bug": 2}}},
    {"id": "algoritmi_java", "title": "Algoritmi in Java", "lang": "java", "mode": "tests",
     "desc": "Gli stessi problemi da colloquio, in Java.",
     "topic": "problemi algoritmici da colloquio tecnico (stringhe, array, HashMap, due puntatori, finestra scorrevole, "
              "Deque come pila e coda, ricorsione, ordinamento, ricerca binaria); scegli un problema classico con un nome chiaro",
     "mix": {"base": {"predici": 2, "zero": 4, "bug": 2}, "pratica": {"predici": 1, "zero": 5, "bug": 2}, "sfida": {"zero": 6, "bug": 2}}},
]
LOGIC_LEVEL_NAMES = {"base": "Facile", "pratica": "Medio", "sfida": "Difficile"}

# ---------------------------------------------------------------- colloquio
INTERVIEW = [
    {"id": "java_backend", "title": "Java backend junior", "lang": "java", "algo": "algoritmi_java",
     "topic": "Java (OOP, collezioni, eccezioni, stream, generics, equals/hashCode, immutabilità), Spring Boot (IoC, DI, REST, JPA, transazioni), "
              "SQL e database, HTTP e REST, Git, test"},
    {"id": "python_backend", "title": "Python backend junior", "lang": "python", "algo": "algoritmi_python",
     "topic": "Python (tipi, mutabilità, liste/dizionari, comprehension, OOP, eccezioni, generatori, decoratori), FastAPI, SQLAlchemy, "
              "SQL e database, HTTP e REST, Git, test"},
    {"id": "sql_db", "title": "SQL e database", "lang": "sql", "algo": "sql_query",
     "topic": "SQL (SELECT, JOIN, GROUP BY, HAVING, sottoquery, window function), progettazione e normalizzazione, chiavi e vincoli, "
              "indici e prestazioni, transazioni e ACID, livelli di isolamento, SQL contro NoSQL, ORM e problema N+1"},
    {"id": "fondamenti", "title": "Fondamenti di informatica", "lang": "python", "algo": "algoritmi_python",
     "topic": "OOP e principi SOLID, strutture dati (array, liste, hash map, alberi, grafi), complessità O-grande, SQL e normalizzazione, "
              "HTTP, REST e autenticazione, Git, processi e thread, sicurezza web di base"},
]
INTERVIEW_MIX = {"base": {"orale": 6}, "pratica": {"orale": 6}, "sfida": {"orale": 6}}
INTERVIEW_LEVEL_NAMES = {"base": "Junior", "pratica": "Junior forte", "sfida": "Verso mid"}


def _lg(q, opts, ans, explain, verify, title):
    return {"type": "logica", "title": title, "question": q, "options": opts, "answer": ans,
            "correct": opts.index(ans), "explain": explain, "verify": verify}


SEEDS.update({
    "logica/rompicapo/base": [
        _lg("Anna è più alta di Bruno. Carla è più bassa di Bruno. Chi è la più bassa dei tre?", ["Carla", "Bruno", "Anna", "Non si può dire"], "Carla",
            "Anna > Bruno > Carla: Carla è sotto entrambi.",
            "from itertools import permutations\nfor o in permutations(['Anna','Bruno','Carla']):\n    h={n:i for i,n in enumerate(o)}\n    if h['Anna']>h['Bruno']>h['Carla']:\n        print(o[0])", "Chi è più basso"),
        _lg("In un cassetto ci sono calzini neri e bianchi mescolati, al buio. Quanti ne devi prendere al minimo per essere sicuro di avere una coppia dello stesso colore?",
            ["3", "2", "4", "5"], "3", "Con 2 calzini potrebbero essere di colori diversi; il terzo è per forza uguale a uno dei due (principio dei cassetti).",
            "from itertools import product\nn=1\nwhile not all(len(set(c))<len(c) for c in product('NB',repeat=n)):\n    n+=1\nprint(n)", "Calzini al buio"),
        _lg("Un mattone pesa 1 kg più mezzo mattone. Quanto pesa un mattone?", ["2 kg", "1,5 kg", "1 kg", "3 kg"], "2 kg",
            "Se m = 1 + m/2, allora m/2 = 1 e quindi m = 2.", "for m in range(1,10):\n    if m == 1 + m/2:\n        print(f'{m} kg')", "Il mattone"),
        _lg("Ci sono 5 persone in una stanza e ognuna stringe la mano a tutte le altre una sola volta. Quante strette di mano ci sono?", ["10", "20", "25", "5"], "10",
            "Ogni coppia si stringe la mano una volta: le coppie di 5 persone sono 5·4/2 = 10.",
            "from itertools import combinations\nprint(len(list(combinations(range(5),2))))", "Strette di mano"),
        _lg("Marco dice: «Luca mente». Luca dice: «Sara mente». Sara dice: «Marco e Luca mentono». Chi dice la verità?",
            ["Luca", "Marco", "Sara", "Nessuno"], "Luca",
            "Se Luca dice il vero, Sara mente; allora non è vero che Marco e Luca mentono entrambi (Luca è sincero), coerente. Marco, dicendo che Luca mente, mente. Solo Luca è sincero.",
            "from itertools import product\nfor m,l,s in product([True,False],repeat=3):\n    if m==(not l) and l==(not s) and s==((not m) and (not l)):\n        print(['Marco','Luca','Sara'][[m,l,s].index(True)] if [m,l,s].count(True)==1 else 'Nessuno')", "Chi mente"),
        _lg("Un orologio segna le 3:15. Quanti gradi ci sono tra la lancetta delle ore e quella dei minuti?", ["7,5", "0", "15", "22,5"], "7,5",
            "I minuti sono su 90°. Le ore in 15 minuti avanzano di un quarto di 30°, cioè 7,5°: stanno a 97,5°. Differenza 7,5°.",
            "h=3; m=15\nore=30*h+0.5*m\nminuti=6*m\nprint(str(abs(ore-minuti)).replace('.',','))", "Lancette alle 3:15"),
    ],
    "logica/sequenze/base": [
        _lg("Qual è il numero successivo? 2, 4, 8, 16, …", ["32", "24", "20", "18"], "32", "Ogni termine è il doppio del precedente.",
            "s=[2,4,8,16]\nprint(s[-1]*2)", "Raddoppi"),
        _lg("Qual è il numero successivo? 1, 1, 2, 3, 5, 8, …", ["13", "11", "12", "16"], "13", "Ogni termine è la somma dei due precedenti (Fibonacci): 5 + 8 = 13.",
            "a,b=5,8\nprint(a+b)", "Fibonacci"),
        _lg("Qual è il numero successivo? 3, 6, 11, 18, 27, …", ["38", "36", "35", "40"], "38", "Le differenze sono 3, 5, 7, 9: la prossima è 11, quindi 27 + 11 = 38.",
            "s=[3,6,11,18,27]\nd=s[-1]-s[-2]\nprint(s[-1]+d+2)", "Differenze dispari"),
        _lg("Un prodotto costa 80 €. Viene scontato del 25% e poi rincarato del 25%. Quanto costa alla fine?", ["75 €", "80 €", "85 €", "70 €"], "75 €",
            "80 · 0,75 = 60; poi 60 · 1,25 = 75. Lo sconto e il rincaro non si annullano perché si applicano a basi diverse.",
            "p=80*0.75*1.25\nprint(f'{p:g} €')", "Sconto e rincaro"),
        _lg("Quale lettera viene dopo? A, C, F, J, O, …", ["U", "T", "S", "V"], "U", "I salti sono +2, +3, +4, +5: dopo O (15ª lettera) si salta di 6 e si arriva a U (21ª).",
            "import string\nL=string.ascii_uppercase\ni=L.index('O')\nprint(L[i+6])", "Salti di lettere"),
        _lg("Lanci due dadi a sei facce. Qual è la probabilità che la somma sia 7?", ["1/6", "1/12", "7/36", "1/7"], "1/6",
            "Le coppie che danno 7 sono 6 su 36 possibili: 6/36 = 1/6.",
            "from fractions import Fraction\nfrom itertools import product\nc=sum(1 for a,b in product(range(1,7),repeat=2) if a+b==7)\nprint(Fraction(c,36))", "Due dadi"),
    ],
})


def _or(q, points, model, follow, title):
    return {"type": "orale", "title": title, "question": q, "points": points, "model": model, "followup": follow}


SEEDS.update({
    "colloquio/java_backend/base": [
        _or("Qual è la differenza tra == ed equals() in Java?", ["== confronta i riferimenti (o i valori per i primitivi)", "equals confronta il contenuto se ridefinito",
            "String va confrontata con equals", "equals e hashCode vanno ridefiniti insieme"],
            "`==` controlla se due riferimenti puntano allo stesso oggetto (per i tipi primitivi confronta i valori). `equals()` confronta il contenuto, se la classe lo ridefinisce, come fa String. Per questo le stringhe si confrontano con equals. Se ridefinisci equals devi ridefinire anche hashCode, altrimenti HashMap e HashSet non funzionano bene.",
            "Cosa succede se ridefinisci equals ma non hashCode e metti l'oggetto in un HashSet?", "== contro equals"),
        _or("Che differenza c'è tra ArrayList e LinkedList? Quando useresti l'una o l'altra?", ["ArrayList è basata su array: accesso per indice O(1)",
            "LinkedList: inserimento/rimozione in testa O(1), accesso per indice O(n)", "nella pratica ArrayList è quasi sempre la scelta giusta", "uso di memoria e località della cache"],
            "ArrayList usa un array ridimensionabile: l'accesso per indice è O(1), l'aggiunta in fondo è O(1) ammortizzato, gli inserimenti in mezzo spostano gli elementi. LinkedList è una lista doppiamente collegata: inserire o togliere agli estremi è O(1), ma l'accesso per indice è O(n) e occupa più memoria. Nella pratica si usa quasi sempre ArrayList; per code e pile si preferisce ArrayDeque.",
            "Che complessità ha list.get(i) su una LinkedList e perché?", "ArrayList e LinkedList"),
        _or("Cos'è la Dependency Injection in Spring e perché si preferisce l'iniezione nel costruttore?", ["Spring crea i bean e li passa alle classi che li usano",
            "riduce l'accoppiamento e rende il codice testabile", "costruttore: dipendenze obbligatorie e campi final", "facile passare mock nei test"],
            "Con la Dependency Injection una classe non crea da sola le sue dipendenze: le riceve dal container di Spring, che crea e gestisce i bean. Questo riduce l'accoppiamento e permette di sostituire un'implementazione con un'altra, per esempio un mock nei test. L'iniezione nel costruttore rende le dipendenze obbligatorie ed esplicite, permette campi final e non richiede Spring per creare l'oggetto in un test.",
            "Che problema ha l'iniezione con @Autowired sui campi?", "Dependency Injection"),
        _or("Cos'è un'eccezione checked e una unchecked? Fai un esempio di ciascuna.", ["checked: va dichiarata o gestita (IOException)", "unchecked: estende RuntimeException (NullPointerException)",
            "le checked rappresentano problemi esterni recuperabili", "le unchecked di solito sono errori di programmazione"],
            "Le eccezioni checked (es. IOException, SQLException) estendono Exception ma non RuntimeException: il compilatore obbliga a gestirle con try/catch o a dichiararle con throws. Le unchecked estendono RuntimeException (es. NullPointerException, IllegalArgumentException) e non vanno dichiarate: di solito indicano errori di programmazione. Le checked servono per problemi esterni da cui ci si può riprendere.",
            "Quando lanceresti una IllegalArgumentException?", "Checked e unchecked"),
        _or("Cosa fa @Transactional e cosa succede se un metodo lancia un'eccezione?", ["il metodo gira in una transazione del database", "commit alla fine se va tutto bene",
            "rollback sulle RuntimeException (di default non sulle checked)", "funziona tramite proxy: le chiamate interne alla stessa classe non passano dal proxy"],
            "@Transactional fa eseguire il metodo dentro una transazione: se termina normalmente si fa commit, se lancia una RuntimeException si fa rollback (per le eccezioni checked di default no, a meno di rollbackFor). Spring lo implementa con un proxy, quindi una chiamata da un metodo della stessa classe non attiva la transazione.",
            "Perché chiamare un metodo @Transactional da un altro metodo della stessa classe non apre una transazione?", "@Transactional"),
        _or("Qual è la differenza tra GET, POST, PUT e DELETE in un'API REST? Quali sono idempotenti?", ["GET legge, POST crea, PUT sostituisce, DELETE cancella",
            "GET, PUT e DELETE sono idempotenti, POST no", "GET non deve modificare dati", "codici di stato tipici: 200, 201, 204, 404"],
            "GET legge una risorsa e non deve modificare nulla; POST crea una nuova risorsa (risposta tipica 201 Created); PUT sostituisce una risorsa esistente; DELETE la elimina (spesso 204 No Content). GET, PUT e DELETE sono idempotenti: ripeterli dà lo stesso stato finale. POST non lo è: due chiamate creano due risorse.",
            "Che differenza c'è tra PUT e PATCH?", "Metodi HTTP"),
    ],
    "colloquio/python_backend/base": [
        _or("Qual è la differenza tra lista e tupla in Python?", ["la lista è mutabile, la tupla immutabile", "la tupla può essere chiave di un dizionario se contiene elementi hashable",
            "la tupla per dati eterogenei a struttura fissa", "unpacking"],
            "La lista è mutabile: puoi aggiungere, togliere e cambiare elementi. La tupla è immutabile: una volta creata non cambia. Per questo una tupla (se contiene solo elementi hashable) può fare da chiave in un dizionario o stare in un set. Si usano le tuple per dati a struttura fissa, come una coppia (x, y), e le liste per collezioni che cambiano.",
            "Perché una lista non può essere chiave di un dizionario?", "Lista e tupla"),
        _or("Cosa succede con un argomento di default mutabile, come def f(x, lista=[])?", ["il default viene creato una sola volta, alla definizione", "le chiamate condividono la stessa lista",
            "si usa None come default e si crea la lista dentro", "bug classico"],
            "Il valore di default viene valutato una sola volta, quando la funzione viene definita. Se è una lista, tutte le chiamate che non passano l'argomento condividono la stessa lista, che quindi accumula valori da una chiamata all'altra. La soluzione è usare None come default e creare la lista dentro la funzione: if lista is None: lista = [].",
            "Lo stesso problema vale per un default intero? Perché?", "Default mutabile"),
        _or("Cos'è un generatore e quando conviene usarlo?", ["funzione con yield che produce valori uno alla volta", "valutazione pigra: non tiene tutto in memoria",
            "utile per file grandi o sequenze infinite", "si può scorrere una sola volta"],
            "Un generatore è una funzione che usa yield: invece di restituire tutti i valori insieme li produce uno alla volta, solo quando servono. Così non tiene tutto in memoria, il che è utile per leggere file grandi o generare sequenze lunghe o infinite. Un generatore si può scorrere una sola volta.",
            "Che differenza c'è tra [x*x for x in r] e (x*x for x in r)?", "Generatori"),
        _or("In FastAPI, a cosa servono i modelli Pydantic?", ["descrivono la forma dei dati in ingresso e uscita", "validano automaticamente i dati e restituiscono 422 se non validi",
            "convertono i tipi", "generano la documentazione OpenAPI"],
            "I modelli Pydantic descrivono la struttura dei dati con i type hint. FastAPI li usa per leggere il corpo delle richieste, convertire i tipi e validare: se i dati non sono validi risponde automaticamente 422 con il dettaglio degli errori. Servono anche per le risposte (response_model) e per generare la documentazione OpenAPI.",
            "Come restituiresti un 404 se l'elemento non esiste?", "Pydantic in FastAPI"),
        _or("Cos'è la SQL injection e come la eviti in Python?", ["inserire input dell'utente nella query come testo eseguibile", "mai concatenare o usare f-string nelle query",
            "query parametrizzate (? o :nome)", "l'ORM parametrizza per te"],
            "La SQL injection succede quando l'input dell'utente viene inserito nel testo della query e finisce per essere eseguito come SQL. Si evita con le query parametrizzate: cursor.execute('SELECT ... WHERE id = ?', (id,)), così il valore viaggia separato dalla query. Mai costruire query con f-string o concatenazioni. Un ORM come SQLAlchemy parametrizza in automatico.",
            "Perché una f-string nella query è pericolosa anche se il campo è numerico nel form?", "SQL injection"),
        _or("Che differenza c'è tra is e ==?", ["== confronta i valori (__eq__)", "is confronta l'identità: stesso oggetto", "si usa is con None", "piccoli interi e stringhe possono essere condivisi: non fidarsi di is"],
            "== confronta i valori chiamando __eq__; is controlla se sono lo stesso oggetto in memoria. Si usa is per None (x is None). Per numeri e stringhe is può dare risultati che sembrano casuali, perché Python a volte riusa gli stessi oggetti: per confrontare valori si usa sempre ==.",
            "Cosa stampa [] is []?", "is e =="),
    ],
})


_ST = ("CREATE TABLE studenti (id INTEGER PRIMARY KEY, nome TEXT NOT NULL, citta TEXT, eta INTEGER, media REAL);\n"
       "INSERT INTO studenti VALUES (1, 'Ada', 'Roma', 21, 27.5), (2, 'Luca', 'Milano', 19, 24.0), (3, 'Sara', 'Roma', 23, 29.0),\n"
       "  (4, 'Marco', 'Napoli', 20, 22.5), (5, 'Giulia', 'Milano', 22, 26.0);")

SEEDS["sql/u1/base"] = [
    {"type": "quiz", "title": "Tutte le colonne", "question": "Cosa restituisce `SELECT * FROM studenti;`?", "code": "",
     "options": ["Tutte le righe con tutte le colonne", "Solo la prima riga", "Il numero di righe", "Solo la colonna id"], "correct": 0,
     "explain": "`*` vuol dire «tutte le colonne», e senza WHERE la query restituisce tutte le righe.", "check": "sql", "setup": _ST},
    {"type": "riempi", "title": "Scegli le colonne", "statement": "Mostra nome e città di tutti gli studenti.",
     "code": "___ nome, citta\nFROM studenti;", "answers": ["SELECT"], "check": "sql", "setup": _ST,
     "explain": "Ogni interrogazione inizia con SELECT, seguito dalle colonne che vuoi vedere."},
    {"type": "riempi", "title": "Da quale tabella", "statement": "Mostra il nome di tutti gli studenti.",
     "code": "SELECT nome\n___ studenti;", "answers": ["FROM"], "check": "sql", "setup": _ST,
     "explain": "FROM indica la tabella da cui leggere le righe."},
    {"type": "predici", "title": "Espressione in colonna", "code": "SELECT nome, eta + 1 AS eta_prossimo_anno\nFROM studenti\nWHERE id = 2;",
     "check": "sql", "setup": _ST, "explain": "Luca ha 19 anni: la colonna calcolata `eta + 1` vale 20. AS dà un nome alla colonna, ma non cambia i valori."},
    {"type": "riempi", "title": "Rinomina la colonna", "statement": "Mostra il nome con l'intestazione `studente`.",
     "code": "SELECT nome ___ studente\nFROM studenti;", "answers": ["AS"], "check": "sql", "setup": _ST,
     "explain": "`AS` assegna un alias alla colonna: cambia l'intestazione, non i dati."},
    {"type": "quiz", "title": "Il punto e virgola", "question": "A cosa serve il `;` alla fine di una query?", "code": "",
     "options": ["Segna la fine dell'istruzione", "Commenta la riga", "Ordina il risultato", "Seleziona tutte le colonne"], "correct": 0,
     "explain": "Il punto e virgola separa un'istruzione SQL dalla successiva: è indispensabile quando ne scrivi più di una.", "check": "sql", "setup": _ST},
    {"type": "predici", "title": "Due colonne", "code": "SELECT citta, nome\nFROM studenti\nWHERE eta > 21;",
     "check": "sql", "setup": _ST, "explain": "Solo Sara (23) e Giulia (22) hanno più di 21 anni; le colonne escono nell'ordine scritto nella SELECT: prima la città, poi il nome."},
    {"type": "riordina", "title": "Rimetti in ordine", "statement": "Mostra nome e media di tutti gli studenti.",
     "solution": "SELECT nome, media\nFROM studenti;", "check": "sql", "setup": _ST, "hints": ["Prima cosa vuoi vedere", "Poi da dove", "SELECT … FROM …"]},
]
