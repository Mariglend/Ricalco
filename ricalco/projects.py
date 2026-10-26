"""Progetti a tappe: un programma vero costruito un pezzo alla volta, con il metodo del ricalco.

Ogni tappa è una lista di modifiche ai file del progetto. Una modifica è:
  ("new", file, codice, cosa_fa, perche)            crea il file
  ("end", file, codice, cosa_fa, perche)            aggiunge in fondo al file
  ("after", file, riga, codice, cosa_fa, perche)    inserisce dopo la riga (uguale, indentazione compresa)
  ("replace", file, vecchio, codice, cosa_fa, perche) sostituisce un pezzo di testo
Applicando le tappe in ordine si ottiene il progetto completo (lo controlla test_progetti).
"""


def _t(title, goal, plan, ops, challenge):
    q, options, correct, why = plan
    return {"title": title, "goal": goal, "plan": {"q": q, "options": options, "correct": correct, "why": why},
            "ops": ops, "challenge": challenge}


INVASIONE = [
    _t("Una finestra vuota", "Aprire la finestra del gioco e tenerla aperta finché non la chiudi.",
       ("Un gioco deve continuare a girare finché il giocatore non lo chiude. Cosa serve?",
        ["Un ciclo infinito che a ogni giro legge gli eventi e ridisegna lo schermo", "Una funzione chiamata una volta sola",
         "Un ciclo for da 1 a 1000", "Un if che controlla se la finestra è aperta"], 0,
        "Ogni gioco ha un «game loop»: a ogni fotogramma legge tastiera e mouse, aggiorna lo stato e ridisegna. Si esce solo quando arriva l'evento di chiusura."),
       [("new", "invasione.py",
         'import sys\n\nimport pygame\n\n\nclass InvasioneAliena:\n    """Gestisce il gioco: finestra, eventi e disegno."""\n\n    def __init__(self):\n        pygame.init()\n        self.orologio = pygame.time.Clock()\n        self.schermo = pygame.display.set_mode((1000, 650))\n        pygame.display.set_caption("Invasione aliena")',
         "Importa pygame, crea la classe del gioco e nel costruttore apre una finestra di 1000×650 pixel.",
         "`pygame.init()` prepara la libreria; va chiamato prima di tutto il resto. L'orologio serve a far girare il gioco alla stessa velocità su ogni PC."),
        ("end", "invasione.py",
         '\n    def avvia(self):\n        """Il ciclo principale del gioco."""\n        while True:\n            for evento in pygame.event.get():\n                if evento.type == pygame.QUIT:\n                    sys.exit()\n            pygame.display.flip()\n            self.orologio.tick(60)',
         "Il ciclo infinito: legge gli eventi, chiude il programma se premi la X, mostra il fotogramma.",
         "`flip()` mostra quello che hai disegnato; `tick(60)` aspetta quanto basta per fare al massimo 60 fotogrammi al secondo."),
        ("end", "invasione.py",
         '\n\nif __name__ == "__main__":\n    gioco = InvasioneAliena()\n    gioco.avvia()',
         "Crea il gioco e lo avvia, ma solo se lanci direttamente questo file.",
         "Con `if __name__ == \"__main__\"` il file si può anche importare senza far partire il gioco.")],
       "Cambia il titolo della finestra e prova un'altra dimensione, per esempio 1200×800."),

    _t("Le impostazioni e lo sfondo", "Mettere tutti i numeri del gioco in una classe Impostazioni e colorare lo sfondo.",
       ("Dimensioni, colori e velocità si useranno in molti file. Dove conviene scriverli?",
        ["In una classe Impostazioni, in un solo posto", "Ripetuti in ogni file dove servono", "In variabili globali sparse", "Dentro il ciclo del gioco"], 0,
        "Se un numero vive in un solo posto, per cambiarlo basta una modifica: niente «numeri magici» sparsi nel codice."),
       [("new", "impostazioni.py",
         'class Impostazioni:\n    """Tutte le impostazioni del gioco in un posto solo."""\n\n    def __init__(self):\n        self.larghezza = 1000\n        self.altezza = 650\n        self.colore_sfondo = (15, 18, 40)',
         "Crea la classe con le dimensioni della finestra e il colore dello sfondo.",
         "Il colore è una tupla RGB: rosso, verde, blu da 0 a 255. (15, 18, 40) è un blu notte."),
        ("after", "invasione.py", "import pygame", "\nfrom impostazioni import Impostazioni",
         "Importa la classe Impostazioni dall'altro file.",
         "Gli import dei tuoi file vanno dopo quelli delle librerie, separati da una riga vuota: è la convenzione di Python (PEP 8)."),
        ("replace", "invasione.py", "        self.schermo = pygame.display.set_mode((1000, 650))",
         "        self.impostazioni = Impostazioni()\n        self.schermo = pygame.display.set_mode(\n            (self.impostazioni.larghezza, self.impostazioni.altezza))",
         "Crea le impostazioni e apre la finestra con le dimensioni prese da lì.",
         "La tupla delle dimensioni va tra parentesi: `set_mode` vuole un solo argomento con larghezza e altezza."),
        ("replace", "invasione.py", "            pygame.display.flip()",
         "            self.schermo.fill(self.impostazioni.colore_sfondo)\n            pygame.display.flip()",
         "A ogni fotogramma riempie lo schermo con il colore di sfondo, poi lo mostra.",
         "Si ridisegna tutto da zero a ogni fotogramma: prima lo sfondo, poi sopra il resto. Così ciò che si muove non lascia scie.")],
       "Cambia il colore di sfondo: prova (0, 0, 0) per il nero o un altro colore che ti piace."),

    _t("La navicella", "Disegnare la navicella in basso al centro.",
       ("La navicella deve stare in basso al centro anche se cambi le dimensioni della finestra. Come la posizioni?",
        ["Allineo un rettangolo al centro del bordo inferiore dello schermo", "Scrivo le coordinate fisse (475, 610)",
         "La metto a caso", "Uso il centro dello schermo"], 0,
        "Con `rect.midbottom = schermo.midbottom` la posizione si calcola dallo schermo: funziona con qualsiasi dimensione."),
       [("new", "navicella.py",
         'import pygame\n\n\nclass Navicella:\n    """La navicella del giocatore, disegnata con un triangolo."""\n\n    def __init__(self, gioco):\n        self.schermo = gioco.schermo\n        self.area = gioco.schermo.get_rect()\n        self.rect = pygame.Rect(0, 0, 50, 40)\n        self.rect.midbottom = self.area.midbottom',
         "Crea la classe Navicella: prende lo schermo dal gioco e mette un rettangolo 50×40 in basso al centro.",
         "In pygame la posizione di un oggetto è un `Rect`. Passare tutto il gioco (`gioco`) al costruttore dà accesso a schermo e impostazioni."),
        ("end", "navicella.py",
         '\n    def disegna(self):\n        """Disegna la navicella nella sua posizione attuale."""\n        r = self.rect\n        punti = [(r.centerx, r.top), (r.left, r.bottom), (r.right, r.bottom)]\n        pygame.draw.polygon(self.schermo, (120, 200, 255), punti)',
         "Disegna un triangolo dentro il rettangolo: punta in alto al centro, base in basso.",
         "Le coordinate partono da (0, 0) in alto a sinistra e la y cresce verso il basso: per questo la punta è a `r.top`."),
        ("after", "invasione.py", "from impostazioni import Impostazioni", "from navicella import Navicella",
         "Importa la classe Navicella.", "Ogni classe in un file suo: il progetto resta ordinato quando cresce."),
        ("after", "invasione.py", '        pygame.display.set_caption("Invasione aliena")', "        self.navicella = Navicella(self)",
         "Crea la navicella passandole il gioco stesso.", "`self` qui è il gioco: la navicella lo usa per trovare lo schermo."),
        ("after", "invasione.py", "            self.schermo.fill(self.impostazioni.colore_sfondo)", "            self.navicella.disegna()",
         "Disegna la navicella dopo lo sfondo.", "L'ordine conta: ciò che disegni dopo sta sopra. Se la disegnassi prima, lo sfondo la coprirebbe.")],
       "Cambia forma o colore alla navicella: per esempio aggiungi un secondo triangolo più piccolo come cabina."),

    _t("Muoversi con le frecce", "Spostare la navicella finché tieni premuta una freccia, con il ciclo diviso in metodi.",
       ("Vuoi che la navicella si muova finché tieni premuto il tasto, non di un passo per pressione. Come?",
        ["Alla pressione accendo un flag, al rilascio lo spengo; a ogni fotogramma mi muovo se il flag è acceso",
         "Sposto la navicella di 50 pixel a ogni pressione", "Leggo la tastiera solo una volta all'avvio", "Uso un ciclo while dentro l'evento"], 0,
        "Gli eventi KEYDOWN e KEYUP arrivano una volta sola; il flag ricorda lo stato del tasto tra un fotogramma e l'altro."),
       [("replace", "invasione.py",
         "        while True:\n            for evento in pygame.event.get():\n                if evento.type == pygame.QUIT:\n                    sys.exit()\n            self.schermo.fill(self.impostazioni.colore_sfondo)\n            self.navicella.disegna()\n            pygame.display.flip()\n            self.orologio.tick(60)",
         "        while True:\n            self._controlla_eventi()\n            self.navicella.aggiorna()\n            self._aggiorna_schermo()\n            self.orologio.tick(60)",
         "Il ciclo ora chiama tre metodi: legge gli eventi, aggiorna la navicella, ridisegna.",
         "Un ciclo corto che chiama metodi con nomi chiari si legge come un riassunto. Il trattino basso iniziale dice «metodo interno»."),
        ("after", "invasione.py", "            self.orologio.tick(60)",
         '\n    def _controlla_eventi(self):\n        """Risponde a tastiera e chiusura della finestra."""\n        for evento in pygame.event.get():\n            if evento.type == pygame.QUIT:\n                sys.exit()\n            elif evento.type == pygame.KEYDOWN:\n                if evento.key == pygame.K_RIGHT:\n                    self.navicella.a_destra = True\n                elif evento.key == pygame.K_LEFT:\n                    self.navicella.a_sinistra = True\n            elif evento.type == pygame.KEYUP:\n                if evento.key == pygame.K_RIGHT:\n                    self.navicella.a_destra = False\n                elif evento.key == pygame.K_LEFT:\n                    self.navicella.a_sinistra = False',
         "Legge gli eventi: con le frecce premute accende i flag di movimento, al rilascio li spegne.",
         "Il codice degli eventi che prima era nel ciclo ora vive qui. Con `elif` ogni evento viene gestito da un solo ramo."),
        ("after", "invasione.py", "                    self.navicella.a_sinistra = False",
         '\n    def _aggiorna_schermo(self):\n        """Ridisegna tutto e mostra il nuovo fotogramma."""\n        self.schermo.fill(self.impostazioni.colore_sfondo)\n        self.navicella.disegna()\n        pygame.display.flip()',
         "Il disegno spostato in un metodo suo: sfondo, navicella, flip.",
         "Separare «cosa succede» (eventi, aggiornamenti) da «cosa si vede» (disegno) è un'idea che ritroverai nel pattern MVC."),
        ("after", "navicella.py", "        self.rect.midbottom = self.area.midbottom",
         "        self.a_destra = False\n        self.a_sinistra = False",
         "I due flag di movimento partono spenti.", "Gli attributi si creano tutti nel costruttore, così esistono sempre quando li usi."),
        ("end", "navicella.py",
         '\n    def aggiorna(self):\n        """Sposta la navicella se un tasto freccia è premuto."""\n        if self.a_destra:\n            self.rect.x += 5\n        if self.a_sinistra:\n            self.rect.x -= 5',
         "A ogni fotogramma sposta la navicella di 5 pixel nella direzione accesa.",
         "Due `if` separati e non `elif`: se tieni premute entrambe le frecce si annullano e la navicella sta ferma.")],
       "Fai muovere la navicella anche con i tasti A e D (pygame.K_a e pygame.K_d)."),

    _t("Velocità e bordi", "Velocità presa dalle impostazioni e navicella che non esce dallo schermo.",
       ("La velocità sarà 6,5 pixel per fotogramma, ma `rect.x` accetta solo interi. Come non perdere i decimali?",
        ["Tengo la posizione in un float a parte e copio il valore nel rect", "Arrotondo la velocità a 6", "Uso velocità 6,5 direttamente sul rect", "Non si può"], 0,
        "Il rect tronca i decimali: sommare 6,5 a un intero darebbe sempre 6. Il float accumula i decimali e il rect riceve la posizione arrotondata."),
       [("after", "impostazioni.py", "        self.colore_sfondo = (15, 18, 40)", "        self.velocita_navicella = 6.5",
         "Aggiunge la velocità della navicella alle impostazioni.", "Ora la velocità si cambia in un solo posto."),
        ("after", "navicella.py", "        self.area = gioco.schermo.get_rect()", "        self.impostazioni = gioco.impostazioni",
         "La navicella tiene un riferimento alle impostazioni.", "Le servono per sapere quanto velocemente muoversi."),
        ("after", "navicella.py", "        self.rect.midbottom = self.area.midbottom", "        self.x = float(self.rect.x)",
         "Salva la posizione orizzontale come numero decimale.", "Il float tiene i decimali che il rect perderebbe."),
        ("replace", "navicella.py",
         "        if self.a_destra:\n            self.rect.x += 5\n        if self.a_sinistra:\n            self.rect.x -= 5",
         "        if self.a_destra and self.rect.right < self.area.right:\n            self.x += self.impostazioni.velocita_navicella\n        if self.a_sinistra and self.rect.left > 0:\n            self.x -= self.impostazioni.velocita_navicella\n        self.rect.x = self.x",
         "Si muove solo se non è già sul bordo, usa la velocità delle impostazioni e aggiorna il rect dal float.",
         "Il controllo sul bordo sta nella stessa condizione: se la navicella tocca il bordo destro, la freccia destra non ha effetto.")],
       "Prova velocità diverse (3, 10) e trova quella che ti sembra più giocabile."),

    _t("Tasti in ordine e uscita con Q", "Dividere la gestione dei tasti in due metodi e chiudere il gioco con Q.",
       ("La gestione degli eventi sta diventando lunga e annidata. Cosa fai?",
        ["Sposto la pressione e il rilascio dei tasti in due metodi separati", "La lascio così", "Metto tutto in una funzione globale", "Uso un dizionario di lambda"], 0,
        "Metodi piccoli con un compito solo: «cosa succede quando premi» e «cosa succede quando rilasci». È il refactoring più comune che farai."),
       [("replace", "invasione.py",
         "            elif evento.type == pygame.KEYDOWN:\n                if evento.key == pygame.K_RIGHT:\n                    self.navicella.a_destra = True\n                elif evento.key == pygame.K_LEFT:\n                    self.navicella.a_sinistra = True\n            elif evento.type == pygame.KEYUP:\n                if evento.key == pygame.K_RIGHT:\n                    self.navicella.a_destra = False\n                elif evento.key == pygame.K_LEFT:\n                    self.navicella.a_sinistra = False",
         "            elif evento.type == pygame.KEYDOWN:\n                self._tasto_premuto(evento)\n            elif evento.type == pygame.KEYUP:\n                self._tasto_rilasciato(evento)",
         "Il ciclo degli eventi delega i tasti a due metodi.", "Il codice del ciclo resta corto; i dettagli dei tasti vivono altrove."),
        ("after", "invasione.py", "                self._tasto_rilasciato(evento)",
         '\n    def _tasto_premuto(self, evento):\n        """Frecce per muoversi, Q per uscire."""\n        if evento.key == pygame.K_RIGHT:\n            self.navicella.a_destra = True\n        elif evento.key == pygame.K_LEFT:\n            self.navicella.a_sinistra = True\n        elif evento.key == pygame.K_q:\n            sys.exit()',
         "Gestisce i tasti premuti: frecce per muoversi, Q per chiudere.", "Aggiungere un tasto nuovo ora vuol dire aggiungere un `elif` qui."),
        ("after", "invasione.py", "            sys.exit()",
         '\n    def _tasto_rilasciato(self, evento):\n        """Ferma la navicella quando lasci la freccia."""\n        if evento.key == pygame.K_RIGHT:\n            self.navicella.a_destra = False\n        elif evento.key == pygame.K_LEFT:\n            self.navicella.a_sinistra = False',
         "Gestisce i tasti rilasciati: spegne il flag della freccia lasciata.", "Simmetrico al metodo precedente: ogni flag acceso ha il suo spegnimento.")],
       "Aggiungi un tasto che mette in pausa il gioco (suggerimento: un flag `self.in_pausa` controllato nel ciclo)."),

    _t("Sparare", "Sparare proiettili con la barra spaziatrice.",
       ("Ci saranno tanti proiettili sullo schermo nello stesso momento. Come li gestisci?",
        ["Una classe Proiettile e un gruppo che li contiene tutti", "Una variabile per ogni proiettile", "Una lista di numeri con le y", "Un solo proiettile che riparte"], 0,
        "Un gruppo di sprite (`pygame.sprite.Group`) aggiorna e gestisce tanti oggetti dello stesso tipo con una sola chiamata."),
       [("after", "impostazioni.py", "        self.velocita_navicella = 6.5",
         "        self.velocita_proiettile = 8.0\n        self.larghezza_proiettile = 4\n        self.altezza_proiettile = 15\n        self.colore_proiettile = (255, 220, 90)",
         "Le impostazioni dei proiettili: velocità, dimensioni e colore.", "Proiettili stretti e alti, gialli per vederli bene sul blu."),
        ("new", "proiettile.py",
         'import pygame\nfrom pygame.sprite import Sprite\n\n\nclass Proiettile(Sprite):\n    """Un proiettile sparato dalla navicella."""\n\n    def __init__(self, gioco):\n        super().__init__()\n        self.schermo = gioco.schermo\n        self.impostazioni = gioco.impostazioni\n        self.colore = self.impostazioni.colore_proiettile\n        self.rect = pygame.Rect(0, 0, self.impostazioni.larghezza_proiettile, self.impostazioni.altezza_proiettile)\n        self.rect.midtop = gioco.navicella.rect.midtop\n        self.y = float(self.rect.y)',
         "La classe Proiettile eredita da Sprite e parte dalla punta della navicella.",
         "`super().__init__()` inizializza la parte di Sprite: senza, il gruppo non riuscirebbe a gestire il proiettile."),
        ("end", "proiettile.py",
         '\n    def update(self):\n        """Sale verso l\'alto."""\n        self.y -= self.impostazioni.velocita_proiettile\n        self.rect.y = self.y\n\n    def disegna(self):\n        pygame.draw.rect(self.schermo, self.colore, self.rect)',
         "Il proiettile sale a ogni fotogramma e si disegna come rettangolo.",
         "Si chiama `update` (in inglese) perché è il metodo che il gruppo chiama da solo su ogni sprite."),
        ("after", "invasione.py", "from navicella import Navicella", "from proiettile import Proiettile",
         "Importa la classe Proiettile.", "Un file per classe, come per la navicella."),
        ("after", "invasione.py", "        self.navicella = Navicella(self)", "        self.proiettili = pygame.sprite.Group()",
         "Crea il gruppo vuoto dei proiettili.", "Il gruppo nasce vuoto; si riempie quando spari."),
        ("after", "invasione.py", "            self.navicella.a_sinistra = True",
         "        elif evento.key == pygame.K_SPACE:\n            self._spara()",
         "La barra spaziatrice chiama il metodo che spara.", "Un altro `elif` nel metodo dei tasti premuti: è il vantaggio del refactoring di prima."),
        ("after", "invasione.py", "            self.navicella.a_sinistra = False",
         '\n    def _spara(self):\n        """Crea un nuovo proiettile e lo aggiunge al gruppo."""\n        nuovo = Proiettile(self)\n        self.proiettili.add(nuovo)',
         "Crea un proiettile e lo mette nel gruppo.", "Una volta nel gruppo, il proiettile viene aggiornato e disegnato insieme agli altri."),
        ("after", "invasione.py", "            self.navicella.aggiorna()", "            self.proiettili.update()",
         "A ogni fotogramma tutti i proiettili salgono.", "`update()` sul gruppo chiama `update()` di ogni proiettile."),
        ("after", "invasione.py", "        self.navicella.disegna()",
         "        for proiettile in self.proiettili.sprites():\n            proiettile.disegna()",
         "Disegna ogni proiettile.", "Il gruppo sa aggiornare da solo, ma il disegno personalizzato lo chiediamo a ogni proiettile.")],
       "Cambia colore e dimensioni dei proiettili, oppure fai partire due proiettili affiancati."),

    _t("Proiettili sotto controllo", "Cancellare i proiettili usciti dallo schermo e limitarne il numero.",
       ("I proiettili usciti in alto continuano a esistere e a salire per sempre. Che problema c'è?",
        ["Occupano memoria e tempo di calcolo senza servire", "Nessuno: non si vedono", "Il gioco si chiude da solo", "Diventano alieni"], 0,
        "Ogni proiettile vivo viene aggiornato a ogni fotogramma: se non li togli, il gioco rallenta. Si cancellano appena escono."),
       [("after", "impostazioni.py", "        self.colore_proiettile = (255, 220, 90)", "        self.proiettili_max = 3",
         "Al massimo 3 proiettili sullo schermo insieme.", "Un limite rende il gioco più interessante: devi mirare invece di sparare a raffica."),
        ("replace", "invasione.py",
         "        nuovo = Proiettile(self)\n        self.proiettili.add(nuovo)",
         "        if len(self.proiettili) < self.impostazioni.proiettili_max:\n            nuovo = Proiettile(self)\n            self.proiettili.add(nuovo)",
         "Spara solo se ci sono meno proiettili del massimo.", "`len()` funziona anche su un gruppo di sprite."),
        ("after", "invasione.py", "            self.proiettili.add(nuovo)",
         '\n    def _aggiorna_proiettili(self):\n        """Muove i proiettili e cancella quelli usciti dallo schermo."""\n        self.proiettili.update()\n        for proiettile in self.proiettili.copy():\n            if proiettile.rect.bottom <= 0:\n                self.proiettili.remove(proiettile)',
         "Muove i proiettili e toglie quelli che hanno superato il bordo in alto.",
         "Si scorre una COPIA del gruppo: togliere elementi dalla collezione che stai scorrendo porta a saltarne qualcuno."),
        ("replace", "invasione.py", "            self.proiettili.update()", "            self._aggiorna_proiettili()",
         "Il ciclo ora chiama il nuovo metodo.", "Anche qui: il ciclo principale resta un elenco di passi con nomi chiari.")],
       "Stampa con print quanti proiettili ci sono a ogni sparo e verifica che non superino mai il massimo."),

    _t("Il primo alieno", "Disegnare un alieno in alto a sinistra.",
       ("L'alieno sarà uno di tanti, come i proiettili. Da cosa lo fai ereditare?",
        ["Da Sprite, così potrà stare in un gruppo", "Da Navicella", "Da niente: basta una funzione", "Da Impostazioni"], 0,
        "Ereditare da Sprite permette di gestire tutta la flotta con un gruppo, come i proiettili."),
       [("new", "alieno.py",
         'import pygame\nfrom pygame.sprite import Sprite\n\n\nclass Alieno(Sprite):\n    """Un alieno della flotta."""\n\n    def __init__(self, gioco):\n        super().__init__()\n        self.schermo = gioco.schermo\n        self.rect = pygame.Rect(0, 0, 46, 32)\n        self.rect.x = self.rect.width\n        self.rect.y = self.rect.height\n        self.x = float(self.rect.x)',
         "La classe Alieno: un rettangolo 46×32 messo a una distanza dal bordo pari alla sua larghezza e altezza.",
         "Lasciare come margine la dimensione dell'alieno stesso dà uno spazio proporzionato senza numeri magici."),
        ("end", "alieno.py",
         '\n    def disegna(self):\n        """Corpo ovale verde con due occhi."""\n        pygame.draw.ellipse(self.schermo, (110, 220, 120), self.rect)\n        occhio = 5\n        pygame.draw.circle(self.schermo, (15, 18, 40), (self.rect.centerx - 9, self.rect.centery - 3), occhio)\n        pygame.draw.circle(self.schermo, (15, 18, 40), (self.rect.centerx + 9, self.rect.centery - 3), occhio)',
         "Disegna l'alieno: un ovale verde e due occhi del colore dello sfondo.",
         "Gli occhi sono posizionati rispetto al centro del rect: se l'alieno si muove, gli occhi lo seguono."),
        ("after", "invasione.py", "from proiettile import Proiettile", "from alieno import Alieno",
         "Importa la classe Alieno.", "Ormai è un'abitudine: una classe, un file, un import."),
        ("after", "invasione.py", "        self.proiettili = pygame.sprite.Group()",
         "        self.alieni = pygame.sprite.Group()\n        self._crea_flotta()",
         "Crea il gruppo degli alieni e lo riempie.", "Il gruppo va creato prima di chiamare il metodo che ci aggiunge alieni."),
        ("after", "invasione.py", "                self.proiettili.remove(proiettile)",
         '\n    def _crea_flotta(self):\n        """Per ora un solo alieno."""\n        alieno = Alieno(self)\n        self.alieni.add(alieno)',
         "Crea un alieno e lo aggiunge al gruppo.", "Partire da un solo alieno e poi passare alla flotta è il modo giusto: prima fai funzionare il caso semplice."),
        ("after", "invasione.py", "            proiettile.disegna()",
         "        for alieno in self.alieni.sprites():\n            alieno.disegna()",
         "Disegna tutti gli alieni del gruppo.", "Stesso schema dei proiettili.")],
       "Cambia l'aspetto dell'alieno: colori, occhi più grandi, un'antenna con pygame.draw.line."),

    _t("La flotta", "Riempire lo schermo di righe e colonne di alieni.",
       ("Come riempi lo schermo di alieni lasciando spazio tra uno e l'altro e in basso per la navicella?",
        ["Due cicli: dentro aggiungo alieni sulla riga finché c'è spazio, fuori passo alla riga sotto", "Una lista scritta a mano con 80 posizioni",
         "Un solo ciclo da 0 a 80", "Ricorsione"], 0,
        "Due cicli annidati che avanzano finché c'è spazio funzionano con qualsiasi dimensione dello schermo e dell'alieno."),
       [("replace", "invasione.py",
         '        """Per ora un solo alieno."""\n        alieno = Alieno(self)\n        self.alieni.add(alieno)',
         '        """Riempie righe e colonne di alieni, lasciando spazio sotto per la navicella."""\n        alieno = Alieno(self)\n        larghezza, altezza = alieno.rect.size\n        x, y = larghezza, altezza\n        while y < self.impostazioni.altezza - 4 * altezza:\n            while x < self.impostazioni.larghezza - 2 * larghezza:\n                self._crea_alieno(x, y)\n                x += 2 * larghezza\n            x = larghezza\n            y += 2 * altezza',
         "Due cicli while: riempie una riga da sinistra a destra, poi torna a sinistra e scende di una riga.",
         "Il primo alieno serve solo a misurare. Il passo è il doppio della dimensione: un alieno e uno spazio grande come un alieno."),
        ("after", "invasione.py", "            y += 2 * altezza",
         '\n    def _crea_alieno(self, x, y):\n        """Crea un alieno nella posizione data."""\n        alieno = Alieno(self)\n        alieno.x = x\n        alieno.rect.x = x\n        alieno.rect.y = y\n        self.alieni.add(alieno)',
         "Crea un alieno in una posizione precisa e lo aggiunge alla flotta.",
         "Va aggiornato anche `alieno.x` (il float), altrimenti quando la flotta si muoverà l'alieno tornerebbe alla posizione iniziale.")],
       "Cambia gli spazi tra gli alieni o il numero di righe e guarda come cambia la difficoltà."),

    _t("La flotta si muove", "Far scorrere la flotta a destra e sinistra, scendendo a ogni bordo.",
       ("Quando un alieno tocca il bordo, cosa deve succedere?",
        ["Tutta la flotta scende di un po' e inverte la direzione", "Solo quell'alieno torna indietro", "L'alieno sparisce", "Il gioco finisce"], 0,
        "La flotta si muove come un blocco: basta che UN alieno tocchi il bordo perché tutti scendano e cambino verso."),
       [("after", "impostazioni.py", "        self.proiettili_max = 3",
         "        self.velocita_alieni = 1.5\n        self.discesa_flotta = 12\n        self.direzione_flotta = 1",
         "Velocità degli alieni, quanto scende la flotta e la direzione (1 destra, -1 sinistra).",
         "Usare 1 e -1 per la direzione permette di moltiplicare: lo stesso calcolo vale per entrambi i versi."),
        ("after", "alieno.py", "        self.schermo = gioco.schermo", "        self.impostazioni = gioco.impostazioni",
         "L'alieno tiene un riferimento alle impostazioni.", "Gli servono velocità e direzione."),
        ("after", "alieno.py", "        self.x = float(self.rect.x)",
         '\n    def tocca_bordo(self):\n        """True se l\'alieno è sul bordo destro o sinistro."""\n        area = self.schermo.get_rect()\n        return self.rect.right >= area.right or self.rect.left <= 0\n\n    def update(self):\n        """Si sposta a destra o a sinistra secondo la direzione della flotta."""\n        self.x += self.impostazioni.velocita_alieni * self.impostazioni.direzione_flotta\n        self.rect.x = self.x',
         "Due metodi: uno dice se l'alieno tocca un bordo, l'altro lo sposta nella direzione della flotta.",
         "`tocca_bordo` restituisce direttamente il risultato del confronto: non serve scrivere `if ...: return True else: return False`."),
        ("after", "invasione.py", "            self._aggiorna_proiettili()", "            self._aggiorna_alieni()",
         "Il ciclo muove anche gli alieni.", "Ogni fotogramma: eventi, navicella, proiettili, alieni, disegno."),
        ("after", "invasione.py", "        self.alieni.add(alieno)",
         '\n    def _controlla_bordi_flotta(self):\n        """Se un alieno tocca un bordo, la flotta scende e cambia direzione."""\n        for alieno in self.alieni.sprites():\n            if alieno.tocca_bordo():\n                for a in self.alieni.sprites():\n                    a.rect.y += self.impostazioni.discesa_flotta\n                self.impostazioni.direzione_flotta *= -1\n                break\n\n    def _aggiorna_alieni(self):\n        """Controlla i bordi e muove tutta la flotta."""\n        self._controlla_bordi_flotta()\n        self.alieni.update()',
         "Se un alieno è sul bordo fa scendere tutti e inverte la direzione; poi muove la flotta.",
         "Il `break` è fondamentale: senza, ogni alieno sul bordo invertirebbe di nuovo la direzione e la flotta resterebbe bloccata.")],
       "Rendi la flotta più veloce o fai scendere di più a ogni bordo e osserva come cambia il gioco."),

    _t("Colpire gli alieni", "Far sparire proiettile e alieno quando si toccano e creare una nuova flotta quando è distrutta.",
       ("Come controlli se un proiettile ha colpito un alieno senza scrivere due cicli a mano?",
        ["Uso pygame.sprite.groupcollide tra il gruppo dei proiettili e quello degli alieni", "Confronto le coordinate x di tutti",
         "Controllo solo il primo alieno", "Aspetto che l'alieno arrivi in fondo"], 0,
        "`groupcollide` confronta ogni elemento di un gruppo con ogni elemento dell'altro e può cancellare da solo quelli che si toccano."),
       [("after", "invasione.py", "                self.proiettili.remove(proiettile)", "        self._controlla_collisioni()",
         "Dopo aver mosso i proiettili controlla le collisioni.", "La riga è indentata come il `for`, non dentro: si esegue una volta, dopo il ciclo."),
        ("after", "invasione.py", "        self._controlla_collisioni()",
         '\n    def _controlla_collisioni(self):\n        """Elimina proiettili e alieni che si toccano; se la flotta è distrutta, ne arriva una nuova."""\n        pygame.sprite.groupcollide(self.proiettili, self.alieni, True, True)\n        if not self.alieni:\n            self.proiettili.empty()\n            self._crea_flotta()',
         "Toglie proiettili e alieni che si toccano; se gli alieni sono finiti svuota i proiettili e crea una nuova flotta.",
         "I due `True` dicono di cancellare sia il proiettile sia l'alieno. `if not self.alieni` è vero quando il gruppo è vuoto.")],
       "Fai in modo che un proiettile attraversi gli alieni invece di sparire (basta cambiare un argomento)."),

    _t("Vite e fine partita", "Perdere una vita quando un alieno ti tocca o arriva in fondo; con zero vite il gioco si ferma.",
       ("Dove conviene tenere il numero di vite rimaste, che cambia durante la partita?",
        ["In una classe Statistiche separata dalle impostazioni", "Nelle impostazioni, che non cambiano", "In una variabile globale", "Nella navicella"], 0,
        "Le impostazioni sono la configurazione del gioco; le statistiche sono lo stato di questa partita e si azzerano quando ricominci."),
       [("after", "impostazioni.py", "        self.velocita_navicella = 6.5", "        self.vite = 3",
         "Il numero di vite all'inizio della partita.", "È configurazione: resta nelle impostazioni."),
        ("new", "statistiche.py",
         'class Statistiche:\n    """Lo stato della partita in corso."""\n\n    def __init__(self, gioco):\n        self.impostazioni = gioco.impostazioni\n        self.azzera()\n\n    def azzera(self):\n        """Riporta i valori all\'inizio della partita."""\n        self.navicelle_rimaste = self.impostazioni.vite',
         "La classe Statistiche: tiene le vite rimaste e sa azzerarle.",
         "Il costruttore chiama `azzera()`: lo stesso metodo servirà quando si ricomincia una partita."),
        ("after", "invasione.py", "from alieno import Alieno", "from statistiche import Statistiche",
         "Importa la classe Statistiche.", "Un file, una classe."),
        ("after", "invasione.py", '        pygame.display.set_caption("Invasione aliena")',
         "        self.statistiche = Statistiche(self)\n        self.attivo = True",
         "Crea le statistiche e un flag che dice se la partita è in corso.", "Le statistiche usano le impostazioni, che a questo punto esistono già."),
        ("replace", "invasione.py",
         "            self.navicella.aggiorna()\n            self._aggiorna_proiettili()\n            self._aggiorna_alieni()",
         "            if self.attivo:\n                self.navicella.aggiorna()\n                self._aggiorna_proiettili()\n                self._aggiorna_alieni()",
         "Navicella, proiettili e alieni si muovono solo se la partita è attiva.",
         "Gli eventi e il disegno continuano anche a partita finita: così puoi ancora chiudere la finestra."),
        ("after", "invasione.py", "        self.alieni.update()",
         "        if pygame.sprite.spritecollideany(self.navicella, self.alieni):\n            self._navicella_colpita()\n        self._controlla_fondo()",
         "Dopo aver mosso gli alieni controlla se uno ha toccato la navicella o è arrivato in fondo.",
         "`spritecollideany` si ferma al primo alieno che tocca la navicella: basta uno."),
        ("after", "invasione.py", "        self._controlla_fondo()",
         '\n    def _navicella_colpita(self):\n        """Toglie una vita e ricomincia l\'ondata; senza vite la partita finisce."""\n        if self.statistiche.navicelle_rimaste > 1:\n            self.statistiche.navicelle_rimaste -= 1\n            self.proiettili.empty()\n            self.alieni.empty()\n            self._crea_flotta()\n            self.navicella.al_centro()\n            pygame.time.wait(500)\n        else:\n            self.attivo = False\n\n    def _controlla_fondo(self):\n        """Un alieno che arriva in fondo conta come navicella colpita."""\n        for alieno in self.alieni.sprites():\n            if alieno.rect.bottom >= self.impostazioni.altezza:\n                self._navicella_colpita()\n                break',
         "Se resta almeno una vita la toglie e ricomincia l'ondata; altrimenti ferma la partita. Un alieno in fondo conta come colpo.",
         "`pygame.time.wait(500)` fa una pausa di mezzo secondo per farti capire che sei stato colpito."),
        ("end", "navicella.py",
         '\n    def al_centro(self):\n        """Riporta la navicella in basso al centro."""\n        self.rect.midbottom = self.area.midbottom\n        self.x = float(self.rect.x)',
         "Riporta la navicella al centro e aggiorna anche il float.", "Se aggiornassi solo il rect, al fotogramma dopo il float la riporterebbe dov'era.")],
       "Dai 5 vite invece di 3, oppure fai lampeggiare lo schermo quando vieni colpito."),

    _t("Il punteggio", "Guadagnare punti per ogni alieno colpito e mostrare punti e vite in alto.",
       ("`groupcollide` restituisce un dizionario: chiave il proiettile, valore la lista degli alieni colpiti da quel proiettile. Come conti i punti?",
        ["Per ogni lista di alieni nel dizionario aggiungo i punti moltiplicati per la sua lunghezza", "Aggiungo i punti una volta per chiamata",
         "Conto le chiavi del dizionario", "Uso il numero di alieni rimasti"], 0,
        "Un proiettile può colpire due alieni insieme: contando la lunghezza di ogni lista non perdi nessun punto."),
       [("after", "impostazioni.py", "        self.direzione_flotta = 1", "        self.punti_alieno = 50",
         "Quanti punti vale un alieno.", "Configurazione: sta nelle impostazioni."),
        ("after", "statistiche.py", "        self.navicelle_rimaste = self.impostazioni.vite", "        self.punteggio = 0",
         "Il punteggio parte da zero a ogni partita.", "Sta in `azzera()`, quindi si azzera anche quando ricominci."),
        ("new", "tabellone.py",
         'import pygame\n\n\nclass Tabellone:\n    """Scrive punteggio e vite in alto a destra."""\n\n    def __init__(self, gioco):\n        self.schermo = gioco.schermo\n        self.statistiche = gioco.statistiche\n        self.font = pygame.font.SysFont(None, 36)\n        self.colore = (230, 230, 230)\n\n    def disegna(self):\n        testo = f"Punti {self.statistiche.punteggio}   Vite {self.statistiche.navicelle_rimaste}"\n        immagine = self.font.render(testo, True, self.colore)\n        rect = immagine.get_rect()\n        rect.topright = (self.schermo.get_rect().right - 20, 15)\n        self.schermo.blit(immagine, rect)',
         "La classe Tabellone: trasforma punti e vite in un'immagine di testo e la disegna in alto a destra.",
         "In pygame il testo si «renderizza» in un'immagine, che poi si copia sullo schermo con `blit`."),
        ("after", "invasione.py", "from statistiche import Statistiche", "from tabellone import Tabellone",
         "Importa la classe Tabellone.", "Un file, una classe."),
        ("after", "invasione.py", "        self.statistiche = Statistiche(self)", "        self.tabellone = Tabellone(self)",
         "Crea il tabellone dopo le statistiche.", "Il tabellone legge le statistiche, quindi devono esistere già."),
        ("replace", "invasione.py", "        pygame.sprite.groupcollide(self.proiettili, self.alieni, True, True)",
         "        colpiti = pygame.sprite.groupcollide(self.proiettili, self.alieni, True, True)\n        for alieni in colpiti.values():\n            self.statistiche.punteggio += self.impostazioni.punti_alieno * len(alieni)",
         "Salva il risultato di groupcollide e aggiunge i punti per ogni alieno colpito.",
         "Ora il valore restituito da `groupcollide` serve: prima lo ignoravamo."),
        ("after", "invasione.py", "            alieno.disegna()", "        self.tabellone.disegna()",
         "Disegna il tabellone sopra tutto il resto.", "Ultimo a essere disegnato, quindi sempre visibile.")],
       "Aggiungi il record (punteggio più alto) e salvalo in un file così resta anche quando chiudi il gioco."),

    _t("Ricominciare e difficoltà crescente", "Partire con il tasto P e rendere ogni flotta più veloce della precedente.",
       ("Quando ricominci una partita, cosa devi rimettere a posto?",
        ["Statistiche, proiettili, alieni, posizione della navicella e velocità della flotta", "Solo il punteggio", "Niente: basta rilanciare il programma",
         "Solo le vite"], 0,
        "Tutto ciò che cambia durante la partita va riportato allo stato iniziale; le impostazioni fisse no."),
       [("after", "impostazioni.py", "        self.punti_alieno = 50", "        self.accelerazione = 1.1",
         "Ogni nuova flotta sarà il 10% più veloce.", "Moltiplicare per 1.1 a ogni ondata fa crescere la difficoltà in modo graduale."),
        ("replace", "invasione.py", "        self.attivo = True", "        self.attivo = False",
         "La partita parte ferma: si inizia premendo P.", "Il giocatore decide quando iniziare."),
        ("after", "invasione.py", "            self._spara()",
         "        elif evento.key == pygame.K_p and not self.attivo:\n            self._nuova_partita()",
         "Con P, solo a partita ferma, ne inizia una nuova.", "Il controllo `not self.attivo` evita di azzerare tutto per sbaglio durante il gioco."),
        ("after", "invasione.py", "            self.proiettili.add(nuovo)",
         '\n    def _nuova_partita(self):\n        """Azzera tutto e fa partire il gioco."""\n        self.impostazioni.velocita_alieni = 1.5\n        self.statistiche.azzera()\n        self.proiettili.empty()\n        self.alieni.empty()\n        self._crea_flotta()\n        self.navicella.al_centro()\n        self.attivo = True',
         "Riporta velocità, statistiche, proiettili, alieni e navicella all'inizio e attiva la partita.",
         "La velocità degli alieni va riportata al valore iniziale perché l'accelerazione la cambia durante la partita."),
        ("replace", "invasione.py",
         "        if not self.alieni:\n            self.proiettili.empty()\n            self._crea_flotta()",
         "        if not self.alieni:\n            self.proiettili.empty()\n            self._crea_flotta()\n            self.impostazioni.velocita_alieni *= self.impostazioni.accelerazione",
         "Quando distruggi una flotta, la prossima è più veloce.", "`*=` moltiplica e riassegna in un colpo solo."),
        ("after", "invasione.py", "        self.tabellone.disegna()",
         '        if not self.attivo:\n            self._scrivi_al_centro("Premi P per giocare")',
         "A partita ferma scrive il messaggio al centro.", "Il messaggio si disegna dopo tutto il resto, quindi sta sopra agli alieni."),
        ("after", "invasione.py", "        pygame.display.flip()",
         '\n    def _scrivi_al_centro(self, testo):\n        """Scrive un messaggio al centro dello schermo."""\n        font = pygame.font.SysFont(None, 56)\n        immagine = font.render(testo, True, (255, 255, 255))\n        rect = immagine.get_rect(center=self.schermo.get_rect().center)\n        self.schermo.blit(immagine, rect)',
         "Trasforma il testo in immagine e la centra sullo schermo.",
         "`get_rect(center=...)` crea il rettangolo già centrato: un modo compatto per posizionare.")],
       "Il gioco è finito: aggiungi una tua idea. Per esempio alieni che sparano, livelli con colori diversi o un suono quando colpisci."),
]

