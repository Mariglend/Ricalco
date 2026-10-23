#!/usr/bin/env sh
# Avvia Ricalco su macOS e Linux.
cd "$(dirname "$0")" || exit 1
if command -v python3 >/dev/null 2>&1; then
    exec python3 server.py
elif command -v python >/dev/null 2>&1; then
    exec python server.py
else
    echo "Python non trovato: installalo da https://www.python.org/downloads/"
    exit 1
fi
