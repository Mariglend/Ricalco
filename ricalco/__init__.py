"""Ricalco: impara a programmare riscrivendo il codice, con un modello locale via Ollama.

Il pacchetto è diviso per aree:
  config          percorsi dei dati, salvataggio, log, priorità delle richieste
  llm             client di Ollama
  esecuzione      esecuzione di Python, Java e SQL, test, scelta del JDK
  generazione     lezioni ed esercizi generati e verificati
  generazione_sql esercizi SQL
  percorsi        archivio esercizi, progressi, sessioni, lavoro in sottofondo
  lezioni         lezioni delle unità (coda, rigenerazione)
  oggi            la pagina «Oggi»: Elo, ripasso, varianti, prova settimanale
  progressi       vista del percorso, teoria, risultati, riepilogo della home
  progetti        progetti a tappe
  colloquio       logica, colloquio, simulazione
  flashcard       ripetizione dilazionata
  feynman         spiegalo a un principiante
  diario          riassunto dei log
  diagnostica     «Prova il modello»
  web             server HTTP e avvio
I moduli dati (curriculum, quick, projects) contengono solo contenuti; spring_runner e sql_runner eseguono Spring e SQL.
"""