PROJECTS = {
    "invasione": {"title": "Invasione aliena", "lang": "python", "folder": "invasione-aliena", "main": "invasione.py", "requires": ["pygame"],
                  "desc": "Un gioco con pygame: una navicella che spara a una flotta di alieni. 15 tappe, dalle classi alle collisioni.",
                  "steps": INVASIONE},
}

# ---------------------------------------------------------------- API Spring Boot: prenotazioni di una palestra
_P = "src/main/java/com/palestra/prenotazioni/"
_T = "src/test/java/com/palestra/prenotazioni/"
_PKG = "package com.palestra.prenotazioni;\n\n"

_POM = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.5.0</version>
    <relativePath/>
  </parent>
  <groupId>com.palestra</groupId>
  <artifactId>prenotazioni</artifactId>
  <version>1.0</version>
  <properties>
    <java.version>17</java.version>
  </properties>
  <dependencies>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-test</artifactId>
      <scope>test</scope>
    </dependency>
  </dependencies>"""

_BUILD = """  <build>
    <plugins>
      <plugin>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-maven-plugin</artifactId>
      </plugin>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-surefire-plugin</artifactId>
        <configuration>
          <argLine>-Dnet.bytebuddy.experimental=true -XX:+EnableDynamicAgentLoading -Xshare:off</argLine>
        </configuration>
      </plugin>
    </plugins>
  </build>
