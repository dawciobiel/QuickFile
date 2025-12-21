#!/usr/bin/env bash

# python -m venv .venv
# source .venv/bin/activate
# pip install pyinstaller

pyinstaller --onefile --name Quickfile main.py
