#!/usr/bin/env python3
"""Ricalco: impara a programmare riscrivendo il codice, con un modello locale via Ollama.

Solo libreria standard: nessun pip install.
Avvio:  python server.py          (apre il browser su http://127.0.0.1:8765)
Opzioni (variabili d'ambiente):
  RICALCO_OLLAMA  indirizzo di Ollama   (predefinito http://127.0.0.1:11434)
  RICALCO_PORT    porta dell'app        (predefinita 8765)
  RICALCO_MODEL   modello da usare      (predefinito: il primo "qwen" installato)
  RICALCO_CTX     contesto del modello  (predefinito 6144 token)
Il codice è nel pacchetto ricalco/.
"""
import sys

if sys.version_info < (3, 9):
    sys.exit("Ricalco richiede Python 3.9 o più recente.")

from ricalco.web import main  # noqa: E402

if __name__ == "__main__":
    main()