</project>"""

_MVC_IMPORTS = """import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.transaction.annotation.Transactional;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
"""

PRENOTAZIONI = [
    _t("Il progetto Spring Boot", "Creare il progetto Maven, la classe che avvia Spring e un primo test che controlla che l'applicazione parta.",
       ("Che cosa fa l'annotazione @SpringBootApplication sulla classe principale?",
        ["Attiva la configurazione automatica e cerca i componenti (controller, service…) nel suo package e nei sotto-package",
         "Crea il database", "Scrive i test da sola", "Serve solo a dare un nome all'applicazione"], 0,
        "È la somma di @Configuration, @EnableAutoConfiguration e @ComponentScan: per questo tutte le classi del progetto devono stare nel suo package o sotto."),
       [("new", "pom.xml", _POM,
         "Il file di Maven: il parent di Spring Boot, le coordinate del progetto, Java 17 e le dipendenze web e di test.",
         "Il parent `spring-boot-starter-parent` decide le versioni compatibili di tutte le librerie: per questo le dipendenze non hanno il numero di versione."),
        ("end", "pom.xml", _BUILD,
         "I plugin: quello di Spring Boot per avviare l'API e quello dei test con un'opzione per le versioni recenti di Java.",
         "`spring-boot-maven-plugin` permette `mvn spring-boot:run`. L'argLine serve ai test sulle JDK 21 e successive."),
        ("new", _P + "PrenotazioniApplication.java",
         _PKG + "import org.springframework.boot.SpringApplication;\nimport org.springframework.boot.autoconfigure.SpringBootApplication;\n\n@SpringBootApplication\npublic class PrenotazioniApplication {\n\n    public static void main(String[] args) {\n        SpringApplication.run(PrenotazioniApplication.class, args);\n    }\n}",
         "La classe che avvia l'applicazione: il main passa il controllo a Spring.",
         "`SpringApplication.run` crea il contenitore di Spring, configura tutto e avvia il server web integrato (Tomcat) sulla porta 8080."),
        ("new", "src/main/resources/application.properties", "spring.application.name=prenotazioni\nspring.main.banner-mode=off",
         "Le impostazioni dell'applicazione: il nome e niente logo all'avvio.", "Qui finiranno porta, database e altre configurazioni, senza toccare il codice."),
        ("new", _T + "PrenotazioniApplicationTests.java",
         _PKG + "import org.junit.jupiter.api.Test;\nimport org.springframework.boot.test.context.SpringBootTest;\n\n@SpringBootTest\nclass PrenotazioniApplicationTests {\n\n    @Test\n    void ilContestoSiAvvia() {\n    }\n}",
         "Un test vuoto che avvia tutta l'applicazione: se la configurazione è sbagliata, fallisce.",
         "`@SpringBootTest` avvia Spring come in produzione. Un test che non fa niente ma passa dimostra già che il progetto si avvia.")],
       "Nel file application.properties aggiungi `server.port=8081` e avvia l'API: ora risponde sulla porta 8081."),

    _t("Il primo endpoint", "Rispondere a GET /api/ciao con un testo, e provarlo con MockMvc.",
       ("Che differenza c'è tra @Controller e @RestController?",
        ["@RestController restituisce direttamente i dati (testo, JSON), @Controller di solito il nome di una pagina", "Nessuna",
         "@RestController funziona solo con POST", "@Controller è più veloce"], 0,
        "@RestController = @Controller + @ResponseBody: quello che il metodo restituisce diventa il corpo della risposta HTTP."),
       [("new", _P + "SalutoController.java",
         _PKG + 'import org.springframework.web.bind.annotation.GetMapping;\nimport org.springframework.web.bind.annotation.RestController;\n\n@RestController\npublic class SalutoController {\n\n    @GetMapping("/api/ciao")\n    public String ciao() {\n        return "Palestra aperta";\n    }\n}',
         "Un controller con un solo endpoint: GET /api/ciao risponde «Palestra aperta».",
         "`@GetMapping` collega il metodo a una richiesta GET su quell'indirizzo. Spring trova la classe da solo grazie alla scansione dei componenti."),
        ("new", _T + "SalutoControllerTest.java",
         _PKG + 'import org.junit.jupiter.api.Test;\nimport org.springframework.beans.factory.annotation.Autowired;\nimport org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;\nimport org.springframework.test.web.servlet.MockMvc;\n\nimport static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;\nimport static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;\nimport static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;\n\n@WebMvcTest(SalutoController.class)\nclass SalutoControllerTest {\n\n    @Autowired\n    private MockMvc mvc;\n\n    @Test\n    void rispondeAlSaluto() throws Exception {\n        mvc.perform(get("/api/ciao"))\n                .andExpect(status().isOk())\n                .andExpect(content().string("Palestra aperta"));\n    }\n}',
         "Il test chiama GET /api/ciao senza avviare un server vero e controlla stato 200 e testo.",
         "`@WebMvcTest` carica solo la parte web: è più veloce di `@SpringBootTest`. MockMvc simula le richieste HTTP.")],
       "Aggiungi un endpoint GET /api/orari che restituisce «Lun-Ven 7-22» e il suo test."),

    _t("Il database e l'entità Corso", "Collegare un database H2 in memoria e descrivere la tabella dei corsi con una classe @Entity.",
       ("Perché l'entità Corso ha un costruttore senza argomenti protected?",
        ["Lo richiede JPA per creare gli oggetti quando li legge dal database", "Per errore", "Per renderla immutabile", "Lo richiede Maven"], 0,
        "Hibernate (l'implementazione di JPA) crea l'oggetto vuoto e poi riempie i campi. `protected` lo rende disponibile a JPA ma scoraggia l'uso dal tuo codice."),
       [("replace", "pom.xml",
         "      <artifactId>spring-boot-starter-web</artifactId>\n    </dependency>",
         "      <artifactId>spring-boot-starter-web</artifactId>\n    </dependency>\n    <dependency>\n      <groupId>org.springframework.boot</groupId>\n      <artifactId>spring-boot-starter-data-jpa</artifactId>\n    </dependency>\n    <dependency>\n      <groupId>org.springframework.boot</groupId>\n      <artifactId>spring-boot-starter-validation</artifactId>\n    </dependency>\n    <dependency>\n      <groupId>com.h2database</groupId>\n      <artifactId>h2</artifactId>\n      <scope>runtime</scope>\n    </dependency>",
         "Aggiunge JPA per il database, la validazione dei dati e H2, un database che vive in memoria.",
         "H2 ha scope `runtime`: serve quando il programma gira, non per compilare. Il tuo codice parla con JPA, non con H2: domani puoi passare a PostgreSQL cambiando solo la configurazione."),
        ("end", "src/main/resources/application.properties",
         "spring.datasource.url=jdbc:h2:mem:palestra\nspring.jpa.hibernate.ddl-auto=create-drop\nspring.jpa.open-in-view=false",
         "Il database in memoria e la creazione automatica delle tabelle dalle entità.",
         "`create-drop` crea le tabelle all'avvio e le cancella alla chiusura: comodo per imparare, non per la produzione."),
        ("new", _P + "Corso.java",
         _PKG + "import jakarta.persistence.Entity;\nimport jakarta.persistence.GeneratedValue;\nimport jakarta.persistence.Id;\n\n@Entity\npublic class Corso {\n\n    @Id\n    @GeneratedValue\n    private Long id;\n    private String nome;\n    private String istruttore;\n    private int postiMax;\n\n    protected Corso() {\n    }\n\n    public Corso(String nome, String istruttore, int postiMax) {\n        this.nome = nome;\n        this.istruttore = istruttore;\n        this.postiMax = postiMax;\n    }",
         "L'entità Corso: una riga della tabella con id generato, nome, istruttore e posti massimi.",
         "`@Id` indica la chiave primaria, `@GeneratedValue` la fa generare al database. L'id è `Long` (oggetto) così può essere null prima del salvataggio."),
        ("end", _P + "Corso.java",
         "\n    public Long getId() {\n        return id;\n    }\n\n    public String getNome() {\n        return nome;\n    }\n\n    public String getIstruttore() {\n        return istruttore;\n    }\n\n    public int getPostiMax() {\n        return postiMax;\n    }\n}",
         "I getter dei campi, e la parentesi che chiude la classe.",
         "Niente setter: i dati si danno nel costruttore. Meno modi di cambiare un oggetto vuol dire meno errori. Jackson userà i getter per scrivere il JSON.")],
       "Aggiungi a Corso un campo `livello` (per esempio «base», «avanzato») con il suo getter e un parametro nel costruttore."),

    _t("Il repository", "Salvare e leggere i corsi con un repository Spring Data, e provarlo con un test sul database.",
       ("Il repository CorsoRepository è un'interfaccia senza codice. Chi scrive i metodi save e findById?",
        ["Spring Data li genera all'avvio estendendo JpaRepository", "Li devo scrivere io dopo", "Il database", "Maven"], 0,
        "Spring Data crea a runtime una classe che implementa l'interfaccia: save, findById, findAll, delete… sono già pronti."),
       [("new", _P + "CorsoRepository.java",
         _PKG + "import org.springframework.data.jpa.repository.JpaRepository;\n\npublic interface CorsoRepository extends JpaRepository<Corso, Long> {\n}",
         "Il repository dei corsi: un'interfaccia che estende JpaRepository con il tipo dell'entità e dell'id.",
         "I due tipi tra < > dicono a Spring Data quale entità gestire (Corso) e di che tipo è la sua chiave (Long)."),
        ("new", _T + "CorsoRepositoryTest.java",
         _PKG + "import org.junit.jupiter.api.Test;\nimport org.springframework.beans.factory.annotation.Autowired;\nimport org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;\n\nimport static org.assertj.core.api.Assertions.assertThat;\n\n@DataJpaTest\nclass CorsoRepositoryTest {\n\n    @Autowired\n    private CorsoRepository repository;\n\n    @Test\n    void salvaERitrovaUnCorso() {\n        Corso salvato = repository.save(new Corso(\"Yoga\", \"Ada\", 10));\n        assertThat(salvato.getId()).isNotNull();\n        assertThat(repository.findById(salvato.getId())).isPresent();\n    }\n}",
         "Il test salva un corso, controlla che abbia ricevuto un id e che si possa ritrovare.",
         "`@DataJpaTest` avvia solo la parte del database e annulla le modifiche alla fine di ogni test: i test non si sporcano a vicenda.")],
       "Aggiungi al repository il metodo `List<Corso> findByIstruttore(String istruttore);` e scrivi un test che lo usa: Spring Data capisce la query dal nome."),

    _t("Il service", "Mettere la logica in un service che usa il repository, con l'iniezione nel costruttore.",
       ("Perché non chiamare il repository direttamente dal controller?",
        ["Il service raccoglie le regole del dominio: il controller resta sottile e la logica si testa e si riusa", "Perché è vietato da Spring",
         "Per rendere il codice più lungo", "Perché il repository funziona solo nei service"], 0,
        "Controller → service → repository: il controller parla HTTP, il service decide, il repository salva. È la versione «backend» dell'MVC che conosci."),
       [("new", _P + "CorsoService.java",
         _PKG + "import java.util.List;\n\nimport org.springframework.stereotype.Service;\n\n@Service\npublic class CorsoService {\n\n    private final CorsoRepository repository;\n\n    public CorsoService(CorsoRepository repository) {\n        this.repository = repository;\n    }\n\n    public List<Corso> elenco() {\n        return repository.findAll();\n    }\n\n    public Corso crea(String nome, String istruttore, int postiMax) {\n        return repository.save(new Corso(nome, istruttore, postiMax));\n    }\n}",
         "Il service dei corsi: riceve il repository nel costruttore e offre elenco e creazione.",
         "Iniezione nel costruttore: il campo è `final`, la dipendenza è obbligatoria ed è facile passare un finto repository nei test. Con un solo costruttore non serve nemmeno @Autowired."),
        ("new", _T + "CorsoServiceTest.java",
         _PKG + "import org.junit.jupiter.api.Test;\nimport org.springframework.beans.factory.annotation.Autowired;\nimport org.springframework.boot.test.context.SpringBootTest;\nimport org.springframework.transaction.annotation.Transactional;\n\nimport static org.assertj.core.api.Assertions.assertThat;\n\n@SpringBootTest\n@Transactional\nclass CorsoServiceTest {\n\n    @Autowired\n    private CorsoService service;\n\n    @Test\n    void creaEdElencaICorsi() {\n        service.crea(\"Pilates\", \"Luca\", 8);\n        assertThat(service.elenco()).extracting(Corso::getNome).contains(\"Pilates\");\n    }\n}",
         "Il test crea un corso con il service e controlla che compaia nell'elenco.",
         "`@Transactional` sul test annulla tutto alla fine. `extracting(Corso::getNome)` trasforma la lista di corsi nella lista dei loro nomi.")],
       "Aggiungi al service un metodo che restituisce solo i corsi con almeno N posti, usando uno stream con filter."),

    _t("L'API REST dei corsi", "Esporre GET /api/corsi e POST /api/corsi, ricevendo i dati in un DTO.",
       ("Per creare un corso il client manda un JSON. Perché riceverlo in un record NuovoCorso invece che direttamente nell'entità?",
        ["Il DTO contiene solo i campi che il client può mandare: niente id deciso dal client e l'entità resta interna", "Perché le entità non si possono convertire in JSON",
         "Perché i record sono più veloci", "Per errore"], 0,
        "Il DTO (Data Transfer Object) è il «contratto» con l'esterno: se l'entità cambia, l'API non cambia per forza, e il client non può impostare campi che non deve."),
       [("new", _P + "NuovoCorso.java",
         _PKG + "public record NuovoCorso(String nome, String istruttore, int postiMax) {\n}",
         "Un record con i dati che il client manda per creare un corso.",
         "Un record genera da solo costruttore, getter (`nome()`, `istruttore()`…), equals e toString. Jackson sa leggerlo dal JSON."),
        ("new", _P + "CorsoController.java",
         _PKG + "import java.util.List;\n\nimport org.springframework.http.HttpStatus;\nimport org.springframework.web.bind.annotation.GetMapping;\nimport org.springframework.web.bind.annotation.PostMapping;\nimport org.springframework.web.bind.annotation.RequestBody;\nimport org.springframework.web.bind.annotation.RequestMapping;\nimport org.springframework.web.bind.annotation.ResponseStatus;\nimport org.springframework.web.bind.annotation.RestController;\n\n@RestController\n@RequestMapping(\"/api/corsi\")\npublic class CorsoController {\n\n    private final CorsoService service;\n\n    public CorsoController(CorsoService service) {\n        this.service = service;\n    }\n\n    @GetMapping\n    public List<Corso> elenco() {\n        return service.elenco();\n    }\n\n    @PostMapping\n    @ResponseStatus(HttpStatus.CREATED)\n    public Corso crea(@RequestBody NuovoCorso richiesta) {\n        return service.crea(richiesta.nome(), richiesta.istruttore(), richiesta.postiMax());\n    }\n}",
         "Il controller dei corsi: GET restituisce la lista, POST crea un corso dal JSON e risponde 201 Created.",
         "`@RequestMapping` sulla classe mette il prefisso comune. `@RequestBody` converte il JSON nel record. 201 è il codice giusto per «risorsa creata»."),
        ("new", _T + "CorsoControllerTest.java",
         _PKG + _MVC_IMPORTS + "\n@SpringBootTest\n@AutoConfigureMockMvc\n@Transactional\nclass CorsoControllerTest {\n\n    @Autowired\n    private MockMvc mvc;\n\n    @Test\n    void creaUnCorso() throws Exception {\n        mvc.perform(post(\"/api/corsi\")\n                        .contentType(MediaType.APPLICATION_JSON)\n                        .content(\"\"\"\n                                {\"nome\": \"Yoga\", \"istruttore\": \"Ada\", \"postiMax\": 10}\n                                \"\"\"))\n                .andExpect(status().isCreated())\n                .andExpect(jsonPath(\"$.id\").exists())\n                .andExpect(jsonPath(\"$.nome\").value(\"Yoga\"));\n    }\n\n    @Test\n    void elencaICorsi() throws Exception {\n        mvc.perform(get(\"/api/corsi\"))\n                .andExpect(status().isOk());\n    }\n}",
         "Due test: la creazione risponde 201 con id e nome nel JSON; l'elenco risponde 200.",
         "Il JSON è in un text block (`\"\"\"`): niente virgolette da escape. `jsonPath(\"$.nome\")` legge un campo del JSON di risposta.")],
       "Aggiungi DELETE /api/corsi/{id} (con `deleteById` nel service) e un test che controlla la risposta 204 No Content."),

    _t("Un corso per id e l'errore 404", "Leggere un corso con GET /api/corsi/{id} e rispondere 404 se non esiste.",
       ("Se il corso non esiste, cosa deve fare il service?",
        ["Lanciare un'eccezione precisa che diventa una risposta 404", "Restituire null", "Restituire un corso vuoto", "Stampare un messaggio"], 0,
        "Con null il problema si sposta più avanti (NullPointerException). Un'eccezione con un nome chiaro dice cosa è successo e si traduce nel codice HTTP giusto."),
       [("new", _P + "CorsoNonTrovatoException.java",
         _PKG + "import org.springframework.http.HttpStatus;\nimport org.springframework.web.bind.annotation.ResponseStatus;\n\n@ResponseStatus(HttpStatus.NOT_FOUND)\npublic class CorsoNonTrovatoException extends RuntimeException {\n\n    public CorsoNonTrovatoException(Long id) {\n        super(\"Corso \" + id + \" non trovato\");\n    }\n}",
         "Un'eccezione per il corso inesistente, che Spring trasforma in 404.",
         "Estende RuntimeException (unchecked): non obbliga a scrivere throws ovunque. `@ResponseStatus` dice a Spring quale codice HTTP usare."),
        ("replace", _P + "CorsoService.java",
         "        return repository.save(new Corso(nome, istruttore, postiMax));\n    }",
         "        return repository.save(new Corso(nome, istruttore, postiMax));\n    }\n\n    public Corso trova(Long id) {\n        return repository.findById(id).orElseThrow(() -> new CorsoNonTrovatoException(id));\n    }",
         "Il service cerca il corso e, se manca, lancia l'eccezione.",
         "`findById` restituisce un Optional; `orElseThrow` estrae il valore o lancia l'eccezione creata dalla lambda."),
        ("after", _P + "CorsoController.java", "import org.springframework.web.bind.annotation.GetMapping;",
         "import org.springframework.web.bind.annotation.PathVariable;", "Importa @PathVariable.", "Serve per leggere l'id dall'indirizzo."),
        ("replace", _P + "CorsoController.java",
         "        return service.elenco();\n    }",
         "        return service.elenco();\n    }\n\n    @GetMapping(\"/{id}\")\n    public Corso dettaglio(@PathVariable Long id) {\n        return service.trova(id);\n    }",
         "GET /api/corsi/{id}: prende l'id dall'indirizzo e restituisce il corso.",
         "`{id}` nel percorso diventa il parametro `id` grazie a @PathVariable. Il controller non controlla niente: se il corso manca ci pensa l'eccezione."),
        ("replace", _T + "CorsoControllerTest.java",
         "        mvc.perform(get(\"/api/corsi\"))\n                .andExpect(status().isOk());\n    }",
         "        mvc.perform(get(\"/api/corsi\"))\n                .andExpect(status().isOk());\n    }\n\n    @Test\n    void corsoInesistenteDa404() throws Exception {\n        mvc.perform(get(\"/api/corsi/999\"))\n                .andExpect(status().isNotFound());\n    }",
         "Un test che chiede un corso inesistente e si aspetta 404.",
         "Testare il caso d'errore è importante quanto il caso felice: ai colloqui ti chiederanno proprio questi.")],
       "Scrivi un test che crea un corso con POST, ne legge l'id dalla risposta e poi lo richiede con GET /api/corsi/{id}."),

    _t("Validare i dati", "Rifiutare con 400 un corso senza nome o con zero posti.",
       ("Dove conviene controllare che il nome non sia vuoto?",
        ["Sul DTO con annotazioni come @NotBlank, attivate da @Valid nel controller", "Con un if in ogni metodo del service", "Nel database", "Non serve controllare"], 0,
        "Le annotazioni di Bean Validation dichiarano le regole una volta sola, vicino ai dati. Con @Valid Spring le controlla e risponde 400 da solo."),
       [("replace", _P + "NuovoCorso.java",
         "public record NuovoCorso(String nome, String istruttore, int postiMax) {",
         "import jakarta.validation.constraints.Min;\nimport jakarta.validation.constraints.NotBlank;\n\npublic record NuovoCorso(@NotBlank String nome, @NotBlank String istruttore, @Min(1) int postiMax) {",
         "Nome e istruttore non possono essere vuoti, i posti devono essere almeno 1.",
         "`@NotBlank` rifiuta null, stringa vuota e solo spazi. `@Min(1)` rifiuta zero e negativi."),
        ("after", _P + "CorsoController.java", "import java.util.List;", "\nimport jakarta.validation.Valid;",
         "Importa @Valid.", "Le annotazioni di validazione vengono dal package jakarta.validation."),
        ("replace", _P + "CorsoController.java", "    public Corso crea(@RequestBody NuovoCorso richiesta) {",
         "    public Corso crea(@Valid @RequestBody NuovoCorso richiesta) {",
         "@Valid fa controllare il DTO prima di entrare nel metodo.", "Senza @Valid le annotazioni sul record verrebbero ignorate."),
        ("replace", _T + "CorsoControllerTest.java",
         "        mvc.perform(get(\"/api/corsi/999\"))\n                .andExpect(status().isNotFound());\n    }",
         "        mvc.perform(get(\"/api/corsi/999\"))\n                .andExpect(status().isNotFound());\n    }\n\n    @Test\n    void corsoSenzaNomeDa400() throws Exception {\n        mvc.perform(post(\"/api/corsi\")\n                        .contentType(MediaType.APPLICATION_JSON)\n                        .content(\"\"\"\n                                {\"nome\": \"\", \"istruttore\": \"Ada\", \"postiMax\": 10}\n                                \"\"\"))\n                .andExpect(status().isBadRequest());\n    }",
         "Un test che manda un corso con il nome vuoto e si aspetta 400 Bad Request.",
         "400 vuol dire «la richiesta è sbagliata»: è colpa del client, non del server.")],
       "Aggiungi la regola che il nome abbia al massimo 40 caratteri (`@Size(max = 40)`) e un test che la verifica."),

    _t("Le prenotazioni", "Creare l'entità Prenotazione collegata a un corso e un repository con query derivate dal nome.",
       ("Molte prenotazioni appartengono a un corso. Come lo dici a JPA?",
        ["@ManyToOne sul campo corso della Prenotazione", "@OneToOne", "Salvando il nome del corso come testo", "Con una lista di stringhe"], 0,
        "@ManyToOne crea nella tabella delle prenotazioni una chiave esterna verso i corsi: tante prenotazioni, un corso."),
       [("new", _P + "Prenotazione.java",
         _PKG + "import java.time.LocalDate;\n\nimport jakarta.persistence.Entity;\nimport jakarta.persistence.GeneratedValue;\nimport jakarta.persistence.Id;\nimport jakarta.persistence.ManyToOne;\n\n@Entity\npublic class Prenotazione {\n\n    @Id\n    @GeneratedValue\n    private Long id;\n\n    @ManyToOne(optional = false)\n    private Corso corso;\n\n    private String cliente;\n    private LocalDate giorno;\n\n    protected Prenotazione() {\n    }\n\n    public Prenotazione(Corso corso, String cliente, LocalDate giorno) {\n        this.corso = corso;\n        this.cliente = cliente;\n        this.giorno = giorno;\n    }",
         "L'entità Prenotazione: un corso, il nome del cliente e il giorno.",
         "`optional = false`: una prenotazione senza corso non ha senso, quindi la colonna non può essere vuota. LocalDate rappresenta un giorno senza ora."),
        ("end", _P + "Prenotazione.java",
         "\n    public Long getId() {\n        return id;\n    }\n\n    public String getCliente() {\n        return cliente;\n    }\n\n    public LocalDate getGiorno() {\n        return giorno;\n    }\n\n    public String getCorso() {\n        return corso.getNome();\n    }\n}",
         "I getter; per il corso restituisce solo il nome.",
         "Restituire l'intero corso nel JSON porterebbe dati inutili. `getCorso()` che dà il nome tiene la risposta semplice."),
        ("new", _P + "PrenotazioneRepository.java",
         _PKG + "import java.time.LocalDate;\nimport java.util.List;\n\nimport org.springframework.data.jpa.repository.JpaRepository;\n\npublic interface PrenotazioneRepository extends JpaRepository<Prenotazione, Long> {\n\n    long countByCorsoIdAndGiorno(Long corsoId, LocalDate giorno);\n\n    List<Prenotazione> findByCorsoIdOrderByGiornoAsc(Long corsoId);\n}",
         "Il repository delle prenotazioni con due query: contare le prenotazioni di un corso in un giorno, e l'elenco di un corso ordinato per giorno.",
         "Spring Data legge il nome del metodo: count + By + CorsoId (il campo id del corso) + And + Giorno. Non scrivi SQL."),
        ("new", _T + "PrenotazioneRepositoryTest.java",
         _PKG + "import java.time.LocalDate;\n\nimport org.junit.jupiter.api.Test;\nimport org.springframework.beans.factory.annotation.Autowired;\nimport org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;\n\nimport static org.assertj.core.api.Assertions.assertThat;\n\n@DataJpaTest\nclass PrenotazioneRepositoryTest {\n\n    @Autowired\n    private CorsoRepository corsi;\n\n    @Autowired\n    private PrenotazioneRepository prenotazioni;\n\n    @Test\n    void contaLePrenotazioniDiUnGiorno() {\n        Corso yoga = corsi.save(new Corso(\"Yoga\", \"Ada\", 10));\n        LocalDate lunedi = LocalDate.of(2030, 1, 7);\n        prenotazioni.save(new Prenotazione(yoga, \"Luca\", lunedi));\n        prenotazioni.save(new Prenotazione(yoga, \"Sara\", lunedi));\n        prenotazioni.save(new Prenotazione(yoga, \"Marco\", lunedi.plusDays(1)));\n        assertThat(prenotazioni.countByCorsoIdAndGiorno(yoga.getId(), lunedi)).isEqualTo(2);\n    }\n}",
         "Il test salva tre prenotazioni, due lo stesso giorno, e controlla che il conteggio di quel giorno sia 2.",
         "Il caso con un giorno diverso serve a dimostrare che il filtro sul giorno funziona davvero.")],
       "Aggiungi al repository un metodo che conta tutte le prenotazioni di un cliente e testalo."),

    _t("Prenotare con il limite di posti", "POST /api/corsi/{id}/prenotazioni: prenota un posto e rispondi 409 se il corso è pieno quel giorno.",
       ("Dove va la regola «non più prenotazioni dei posti disponibili»?",
        ["Nel service, dentro una transazione", "Nel controller", "Nel test", "Nel JSON della richiesta"], 0,
        "È una regola del dominio: sta nel service. La transazione fa sì che conteggio e salvataggio avvengano come un'unica operazione."),
       [("new", _P + "PostiEsauritiException.java",
         _PKG + "import java.time.LocalDate;\n\nimport org.springframework.http.HttpStatus;\nimport org.springframework.web.bind.annotation.ResponseStatus;\n\n@ResponseStatus(HttpStatus.CONFLICT)\npublic class PostiEsauritiException extends RuntimeException {\n\n    public PostiEsauritiException(String corso, LocalDate giorno) {\n        super(\"Posti esauriti per \" + corso + \" il \" + giorno);\n    }\n}",
         "L'eccezione per il corso pieno, tradotta in 409 Conflict.",
         "409 vuol dire che la richiesta è corretta ma va in conflitto con lo stato attuale: il corso è pieno."),
        ("new", _P + "NuovaPrenotazione.java",
         _PKG + "import java.time.LocalDate;\n\nimport jakarta.validation.constraints.FutureOrPresent;\nimport jakarta.validation.constraints.NotBlank;\nimport jakarta.validation.constraints.NotNull;\n\npublic record NuovaPrenotazione(@NotBlank String cliente, @NotNull @FutureOrPresent LocalDate giorno) {\n}",
         "Il DTO della prenotazione: cliente obbligatorio e giorno non nel passato.",
         "Il JSON manda la data come testo «2030-01-07»: Spring Boot la converte in LocalDate da solo."),
        ("new", _P + "PrenotazioneService.java",
         _PKG + "import java.time.LocalDate;\n\nimport org.springframework.stereotype.Service;\nimport org.springframework.transaction.annotation.Transactional;\n\n@Service\npublic class PrenotazioneService {\n\n    private final PrenotazioneRepository prenotazioni;\n    private final CorsoService corsi;\n\n    public PrenotazioneService(PrenotazioneRepository prenotazioni, CorsoService corsi) {\n        this.prenotazioni = prenotazioni;\n        this.corsi = corsi;\n    }\n\n    @Transactional\n    public Prenotazione prenota(Long corsoId, String cliente, LocalDate giorno) {\n        Corso corso = corsi.trova(corsoId);\n        long occupati = prenotazioni.countByCorsoIdAndGiorno(corsoId, giorno);\n        if (occupati >= corso.getPostiMax()) {\n            throw new PostiEsauritiException(corso.getNome(), giorno);\n        }\n        return prenotazioni.save(new Prenotazione(corso, cliente, giorno));\n    }\n}",
         "Il service: trova il corso (404 se manca), conta i posti occupati quel giorno, lancia l'eccezione se è pieno, altrimenti salva.",
         "Riusa `corsi.trova`: niente codice duplicato. `@Transactional` tiene insieme lettura e scrittura; se qualcosa fallisce, non resta nulla a metà."),
        ("new", _P + "PrenotazioneController.java",
         _PKG + "import jakarta.validation.Valid;\n\nimport org.springframework.http.HttpStatus;\nimport org.springframework.web.bind.annotation.PathVariable;\nimport org.springframework.web.bind.annotation.PostMapping;\nimport org.springframework.web.bind.annotation.RequestBody;\nimport org.springframework.web.bind.annotation.RequestMapping;\nimport org.springframework.web.bind.annotation.ResponseStatus;\nimport org.springframework.web.bind.annotation.RestController;\n\n@RestController\n@RequestMapping(\"/api/corsi/{corsoId}/prenotazioni\")\npublic class PrenotazioneController {\n\n    private final PrenotazioneService service;\n\n    public PrenotazioneController(PrenotazioneService service) {\n        this.service = service;\n    }\n\n    @PostMapping\n    @ResponseStatus(HttpStatus.CREATED)\n    public Prenotazione prenota(@PathVariable Long corsoId, @Valid @RequestBody NuovaPrenotazione richiesta) {\n        return service.prenota(corsoId, richiesta.cliente(), richiesta.giorno());\n    }\n}",
         "Il controller delle prenotazioni, annidato sotto il corso: POST crea una prenotazione.",
         "L'indirizzo /api/corsi/{corsoId}/prenotazioni dice che la prenotazione appartiene a quel corso: è lo stile REST delle risorse annidate."),
        ("new", _T + "PrenotazioneControllerTest.java",
         _PKG + _MVC_IMPORTS + "\n@SpringBootTest\n@AutoConfigureMockMvc\n@Transactional\nclass PrenotazioneControllerTest {\n\n    @Autowired\n    private MockMvc mvc;\n\n    @Autowired\n    private CorsoService corsi;\n\n    private String prenotazione(String cliente) {\n        return \"\"\"\n                {\"cliente\": \"%s\", \"giorno\": \"2030-01-07\"}\n                \"\"\".formatted(cliente);\n    }\n\n    @Test\n    void prenotaUnPosto() throws Exception {\n        Corso corso = corsi.crea(\"Spinning\", \"Gio\", 2);\n        mvc.perform(post(\"/api/corsi/\" + corso.getId() + \"/prenotazioni\")\n                        .contentType(MediaType.APPLICATION_JSON)\n                        .content(prenotazione(\"Ada\")))\n                .andExpect(status().isCreated())\n                .andExpect(jsonPath(\"$.cliente\").value(\"Ada\"));\n    }\n\n    @Test\n    void oltreIPostiDa409() throws Exception {\n        Corso corso = corsi.crea(\"Spinning\", \"Gio\", 1);\n        String url = \"/api/corsi/\" + corso.getId() + \"/prenotazioni\";\n        mvc.perform(post(url).contentType(MediaType.APPLICATION_JSON).content(prenotazione(\"Ada\")))\n                .andExpect(status().isCreated());\n        mvc.perform(post(url).contentType(MediaType.APPLICATION_JSON).content(prenotazione(\"Luca\")))\n                .andExpect(status().isConflict());\n    }\n}",
         "Due test: una prenotazione va a buon fine (201); con un solo posto, la seconda risponde 409.",
         "Il metodo `prenotazione()` evita di ripetere il JSON. Il secondo test prepara la situazione limite (un posto) e verifica la regola.")],
       "Impedisci che lo stesso cliente prenoti due volte lo stesso corso nello stesso giorno (una query `existsBy…` nel repository e una nuova eccezione)."),

    _t("Errori in JSON", "Rispondere agli errori con un JSON chiaro {\"errore\": \"…\"} grazie a un @RestControllerAdvice.",
       ("Come dai a tutti gli errori della API la stessa forma senza ripetere codice in ogni controller?",
        ["Un @RestControllerAdvice con un @ExceptionHandler per ogni tipo di errore", "Un try/catch in ogni metodo", "Restituendo sempre 200", "Con un filtro nel database"], 0,
        "Il controller advice intercetta le eccezioni di tutti i controller: un solo posto per decidere codice HTTP e corpo della risposta."),
       [("new", _P + "GestoreErrori.java",
         _PKG + "import java.util.Map;\n\nimport org.springframework.http.HttpStatus;\nimport org.springframework.web.bind.MethodArgumentNotValidException;\nimport org.springframework.web.bind.annotation.ExceptionHandler;\nimport org.springframework.web.bind.annotation.ResponseStatus;\nimport org.springframework.web.bind.annotation.RestControllerAdvice;\n\n@RestControllerAdvice\npublic class GestoreErrori {\n\n    @ExceptionHandler(CorsoNonTrovatoException.class)\n    @ResponseStatus(HttpStatus.NOT_FOUND)\n    public Map<String, String> nonTrovato(CorsoNonTrovatoException e) {\n        return Map.of(\"errore\", e.getMessage());\n    }\n\n    @ExceptionHandler(PostiEsauritiException.class)\n    @ResponseStatus(HttpStatus.CONFLICT)\n    public Map<String, String> postiEsauriti(PostiEsauritiException e) {\n        return Map.of(\"errore\", e.getMessage());\n    }\n\n    @ExceptionHandler(MethodArgumentNotValidException.class)\n    @ResponseStatus(HttpStatus.BAD_REQUEST)\n    public Map<String, String> datiNonValidi(MethodArgumentNotValidException e) {\n        String campo = e.getBindingResult().getFieldErrors().get(0).getField();\n        return Map.of(\"errore\", \"Dato non valido: \" + campo);\n    }\n}",
         "Un gestore degli errori per tutta l'API: 404, 409 e 400 rispondono con un JSON che spiega cosa è andato storto.",
         "Ogni @ExceptionHandler dice quale eccezione gestisce e restituisce il corpo della risposta. `MethodArgumentNotValidException` è quella lanciata da @Valid."),
        ("replace", _T + "PrenotazioneControllerTest.java",
         "                .andExpect(status().isConflict());",
         "                .andExpect(status().isConflict())\n                .andExpect(jsonPath(\"$.errore\").exists());",
         "Il test del corso pieno ora controlla anche che la risposta contenga il campo errore.",
         "Un client (un'app, un sito) può mostrare il messaggio all'utente invece di un errore generico."),
        ("replace", _T + "CorsoControllerTest.java",
         "                .andExpect(status().isBadRequest());",
         "                .andExpect(status().isBadRequest())\n                .andExpect(jsonPath(\"$.errore\").value(\"Dato non valido: nome\"));",
         "Il test della validazione controlla il messaggio con il nome del campo sbagliato.",
         "Ora l'errore dice esattamente quale campo correggere.")],
       "Aggiungi un gestore generico per Exception che risponde 500 con «Errore interno», senza mostrare dettagli tecnici al client."),

    _t("Le prenotazioni di un corso", "GET /api/corsi/{id}/prenotazioni: l'elenco ordinato per giorno. L'API è completa.",
       ("Se chiedi le prenotazioni di un corso che non esiste, cosa deve rispondere l'API?",
        ["404, come per il corso: prima si controlla che il corso esista", "Una lista vuota", "500", "200 con null"], 0,
        "Una lista vuota direbbe «il corso esiste ma è senza prenotazioni»: sarebbe un'informazione falsa. Riusare `trova` dà il 404 corretto."),
       [("after", _P + "PrenotazioneService.java", "import java.time.LocalDate;", "import java.util.List;",
         "Importa List.", "Serve per il tipo restituito dal nuovo metodo."),
        ("replace", _P + "PrenotazioneService.java",
         "        return prenotazioni.save(new Prenotazione(corso, cliente, giorno));\n    }",
         "        return prenotazioni.save(new Prenotazione(corso, cliente, giorno));\n    }\n\n    public List<Prenotazione> diCorso(Long corsoId) {\n        corsi.trova(corsoId);\n        return prenotazioni.findByCorsoIdOrderByGiornoAsc(corsoId);\n    }",
         "Il service controlla che il corso esista, poi restituisce le sue prenotazioni in ordine di giorno.",
         "`corsi.trova(corsoId)` non usa il risultato: serve solo a lanciare il 404 se il corso manca."),
        ("after", _P + "PrenotazioneController.java", "import jakarta.validation.Valid;", "\nimport java.util.List;",
         "Importa List.", "Gli import di java.* e jakarta.* stanno di solito in gruppi separati."),
        ("after", _P + "PrenotazioneController.java", "import org.springframework.http.HttpStatus;",
         "import org.springframework.web.bind.annotation.GetMapping;", "Importa @GetMapping.", "Serve per il nuovo endpoint."),
        ("replace", _P + "PrenotazioneController.java",
         "        return service.prenota(corsoId, richiesta.cliente(), richiesta.giorno());\n    }",
         "        return service.prenota(corsoId, richiesta.cliente(), richiesta.giorno());\n    }\n\n    @GetMapping\n    public List<Prenotazione> elenco(@PathVariable Long corsoId) {\n        return service.diCorso(corsoId);\n    }",
         "GET sullo stesso indirizzo: l'elenco delle prenotazioni del corso.",
         "Stesso percorso, metodo HTTP diverso: POST crea, GET legge. È il cuore dello stile REST."),
        ("replace", _T + "PrenotazioneControllerTest.java",
         "                .andExpect(jsonPath(\"$.errore\").exists());\n    }",
         "                .andExpect(jsonPath(\"$.errore\").exists());\n    }\n\n    @Test\n    void elencaLePrenotazioniDelCorso() throws Exception {\n        Corso corso = corsi.crea(\"Yoga\", \"Ada\", 5);\n        String url = \"/api/corsi/\" + corso.getId() + \"/prenotazioni\";\n        mvc.perform(post(url).contentType(MediaType.APPLICATION_JSON).content(prenotazione(\"Luca\")))\n                .andExpect(status().isCreated());\n        mvc.perform(get(url))\n                .andExpect(status().isOk())\n                .andExpect(jsonPath(\"$.length()\").value(1))\n                .andExpect(jsonPath(\"$[0].cliente\").value(\"Luca\"));\n    }",
         "Un test che prenota e poi legge l'elenco: un elemento, con il cliente giusto.",
         "`$.length()` e `$[0].cliente` sono espressioni JsonPath per lunghezza e primo elemento di un array.")],
       "Il progetto è completo: scrivi un README.md che spiega come avviarlo e quali endpoint ha, poi mettilo su GitHub. È il primo progetto del tuo portfolio."),
]

PROJECTS["prenotazioni"] = {
    "title": "API prenotazioni palestra", "lang": "java", "kind": "maven", "folder": "prenotazioni-api", "main": "pom.xml", "requires": [],
    "desc": "Un'API REST con Spring Boot: corsi, prenotazioni, regole di business, validazione, errori in JSON e test. 12 tappe, dal pom.xml ai test MockMvc.",
    "url": "http://localhost:8080/api/corsi", "steps": PRENOTAZIONI}


# ================================================================ Palestra web (Spring MVC + Thymeleaf)
_WP = "src/main/java/com/palestra/web/"
_WT = "src/test/java/com/palestra/web/"
_WR = "src/main/resources/templates/"
_WPKG = "package com.palestra.web;\n\n"

_WPOM = (_POM.replace("<artifactId>prenotazioni</artifactId>", "<artifactId>palestra-web</artifactId>")
         .replace("      <artifactId>spring-boot-starter-web</artifactId>\n    </dependency>",
                  "      <artifactId>spring-boot-starter-web</artifactId>\n    </dependency>\n    <dependency>\n      <groupId>org.springframework.boot</groupId>\n      <artifactId>spring-boot-starter-thymeleaf</artifactId>\n    </dependency>"))

_WEB_TEST_IMPORTS = """import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.web.servlet.MockMvc;

