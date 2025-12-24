#!/usr/bin/env bash

# TODO
# Need to be added do binary file:
# `themes/`,
# `translations`,
# `README.md`
# `docs/about/*`,
# `docs/BUGS.md`
# `docs/TODO.md` or `docs/TODO.PL.md`

cd ..

# python -m venv .venv
echo "🧪 Activating the virtual environment..."
source .venv/bin/activate
# source .venv/bin/activate.fish
# pip install pyinstaller

pyinstaller --onefile --name Quickfile main.py
