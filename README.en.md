# Ricalco

[Italiano](README.md) · **English**

**Learn to code by rewriting code, not by copying it.**

Ricalco is a local web app for learning Python, Java and SQL and preparing for technical interviews. It uses the tracing method: first you think about how to solve the problem, then you rewrite the solution block by block with less and less help, until you can write it from memory or on your own.

Lessons, exercises and feedback are prepared by a language model **running on your own PC** through [Ollama]. No account, no API key, and no data leaves your computer. Your code and the model's code are **actually run**: an exercise that doesn't work never reaches you.

The app was born in Italian and also works in English: switch with the **IT / EN** selector at the top (see [Language](#language-italian-or-english)).

![Today: the day's plan and an exercise at level 2 "Structure"](docs/oggi.png)

## Contents

- [What's inside](#whats-inside)
- [Installation](#installation)
- [First run](#first-run)
- [How to use it](#how-to-use-it)
- [Choosing the model](#choosing-the-model)
- [Java and Spring Boot](#java-and-spring-boot)
- [Your data](#your-data)
- [Options](#options)
- [Common problems](#common-problems)
- [Language: Italian or English](#language-italian-or-english)
- [How it's built](#how-its-built)
- [Contributing and license](#contributing-and-license)

## What's inside

| Section | What you do |
|---|---|
| **Today** | One exercise at a time, chosen for your level (Elo-style rating). You think about the method, then rewrite the solution at 4 help levels: Trace, Structure, Memory, Write it yourself. Topics follow the path, unit after unit, as algorithms. |
| **Paths** | Python (24 units, up to FastAPI and SQLAlchemy), Java (33 units, up to Spring Boot, Spring Security and Spring AI), SQL (17 units), Algorithms and data structures (30 units, in Python or Java). |
| **Projects** | Real programs built step by step: a pygame game, a Spring Boot REST API, a Spring MVC web app with Thymeleaf, a SQLite database. The files go into a folder you open with your editor. |
| **Algorithms** | A catalog of 150+ interview problems in Python and Java, grouped by pattern (two pointers, sliding window, graphs, dynamic programming…), hand-written and verified. |
| **Logic** | Reasoning puzzles, algorithms and queries, checked by running code. |
| **Flashcards** | Spaced repetition (Leitner system). Before flipping the card you can explain the answer in words and Qwen grades it. |
| **Interview** | Chained questions (the interviewer digs until they find your limit), junior system design, code review, behavioral questions with the STAR method, live coding with a timer, and a full mock interview with a scorecard, in Italian or English. |
| **Journal** | A summary of how you study: time, scores, reasoning mistakes, hardest blocks, model speed. |

A few ideas it is built on:

- **Reasoning first, then code.** Every exercise starts with a question about the method. In the journal, reasoning mistakes are kept apart from typing mistakes.
- **Help that fades.** 1 Trace (the code shown faintly underneath), 2 Structure (only keywords and punctuation), 3 Memory (no code), 4 Write it yourself (write the program your way; Ricalco runs it and Qwen reviews it). Once you start, you can't go back to peek.
- **Explain it to a beginner.** After each piece of code you explain the solution in your own words (Feynman method). A simulated "beginner" asks you about the vague parts.
- **Review.** Past exercises come back as flashcards after hours or days, depending on how they went.
- **Real checking.** Every generated exercise is run: with tests (Python, Java), on SQLite (SQL) or with Maven and JUnit (Spring). If it doesn't pass, the model has to redo it.

| | |
|---|---|
| ![The algorithm catalog, grouped by pattern](docs/algoritmi.png) | ![Level 4 "Write it yourself" with Qwen's review](docs/scrivi-tu.png) |
| ![Interview: chained questions by area and level](docs/colloquio.png) | ![Interview: code review](docs/review.png) |
| ![The Java path](docs/percorso.png) | ![Step-by-step projects](docs/progetti.png) |

The screenshots show the Italian interface.

## Installation

You need three things:

| What | Why | Required? |
|---|---|---|
| **Python 3.10 or newer** | Runs the app. Standard library only: no `pip install`. | Yes |
| **[Ollama]** with a model | Writes lessons and exercises, acts as tutor and interviewer. | Yes |
| **JDK 17 or newer** | Runs the Java exercises. | Only for Java |

### Windows

In PowerShell:

```powershell
winget install -e --id Python.Python.3.12
winget install -e --id Ollama.Ollama
winget install -e --id EclipseAdoptium.Temurin.21.JDK   # only for Java
```

Close and reopen PowerShell, then download the model:

```powershell
ollama pull qwen3:14b
```

Without `winget` you can install them by hand from [python.org](https://www.python.org/downloads/) (tick "Add python.exe to PATH"), [ollama.com](https://ollama.com/download) and [adoptium.net](https://adoptium.net/) (tick "Set JAVA_HOME").

### macOS

With [Homebrew](https://brew.sh/):

```sh
brew install python ollama
brew install --cask temurin            # only for Java
ollama serve &                         # if Ollama isn't already running
ollama pull qwen3:14b
```

### Linux

```sh
sudo apt install python3 openjdk-21-jdk     # or your distribution's equivalent
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen3:14b
```

### Getting Ricalco

```sh
git clone https://github.com/Mariglend/Ricalco.git
cd Ricalco
```

Or download the zip from GitHub's **Code → Download ZIP** button and extract it.

### Optional packages

Only needed for Python units 21-24 (FastAPI, SQLAlchemy) and for the pygame project:

```sh
python -m pip install --upgrade fastapi httpx sqlalchemy pygame
```

On Windows you can just double-click `installa_extra.bat`.

## First run

- **Windows:** double-click `avvia.bat`
- **macOS / Linux:** `./avvia.sh`
- **From a terminal, anywhere:** `python server.py` (or `python3 server.py`)

The browser opens at <http://127.0.0.1:8765>. The terminal window shows which model, Python and Java are in use. To close Ricalco, close that window or press `Ctrl+C`.

On first run:

1. Click **EN** at the top if you want the app in English.
2. At the top right, check that the dot is green and the right model is selected.
3. Open **Test the model**: Ricalco generates and checks one exercise per section and tells you whether the model is good enough.
4. If you want Spring exercises to really run, press **Prepare Spring** (see [Java and Spring Boot](#java-and-spring-boot)).
5. Go back to **Today**, pick a language and start.

## How to use it

**Today** is the main page. An exercise works like this:

1. **Think.** Read the problem and write how you'd solve it, or pick one of four methods. Qwen grades the plan.
2. **Write.** Rewrite the solution block by block. Above the sheet you see what the block does; when you finish it, you see why it's written that way. At level 4 you write everything yourself.
3. **Score.** The plan counts 40% and the code 60%: level, accuracy and the words you asked to see. Your Elo rating goes up when you do well on exercises at your level, and difficulty and topics go up with it.
4. **After.** A from-scratch variant, "Predict and run", and explaining it to a beginner. The exercise will come back later as a flashcard.

The top bar has two handy things:

- **Note:** write in one line what's blocking you or what you'd improve. It goes into the journal.
- **Tutor:** the panel on the right. It knows what you're looking at and guides you without giving away the solution. You can select some code and press **What does it do?**.

The full guide to every section is in [LEGGIMI.md](LEGGIMI.md) (Italian).

## Choosing the model

Ricalco works with any model installed in Ollama: pick it from the menu at the top right.

| Model | Video memory | Notes |
|---|---|---|
| `qwen3:14b` | ~10-12 GB | Recommended: follows the answer format well, good in Italian and English. |
| `qwen3:8b` | ~6-8 GB | For less powerful PCs. |
| `gemma3:12b` | ~9-10 GB | A good alternative. |
| `llama3.1:8b` | ~6 GB | Works, especially in English; more attempts needed. |

Even with a smaller model the exercises stay correct, because Ricalco runs them before showing them to you. Only the number of attempts changes, that is, how long you wait.

**More speed.** With a GPU of 12 GB or less, turn on flash attention and the compressed cache in Ollama: they use less video memory and keep the whole model on the GPU. On Windows, in PowerShell, then restart Ollama:

```powershell
setx OLLAMA_FLASH_ATTENTION 1
setx OLLAMA_KV_CACHE_TYPE q8_0
```

On macOS and Linux export the same variables before `ollama serve`. `ollama ps` shows whether the model is "100% GPU".

## Java and Spring Boot

- **Java exercises:** Ricalco finds the newest JDK by itself (JAVA_HOME, PATH and the usual install folders, including JDKs downloaded by IntelliJ). It skips old Java 8 installs and JREs without a compiler. The startup window shows which one it picked.
- **Spring Boot, Spring Security, Spring AI:** in **Test the model → Prepare Spring** Ricalco downloads Maven (if missing) and the libraries, once (a few hundred MB). From then on Spring exercises and projects are compiled and run with Maven and JUnit on your PC. Spring AI tests use a fake model, so no API key is needed.
- **Versions:** Spring Boot 3.5, Spring AI 1.0, Java 17 as the minimum code level.

## Your data

Everything stays in the app folder:

| Folder | Contents |
|---|---|
| `data/` | Progress, ratings, generated lessons and exercises, flashcards, mock interviews, usage logs (`data/logs/`), Maven and the Spring libraries. Content generated in English lives in `data/en/`. |
| `progetti/` | The step-by-step projects. |

To move Ricalco to another PC, copy `data/` too. `data/` is excluded from git (`.gitignore`), so your progress and logs never end up on GitHub. `progetti/` is included: the code you built step by step goes into the repository. Only files generated when you run it are left out (Maven's `target/`, `biblioteca.db`, `avvio.log`).

**Security.** The server listens only on `127.0.0.1` and only accepts requests from its own page. Code runs on your PC in a temporary folder, with a time limit, but **without sandboxing**: it's like running it yourself from a terminal.

## Options

Environment variables:

| Variable | Default | What it does |
|---|---|---|
| `RICALCO_OLLAMA` | `http://127.0.0.1:11434` | Ollama address |
| `RICALCO_PORT` | `8765` | App port (if busy, tries the next 9) |
| `RICALCO_MODEL` | the first Qwen installed | Model to use at startup |
| `RICALCO_CTX` | `6144` | Model context, in tokens |

## Common problems

| Symptom | Cause and fix |
|---|---|
| Red dot, "Ollama is not responding" | Ollama is off: start it (`ollama serve`, or from the tray icon). Check the model is there with `ollama list`. |
| "Could not find or load main class Main.java" | Java 8 is being used. Install JDK 17+ and restart Ricalco. |
| "No compiler is provided… JRE rather than a JDK" (Maven) | Only a JRE is installed. Install a JDK (for example Temurin 21) and restart. |
| Java or Spring exercises often fail to generate | The model writes broken code: Ricalco discards it and retries. A bigger model makes this rarer. |
| A lesson shows "the program did not run successfully" | Press **Have Qwen rewrite the lesson**, or **↻ Rebuild the unit** in the path. |
| The page doesn't open | Check the startup window for the port: if 8765 is busy it uses another one. |

## Language: Italian or English

Ricalco was born in Italian and also works in English. The **IT / EN** selector is in the top bar. In English:

- the interface, path units, projects and ready-made exercises are translated;
- Qwen writes lessons, exercises, feedback and tutor answers in English;
- lessons and exercises generated in English live in `data/en/`, separate from the Italian ones, so switching language loses nothing.

Progress, rating, flashcards and journal are shared between the two languages. Translations are in `static/i18n/en.js`: to fix one, just change the text on the right.

## How it's built

```
server.py              launcher: checks the Python version and starts the server
ricalco/               the server (standard library only), split into modules:
  config.py            data paths, configuration, usage log, request priority
  llm.py               Ollama client (JSON answers with a schema, and streaming)
  esecuzione.py        runs Python and Java with tests, picks the JDK
  generazione*.py      lessons and exercises generated and checked by running them
  percorsi.py          exercise store, progress, background work
  lezioni.py           unit lessons, priority queue
  oggi.py              "Today": Elo rating, levels, review, weekly test
  progetti.py, colloquio.py, flashcard.py, feynman.py, diario.py, diagnostica.py
  catalogo.py          catalog of interview algorithms
  approfondimenti.py   chained questions, system design, code review, behavioral questions
  dati/                hand-written content: algorithms and interview (JSON)
  i18n.py              English translation of API answers
  web.py               HTTP server: API and static files
  curriculum.py        paths, units, starter exercises
  quick.py             ready-made "Today" exercises, levels, patterns
  projects.py          step-by-step projects
  spring_runner.py     Spring Boot and JUnit with Maven
  sql_runner.py        SQL on SQLite, in a subprocess
static/                the interface (JavaScript with no framework and no build)
  index.html, app.css
  js/                  one file per section, loaded in order (00-i18n.js … 99-avvio.js)
  i18n/en.js           English translations
LEGGIMI.md             the full guide (Italian)
```

Module and function names are in Italian, like the rest of the code.

- **Frontend:** a vanilla JavaScript single page, nothing to download.
- **Backend:** the standard library's `ThreadingHTTPServer`. The model is called through Ollama's `/api/chat` with structured answers (JSON schema).
- **Background work:** a worker prepares lessons and exercises while you study and pauses when you ask for something, so your requests come first.
- **Running code:**
  - Python in a subprocess isolated from `site-packages` (`-I`);
  - Java with the single-file source launcher;
  - SQL on in-memory SQLite;
  - Spring with `mvn test` on a template project.

## Contributing and license

Bug reports and ideas are welcome: read [CONTRIBUTING.md](CONTRIBUTING.md) and open an issue with the right template (bug or idea).

Ricalco is released under the [MIT](LICENSE) license.

[Ollama]: https://ollama.com