import static org.hamcrest.Matchers.containsString;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.model;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.view;
"""

_WEB_POST_IMPORTS = """import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.transaction.annotation.Transactional;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.flash;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.model;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.redirectedUrl;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.view;
"""


def _page(title, body):
    """Una pagina Thymeleaf completa, con l'head «a mano» (il layout comune arriva alla tappa 8)."""
    return ('<!DOCTYPE html>\n<html xmlns:th="http://www.thymeleaf.org">\n<head>\n  <meta charset="UTF-8">\n'
            f"  <title>{title}</title>\n</head>\n<body>\n{body}\n</body>\n</html>")


def _head(title):
    return f'<head>\n  <meta charset="UTF-8">\n  <title>{title}</title>\n</head>\n<body>'


def _layout(title):
    return f"<head th:replace=\"~{{fragments :: head('{title}')}}\"></head>\n<body>\n  <nav th:replace=\"~{{fragments :: menu}}\"></nav>"


_CTRL_IMPORTS_1 = """import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;"""

_CTRL_IMPORTS_2 = """import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;"""

_CTRL_IMPORTS_3 = """import jakarta.validation.Valid;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.validation.BindingResult;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.servlet.mvc.support.RedirectAttributes;"""

PALESTRA_WEB = [
    _t("Il progetto web", "Creare il progetto Maven con Spring Web e Thymeleaf, la classe che avvia Spring e il primo test.",
       ("In un'app MVC con Thymeleaf, chi produce l'HTML che arriva al browser?",
        ["Il server: Thymeleaf riempie un template HTML con i dati del model", "Il browser, con JavaScript", "Il database", "Maven, quando compila"], 0,
        "È il rendering lato server: il controller prepara i dati, Thymeleaf li mette nel template e al browser arriva una pagina HTML già completa."),
       [("new", "pom.xml", _WPOM,
         "Il file di Maven: parent di Spring Boot, Java 17, Spring Web, Thymeleaf e le librerie di test.",
         "`spring-boot-starter-thymeleaf` porta il motore dei template e lo configura da solo: i template si cercano in `src/main/resources/templates`."),
        ("end", "pom.xml", _BUILD,
         "I plugin: quello di Spring Boot per avviare l'app e quello dei test.",
         "`spring-boot-maven-plugin` permette `mvn spring-boot:run`. L'argLine serve ai test sulle JDK 21 e successive."),
        ("new", _WP + "PalestraWebApplication.java",
         _WPKG + "import org.springframework.boot.SpringApplication;\nimport org.springframework.boot.autoconfigure.SpringBootApplication;\n\n@SpringBootApplication\npublic class PalestraWebApplication {\n\n    public static void main(String[] args) {\n        SpringApplication.run(PalestraWebApplication.class, args);\n    }\n}",
         "La classe che avvia l'applicazione web.",
         "Tutte le altre classi stanno nel package `com.palestra.web` o sotto: è lì che Spring cerca controller, service e repository."),
        ("new", "src/main/resources/application.properties", "spring.application.name=palestra-web\nspring.main.banner-mode=off",
         "Le impostazioni dell'app: il nome e niente logo all'avvio.", "Qui finiranno database e altre configurazioni."),
        ("new", _WT + "PalestraWebApplicationTests.java",
         _WPKG + "import org.junit.jupiter.api.Test;\nimport org.springframework.boot.test.context.SpringBootTest;\n\n@SpringBootTest\nclass PalestraWebApplicationTests {\n\n    @Test\n    void ilContestoSiAvvia() {\n    }\n}",
         "Un test che avvia tutta l'applicazione: se la configurazione è sbagliata, fallisce.",
         "Passa senza fare niente, ma dimostra che il progetto si avvia.")],
       "Aggiungi `server.port=8081` in application.properties e avvia l'app: ora risponde su localhost:8081."),

    _t("La prima pagina", "Un @Controller che mette un dato nel model e restituisce il nome della vista, e il suo template.",
       ("Il metodo di un @Controller restituisce la stringa \"home\". Cosa vede il browser?",
        ["La pagina templates/home.html riempita da Thymeleaf", "Il testo «home»", "Un JSON con «home»", "Un errore 404"], 0,
        "In un @Controller la stringa restituita è il nome della vista: Spring cerca `templates/home.html` e la fa riempire a Thymeleaf. Con @RestController invece sarebbe il testo stesso."),
       [("new", _WP + "HomeController.java",
         _WPKG + 'import org.springframework.stereotype.Controller;\nimport org.springframework.ui.Model;\nimport org.springframework.web.bind.annotation.GetMapping;\n\n@Controller\npublic class HomeController {\n\n    @GetMapping("/")\n    public String home(Model model) {\n        model.addAttribute("palestra", "Palestra Ricalco");\n        return "home";\n    }\n}',
         "Il controller della home: mette il nome della palestra nel model e sceglie la vista «home».",
         "Il `Model` è il ponte tra controller e vista: quello che ci metti con `addAttribute` il template lo legge con `${nome}`."),
        ("new", _WR + "home.html",
         _page("Palestra", '  <main class="container">\n    <h1 th:text="${palestra}">Nome della palestra</h1>\n    <p>Benvenuto! Guarda i nostri <a th:href="@{/corsi}">corsi</a>.</p>\n  </main>'),
         "Il template della home: il titolo viene dal model, il link punta all'elenco dei corsi.",
         "`th:text` sostituisce il testo del tag con il valore: «Nome della palestra» si vede solo aprendo il file nel browser senza server. `@{/corsi}` costruisce l'indirizzo giusto anche se l'app non è sulla radice."),
        ("new", _WT + "HomeControllerTest.java",
         _WPKG + 'import org.junit.jupiter.api.Test;\nimport org.springframework.beans.factory.annotation.Autowired;\nimport org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;\nimport org.springframework.test.web.servlet.MockMvc;\n\nimport static org.hamcrest.Matchers.containsString;\nimport static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;\nimport static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;\nimport static org.springframework.test.web.servlet.result.MockMvcResultMatchers.model;\nimport static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;\nimport static org.springframework.test.web.servlet.result.MockMvcResultMatchers.view;\n\n@WebMvcTest(HomeController.class)\nclass HomeControllerTest {\n\n    @Autowired\n    private MockMvc mvc;\n\n    @Test\n    void laHomeMostraIlNomeDellaPalestra() throws Exception {\n        mvc.perform(get("/"))\n                .andExpect(status().isOk())\n                .andExpect(view().name("home"))\n                .andExpect(model().attribute("palestra", "Palestra Ricalco"))\n                .andExpect(content().string(containsString("Palestra Ricalco")));\n    }\n}',
         "Il test controlla la vista scelta, il dato nel model e che il nome compaia davvero nell'HTML.",
         "`view()` e `model()` controllano il lavoro del controller, `content()` quello del template. `@WebMvcTest` carica solo la parte web, Thymeleaf compreso.")],
       "Aggiungi al model l'orario di apertura e mostralo nella home in un paragrafo con th:text."),

    _t("I corsi nel database", "Aggiungere JPA e H2, l'entità Corso, il repository e alcuni corsi caricati all'avvio.",
       ("Vuoi che all'avvio ci siano già tre corsi. Dove li crei?",
        ["In un componente CommandLineRunner, che Spring esegue appena l'app è pronta", "Nel costruttore dell'entità", "Nel template", "Nel test"], 0,
        "Un bean che implementa `CommandLineRunner` viene eseguito una volta all'avvio, con tutti gli altri bean già pronti: il posto giusto per i dati iniziali."),
       [("replace", "pom.xml",
         "      <artifactId>spring-boot-starter-thymeleaf</artifactId>\n    </dependency>",
         "      <artifactId>spring-boot-starter-thymeleaf</artifactId>\n    </dependency>\n    <dependency>\n      <groupId>org.springframework.boot</groupId>\n      <artifactId>spring-boot-starter-data-jpa</artifactId>\n    </dependency>\n    <dependency>\n      <groupId>org.springframework.boot</groupId>\n      <artifactId>spring-boot-starter-validation</artifactId>\n    </dependency>\n    <dependency>\n      <groupId>com.h2database</groupId>\n      <artifactId>h2</artifactId>\n      <scope>runtime</scope>\n    </dependency>",
         "Aggiunge JPA, la validazione (servirà per il form) e il database H2 in memoria.",
         "Senza `spring.datasource.url` Spring Boot crea da solo un H2 in memoria con le tabelle generate dalle entità. Per MySQL basterebbe cambiare la dipendenza e tre righe di configurazione."),
        ("end", "src/main/resources/application.properties", "spring.jpa.open-in-view=false",
         "Spegne «open in view»: le query si fanno nel service, non mentre il template viene disegnato.",
         "Con open-in-view acceso una query lenta può partire dal template senza che tu te ne accorga. Spento, tutto quello che la vista usa deve essere già caricato."),
        ("new", _WP + "Corso.java",
         _WPKG + "import jakarta.persistence.Entity;\nimport jakarta.persistence.GeneratedValue;\nimport jakarta.persistence.Id;\n\n@Entity\npublic class Corso {\n\n    @Id\n    @GeneratedValue\n    private Long id;\n    private String nome;\n    private String istruttore;\n    private int postiMax;\n    private int iscritti;\n\n    protected Corso() {\n    }\n\n    public Corso(String nome, String istruttore, int postiMax) {\n        this.nome = nome;\n        this.istruttore = istruttore;\n        this.postiMax = postiMax;\n    }",
         "L'entità Corso: id generato, nome, istruttore, posti massimi e iscritti.",
         "Il costruttore vuoto `protected` serve a JPA per creare gli oggetti letti dal database; il tuo codice usa quello con i parametri."),
        ("end", _WP + "Corso.java",
         "\n    public Long getId() {\n        return id;\n    }\n\n    public String getNome() {\n        return nome;\n    }\n\n    public String getIstruttore() {\n        return istruttore;\n    }\n\n    public int getPostiMax() {\n        return postiMax;\n    }\n\n    public int getIscritti() {\n        return iscritti;\n    }\n\n    public int getPostiLiberi() {\n        return postiMax - iscritti;\n    }\n}",
         "I getter, compreso uno calcolato: i posti liberi.",
         "Thymeleaf legge le proprietà con i getter: `${c.postiLiberi}` chiama `getPostiLiberi()`. Una proprietà non deve per forza essere un campo."),
        ("new", _WP + "CorsoRepository.java",
         _WPKG + "import org.springframework.data.jpa.repository.JpaRepository;\n\npublic interface CorsoRepository extends JpaRepository<Corso, Long> {\n}",
         "Il repository: salvare, cercare ed elencare i corsi senza scrivere codice.",
         "Spring Data genera l'implementazione all'avvio."),
        ("new", _WP + "DatiIniziali.java",
         _WPKG + 'import org.springframework.boot.CommandLineRunner;\nimport org.springframework.stereotype.Component;\n\n@Component\npublic class DatiIniziali implements CommandLineRunner {\n\n    private final CorsoRepository repository;\n\n    public DatiIniziali(CorsoRepository repository) {\n        this.repository = repository;\n    }\n\n    @Override\n    public void run(String... args) {\n        if (repository.count() == 0) {\n            repository.save(new Corso("Yoga", "Ada", 12));\n            repository.save(new Corso("Pilates", "Luca", 8));\n            repository.save(new Corso("Crossfit", "Sara", 15));\n        }\n    }\n}',
         "All'avvio, se il database è vuoto, salva tre corsi.",
         "Il controllo `count() == 0` evita i doppioni se un giorno il database non sarà più in memoria."),
        ("new", _WT + "DatiInizialiTest.java",
         _WPKG + 'import org.junit.jupiter.api.Test;\nimport org.springframework.beans.factory.annotation.Autowired;\nimport org.springframework.boot.test.context.SpringBootTest;\n\nimport static org.assertj.core.api.Assertions.assertThat;\n\n@SpringBootTest\nclass DatiInizialiTest {\n\n    @Autowired\n    private CorsoRepository repository;\n\n    @Test\n    void allAvvioCiSonoITreCorsi() {\n        assertThat(repository.findAll()).extracting(Corso::getNome).contains("Yoga", "Pilates", "Crossfit");\n    }\n}',
         "Il test avvia l'app e controlla che i tre corsi ci siano.",
         "`extracting(Corso::getNome)` trasforma la lista di corsi nella lista dei nomi, così il controllo resta leggibile.")],
       "Aggiungi un quarto corso ai dati iniziali e controlla che il test passi ancora."),

    _t("Il service", "Un service che elenca i corsi in ordine e trova un corso per id, con un'eccezione se non c'è.",
       ("`repository.findById(id)` restituisce un Optional. Se il corso non esiste cosa conviene fare nel service?",
        ["Lanciare un'eccezione con un nome chiaro, che il controller trasformerà in una pagina 404", "Restituire null", "Restituire un corso vuoto", "Ignorare il problema"], 0,
        "Un'eccezione del dominio (CorsoNonTrovatoException) dice esattamente cosa è successo, e un solo punto (tappa 7) decide come mostrarla all'utente."),
       [("new", _WP + "CorsoNonTrovatoException.java",
         _WPKG + 'public class CorsoNonTrovatoException extends RuntimeException {\n\n    public CorsoNonTrovatoException(Long id) {\n        super("Corso " + id + " non trovato");\n    }\n}',
         "L'eccezione per un corso che non esiste, con il messaggio già pronto.",
         "Estende `RuntimeException` (unchecked): non costringe ogni metodo a dichiararla con throws."),
        ("new", _WP + "CorsoService.java",
         _WPKG + 'import java.util.List;\n\nimport org.springframework.data.domain.Sort;\nimport org.springframework.stereotype.Service;\n\n@Service\npublic class CorsoService {\n\n    private final CorsoRepository repository;\n\n    public CorsoService(CorsoRepository repository) {\n        this.repository = repository;\n    }\n\n    public List<Corso> elenco() {\n        return repository.findAll(Sort.by("nome"));\n    }\n\n    public Corso trova(Long id) {\n        return repository.findById(id).orElseThrow(() -> new CorsoNonTrovatoException(id));\n    }\n}',
         "Il service: elenco ordinato per nome e ricerca per id.",
         "`Sort.by(\"nome\")` fa ordinare al database. `orElseThrow` apre l'Optional o lancia l'eccezione, in una riga."),
        ("new", _WT + "CorsoServiceTest.java",
         _WPKG + 'import org.junit.jupiter.api.Test;\nimport org.springframework.beans.factory.annotation.Autowired;\nimport org.springframework.boot.test.context.SpringBootTest;\n\nimport static org.assertj.core.api.Assertions.assertThat;\nimport static org.junit.jupiter.api.Assertions.assertThrows;\n\n@SpringBootTest\nclass CorsoServiceTest {\n\n    @Autowired\n    private CorsoService service;\n\n    @Test\n    void elencaICorsiInOrdineDiNome() {\n        assertThat(service.elenco()).extracting(Corso::getNome).containsSubsequence("Crossfit", "Pilates", "Yoga");\n    }\n\n    @Test\n    void unCorsoCheNonEsisteLanciaLEccezione() {\n        assertThrows(CorsoNonTrovatoException.class, () -> service.trova(9999L));\n    }\n}',
         "Due test: l'ordine dell'elenco e l'eccezione per un id inesistente.",
         "`containsSubsequence` controlla l'ordine senza pretendere che non ci siano altri corsi in mezzo.")],
       "Aggiungi al service `List<Corso> conPostiLiberi()` che restituisce solo i corsi con almeno un posto, usando uno stream."),

    _t("L'elenco dei corsi", "La pagina /corsi con una tabella costruita con th:each.",
       ("Nel template vuoi una riga della tabella per ogni corso. Quale attributo Thymeleaf usi?",
        ["th:each sul tag <tr>", "th:text sulla tabella", "th:if su ogni riga", "Un ciclo for in JavaScript"], 0,
        "`th:each=\"c : ${corsi}\"` ripete il tag su cui si trova (qui la riga) una volta per ogni elemento, e dentro `c` è il corso corrente."),
       [("new", _WP + "CorsiController.java",
         _WPKG + _CTRL_IMPORTS_1 + '\n\n@Controller\n@RequestMapping("/corsi")\npublic class CorsiController {\n\n    private final CorsoService service;\n\n    public CorsiController(CorsoService service) {\n        this.service = service;\n    }\n\n    @GetMapping\n    public String elenco(Model model) {\n        model.addAttribute("corsi", service.elenco());\n        return "corsi/elenco";\n    }\n}',
         "Il controller dei corsi: GET /corsi mette la lista nel model e sceglie la vista corsi/elenco.",
         "`@RequestMapping(\"/corsi\")` sulla classe fa da prefisso a tutti i metodi. La vista `corsi/elenco` è il file `templates/corsi/elenco.html`."),
        ("new", _WR + "corsi/elenco.html",
         _page("Corsi", '  <main class="container">\n    <h1>I nostri corsi</h1>\n    <p th:if="${corsi.isEmpty()}">Nessun corso, per ora.</p>\n    <table class="table" th:unless="${corsi.isEmpty()}">\n      <thead>\n        <tr><th>Corso</th><th>Istruttore</th><th>Posti liberi</th></tr>\n      </thead>\n      <tbody>\n        <tr th:each="c : ${corsi}">\n          <td th:text="${c.nome}">Nome</td>\n          <td th:text="${c.istruttore}">Istruttore</td>\n          <td th:text="${c.postiLiberi}">0</td>\n        </tr>\n      </tbody>\n    </table>\n  </main>'),
         "La tabella dei corsi: una riga per corso, e un messaggio se la lista è vuota.",
         "`th:if` e `th:unless` mostrano o tolgono un tag. Le classi `container` e `table` sono di Bootstrap: prenderanno stile alla tappa 8."),
        ("new", _WT + "ElencoCorsiTest.java",
         _WPKG + _WEB_TEST_IMPORTS + '\n@SpringBootTest\n@AutoConfigureMockMvc\nclass ElencoCorsiTest {\n\n    @Autowired\n    private MockMvc mvc;\n\n    @Test\n    void mostraLaTabellaDeiCorsi() throws Exception {\n        mvc.perform(get("/corsi"))\n                .andExpect(status().isOk())\n                .andExpect(view().name("corsi/elenco"))\n                .andExpect(model().attributeExists("corsi"))\n                .andExpect(content().string(containsString("Pilates")));\n    }\n}',
         "Il test apre /corsi e controlla vista, model e che un corso compaia nella pagina.",
         "Qui serve `@SpringBootTest` con MockMvc: il controller usa il service e il database, che `@WebMvcTest` non caricherebbe.")],
       "Aggiungi una colonna con i posti massimi e, sotto la tabella, il numero di corsi con `${corsi.size()}`."),

    _t("Il dettaglio di un corso", "La pagina /corsi/{id} e i link dall'elenco.",
       ("Come costruisci in Thymeleaf il link /corsi/3 per il corso con id 3?",
        ["th:href=\"@{/corsi/{id}(id=${c.id})}\"", "href=\"/corsi/${c.id}\"", "th:text=\"/corsi/3\"", "th:each=\"id : ${c}\""], 0,
        "Nella sintassi `@{...}` i segnaposto tra graffe si riempiono con i parametri tra parentesi tonde. Thymeleaf aggiunge anche il percorso base dell'app."),
       [("replace", _WP + "CorsiController.java", _CTRL_IMPORTS_1, _CTRL_IMPORTS_2,
         "Aggiunge l'import di @PathVariable.", "Gli import in ordine alfabetico si leggono e si confrontano meglio."),
        ("replace", _WP + "CorsiController.java", '        return "corsi/elenco";\n    }',
         '        return "corsi/elenco";\n    }\n\n    @GetMapping("/{id}")\n    public String dettaglio(@PathVariable Long id, Model model) {\n        model.addAttribute("corso", service.trova(id));\n        return "corsi/dettaglio";\n    }',
         "GET /corsi/{id}: prende l'id dall'indirizzo, cerca il corso e mostra la pagina di dettaglio.",
         "`@PathVariable` legge il pezzo `{id}` dell'URL e lo converte in Long. Se il corso non c'è, il service lancia l'eccezione."),
        ("new", _WR + "corsi/dettaglio.html",
         _page("Dettaglio", '  <main class="container">\n    <h1 th:text="${corso.nome}">Corso</h1>\n    <p>Istruttore: <b th:text="${corso.istruttore}">Nome</b></p>\n    <p>Posti liberi: <span th:text="${corso.postiLiberi}">0</span> su <span th:text="${corso.postiMax}">0</span></p>\n    <a th:href="@{/corsi}">Torna ai corsi</a>\n  </main>'),
         "La pagina di un corso: nome, istruttore e posti.",
         "Ogni `th:text` sostituisce il segnaposto: «Corso», «Nome» e «0» si vedono solo aprendo il file senza server."),
        ("replace", _WR + "corsi/elenco.html", '          <td th:text="${c.nome}">Nome</td>',
         '          <td><a th:href="@{/corsi/{id}(id=${c.id})}" th:text="${c.nome}">Nome</a></td>',
         "Il nome del corso nell'elenco diventa un link al suo dettaglio.",
         "L'id del link viene dal corso della riga: ogni riga punta al suo corso."),
        ("new", _WT + "DettaglioCorsoTest.java",
         _WPKG + _WEB_TEST_IMPORTS + '\n@SpringBootTest\n@AutoConfigureMockMvc\nclass DettaglioCorsoTest {\n\n    @Autowired\n    private MockMvc mvc;\n\n    @Autowired\n    private CorsoService service;\n\n    @Test\n    void mostraIlDettaglioDelCorso() throws Exception {\n        Corso yoga = service.elenco().stream().filter(c -> c.getNome().equals("Yoga")).findFirst().orElseThrow();\n        mvc.perform(get("/corsi/" + yoga.getId()))\n                .andExpect(status().isOk())\n                .andExpect(view().name("corsi/dettaglio"))\n                .andExpect(model().attributeExists("corso"))\n                .andExpect(content().string(containsString("Ada")));\n    }\n}',
         "Il test prende l'id vero del corso Yoga e apre la sua pagina.",
         "L'id lo genera il database, quindi il test non lo scrive a mano: lo cerca con il service.")],
       "Nel dettaglio mostra «Corso pieno» in rosso quando i posti liberi sono zero, con th:if."),

    _t("Le pagine di errore", "Mostrare una pagina 404 chiara quando il corso non esiste, con un @ControllerAdvice.",
       ("L'eccezione CorsoNonTrovatoException può partire da più controller. Dove decidi la pagina da mostrare?",
        ["In una classe @ControllerAdvice con un @ExceptionHandler: un solo punto per tutti i controller", "In un try/catch in ogni metodo",
         "Nel template", "Nel service"], 0,
        "`@ControllerAdvice` raccoglie la gestione degli errori di tutti i controller: i metodi restano puliti e la pagina d'errore è sempre la stessa."),
       [("new", _WP + "GestoreErrori.java",
         _WPKG + 'import org.springframework.http.HttpStatus;\nimport org.springframework.web.bind.annotation.ControllerAdvice;\nimport org.springframework.web.bind.annotation.ExceptionHandler;\nimport org.springframework.web.servlet.ModelAndView;\n\n@ControllerAdvice\npublic class GestoreErrori {\n\n    @ExceptionHandler(CorsoNonTrovatoException.class)\n    public ModelAndView corsoNonTrovato(CorsoNonTrovatoException e) {\n        ModelAndView pagina = new ModelAndView("errore", HttpStatus.NOT_FOUND);\n        pagina.addObject("messaggio", e.getMessage());\n        return pagina;\n    }\n}',
         "Quando un controller lancia CorsoNonTrovatoException, mostra la vista «errore» con stato 404 e il messaggio.",
         "`ModelAndView` mette insieme vista, dati e stato HTTP. Il 404 conta: i motori di ricerca e i browser capiscono che la pagina non esiste."),
        ("new", _WR + "errore.html",
         _page("Errore", '  <main class="container">\n    <h1>Ops!</h1>\n    <p class="alert alert-warning" th:text="${messaggio}">Qualcosa è andato storto.</p>\n    <a th:href="@{/corsi}">Torna ai corsi</a>\n  </main>'),
         "La pagina d'errore: il messaggio e un link per tornare ai corsi.",
         "Una pagina d'errore utile dice cosa è successo e offre una via d'uscita."),
        ("new", _WT + "ErroriTest.java",
         _WPKG + _WEB_TEST_IMPORTS + '\n@SpringBootTest\n@AutoConfigureMockMvc\nclass ErroriTest {\n\n    @Autowired\n    private MockMvc mvc;\n\n    @Test\n    void unCorsoCheNonEsisteDa404() throws Exception {\n        mvc.perform(get("/corsi/9999"))\n                .andExpect(status().isNotFound())\n                .andExpect(view().name("errore"))\n                .andExpect(content().string(containsString("Corso 9999 non trovato")));\n    }\n}',
         "Il test apre un corso inesistente: stato 404, vista errore e messaggio nella pagina.",
         "Senza il gestore, l'eccezione arriverebbe fino a Spring e l'utente vedrebbe una pagina d'errore generica con stato 500.")],
       "Prova ad aprire /corsi/abc: l'id non è un numero. Aggiungi un @ExceptionHandler per MethodArgumentTypeMismatchException che mostri la stessa pagina con un messaggio adatto."),

    _t("Layout comune e Bootstrap", "Mettere head e menu in un frammento Thymeleaf riusato da tutte le pagine, con Bootstrap 5.",
       ("Ogni pagina ripete lo stesso head e lo stesso menu. Come eviti di copiarli?",
        ["Li scrivi una volta come frammenti (th:fragment) e li includi con th:replace", "Li copi in ogni pagina", "Li carichi con JavaScript", "Li metti nel controller"], 0,
        "Un frammento è un pezzo di template con un nome: `th:replace` lo inserisce al posto del tag. Cambi il menu in un posto e cambia ovunque."),
       [("new", _WR + "fragments.html",
         '<!DOCTYPE html>\n<html xmlns:th="http://www.thymeleaf.org">\n<head th:fragment="head(titolo)">\n  <meta charset="UTF-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1">\n  <title th:text="${titolo} + \' · Palestra\'">Palestra</title>\n  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">\n</head>\n<body>\n  <nav th:fragment="menu" class="navbar navbar-expand navbar-dark bg-dark mb-4">\n    <div class="container">\n      <a class="navbar-brand" th:href="@{/}">Palestra</a>\n      <div class="navbar-nav">\n        <a class="nav-link" th:href="@{/corsi}">Corsi</a>\n        <a class="nav-link" th:href="@{/corsi/nuovo}">Nuovo corso</a>\n      </div>\n    </div>\n  </nav>\n</body>\n</html>',
         "Due frammenti: l'head con un titolo come parametro e Bootstrap, e la barra di navigazione.",
         "`head(titolo)` è un frammento con parametro: ogni pagina passa il suo titolo. Bootstrap arriva da una CDN, quindi non serve scaricare niente."),
        ("replace", _WR + "home.html", _head("Palestra"), _layout("Home"),
         "La home usa l'head e il menu comuni.", "`~{fragments :: head('Home')}` vuol dire: dal file fragments.html prendi il frammento head con titolo «Home»."),
        ("replace", _WR + "corsi/elenco.html", _head("Corsi"), _layout("Corsi"),
         "Lo stesso per l'elenco dei corsi.", "Ora le classi `container` e `table` scritte prima prendono lo stile di Bootstrap."),
        ("replace", _WR + "corsi/dettaglio.html", _head("Dettaglio"), _layout("Dettaglio"),
         "Lo stesso per il dettaglio.", "Il tag `<head>` della pagina viene sostituito per intero da quello del frammento."),
        ("replace", _WR + "errore.html", _head("Errore"), _layout("Errore"),
         "E per la pagina d'errore.", "Anche gli errori hanno il menu: l'utente non resta senza via d'uscita."),
        ("new", _WT + "LayoutTest.java",
         _WPKG + _WEB_TEST_IMPORTS + '\n@SpringBootTest\n@AutoConfigureMockMvc\nclass LayoutTest {\n\n    @Autowired\n    private MockMvc mvc;\n\n    @Test\n    void lePagineHannoMenuEBootstrap() throws Exception {\n        mvc.perform(get("/corsi"))\n                .andExpect(status().isOk())\n                .andExpect(content().string(containsString("navbar")))\n                .andExpect(content().string(containsString("bootstrap.min.css")))\n                .andExpect(content().string(containsString("Corsi · Palestra")));\n    }\n}',
         "Il test controlla che la pagina dei corsi contenga il menu, Bootstrap e il titolo composto.",
         "Il titolo «Corsi · Palestra» dimostra che il parametro del frammento è arrivato.")],
       "Aggiungi un frammento `footer` con il nome della palestra e l'anno, e includilo in tutte le pagine."),

    _t("Il form per un nuovo corso", "Mostrare un form legato a un oggetto con th:object e th:field.",
       ("Perché il form usa una classe CorsoForm invece dell'entità Corso?",
        ["Il form contiene solo i campi che l'utente può scrivere, con le loro regole di validazione", "Perché Thymeleaf non legge le entità",
         "Per avere più file", "Perché l'entità non ha getter"], 0,
        "Il form-backing object è il «contratto» con la pagina: niente id né iscritti decisi dall'utente, e le regole (@NotBlank, @Min) stanno vicino ai campi del form."),
       [("new", _WP + "CorsoForm.java",
         _WPKG + 'import jakarta.validation.constraints.Max;\nimport jakarta.validation.constraints.Min;\nimport jakarta.validation.constraints.NotBlank;\n\npublic class CorsoForm {\n\n    @NotBlank(message = "Scrivi il nome del corso")\n    private String nome;\n\n    @NotBlank(message = "Scrivi il nome dell\'istruttore")\n    private String istruttore;\n\n    @Min(value = 1, message = "Almeno un posto")\n    @Max(value = 50, message = "Al massimo 50 posti")\n    private int postiMax = 10;\n\n    public String getNome() {\n        return nome;\n    }\n\n    public void setNome(String nome) {\n        this.nome = nome;\n    }\n\n    public String getIstruttore() {\n        return istruttore;\n    }\n\n    public void setIstruttore(String istruttore) {\n        this.istruttore = istruttore;\n    }\n\n    public int getPostiMax() {\n        return postiMax;\n    }\n\n    public void setPostiMax(int postiMax) {\n        this.postiMax = postiMax;\n    }\n}',
         "L'oggetto del form: tre campi con le regole di validazione e getter e setter.",
         "Qui servono i setter: Spring riempie l'oggetto con i valori del form chiamando `setNome`, `setIstruttore`… `postiMax = 10` è il valore proposto nel form vuoto."),
        ("replace", _WP + "CorsiController.java", '        return "corsi/dettaglio";\n    }',
         '        return "corsi/dettaglio";\n    }\n\n    @GetMapping("/nuovo")\n    public String nuovo(Model model) {\n        model.addAttribute("corso", new CorsoForm());\n        return "corsi/form";\n    }',
         "GET /corsi/nuovo: mette nel model un CorsoForm vuoto e mostra il form.",
         "Spring sceglie `/nuovo` prima di `/{id}`: un indirizzo scritto per intero vince su uno con segnaposto."),
        ("new", _WR + "corsi/form.html",
         '<!DOCTYPE html>\n<html xmlns:th="http://www.thymeleaf.org">\n' + _layout("Nuovo corso") + '\n  <main class="container">\n    <h1>Nuovo corso</h1>\n    <form th:action="@{/corsi}" th:object="${corso}" method="post" novalidate>\n      <div class="mb-3">\n        <label class="form-label" for="nome">Nome</label>\n        <input class="form-control" th:field="*{nome}">\n        <div class="text-danger" th:if="${#fields.hasErrors(\'nome\')}" th:errors="*{nome}"></div>\n      </div>\n      <div class="mb-3">\n        <label class="form-label" for="istruttore">Istruttore</label>\n        <input class="form-control" th:field="*{istruttore}">\n        <div class="text-danger" th:if="${#fields.hasErrors(\'istruttore\')}" th:errors="*{istruttore}"></div>\n      </div>\n      <div class="mb-3">\n        <label class="form-label" for="postiMax">Posti</label>\n        <input class="form-control" type="number" th:field="*{postiMax}">\n        <div class="text-danger" th:if="${#fields.hasErrors(\'postiMax\')}" th:errors="*{postiMax}"></div>\n      </div>\n      <button class="btn btn-primary">Salva</button>\n    </form>\n  </main>\n</body>\n</html>',
         "Il form: ogni input è legato a un campo di CorsoForm, e sotto ogni campo c'è il suo eventuale errore.",
         "`th:object` sceglie l'oggetto, `*{nome}` è un suo campo: `th:field` scrive da solo id, name e value. `novalidate` spegne i controlli del browser, così vedi quelli del server."),
        ("new", _WT + "FormCorsoTest.java",
         _WPKG + _WEB_TEST_IMPORTS + '\n@SpringBootTest\n@AutoConfigureMockMvc\nclass FormCorsoTest {\n\n    @Autowired\n    private MockMvc mvc;\n\n    @Test\n    void mostraIlFormVuoto() throws Exception {\n        mvc.perform(get("/corsi/nuovo"))\n                .andExpect(status().isOk())\n                .andExpect(view().name("corsi/form"))\n                .andExpect(model().attributeExists("corso"))\n                .andExpect(content().string(containsString("name=\\"istruttore\\"")));\n    }\n}',
         "Il test apre il form e controlla vista, oggetto nel model e che il campo istruttore ci sia.",
         "Il `name=\"istruttore\"` nell'HTML lo ha scritto `th:field`: è il nome con cui il valore tornerà al server.")],
       "Aggiungi al form un campo «descrizione» (CorsoForm, template) con un limite di 200 caratteri (@Size)."),

    _t("Salvare il form", "Ricevere il form con @Valid, rimostrarlo con gli errori o salvare e fare redirect con un messaggio.",
       ("Dopo un POST andato a buon fine, perché fare redirect a /corsi invece di mostrare subito l'elenco?",
        ["Così ricaricare la pagina non rimanda il form (pattern Post/Redirect/Get)", "Perché è più veloce", "Perché Thymeleaf non sa mostrare l'elenco dopo un POST", "Per cambiare porta"], 0,
        "Se dopo il POST mostri una pagina, il tasto «ricarica» rifà il POST e crea un doppione. Con il redirect il browser fa una GET: ricaricare è innocuo."),
       [("replace", _WP + "CorsoService.java", '        return repository.findById(id).orElseThrow(() -> new CorsoNonTrovatoException(id));\n    }',
         '        return repository.findById(id).orElseThrow(() -> new CorsoNonTrovatoException(id));\n    }\n\n    public Corso crea(String nome, String istruttore, int postiMax) {\n        return repository.save(new Corso(nome, istruttore, postiMax));\n    }',
         "Il service impara a creare un corso.", "Il controller non sa che esiste un repository: chiede al service."),
        ("replace", _WP + "CorsiController.java", _CTRL_IMPORTS_2, _CTRL_IMPORTS_3,
         "Gli import per validazione, form e redirect.", "`@Valid` viene da Jakarta Validation, `RedirectAttributes` da Spring MVC."),
        ("replace", _WP + "CorsiController.java", '        return "corsi/form";\n    }',
         '        return "corsi/form";\n    }\n\n    @PostMapping\n    public String salva(@Valid @ModelAttribute("corso") CorsoForm form, BindingResult errori, RedirectAttributes redirect) {\n        if (errori.hasErrors()) {\n            return "corsi/form";\n        }\n        Corso corso = service.crea(form.getNome(), form.getIstruttore(), form.getPostiMax());\n        redirect.addFlashAttribute("messaggio", "Corso «" + corso.getNome() + "» creato.");\n        return "redirect:/corsi";\n    }',
         "POST /corsi: se ci sono errori rimostra il form, altrimenti salva e torna all'elenco con un messaggio.",
         "`BindingResult` deve stare subito dopo l'oggetto validato. Il flash attribute sopravvive a un solo redirect: il messaggio si vede una volta e poi sparisce."),
        ("replace", _WR + "corsi/elenco.html", "    <h1>I nostri corsi</h1>",
         '    <h1>I nostri corsi</h1>\n    <div class="alert alert-success" th:if="${messaggio}" th:text="${messaggio}"></div>',
         "L'elenco mostra il messaggio di conferma, se c'è.", "Dopo il redirect il flash attribute finisce nel model della pagina successiva."),
        ("new", _WT + "SalvaCorsoTest.java",
         _WPKG + _WEB_POST_IMPORTS + '\n@SpringBootTest\n@AutoConfigureMockMvc\n@Transactional\nclass SalvaCorsoTest {\n\n    @Autowired\n    private MockMvc mvc;\n\n    @Test\n    void unFormGiustoSalvaETornaAllElenco() throws Exception {\n        mvc.perform(post("/corsi").param("nome", "Boxe").param("istruttore", "Rocco").param("postiMax", "6"))\n                .andExpect(status().is3xxRedirection())\n                .andExpect(redirectedUrl("/corsi"))\n                .andExpect(flash().attribute("messaggio", "Corso «Boxe» creato."));\n    }\n\n    @Test\n    void unFormSenzaNomeTornaConLErrore() throws Exception {\n        mvc.perform(post("/corsi").param("nome", "").param("istruttore", "Rocco").param("postiMax", "6"))\n                .andExpect(status().isOk())\n                .andExpect(view().name("corsi/form"))\n                .andExpect(model().attributeHasFieldErrors("corso", "nome"));\n    }\n}',
         "Due test: il form giusto fa redirect con il messaggio, quello senza nome torna al form con l'errore sul campo.",
         "`@Transactional` sul test annulla il salvataggio alla fine: gli altri test trovano il database come prima.")],
       "Aggiungi le pagine per modificare un corso: GET /corsi/{id}/modifica con il form già pieno e POST che aggiorna."),

    _t("Prenotare un posto", "Un bottone nel dettaglio che prenota un posto, con la regola dei posti esauriti nell'entità.",
       ("Dove metti la regola «non si prenota se i posti sono finiti»?",
        ["Nell'entità Corso, in un metodo iscrivi() che lancia un'eccezione", "Nel template, nascondendo il bottone", "Nel controller, con un if", "Nel test"], 0,
        "La regola appartiene al corso: chiunque chiami `iscrivi()` la rispetta. Disattivare il bottone nel template è solo una cortesia, non una protezione."),
       [("new", _WP + "PostiEsauritiException.java",
         _WPKG + 'public class PostiEsauritiException extends RuntimeException {\n\n    public PostiEsauritiException(String corso) {\n        super("Posti esauriti per " + corso);\n    }\n}',
         "L'eccezione per un corso pieno.", "Un'eccezione con un nome del dominio rende chiaro il motivo del rifiuto."),
        ("replace", _WP + "Corso.java", "    public int getPostiLiberi() {\n        return postiMax - iscritti;\n    }",
         "    public int getPostiLiberi() {\n        return postiMax - iscritti;\n    }\n\n    public void iscrivi() {\n        if (getPostiLiberi() == 0) {\n            throw new PostiEsauritiException(nome);\n        }\n        iscritti++;\n    }",
         "Il corso sa iscrivere una persona, e rifiuta se è pieno.",
         "È un'entità «ricca»: i dati e le regole che li proteggono stanno insieme."),
        ("replace", _WP + "CorsoService.java", "import org.springframework.stereotype.Service;",
         "import org.springframework.stereotype.Service;\nimport org.springframework.transaction.annotation.Transactional;",
         "L'import di @Transactional.", "È quello di Spring, non quello di Jakarta: offre più opzioni ed è il più usato nei progetti Spring."),
        ("replace", _WP + "CorsoService.java", "        return repository.save(new Corso(nome, istruttore, postiMax));\n    }",
         "        return repository.save(new Corso(nome, istruttore, postiMax));\n    }\n\n    @Transactional\n    public Corso prenota(Long id) {\n        Corso corso = trova(id);\n        corso.iscrivi();\n        return corso;\n    }",
         "Prenota: trova il corso e chiama iscrivi(), dentro una transazione.",
         "Non serve `save`: dentro la transazione JPA si accorge che `iscritti` è cambiato e lo salva alla fine (dirty checking)."),
        ("replace", _WP + "CorsiController.java", '        return "redirect:/corsi";\n    }',
         '        return "redirect:/corsi";\n    }\n\n    @PostMapping("/{id}/prenota")\n    public String prenota(@PathVariable Long id, RedirectAttributes redirect) {\n        try {\n            service.prenota(id);\n            redirect.addFlashAttribute("messaggio", "Posto prenotato.");\n        } catch (PostiEsauritiException e) {\n            redirect.addFlashAttribute("errore", e.getMessage());\n        }\n        return "redirect:/corsi/" + id;\n    }',
         "POST /corsi/{id}/prenota: prova a prenotare e torna al dettaglio con un messaggio di conferma o di errore.",
         "Anche qui Post/Redirect/Get. Il posto esaurito non è un guasto: è un caso previsto, quindi diventa un messaggio, non una pagina d'errore."),
        ("replace", _WR + "corsi/dettaglio.html", '    <a th:href="@{/corsi}">Torna ai corsi</a>',
         '    <div class="alert alert-success" th:if="${messaggio}" th:text="${messaggio}"></div>\n    <div class="alert alert-danger" th:if="${errore}" th:text="${errore}"></div>\n    <form th:action="@{/corsi/{id}/prenota(id=${corso.id})}" method="post" class="mb-3">\n      <button class="btn btn-primary" th:disabled="${corso.postiLiberi == 0}">Prenota un posto</button>\n    </form>\n    <a th:href="@{/corsi}">Torna ai corsi</a>',
         "Nel dettaglio: i messaggi e il bottone che prenota, disattivato se il corso è pieno.",
         "Il form fa un POST perché prenotare cambia i dati: una GET non deve mai modificare niente."),
        ("new", _WT + "PrenotazioneTest.java",
         _WPKG + _WEB_POST_IMPORTS + '\n@SpringBootTest\n@AutoConfigureMockMvc\n@Transactional\nclass PrenotazioneTest {\n\n    @Autowired\n    private MockMvc mvc;\n\n    @Autowired\n    private CorsoService service;\n\n    @Test\n    void ilSecondoPostoDiUnCorsoDaUnoEEsaurito() throws Exception {\n        Corso mini = service.crea("Mini", "Ada", 1);\n        String indirizzo = "/corsi/" + mini.getId();\n        mvc.perform(post(indirizzo + "/prenota"))\n                .andExpect(redirectedUrl(indirizzo))\n                .andExpect(flash().attribute("messaggio", "Posto prenotato."));\n        mvc.perform(post(indirizzo + "/prenota"))\n                .andExpect(redirectedUrl(indirizzo))\n                .andExpect(flash().attribute("errore", "Posti esauriti per Mini"));\n    }\n}',
         "Il test crea un corso con un posto: la prima prenotazione riesce, la seconda dà l'errore.",
         "Il test e il service condividono la stessa transazione, annullata alla fine: il corso «Mini» non resta nel database.")],
       "Aggiungi un bottone «Annulla prenotazione» che toglie un iscritto (senza andare sotto zero)."),
]

