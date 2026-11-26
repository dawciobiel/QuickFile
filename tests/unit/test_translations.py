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
import glob
import importlib.util
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from unittest.mock import MagicMock

import pytest
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QComboBox,
    QDialogButtonBox,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QTabWidget,
    QWidget,
)

from app.dialog_handler import DialogHandler
from app.enums import TaskType
from app.plugin_installer import PluginInstallationError, install
from app.plugin_settings import PluginSettingsError, validate_schema
from app.plugin_state import PluginStateError, disable_plugin
from app.plugin_updater import UpdateError, load_feed
from app.settings_manager import SettingsManager
from app.theme_manager import ThemeManager
from app.translation_manager import translation_manager
from app.ui_translation import install_qt_translations, translate_widgets
from file_operations.properties_manager import get_file_properties
from panels.menu_panel import MenuPanel
from tests.plugin_helpers import iter_plugin_metadata, iter_plugin_version_paths
from utils.create_archive_dialog import CreateArchiveDialog
from utils.plugin_management_page import STATUS_LABELS
from utils.plugin_settings_dialog import PluginSettingsDialog
from utils.properties_dialog import PropertiesDialog

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
TRANSLATIONS_DIR = os.path.join(PROJECT_ROOT, "resources", "translations")
SOURCE_ROOTS = (
    "app",
    "file_operations",
    "favorites",
    "ui",
    "utils",
    "browser",
    "panels",
    "plugins",
    "plugins-external",
)
LANGUAGES = ("en_US.json", "pl_PL.json")
SKIPPED_DIRECTORIES = {"__pycache__", "tests", "experiments"}
HOST_SOURCE_ROOTS = (
    "app",
    "browser",
    "favorites",
    "file_operations",
    "panels",
    "ui",
    "utils",
)
# Plugin-author validation and internal protocol signals. Plugin Management
# reports the former separately; the latter never reach a dialog.
INTERNAL_ERROR_MODULES = {
    "app/action_replayer.py",
    "app/external_tools.py",
    "app/plugin_system/api.py",
    "app/plugin_system/host.py",
    "app/plugin_system/protocol.py",
    "app/plugin_system/runtime.py",
    "app/plugin_task_interface.py",
}
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


def source_files(roots=SOURCE_ROOTS):
    for root in roots:
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


def contains_translate(call):
    """Whether ``call`` already runs its text through ``translate``."""
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "translate"
        for node in ast.walk(call)
    )


