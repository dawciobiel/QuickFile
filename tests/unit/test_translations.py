# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Every string the application asks for is translated.

The application looks strings up as ``Context.Text`` in flat JSON files under
``resources/translations/``. This test parses literal ``translate(...)`` calls
in the source tree, adds the strings built at runtime (status labels and task
names), reads the texts that Qt Designer stored in ``ui/*.ui``, and checks that
both language files cover them.

Strings assembled from variables or formatted with runtime values cannot be
checked here; they must be listed explicitly by the code that builds them.

Specification: ``docs/developer_guide/translation.md``.
"""

import ast
import json
import os
import re
import xml.etree.ElementTree as ET

import pytest
from PyQt6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QWidget,
)

from app.enums import TaskType
from app.translation_manager import translation_manager
from app.ui_translation import translate_widgets
from utils.plugin_management_page import STATUS_LABELS

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
TRANSLATIONS_DIR = os.path.join(PROJECT_ROOT, "resources", "translations")
SOURCE_ROOTS = (
    "app",
    "ui",
    "utils",
    "browser",
    "panels",
    "plugins",
    "plugins-external",
)
LANGUAGES = ("en_US.json", "pl_PL.json")
SKIPPED_DIRECTORIES = {"__pycache__", "tests", "experiments"}
TASK_NOTIFICATION = "Notify on '{task}' completion"
UI_DIR = os.path.join(PROJECT_ROOT, "ui")
UI_CONTEXT = "Ui"
UI_PROPERTIES = ("text", "title", "windowTitle", "placeholderText")
# Examples and app names that must stay exactly as written.
UNTRANSLATED_UI_TEXTS = {
    "QuickFile",
    "/path/to/source",
    "/path/to/destination",
    "e.g. *.txt, report_??.doc",
    "e.g. py, cpp",
    "rwx",
    "r-x",
    "---",
    "...",
}


def source_files():
    for root in SOURCE_ROOTS:
        root_path = os.path.join(PROJECT_ROOT, root)
        if not os.path.isdir(root_path):
            continue
        for dirpath, dirnames, filenames in os.walk(root_path):
            dirnames[:] = sorted(
                name for name in dirnames if name not in SKIPPED_DIRECTORIES
            )
            for name in sorted(filenames):
                if name.endswith(".py"):
                    yield os.path.join(dirpath, name)


def literal_text(node):
    """Return a constant string, also for an f-string without placeholders."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr) and all(
        isinstance(value, ast.Constant) for value in node.values
    ):
        return "".join(value.value for value in node.values)
    return None


def literal_calls():
    """Map every literal ``Context.Text`` key to its English text."""
    expected = {}
    for path in source_files():
        with open(path, encoding="utf-8") as handle:
            tree = ast.parse(handle.read(), filename=path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr != "translate" or len(node.args) < 2:
                continue
            context = literal_text(node.args[0])
            text = literal_text(node.args[1])
            if context is None or text is None:
                continue
            key = f"{context}.{text}"
            previous = expected.setdefault(key, text)
            assert previous == text, f"{path} uses {key} with a different text"
    return expected


def designer_strings():
    """Every text Qt Designer stored in a host ``.ui`` file."""
    found = {}
    for name in sorted(os.listdir(UI_DIR)):
        if not name.endswith(".ui"):
            continue
        path = os.path.join(UI_DIR, name)
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        parents = {child: node for node in root.iter() for child in node}
        for element in root.iter("string"):
            text = element.text.strip() if element.text else ""
            if not text:
                continue
            holder = parents[element]
            translated_property = holder.tag == "property" and holder.get(
                "name"
            ) in UI_PROPERTIES
            translated_tab = (
                holder.tag == "attribute" and holder.get("name") == "title"
            )
            if translated_property or translated_tab:
                found[text] = name
    return found


def expected_strings():
    """Every key the application can look up, with its English text."""
    expected = dict(literal_calls())
    for label in STATUS_LABELS.values():
        expected[f"PluginManagement.{label}"] = label
    for task_type in TaskType:
        name = task_type.name.replace("_", " ").title()
        expected[f"TaskType.{name}"] = name
    expected[f"SettingsDialog.{TASK_NOTIFICATION}"] = TASK_NOTIFICATION
    for text in designer_strings():
        if text not in UNTRANSLATED_UI_TEXTS:
            expected[f"{UI_CONTEXT}.{text}"] = text
    return expected


def load_translations(name):
    with open(os.path.join(TRANSLATIONS_DIR, name), encoding="utf-8") as handle:
        return json.load(handle)


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_source_string_has_a_translation(language):
    translations = load_translations(language)
    missing = sorted(
        key for key in expected_strings() if not translations.get(key)
    )

    assert missing == [], f"{language} is missing {len(missing)} keys"


def test_english_values_match_the_source_text():
    translations = load_translations("en_US.json")
    wrong = sorted(
        key
        for key, text in expected_strings().items()
        if translations.get(key) != text
    )

    assert wrong == []


def test_both_language_files_share_the_same_keys():
    english = set(load_translations("en_US.json"))
    polish = set(load_translations("pl_PL.json"))

    assert sorted(english - polish) == []
    assert sorted(polish - english) == []


@pytest.mark.parametrize("language", LANGUAGES)
def test_translations_keep_placeholders(language):
    translations = load_translations(language)
    broken = []
    for key, text in expected_strings().items():
        translated = translations.get(key, "")
        for placeholder in re.findall(r"\{[^}]+\}", text):
            if placeholder not in translated:
                broken.append(key)
                break

    assert sorted(broken) == []


@pytest.fixture
def polish_translations():
    previous = translation_manager.translations
    translation_manager.translations = load_translations("pl_PL.json")
    try:
        yield translation_manager.translations
    finally:
        translation_manager.translations = previous


def test_translate_widgets_replaces_designer_texts(qapp, polish_translations):
    root = QWidget()
    root.setWindowTitle("Settings")
    QLabel("Source:", root)
    QGroupBox("Options", root)
    QPushButton("Browse...", root)
    field = QLineEdit(root)
    field.setPlaceholderText("Filter bookmarks...")
    tabs = QTabWidget(root)
    tabs.addTab(QWidget(), "Browser")
    combo = QComboBox(root)
    combo.addItem("Case sensitive")

    translate_widgets(root)

    assert root.windowTitle() == polish_translations["Ui.Settings"]
    assert root.findChild(QLabel).text() == polish_translations["Ui.Source:"]
    assert root.findChild(QGroupBox).title() == polish_translations["Ui.Options"]
    assert (
        root.findChild(QPushButton).text() == polish_translations["Ui.Browse..."]
    )
    assert (
        field.placeholderText()
        == polish_translations["Ui.Filter bookmarks..."]
    )
    assert tabs.tabText(0) == polish_translations["Ui.Browser"]
    assert combo.itemText(0) == polish_translations["Ui.Case sensitive"]
    root.deleteLater()


def test_translate_widgets_keeps_texts_without_a_key(qapp, polish_translations):
    label = QLabel("/path/to/source")

    translate_widgets(label)

    assert label.text() == "/path/to/source"
    label.deleteLater()