PROJECTS["palestra-web"] = {
    "title": "Web app palestra (MVC)", "lang": "java", "kind": "maven", "folder": "palestra-web", "main": "pom.xml", "requires": [],
    "desc": "Una web app Spring MVC con Thymeleaf e Bootstrap: pagine, form validati, layout comune, errori e prenotazioni. 11 tappe, con i test MockMvc su viste e model.",
    "url": "http://localhost:8080/corsi", "steps": PALESTRA_WEB}


# ================================================================ Biblioteca (SQL, SQLite)
_CHIUSI = "julianday(p.reso_il) - julianday(p.preso_il)"

BIBLIOTECA = [
    _t("Le prime tabelle", "Creare le tabelle degli autori e dei libri, collegate da una chiave esterna.",
       ("Ogni libro ha un autore, e un autore può aver scritto più libri. Come lo rappresenti?",
        ["Una tabella autori e una libri; ogni libro tiene l'id del suo autore", "Una sola tabella con il nome dell'autore ripetuto in ogni libro",
         "Una tabella autori con una colonna per ogni libro", "Una tabella per ogni autore"], 0,
        "È una relazione uno-a-molti: il «molti» (libri) tiene la chiave dell'«uno» (autori). Il nome dell'autore sta in un posto solo, quindi se lo correggi lo correggi ovunque."),
       [("new", "schema.sql",
         "-- Biblioteca: lo schema del database\nPRAGMA foreign_keys = ON;\n\nCREATE TABLE autori (\n    id      INTEGER PRIMARY KEY,\n    nome    TEXT NOT NULL,\n    nazione TEXT\n);",
         "Accende il controllo delle chiavi esterne e crea la tabella degli autori.",
         "In SQLite le chiavi esterne sono spente di default: `PRAGMA foreign_keys = ON` le attiva. `INTEGER PRIMARY KEY` dà un id che si numera da solo."),
        ("end", "schema.sql",
         "\nCREATE TABLE libri (\n    id        INTEGER PRIMARY KEY,\n    titolo    TEXT NOT NULL,\n    anno      INTEGER CHECK (anno > 0),\n    genere    TEXT NOT NULL DEFAULT 'romanzo',\n    autore_id INTEGER NOT NULL REFERENCES autori(id)\n);",
         "Crea la tabella dei libri: ogni libro punta al suo autore con `autore_id`.",
         "`REFERENCES autori(id)` è la chiave esterna: il database rifiuta un libro con un autore che non esiste. `CHECK` e `DEFAULT` mettono le regole nei dati, non solo nel codice."),
        ("new", "query.sql",
         "-- Le tabelle del database\nSELECT name AS tabella FROM sqlite_master WHERE type = 'table' ORDER BY name;",
         "Elenca le tabelle che esistono, per controllare che lo schema sia stato creato.",
         "`sqlite_master` è il catalogo interno di SQLite: una tabella che descrive le altre tabelle.")],
       "Aggiungi alla tabella autori una colonna `nato_il TEXT` e riesegui."),

    _t("I primi dati", "Inserire autori e libri.",
       ("In che ordine vanno inseriti autori e libri?",
        ["Prima gli autori, poi i libri", "Prima i libri, poi gli autori", "Non conta l'ordine", "Insieme nella stessa INSERT"], 0,
        "Un libro punta a un autore: con le chiavi esterne attive, l'autore deve già esistere quando inserisci il libro."),
       [("new", "dati.sql",
         "-- Biblioteca: i dati di prova\nINSERT INTO autori (id, nome, nazione) VALUES\n    (1, 'Italo Calvino', 'Italia'),\n    (2, 'Elsa Morante', 'Italia'),\n    (3, 'Gabriel García Márquez', 'Colombia'),\n    (4, 'Jane Austen', 'Regno Unito'),\n    (5, 'Primo Levi', 'Italia'),\n    (6, 'Ursula K. Le Guin', 'Stati Uniti');",
         "Inserisce sei autori con una sola INSERT.",
         "Una INSERT con più righe dopo `VALUES` è più veloce e più leggibile di sei INSERT separate. Gli id li scrivo io, così i libri possono usarli."),
        ("end", "dati.sql",
         "\nINSERT INTO libri (id, titolo, anno, genere, autore_id) VALUES\n    (1, 'Il barone rampante', 1957, 'romanzo', 1),\n    (2, 'Le città invisibili', 1972, 'romanzo', 1),\n    (3, 'Se una notte d''inverno un viaggiatore', 1979, 'romanzo', 1),\n    (4, 'La storia', 1974, 'romanzo', 2),\n    (5, 'L''isola di Arturo', 1957, 'romanzo', 2),\n    (6, 'Cent''anni di solitudine', 1967, 'romanzo', 3),\n    (7, 'Orgoglio e pregiudizio', 1813, 'romanzo', 4),\n    (8, 'Emma', 1815, 'romanzo', 4),\n    (9, 'Se questo è un uomo', 1947, 'memorie', 5),\n    (10, 'Il sistema periodico', 1975, 'racconti', 5),\n    (11, 'La mano sinistra del buio', 1969, 'fantascienza', 6),\n    (12, 'I reietti dell''altro pianeta', 1974, 'fantascienza', 6);",
         "Inserisce dodici libri, ognuno con l'id del suo autore.",
         "L'apostrofo dentro una stringa SQL si scrive doppio: `'Cent''anni'`. Con uno solo la stringa finirebbe lì."),
        ("end", "query.sql",
         "\n-- Quanti libri ci sono\nSELECT COUNT(*) AS libri FROM libri;",
         "Conta le righe della tabella libri.",
         "`COUNT(*)` conta le righe; `AS libri` dà un nome alla colonna del risultato.")],
       "Aggiungi un tuo autore e due suoi libri. Poi prova a inserire un libro con `autore_id` 99: cosa dice il database?"),

    _t("Cercare e ordinare", "Filtrare i libri con WHERE, ordinarli e prenderne solo alcuni.",
       ("`WHERE anno BETWEEN 1950 AND 1979` include i libri del 1950 e del 1979?",
        ["Sì, BETWEEN include entrambi gli estremi", "No, li esclude tutti e due", "Include solo il 1950", "Dipende dal database"], 0,
        "`BETWEEN a AND b` equivale a `>= a AND <= b`: gli estremi sono compresi."),
       [("end", "query.sql",
         "\n-- I libri usciti tra il 1950 e il 1979, dal più vecchio\nSELECT titolo, anno\nFROM libri\nWHERE anno BETWEEN 1950 AND 1979\nORDER BY anno, titolo;",
         "Prende i libri di un intervallo di anni e li ordina per anno, poi per titolo.",
         "Il secondo criterio di `ORDER BY` decide l'ordine tra libri dello stesso anno: senza, l'ordine tra pari non è garantito."),
        ("end", "query.sql",
         "\n-- I titoli che cominciano con «Il» o «La»\nSELECT titolo\nFROM libri\nWHERE titolo LIKE 'Il %' OR titolo LIKE 'La %'\nORDER BY titolo;",
         "Cerca i titoli con un inizio preciso.",
         "In `LIKE` il `%` vale «qualsiasi testo». Lo spazio dopo «Il» evita di prendere anche «Isola» o «Lago»."),
        ("end", "query.sql",
         "\n-- I tre libri più recenti\nSELECT titolo, anno\nFROM libri\nORDER BY anno DESC\nLIMIT 3;",
         "Ordina dal più nuovo e tiene solo le prime tre righe.",
         "`LIMIT` si applica dopo `ORDER BY`: prima ordini, poi tagli. È lo schema di ogni «top N».")],
       "Scrivi una query con i libri di genere diverso da «romanzo», ordinati per titolo."),

    _t("Unire libri e autori", "Mostrare ogni libro con il nome del suo autore usando una JOIN.",
       ("Nella tabella libri c'è solo `autore_id`. Come ottieni il nome dell'autore accanto al titolo?",
        ["Con una JOIN tra libri e autori su autori.id = libri.autore_id", "Con una seconda SELECT per ogni libro", "Aggiungendo la colonna nome a libri", "Con ORDER BY autore_id"], 0,
        "La JOIN accoppia ogni riga di libri con la riga di autori che ha lo stesso id. La condizione dopo `ON` dice quali righe vanno insieme."),
       [("end", "query.sql",
         "\n-- Ogni libro con il suo autore\nSELECT l.titolo, a.nome AS autore\nFROM libri AS l\nJOIN autori AS a ON a.id = l.autore_id\nORDER BY a.nome, l.titolo;",
         "Unisce le due tabelle e mostra titolo e autore.",
         "Gli alias `l` e `a` accorciano la query e dicono da quale tabella viene ogni colonna: serve quando due tabelle hanno colonne con lo stesso nome (qui `id`)."),
        ("end", "query.sql",
         "\n-- I libri di autori italiani\nSELECT l.titolo, a.nome AS autore\nFROM libri AS l\nJOIN autori AS a ON a.id = l.autore_id\nWHERE a.nazione = 'Italia'\nORDER BY l.anno;",
         "Dopo la JOIN filtra su una colonna dell'altra tabella.",
         "Una volta unite, le colonne di entrambe le tabelle si usano ovunque: nel `WHERE`, nell'`ORDER BY` e nella `SELECT`.")],
       "Mostra titolo, autore e nazione dei libri usciti dopo il 1970."),

    _t("Soci e prestiti", "Aggiungere i soci della biblioteca e la tabella dei prestiti.",
       ("Un prestito ha una data in cui è stato preso e una in cui è stato reso. Che valore dai a `reso_il` per un libro ancora fuori?",
        ["NULL: il dato non c'è ancora", "Una data finta come 9999-12-31", "La stessa data di preso_il", "Una stringa vuota"], 0,
        "NULL vuol dire «valore mancante». È il modo corretto per dire «non ancora reso»: le date finte si confondono con i dati veri e rovinano conti e medie."),
       [("end", "schema.sql",
         "\nCREATE TABLE soci (\n    id          INTEGER PRIMARY KEY,\n    nome        TEXT NOT NULL,\n    email       TEXT NOT NULL UNIQUE,\n    iscritto_il TEXT NOT NULL\n);",
         "Crea la tabella dei soci, con l'email che non si può ripetere.",
         "`UNIQUE` fa rifiutare al database una seconda iscrizione con la stessa email: la regola vale anche se il programma che inserisce i dati ha un bug."),
        ("end", "schema.sql",
         "\nCREATE TABLE prestiti (\n    id       INTEGER PRIMARY KEY,\n    libro_id INTEGER NOT NULL REFERENCES libri(id),\n    socio_id INTEGER NOT NULL REFERENCES soci(id),\n    preso_il TEXT NOT NULL,\n    reso_il  TEXT,\n    CHECK (reso_il IS NULL OR reso_il >= preso_il)\n);",
         "Crea i prestiti: quale libro, quale socio, quando è uscito e quando è tornato.",
         "È una tabella «ponte» tra libri e soci (molti-a-molti). Le date sono testo `AAAA-MM-GG`: in questo formato l'ordine alfabetico coincide con quello cronologico, quindi `>=` funziona."),
        ("end", "dati.sql",
         "\nINSERT INTO soci (id, nome, email, iscritto_il) VALUES\n    (1, 'Giulia Rossi', 'giulia@esempio.it', '2025-01-10'),\n    (2, 'Marco Bianchi', 'marco@esempio.it', '2025-03-02'),\n    (3, 'Sara Conti', 'sara@esempio.it', '2025-09-15'),\n    (4, 'Luca Ferri', 'luca@esempio.it', '2026-02-20'),\n    (5, 'Anna Greco', 'anna@esempio.it', '2026-06-01');",
         "Inserisce cinque soci.",
         "Anna non prenderà nessun libro: servirà più avanti per vedere cosa fa una LEFT JOIN."),
        ("end", "dati.sql",
         "\nINSERT INTO prestiti (id, libro_id, socio_id, preso_il, reso_il) VALUES\n    (1, 6, 1, '2026-01-05', '2026-01-25'),\n    (2, 1, 2, '2026-01-10', '2026-02-20'),\n    (3, 9, 1, '2026-02-01', '2026-02-15'),\n    (4, 6, 3, '2026-02-10', '2026-03-30'),\n    (5, 7, 2, '2026-03-01', '2026-03-20'),\n    (6, 11, 4, '2026-03-05', '2026-03-25'),\n    (7, 6, 2, '2026-04-02', '2026-04-28'),\n    (8, 2, 1, '2026-04-10', '2026-05-05'),\n    (9, 9, 3, '2026-05-01', '2026-06-20'),\n    (10, 4, 1, '2026-06-01', '2026-06-18'),\n    (11, 6, 4, '2026-09-01', NULL),\n    (12, 12, 1, '2026-09-10', NULL),\n    (13, 1, 3, '2026-09-20', NULL);",
         "Inserisce tredici prestiti: dieci chiusi e tre ancora aperti.",
         "Prima tutti i prestiti chiusi, poi quelli aperti: alla tappa 13 una regola impedirà di prestare un libro che è già fuori."),
        ("end", "query.sql",
         "\n-- Quanti prestiti, e quanti ancora aperti\nSELECT COUNT(*) AS prestiti, COUNT(reso_il) AS resi\nFROM prestiti;",
         "Conta tutti i prestiti e quelli con una data di restituzione.",
         "`COUNT(*)` conta le righe, `COUNT(colonna)` conta solo i valori non NULL: la differenza sono i prestiti aperti.")],
       "Prova a inserire un socio con un'email già usata, e un prestito con `reso_il` prima di `preso_il`: leggi gli errori."),

    _t("Chi ha cosa", "Unire tre tabelle per vedere quali libri sono fuori e chi li ha.",
       ("Per trovare i prestiti aperti scrivi `WHERE reso_il = NULL`. Cosa succede?",
        ["Non trova niente: con NULL si usa IS NULL", "Trova i prestiti aperti", "Dà errore di sintassi", "Trova tutti i prestiti"], 0,
        "NULL non è uguale a niente, nemmeno a NULL: `reso_il = NULL` non è mai vero. Per controllarlo si usano `IS NULL` e `IS NOT NULL`."),
       [("end", "query.sql",
         "\n-- I libri fuori adesso e chi li ha\nSELECT l.titolo, s.nome AS socio, p.preso_il\nFROM prestiti AS p\nJOIN libri AS l ON l.id = p.libro_id\nJOIN soci AS s ON s.id = p.socio_id\nWHERE p.reso_il IS NULL\nORDER BY p.preso_il;",
         "Parte dai prestiti, aggiunge libro e socio, tiene solo quelli non ancora resi.",
         "Si parte dalla tabella ponte (prestiti) e si aggiunge una JOIN per ogni tabella collegata. Ogni JOIN ha la sua condizione `ON`."),
        ("end", "query.sql",
         "\n-- Lo storico dei prestiti di Giulia\nSELECT l.titolo, p.preso_il, p.reso_il\nFROM prestiti AS p\nJOIN libri AS l ON l.id = p.libro_id\nJOIN soci AS s ON s.id = p.socio_id\nWHERE s.nome = 'Giulia Rossi'\nORDER BY p.preso_il;",
         "Tutti i prestiti di un socio, in ordine di data.",
         "Nel risultato il prestito ancora aperto mostra NULL in `reso_il`: è il dato mancante, non un errore.")],
       "Mostra i prestiti di «Cent'anni di solitudine» con il nome di chi l'ha preso."),

    _t("Contare con GROUP BY", "Raggruppare i prestiti per socio e per libro.",
       ("Vuoi solo i libri prestati almeno due volte. Dove va la condizione `COUNT(*) >= 2`?",
        ["In HAVING, dopo GROUP BY", "In WHERE, prima di GROUP BY", "In ORDER BY", "Nella SELECT"], 0,
        "`WHERE` filtra le righe prima di raggrupparle, quando i conteggi non esistono ancora. `HAVING` filtra i gruppi già formati, quindi può usare `COUNT`, `SUM`, `AVG`."),
       [("end", "query.sql",
         "\n-- Prestiti per socio, dal lettore più forte\nSELECT s.nome, COUNT(*) AS prestiti\nFROM prestiti AS p\nJOIN soci AS s ON s.id = p.socio_id\nGROUP BY s.id, s.nome\nORDER BY prestiti DESC, s.nome;",
         "Un gruppo per ogni socio, con il numero dei suoi prestiti.",
         "Si raggruppa per `s.id`, non solo per nome: due soci possono chiamarsi uguale. Ogni colonna della SELECT o è nel `GROUP BY` o è dentro una funzione come `COUNT`."),
        ("end", "query.sql",
         "\n-- I libri presi in prestito almeno due volte\nSELECT l.titolo, COUNT(*) AS volte\nFROM prestiti AS p\nJOIN libri AS l ON l.id = p.libro_id\nGROUP BY l.id, l.titolo\nHAVING COUNT(*) >= 2\nORDER BY volte DESC, l.titolo;",
         "Conta i prestiti di ogni libro e tiene solo i gruppi con almeno due.",
         "L'ordine logico è FROM, WHERE, GROUP BY, HAVING, SELECT, ORDER BY: per questo in `ORDER BY` puoi usare l'alias `volte`.")],
       "Conta i prestiti per genere (ti serve la tabella libri) e ordina dal genere più letto."),

    _t("Chi manca: la LEFT JOIN", "Trovare i libri mai prestati e contare anche quelli a zero.",
       ("Una JOIN normale tra libri e prestiti fa sparire i libri mai prestati. Perché?",
        ["Perché tiene solo le righe che trovano un partner nell'altra tabella", "Perché ordina male", "Perché i libri mai prestati hanno id NULL", "Perché serve un GROUP BY"], 0,
        "La `JOIN` (INNER) tiene solo le coppie che combaciano. La `LEFT JOIN` tiene tutte le righe della tabella di sinistra; dove non c'è un partner, le colonne dell'altra tabella valgono NULL."),
       [("end", "query.sql",
         "\n-- I libri mai prestati\nSELECT l.titolo\nFROM libri AS l\nLEFT JOIN prestiti AS p ON p.libro_id = l.id\nWHERE p.id IS NULL\nORDER BY l.titolo;",
         "Tiene tutti i libri e poi solo quelli senza nessun prestito collegato.",
         "Il trucco «LEFT JOIN + IS NULL»: le righe senza partner hanno NULL nelle colonne dei prestiti, e il `WHERE` tiene proprio quelle."),
        ("end", "query.sql",
         "\n-- Prestiti per libro, compresi quelli a zero\nSELECT l.titolo, COUNT(p.id) AS prestiti\nFROM libri AS l\nLEFT JOIN prestiti AS p ON p.libro_id = l.id\nGROUP BY l.id, l.titolo\nORDER BY prestiti DESC, l.titolo;",
         "Conta i prestiti di ogni libro, anche quando sono zero.",
         "Qui serve `COUNT(p.id)` e non `COUNT(*)`: un libro mai prestato ha comunque una riga (con NULL), e `COUNT(*)` la conterebbe come 1.")],
       "Trova i soci che non hanno mai preso un libro, con una LEFT JOIN."),

    _t("Date e durate", "Calcolare quanto è durato ogni prestito e trovare i ritardi.",
       ("Le date sono testo `AAAA-MM-GG`. Come calcoli i giorni tra preso_il e reso_il?",
        ["Converto le date in numeri con julianday() e le sottraggo", "Sottraggo direttamente i due testi", "Con LENGTH()", "Non si può fare in SQL"], 0,
        "`julianday()` trasforma una data nel numero di giorni da un'origine fissa: la differenza tra due date diventa una sottrazione. Sottrarre i testi darebbe un numero senza senso."),
       [("end", "query.sql",
         f"\n-- Quanto è durato ogni prestito chiuso\nSELECT l.titolo, p.preso_il, p.reso_il,\n       CAST({_CHIUSI} AS INTEGER) AS giorni\nFROM prestiti AS p\nJOIN libri AS l ON l.id = p.libro_id\nWHERE p.reso_il IS NOT NULL\nORDER BY giorni DESC, l.titolo;",
         "Per ogni prestito chiuso calcola i giorni tra uscita e rientro.",
         "`CAST(... AS INTEGER)` toglie la parte decimale. I prestiti aperti si escludono: con `reso_il` NULL anche il risultato del calcolo sarebbe NULL."),
        ("end", "query.sql",
         f"\n-- Restituiti in ritardo (il prestito dura 30 giorni)\nSELECT s.nome, l.titolo,\n       CAST({_CHIUSI} AS INTEGER) - 30 AS giorni_di_ritardo\nFROM prestiti AS p\nJOIN libri AS l ON l.id = p.libro_id\nJOIN soci AS s ON s.id = p.socio_id\nWHERE {_CHIUSI} > 30\nORDER BY giorni_di_ritardo DESC;",
         "Trova i prestiti tenuti più di 30 giorni e di quanto hanno sforato.",
         "Il calcolo si ripete nel `WHERE` perché il `WHERE` viene valutato prima della SELECT e non vede ancora l'alias `giorni_di_ritardo`.")],
       "Calcola la durata media dei prestiti chiusi di ogni socio, arrotondata con ROUND."),

    _t("Sottoquery", "Usare una query dentro un'altra: confronti con la media ed EXISTS.",
       ("Vuoi i soci che hanno preso più libri della media. Perché non basta `HAVING COUNT(*) > AVG(COUNT(*))`?",
        ["Non si possono annidare due funzioni di gruppo: la media va calcolata in una sottoquery", "Funziona, va bene così", "Perché AVG non esiste in SQLite", "Perché manca ORDER BY"], 0,
        "Prima va calcolato quanti prestiti ha ogni socio, poi la media di quei numeri: sono due passaggi, quindi due query, una dentro l'altra."),
       [("end", "query.sql",
         "\n-- I soci che hanno preso più libri della media\nSELECT s.nome, COUNT(*) AS prestiti\nFROM prestiti AS p\nJOIN soci AS s ON s.id = p.socio_id\nGROUP BY s.id, s.nome\nHAVING COUNT(*) > (\n    SELECT AVG(n) FROM (\n        SELECT COUNT(*) AS n FROM prestiti GROUP BY socio_id\n    )\n)\nORDER BY prestiti DESC;",
         "Confronta i prestiti di ogni socio con la media calcolata in una sottoquery.",
         "Si legge dall'interno: la query più interna conta i prestiti per socio, quella in mezzo ne fa la media, quella esterna tiene chi sta sopra."),
        ("end", "query.sql",
         "\n-- I soci che non hanno mai preso un libro di Calvino\nSELECT s.nome\nFROM soci AS s\nWHERE NOT EXISTS (\n    SELECT 1\n    FROM prestiti AS p\n    JOIN libri AS l ON l.id = p.libro_id\n    JOIN autori AS a ON a.id = l.autore_id\n    WHERE p.socio_id = s.id AND a.nome = 'Italo Calvino'\n)\nORDER BY s.nome;",
         "Per ogni socio controlla che non esista nessun suo prestito di Calvino.",
         "È una sottoquery correlata: usa `s.id` della query esterna, quindi viene valutata per ogni socio. `EXISTS` si ferma alla prima riga trovata, per questo basta `SELECT 1`.")],
       "Trova i libri che hanno avuto più prestiti della media dei libri prestati."),

    _t("Una vista", "Salvare una query usata spesso come vista e interrogarla come una tabella.",
       ("La query «prestiti aperti con titolo e socio» ti serve in molti punti. Cosa conviene fare?",
        ["Crearne una vista e usarla come una tabella", "Copiarla ogni volta", "Creare una nuova tabella con quei dati", "Metterla in un commento"], 0,
        "Una vista è una query con un nome. Non copia i dati: ogni volta che la interroghi rilegge le tabelle, quindi è sempre aggiornata."),
       [("new", "viste.sql",
         "-- Viste: query salvate con un nome\nCREATE VIEW prestiti_aperti AS\nSELECT p.id, l.titolo, s.nome AS socio, p.preso_il\nFROM prestiti AS p\nJOIN libri AS l ON l.id = p.libro_id\nJOIN soci AS s ON s.id = p.socio_id\nWHERE p.reso_il IS NULL;",
         "Crea la vista dei prestiti aperti.",
         "Il file `viste.sql` viene eseguito dopo lo schema e i dati: la vista si appoggia alle tabelle, che devono già esistere."),
        ("end", "query.sql",
         "\n-- La vista si interroga come una tabella\nSELECT titolo, socio FROM prestiti_aperti ORDER BY preso_il;",
         "Legge la vista con una SELECT normale.",
         "Chi usa la vista non deve sapere come è fatta dentro: le tre JOIN sono nascoste dietro un nome.")],
       "Crea una vista `libri_con_autore` (titolo, anno, autore) e usala in una query."),

    _t("Classifiche: CTE e funzioni finestra", "Fare la classifica dei libri più prestati dentro ogni genere.",
       ("Vuoi il «posto in classifica» di ogni libro dentro il suo genere, senza perdere le righe dei singoli libri. Cosa usi?",
        ["Una funzione finestra: RANK() OVER (PARTITION BY genere ...)", "GROUP BY genere", "Una sottoquery per genere", "ORDER BY genere"], 0,
        "`GROUP BY` schiaccia le righe in una per gruppo. Una funzione finestra calcola un valore guardando le righe del gruppo, ma lascia ogni riga al suo posto."),
       [("end", "query.sql",
         "\n-- Classifica dei libri più prestati dentro ogni genere\nWITH conteggi AS (\n    SELECT l.genere, l.titolo, COUNT(p.id) AS prestiti\n    FROM libri AS l\n    LEFT JOIN prestiti AS p ON p.libro_id = l.id\n    GROUP BY l.id, l.genere, l.titolo\n)\nSELECT genere, titolo, prestiti,\n       RANK() OVER (PARTITION BY genere ORDER BY prestiti DESC) AS posto\nFROM conteggi\nORDER BY genere, posto, titolo;",
         "Prima conta i prestiti per libro (nella CTE), poi assegna il posto dentro ogni genere.",
         "`WITH` dà un nome a un risultato intermedio, come una vista che vive solo in questa query. `RANK` dà lo stesso posto ai pari merito e poi salta: 1, 1, 3."),
        ("end", "query.sql",
         "\n-- Il libro più prestato di ogni genere\nWITH conteggi AS (\n    SELECT l.genere, l.titolo, COUNT(p.id) AS prestiti\n    FROM libri AS l\n    LEFT JOIN prestiti AS p ON p.libro_id = l.id\n    GROUP BY l.id, l.genere, l.titolo\n),\nclassifica AS (\n    SELECT genere, titolo, prestiti,\n           RANK() OVER (PARTITION BY genere ORDER BY prestiti DESC) AS posto\n    FROM conteggi\n)\nSELECT genere, titolo, prestiti\nFROM classifica\nWHERE posto = 1 AND prestiti > 0\nORDER BY genere, titolo;",
         "Riusa la classifica e tiene solo i primi di ogni genere.",
         "Una funzione finestra non si può usare nel `WHERE` della stessa query: per filtrare sul posto serve un passaggio in più, qui la seconda CTE.")],
       "Sostituisci RANK con ROW_NUMBER e poi con DENSE_RANK: cosa cambia con i pari merito?"),

    _t("Regole nel database: trigger e transazioni", "Impedire di prestare un libro già fuori e registrare una restituzione in modo sicuro.",
       ("La regola «un libro già in prestito non si presta di nuovo» dove la metti perché valga sempre?",
        ["In un trigger nel database, che rifiuta l'inserimento", "Solo nel programma che usa il database", "In una vista", "In un commento nello schema"], 0,
        "Una regola scritta nel database vale per chiunque scriva i dati: l'app, uno script, tu a mano. Nel programma si può dimenticare."),
       [("end", "schema.sql",
         "\n-- Un libro già fuori non si può prestare di nuovo\nCREATE TRIGGER libro_gia_in_prestito\nBEFORE INSERT ON prestiti\nWHEN EXISTS (\n    SELECT 1 FROM prestiti\n    WHERE libro_id = NEW.libro_id AND reso_il IS NULL\n)\nBEGIN\n    SELECT RAISE(ABORT, 'Il libro è già in prestito');\nEND;",
         "Prima di ogni nuovo prestito controlla che lo stesso libro non sia ancora fuori; se lo è, blocca l'inserimento.",
         "`NEW` è la riga che si sta inserendo. `RAISE(ABORT, ...)` annulla l'istruzione con un messaggio d'errore leggibile."),
        ("end", "schema.sql",
         "\nCREATE INDEX idx_prestiti_libro ON prestiti(libro_id);",
         "Crea un indice sui prestiti per libro.",
         "Il trigger e molte query cercano i prestiti di un libro: con l'indice il database va dritto alle righe giuste invece di leggere tutta la tabella."),
        ("end", "query.sql",
         "\n-- Luca restituisce il libro e Anna lo prende: o tutte e due le cose o nessuna\nBEGIN;\nUPDATE prestiti SET reso_il = '2026-10-01' WHERE id = 11;\nINSERT INTO prestiti (libro_id, socio_id, preso_il) VALUES (6, 5, '2026-10-02');\nCOMMIT;",
         "Chiude un prestito e ne apre uno nuovo dentro una transazione.",
         "Se una delle due istruzioni fallisse, con `ROLLBACK` si tornerebbe allo stato di prima: niente libri «a metà». L'INSERT passa il trigger perché l'UPDATE ha appena chiuso il prestito."),
        ("end", "query.sql",
         "\n-- Adesso il libro è di Anna\nSELECT titolo, socio, preso_il FROM prestiti_aperti ORDER BY preso_il;",
         "Rilegge la vista dei prestiti aperti dopo la transazione.",
         "La vista è già aggiornata: non contiene dati suoi, rilegge le tabelle.")],
       "In fondo a query.sql prova a prestare «I reietti dell'altro pianeta» (id 12), che è ancora fuori: leggi l'errore del trigger, poi togli la riga."),
]