def literal_setters(method):
    """Yield ``(path, line, text)`` for a literal first argument of ``method``."""
    for path in source_files():
        with open(path, encoding="utf-8") as handle:
            tree = ast.parse(handle.read(), filename=path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr != method or not node.args:
                continue
            text = literal_text(node.args[0])
            if text is None or contains_translate(node):
                continue
            yield os.path.relpath(path, PROJECT_ROOT), node.lineno, text


def interpolated_setters():
    """Yield ``(path, line, expression)`` for an f-string handed to a setter."""
    for path in source_files():
        with open(path, encoding="utf-8") as handle:
            tree = ast.parse(handle.read(), filename=path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr not in INTERPOLATED_TEXT_METHODS or not node.args:
                continue
            text = node.args[0]
            if not isinstance(text, ast.JoinedStr) or contains_translate(node):
                continue
            literal = "".join(
                value.value
                for value in text.values
                if isinstance(value, ast.Constant)
            )
            if not any(character.isalpha() for character in literal):
                continue
            if literal in UNTRANSLATED_INTERPOLATED_TEXTS:
                continue
            yield os.path.relpath(path, PROJECT_ROOT), node.lineno, ast.unparse(text)


def runtime_built_keys():
    """Yield ``(path, line, expression)`` for ``translate`` keys with placeholders."""
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
            text = node.args[1]
            if not isinstance(text, ast.JoinedStr):
                continue
            if any(isinstance(value, ast.FormattedValue) for value in text.values):
                yield os.path.relpath(path, PROJECT_ROOT), node.lineno, ast.unparse(text)


DIALOG_CLASSES = {"QFileDialog", "QInputDialog", "QMessageBox"}
MESSAGE_HELPER_FUNCTIONS = {"show_error_message", "show_info_message"}
INTERPOLATED_TEXT_METHODS = {
    "setPlaceholderText",
    "setText",
    "setTitle",
    "setToolTip",
    "setWindowTitle",
    "showMessage",
}
TEXT_WIDGET_CLASSES = {
    "QAction",
    "QCheckBox",
    "QGroupBox",
    "QLabel",
    "QPushButton",
    "QRadioButton",
}
# Viewer radix switches: abbreviations, not sentences.
UNTRANSLATED_WIDGET_TEXTS = {"HEX", "DEC", "BIN"}
DIALOG_METHODS = {
    "about",
    "critical",
    "getExistingDirectory",
    "getItem",
    "getMultiLineText",
    "getOpenFileName",
    "getOpenFileNames",
    "getSaveFileName",
    "getText",
    "information",
    "question",
    "warning",
}


def dialog_strings():
    """Yield literal titles and texts passed to a standard Qt dialog."""
    for path in source_files():
        with open(path, encoding="utf-8") as handle:
            tree = ast.parse(handle.read(), filename=path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Attribute):
                continue
            if func.attr not in DIALOG_METHODS:
                continue
            if (
                not isinstance(func.value, ast.Name)
                or func.value.id not in DIALOG_CLASSES
            ):
                continue
            # The first argument is the parent widget, never a caption.
            for argument in node.args[1:]:
                if contains_translate(argument):
                    continue
                if isinstance(argument, ast.Constant) and isinstance(
                    argument.value, str
                ):
                    if argument.value:
                        yield (
                            os.path.relpath(path, PROJECT_ROOT),
                            node.lineno,
                            argument.value,
                        )
                elif isinstance(argument, ast.JoinedStr):
                    yield (
                        os.path.relpath(path, PROJECT_ROOT),
                        node.lineno,
                        ast.unparse(argument),
                    )


def message_helper_strings():
    """Yield literal titles and texts passed to a message helper."""
    for path in source_files():
        with open(path, encoding="utf-8") as handle:
            tree = ast.parse(handle.read(), filename=path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name):
                continue
            if node.func.id not in MESSAGE_HELPER_FUNCTIONS:
                continue
            # show_*_message(parent, title, message)
            for argument in node.args[1:]:
                if contains_translate(argument):
                    continue
                if isinstance(argument, ast.Constant) and isinstance(
                    argument.value, str
                ):
                    if argument.value:
                        yield (
                            os.path.relpath(path, PROJECT_ROOT),
                            node.lineno,
                            argument.value,
                        )
                elif isinstance(argument, ast.JoinedStr):
                    literal = "".join(
                        value.value
                        for value in argument.values
                        if isinstance(value, ast.Constant)
                    )
                    if any(character.isalpha() for character in literal):
                        yield (
                            os.path.relpath(path, PROJECT_ROOT),
                            node.lineno,
                            ast.unparse(argument),
                        )


def widget_constructor_strings():
    """Yield literal texts passed to a widget constructor."""
    for path in source_files():
        with open(path, encoding="utf-8") as handle:
            tree = ast.parse(handle.read(), filename=path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name):
                continue
            if node.func.id not in TEXT_WIDGET_CLASSES or not node.args:
                continue
            argument = node.args[0]
            if contains_translate(argument):
                continue
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                if argument.value and argument.value not in UNTRANSLATED_WIDGET_TEXTS:
                    yield (
                        os.path.relpath(path, PROJECT_ROOT),
                        node.lineno,
                        argument.value,
                    )
            elif isinstance(argument, ast.JoinedStr):
                literal = "".join(
                    value.value
                    for value in argument.values
                    if isinstance(value, ast.Constant)
                )
                if any(character.isalpha() for character in literal):
                    yield (
                        os.path.relpath(path, PROJECT_ROOT),
                        node.lineno,
                        ast.unparse(argument),
                    )


def host_error_strings():
    """Yield literal messages raised in host code and shown to the user."""
    for path in source_files(HOST_SOURCE_ROOTS):
        relative = os.path.relpath(path, PROJECT_ROOT)
        if relative in INTERNAL_ERROR_MODULES:
            continue
        with open(path, encoding="utf-8") as handle:
            tree = ast.parse(handle.read(), filename=path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Raise) or node.exc is None:
                continue
            if not isinstance(node.exc, ast.Call):
                continue
            for argument in node.exc.args:
                if contains_translate(argument):
                    continue
                if isinstance(argument, ast.Constant) and isinstance(
                    argument.value, str
                ):
                    if argument.value:
                        yield relative, node.lineno, argument.value
                elif isinstance(argument, ast.JoinedStr):
                    yield relative, node.lineno, ast.unparse(argument)


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


# QToolBar titles are object names (``toolBar``) shown only in Qt's toolbar
# menu, so a plugin does not translate them.
IGNORED_PLUGIN_WIDGET_CLASSES = {"QToolBar"}


def plugin_translate_calls(directory):
    """Return the texts a bundled plugin translates explicitly in its code."""
    texts = set()
    for path in sorted(glob.glob(os.path.join(directory, "*.py"))):
        with open(path, encoding="utf-8") as handle:
            tree = ast.parse(handle.read(), filename=path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr != "translate" or len(node.args) < 2:
                continue
            text = literal_text(node.args[1])
            if text is not None:
                texts.add(text)
    return texts


def plugin_menu_action_texts(directory):
    """Return the literal labels a bundled plugin puts in ``get_menu_actions``."""
    texts = set()
    for path in sorted(glob.glob(os.path.join(directory, "*.py"))):
        with open(path, encoding="utf-8") as handle:
            tree = ast.parse(handle.read(), filename=path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            if node.name != "get_menu_actions":
                continue
            for inner in ast.walk(node):
                if not isinstance(inner, ast.Dict):
                    continue
                for key, value in zip(inner.keys, inner.values):
                    if isinstance(key, ast.Constant) and key.value == "text":
                        text = literal_text(value)
                        if text is not None:
                            texts.add(text)
    return texts


def plugin_designer_strings():
    """Map a text from a bundled plugin ``.ui`` to whether its code translates it."""
    found = {}
    for _name, _version, metadata_path in iter_plugin_version_paths():
        directory = os.path.dirname(metadata_path)
        explicit = plugin_translate_calls(directory)
        source = ""
        for path in sorted(glob.glob(os.path.join(directory, "*.py"))):
            with open(path, encoding="utf-8") as handle:
                source += handle.read()
        for path in sorted(glob.glob(os.path.join(directory, "*.ui"))):
            with open(path, encoding="utf-8") as handle:
                content = handle.read()
            if not content.strip():
                # A zero-byte .ui file never loads.
                continue
            root = ET.fromstring(content)
            parents = {child: node for node in root.iter() for child in node}
            top_widget = root.find("widget")
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
                if not (translated_property or translated_tab):
                    continue
                widget = parents[holder]
                if widget.get("class") in IGNORED_PLUGIN_WIDGET_CLASSES:
                    continue
                # The dialog sets its own title before it is shown, so the text
                # stored in the .ui file never reaches the user.
                if (
                    holder.get("name") == "windowTitle"
                    and widget is top_widget
                    and "self.setWindowTitle(" in source
                ):
                    continue
                found[text] = found.get(text, False) or text in explicit
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


# Symbols and empty clears that are not sentences.
UNTRANSLATED_SET_TEXTS = {"", "~", "/", "..", "="}
# The window title is the product name and version, identical in every language.
UNTRANSLATED_INTERPOLATED_TEXTS = {"QuickFile v"}


def test_literal_widget_texts_are_translated():
    found = sorted(
        (path, line, text)
        for path, line, text in literal_setters("setText")
        if text not in UNTRANSLATED_SET_TEXTS
    )

    assert found == []


def test_literal_status_bar_messages_are_translated():
    found = sorted(literal_setters("showMessage"))

    assert found == []


def test_interpolated_widget_texts_are_translated():
    """An f-string with English words in a setter stays English."""
    found = sorted(interpolated_setters())

    assert found == []


def test_translation_keys_are_not_built_at_runtime():
    """An interpolated key never matches the JSON dictionary."""
    found = sorted(runtime_built_keys())

    assert found == []


def test_dialog_strings_are_translated():
    """A dialog caption or message must not be a plain literal."""
    found = sorted(dialog_strings())

    assert found == []


def test_message_helper_texts_are_translated():
    """The helper that shows a blocking dialog must receive translated text."""
    found = sorted(message_helper_strings())

    assert found == []


def test_widget_constructor_texts_are_translated():
    """A label, button or action built with a plain literal stays English."""
    found = sorted(widget_constructor_strings())

    assert found == []


def test_host_error_messages_are_translated():
    """The error dialog shows the message raised by a host action."""
    found = sorted(host_error_strings())

    assert found == []


def test_host_action_error_uses_the_current_language(polish_translations):
    handler = DialogHandler.__new__(DialogHandler)
    handler.ui_state_provider = MagicMock()
    handler.ui_state_provider.get_selected_paths.return_value = []

    with pytest.raises(ValueError) as error:
        handler.create_archive()

    assert str(error.value) == "Nie wybrano pliku ani katalogu do archiwizacji."


def test_plugin_installer_error_uses_the_current_language(
    polish_translations, tmp_path
):
    missing = tmp_path / "missing.zip"

    with pytest.raises(PluginInstallationError) as error:
        install(missing)

    assert str(error.value) == f"Nie znaleziono paczki: {missing}"


def test_plugin_settings_error_uses_the_current_language(polish_translations):
    with pytest.raises(PluginSettingsError) as error:
        validate_schema({"name": "not-a-field"})

    assert str(error.value) == "Ustawienie 'name' musi być obiektem"


def test_plugin_state_error_uses_the_current_language(polish_translations, tmp_path):
    with pytest.raises(PluginStateError) as error:
        disable_plugin(
            "org.example.plugin",
            destination=str(tmp_path),
            install_dir=str(tmp_path / "shipped"),
        )

    assert str(error.value) == (
        f"Wtyczka org.example.plugin nie jest zainstalowana w {tmp_path}."
    )


def test_plugin_updater_error_uses_the_current_language(polish_translations):
    with pytest.raises(UpdateError) as error:
        load_feed("ftp://example.com/plugin-index.json")

    assert str(error.value) == (
        "Nieobsługiwany schemat adresu URL 'ftp' w "
        "ftp://example.com/plugin-index.json; użyj https lub file."
    )


def test_translation_manager_imports_without_qt(tmp_path):
    """The package builder imports the translation manager without PyQt6."""
    stub = tmp_path / "PyQt6"
    stub.mkdir()
    (stub / "__init__.py").write_text(
        "raise ImportError('PyQt6 is not installed')\n", encoding="utf-8"
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.translation_manager import translation_manager;"
            "print(translation_manager.current_locale)",
        ],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip()


@pytest.mark.parametrize("language", LANGUAGES)
def test_bundled_plugin_ui_texts_are_translated(language):
    """A plugin either translates a ``.ui`` text in code or has a ``Ui.`` key."""
    required = {
        text
        for text, explicit in plugin_designer_strings().items()
        if not explicit and text not in UNTRANSLATED_UI_TEXTS
    }
    translations = load_translations(language)
    missing = sorted(
        text for text in required if f"{UI_CONTEXT}.{text}" not in translations
    )

    assert missing == []
    if language == "en_US.json":
        wrong = sorted(
            text for text in required if translations[f"{UI_CONTEXT}.{text}"] != text
        )
        assert wrong == []


def plugin_menu_action_labels():
    """Return the literal labels every bundled plugin puts in ``get_menu_actions``."""
    labels = set()
    for _name, _version, metadata_path in iter_plugin_version_paths():
        labels.update(plugin_menu_action_texts(os.path.dirname(metadata_path)))
    return labels


@pytest.mark.parametrize("language", LANGUAGES)
def test_bundled_plugin_menu_actions_are_translated(language):
    translations = load_translations(language)
    labels = plugin_menu_action_labels()

    missing = sorted(
        label for label in labels if f"PluginAction.{label}" not in translations
    )
    assert missing == []

    if language == "en_US.json":
        wrong = sorted(
            label
            for label in labels
            if translations[f"PluginAction.{label}"] != label
        )
        assert wrong == []


def plugin_names():
    """Return the display names of every bundled plugin."""
    return {
        metadata["name"]
        for _path, metadata in iter_plugin_metadata()
        if metadata.get("name")
    }


@pytest.mark.parametrize("language", LANGUAGES)
def test_bundled_plugin_names_are_translated(language):
    translations = load_translations(language)
    names = plugin_names()

    missing = sorted(
        name for name in names if f"PluginName.{name}" not in translations
    )
    assert missing == []

    if language == "en_US.json":
        wrong = sorted(
            name for name in names if translations[f"PluginName.{name}"] != name
        )
        assert wrong == []


def plugin_settings_texts():
    """Return the titles, descriptions and choice labels in plugin metadata."""
    texts = set()
    for _path, metadata in iter_plugin_metadata():
        schema = (metadata.get("settings") or {}).get("schema") or {}
        for field in schema.values():
            if field.get("title"):
                texts.add(field["title"])
            if field.get("description"):
                texts.add(field["description"])
            for choice in field.get("choices", []):
                if choice.get("label"):
                    texts.add(choice["label"])
    return texts


@pytest.mark.parametrize("language", LANGUAGES)
def test_bundled_plugin_settings_texts_are_translated(language):
    translations = load_translations(language)
    texts = plugin_settings_texts()

    missing = sorted(
        text for text in texts if f"PluginSettings.{text}" not in translations
    )
    assert missing == []

    if language == "en_US.json":
        wrong = sorted(
            text for text in texts if translations[f"PluginSettings.{text}"] != text
        )
        assert wrong == []


@pytest.fixture
def polish_translations():
    previous = translation_manager.translations
    previous_locale = translation_manager.current_locale
    translation_manager.translations = load_translations("pl_PL.json")
    translation_manager.current_locale = "pl_PL"
    try:
        yield translation_manager.translations
    finally:
        translation_manager.translations = previous
        translation_manager.current_locale = previous_locale


def test_qt_standard_buttons_use_the_current_language(qapp, polish_translations):
    translator = install_qt_translations(qapp)
    assert translator is not None
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
    try:
        assert (
            box.button(QDialogButtonBox.StandardButton.Cancel).text() == "Anuluj"
        )
    finally:
        box.deleteLater()
        qapp.removeTranslator(translator)
        translator.deleteLater()


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


def test_plugin_menu_label_uses_the_current_language(qapp, polish_translations):
    panel = MenuPanel.__new__(MenuPanel)
    panel.main_window = QWidget()
    panel.icon_color = "#000000"
    panel.file_menu = QMenu()
    panel.operations_menu = QMenu()
    panel.view_menu = QMenu()
    panel.options_menu = QMenu()
    panel.help_menu = QMenu()
    panel.actions = {"file.exit": QAction("Exit", panel.main_window)}

    class Plugin:
        def get_menu_actions(self):
            return [
                {
                    "text": "Split File...",
                    "menu": "file",
                    "action_id": "split_file",
                    "callback": lambda: None,
                }
            ]

    manager = MagicMock()
    manager.get_menu_action_plugins.return_value = [Plugin()]
    panel.app_logic_handler = MagicMock()
    panel.app_logic_handler.task_queue_manager.plugin_manager = manager

    panel._add_plugin_actions()

    labels = {action.text() for action in panel.file_menu.actions()}
    assert "Podziel plik..." in labels
    panel.main_window.deleteLater()


def test_plugin_settings_title_uses_the_current_language(qapp, polish_translations):
    dialog = PluginSettingsDialog(
        None,
        "Standard ZIP Archiver",
        {"enabled": {"type": "boolean", "title": "Enabled", "default": True}},
    )
    try:
        assert (
            dialog.windowTitle()
            == "Ustawienia pluginu: Standardowy archiwizator ZIP"
        )
    finally:
        dialog.deleteLater()


def test_plugin_settings_fields_use_the_current_language(qapp, polish_translations):
    schema = {
        "compression": {
            "type": "enum",
            "title": "Compression method",
            "default": "deflate",
            "choices": [
                {"value": "deflate", "label": "Deflate"},
                {"value": "store", "label": "Store (no compression)"},
            ],
        },
        "compresslevel": {
            "type": "integer",
            "title": "Compression level",
            "description": "Ignored when the compression method is Store.",
            "default": 6,
            "minimum": 1,
            "maximum": 9,
        },
    }
    dialog = PluginSettingsDialog(None, "Standard ZIP Archiver", schema)
    try:
        labels = {label.text() for label in dialog.findChildren(QLabel)}
        assert "Metoda kompresji" in labels
        assert "Poziom kompresji" in labels

        combo = dialog.findChild(QComboBox)
        assert [combo.itemText(index) for index in range(combo.count())] == [
            "Deflate",
            "Bez kompresji (Store)",
        ]
        assert dialog._widgets["compresslevel"].toolTip() == (
            "Ignorowane, gdy metodą kompresji jest Store."
        )
    finally:
        dialog.deleteLater()


def test_archive_plugin_label_uses_the_current_language(qapp, polish_translations):
    class Plugin:
        metadata = {"id": "org.example.creator"}

        def get_name(self):
            return "Standard ZIP Archiver"

        def get_supported_extensions(self):
            return ["zip"]

    class Settings:
        def get_plugin_settings(self, plugin_id):
            return {}

        def set_plugin_settings(self, plugin_id, options):
            pass

    manager = MagicMock()
    manager.get_archivers.return_value = [Plugin()]
    dialog = CreateArchiveDialog(None, manager, "/tmp", settings_manager=Settings())
    try:
        assert dialog.type_combo.itemText(0) == "Standardowy archiwizator ZIP (zip)"
    finally:
        dialog.deleteLater()


def load_plugin_module(plugin_name, module_name):
    """Import a bundled plugin module by path, as the plugin loader does."""
    pattern = os.path.join(
        PROJECT_ROOT,
        "plugins",
        "org.quickfile",
        plugin_name,
        "*",
        f"{module_name}.py",
    )
    paths = sorted(glob.glob(pattern))
    assert len(paths) == 1, paths
    spec = importlib.util.spec_from_file_location(
        f"plugin_{plugin_name}_{module_name}", paths[0]
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bundled_attribute_editor_translates_its_dialog(
    qapp, polish_translations, tmp_path
):
    target = tmp_path / "example.txt"
    target.write_text("content", encoding="utf-8")
    module = load_plugin_module("linux_attribute_editor", "change_owner_dialog")

    dialog = module.ChangeOwnerDialog(str(target))

    try:
        assert dialog.windowTitle() == "Zmień właściciela i grupę"
        labels = {label.text() for label in dialog.findChildren(QLabel)}
        assert "Nazwa:" in labels
        assert "Rozmiar:" in labels
        assert "Uprawnienia:" in labels
        titles = {box.title() for box in dialog.findChildren(QGroupBox)}
        assert "Bieżące atrybuty" in titles
        assert "Nowy właściciel" in titles
        assert "Nowa grupa" in titles
    finally:
        dialog.deleteLater()


def test_bundled_viewer_translates_status_and_modes(
    qapp, polish_translations, tmp_path
):
    target = tmp_path / "example.txt"
    target.write_text("hello", encoding="utf-8")
    module = load_plugin_module("standard_viewer", "file_viewer_dialog")

    viewer = module.FileViewerWindow(str(target), ThemeManager(SettingsManager()))

    try:
        assert viewer.statusBar.currentMessage() == "Kodowanie: utf-8"
        modes = {action.text() for action in viewer.findChildren(QAction)}
        assert {"Tekst", "Obraz", "Markdown", "Kod"} <= modes
    finally:
        viewer.deleteLater()


def test_bundled_editor_translates_window_and_toolbar(
    qapp, polish_translations, tmp_path
):
    target = tmp_path / "note.txt"
    target.write_text("content", encoding="utf-8")
    module = load_plugin_module("standard_editor", "plugin")
    plugin = module.StandardEditorPlugin()

    window = plugin.open_editor(
        str(target), ThemeManager(SettingsManager()), None
    )

    try:
        assert window.windowTitle() == "Edytor - note.txt"
        labels = {action.text() for action in window.findChildren(QAction)}
        assert {
            "Zapisz",
            "Cofnij",
            "Ponów",
            "Wytnij",
            "Kopiuj",
            "Wklej",
        } <= labels
    finally:
        window.deleteLater()
        for name in list(sys.modules):
            if name == "widgets" or name.startswith("widgets."):
                sys.modules.pop(name, None)


def test_properties_dialog_translates_labels_and_size(
    qapp, polish_translations, tmp_path
):
    target = tmp_path / "example.txt"
    target.write_text("content", encoding="utf-8")
    properties = get_file_properties(str(target))

    dialog = PropertiesDialog(properties)

    try:
        labels = {label.text() for label in dialog.findChildren(QLabel)}
        assert {
            "Pełna ścieżka:",
            "Rozmiar:",
            "Data modyfikacji:",
            "Data utworzenia:",
            "Uprawnienia:",
            "Właściciel:",
            "Grupa:",
        } <= labels
        assert f"{target.stat().st_size} bajtów" in labels
    finally:
        dialog.deleteLater()
