# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Every string on the plugin management page has a translation.

The page is built from Python, so its keys live in ``translation_manager``
calls rather than in a ``.ui`` file. ``en_US.json`` is the source language and
must map each key to the exact English text; ``pl_PL.json`` must provide a
non-empty translation. Both language files always share the same key set.

Specification: ``docs/architecture/plugins/plugins.md``
("Zarządzanie wtyczkami zewnętrznymi").
"""

import ast
import json
import os

from utils import plugin_management_page

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
PAGE_PATH = os.path.join(PROJECT_ROOT, "utils", "plugin_management_page.py")
TRANSLATIONS_DIR = os.path.join(PROJECT_ROOT, "resources", "translations")
LANGUAGES = ("en_US.json", "pl_PL.json")
CONTEXT = "PluginManagement"


def load_translations(name):
    with open(os.path.join(TRANSLATIONS_DIR, name), encoding="utf-8") as handle:
        return json.load(handle)


def literal_calls(path):
    """Return ``(context, text)`` for translate calls with literal arguments."""
    with open(path, encoding="utf-8") as handle:
        tree = ast.parse(handle.read(), filename=path)

    calls = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "translate" or len(node.args) < 2:
            continue
        context, text = node.args[0], node.args[1]
        if isinstance(context, ast.Constant) and isinstance(text, ast.Constant):
            if isinstance(context.value, str) and isinstance(text.value, str):
                calls.add((context.value, text.value))
    return calls


def page_calls():
    calls = literal_calls(PAGE_PATH)
    calls.update(
        (CONTEXT, label) for label in plugin_management_page.STATUS_LABELS.values()
    )
    return calls


def test_every_plugin_management_string_is_translated():
    calls = page_calls()
    assert calls

    for language in LANGUAGES:
        translations = load_translations(language)
        missing = sorted(
            f"{context}.{text}"
            for context, text in calls
            if not translations.get(f"{context}.{text}")
        )
        assert missing == [], f"{language} is missing {missing}"


def test_english_translations_match_the_source_strings():
    translations = load_translations("en_US.json")

    wrong = sorted(
        f"{context}.{text}"
        for context, text in page_calls()
        if translations.get(f"{context}.{text}") != text
    )

    assert wrong == []


def test_the_settings_tab_title_is_translated():
    for language in LANGUAGES:
        translations = load_translations(language)
        assert translations.get("SettingsDialog.Plugins")


def test_both_language_files_share_the_same_keys():
    english = set(load_translations("en_US.json"))
    polish = set(load_translations("pl_PL.json"))

    assert english - polish == set()
    assert polish - english == set()