PROJECTS["biblioteca"] = {
    "title": "Database biblioteca", "lang": "sql", "kind": "sql", "folder": "biblioteca-sql", "main": "schema.sql", "requires": [],
    "order": ["schema.sql", "dati.sql", "viste.sql", "query.sql"], "db": "biblioteca.db",
    "desc": "Un database SQLite vero: autori, libri, soci e prestiti. 13 tappe, dal CREATE TABLE a JOIN, GROUP BY, sottoquery, viste, funzioni finestra, trigger e transazioni.",
    "steps": BIBLIOTECA}


def apply_op(files, op):
    """Applica una modifica e restituisce (file, posizione per il contesto)."""
    kind, name = op[0], op[1]
    if kind == "new":
        files[name] = op[2] + "\n"
        return
    text = files[name]
    if kind == "end":
        files[name] = text.rstrip("\n") + "\n" + op[2].rstrip("\n") + "\n"
    elif kind == "after":
        lines = text.split("\n")
        idx = [i for i, ln in enumerate(lines) if ln == op[2]]
        if len(idx) != 1:
            raise ValueError(f"{name}: la riga «{op[2]}» compare {len(idx)} volte")
        lines[idx[0] + 1:idx[0] + 1] = op[3].split("\n")
        files[name] = "\n".join(lines)
    elif kind == "replace":
        if text.count(op[2]) != 1:
            raise ValueError(f"{name}: il testo da sostituire compare {text.count(op[2])} volte: {op[2][:60]}")
        files[name] = text.replace(op[2], op[3])
    else:
        raise ValueError("modifica sconosciuta: " + kind)


