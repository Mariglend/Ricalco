# Contribuire a Ricalco

**Italiano** · [English](#contributing-to-ricalco)

Grazie se vuoi dare una mano. Ricalco è un progetto personale, quindi le risposte possono arrivare con qualche giorno di ritardo.

## Segnalare un problema

Apri una issue con il modello **Bug** e scrivi:

- cosa stavi facendo (sezione, linguaggio, livello);
- cosa ti aspettavi e cosa è successo;
- sistema operativo, versione di Python, Java (se c'entra) e modello di Ollama;
- il messaggio d'errore della finestra di avvio, se c'è.

Il diario d'uso (`data/logs/`) può aiutare, ma **controllalo prima di allegarlo**: contiene le tue risposte e il codice che hai scritto.

## Proporre un'idea

Apri una issue con il modello **Idea**. Spiega il problema che risolve per chi studia, prima della soluzione.

## Modificare il codice

1. Fai un fork e crea un ramo (`git checkout -b nome-della-modifica`).
2. Avvia l'app con `python server.py` e prova la modifica nel browser, con un modello vero o piccolo (`qwen3:8b` va bene).
3. Apri una pull request che spieghi cosa cambia e come l'hai provata.

Alcune regole del progetto:

- **Solo libreria standard** nel server: niente dipendenze da installare con `pip`.
- **Niente build** nel frontend: JavaScript semplice, un file per sezione in `static/js/`, caricati in ordine da `index.html`. I file condividono le variabili globali.
- **Nomi e commenti in italiano**, come il resto del codice.
- **Testi in due lingue.** Le pagine si scrivono in italiano. Se aggiungi un testo all'interfaccia, aggiungi la traduzione in `static/i18n/en.js` (i `{}` stanno al posto dei valori, nello stesso numero). I prompt per il modello restano in italiano: quando la lingua è l'inglese, `ricalco/llm.py` chiede al modello di rispondere in inglese.
- **Gli esercizi si verificano eseguendoli.** Se aggiungi un tipo di esercizio, il codice del modello va eseguito prima di mostrarlo.
- Per lo stile Python segui quello che trovi (righe fino a circa 130 caratteri).

## Struttura

La mappa dei moduli è nel [README](README.md#comè-fatto).

---

# Contributing to Ricalco

[Italiano](#contribuire-a-ricalco) · **English**

Thanks for wanting to help. Ricalco is a personal project, so replies may take a few days.

## Reporting a problem

Open an issue with the **Bug** template and include:

- what you were doing (section, language, level);
- what you expected and what happened;
- operating system, Python version, Java (if relevant) and the Ollama model;
- the error message from the startup window, if any.

The usage journal (`data/logs/`) can help, but **check it before attaching it**: it contains your answers and the code you wrote.

## Suggesting an idea

Open an issue with the **Idea** template. Describe the problem it solves for a learner before the solution.

## Changing the code

1. Fork the repository and create a branch (`git checkout -b change-name`).
2. Start the app with `python server.py` and try your change in the browser, with a real model or a small one (`qwen3:8b` is fine).
3. Open a pull request that explains what changes and how you tested it.

Project rules:

- **Standard library only** on the server: no dependencies to install with `pip`.
- **No build step** on the frontend: plain JavaScript, one file per section in `static/js/`, loaded in order by `index.html`. The files share global variables.
- **Names and comments in Italian**, like the rest of the code.
- **Text in two languages.** Pages are written in Italian. If you add text to the interface, add its translation to `static/i18n/en.js` (`{}` stands for values, same count). Prompts for the model stay in Italian: when the language is English, `ricalco/llm.py` asks the model to answer in English.
- **Exercises are checked by running them.** If you add an exercise type, the model's code must run before it is shown.
- For Python style, follow what's already there (lines up to about 130 characters).

## Structure

The module map is in the [README](README.en.md#how-its-built).