def op_lang(name):
    return {"py": "python", "java": "java", "sql": "sql"}.get(name.rsplit(".", 1)[-1], "plain")


def op_view(files, op):
    """Descrive una modifica per il ricalco: file, dove, contesto prima, righe tolte, codice nuovo, cosa fa, perché."""
    v = _op_view(files, op)
    v["lang"] = op_lang(v["file"])
    return v


def _op_view(files, op):
    kind, name = op[0], op[1]
    if kind in ("new", "end"):
        code, what, why = op[2], op[3], op[4]
        code = code.lstrip("\n")
        before = files.get(name, "").rstrip("\n").split("\n")[-4:] if kind == "end" else []
        where = "nuovo file" if kind == "new" else "in fondo al file"
        return {"file": name, "kind": kind, "where": where, "before": before, "removed": [], "code": code, "what": what, "why": why}
    if kind == "after":
        lines = files[name].split("\n")
        i = lines.index(op[2])
        return {"file": name, "kind": kind, "where": f"dopo la riga «{op[2].strip()}»", "before": lines[max(0, i - 3):i + 1],
                "removed": [], "code": op[3].lstrip("\n"), "what": op[4], "why": op[5]}
    text = files[name]
    pos = text.index(op[2])
    before = text[:pos].rstrip("\n").split("\n")[-3:]
    return {"file": name, "kind": kind, "where": "al posto di queste righe", "before": before, "removed": op[2].split("\n"),
            "code": op[3], "what": op[4], "why": op[5]}


def snapshot(pid, upto):
    """I file del progetto dopo le prime `upto` tappe."""
    files = {}
    for step in PROJECTS[pid]["steps"][:upto]:
        for op in step["ops"]:
            apply_op(files, op)
    return files


def step_view(pid, k):
    """La tappa k (0-based) con le modifiche pronte per il ricalco."""
    files = snapshot(pid, k)
    step = PROJECTS[pid]["steps"][k]
    ops = []
    for op in step["ops"]:
        ops.append(op_view(files, op))
        apply_op(files, op)
    return dict({kk: v for kk, v in step.items() if kk != "ops"}, n=k + 1, ops=ops, files=files)
