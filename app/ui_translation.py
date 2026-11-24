# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Translations for texts that Qt Designer stored in ``.ui`` files.

``uic.loadUi`` copies the strings from the ``.ui`` file verbatim, so a dialog
built only from a ``.ui`` file stays English regardless of the selected
language. ``translate_widgets`` walks the loaded widget tree and replaces each
text with its ``Ui.<text>`` translation. Texts without a key keep their
original value, so examples such as ``/path/to/source`` are left alone.

Call it right after ``loadUi`` and before setting any text from data.

Specification: ``docs/developer_guide/translation.md``.
"""

from PyQt6.QtCore import QLibraryInfo, QTranslator
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QTabWidget,
    QTextEdit,
    QToolButton,
    QWidget,
)

from app.translation_manager import translation_manager

CONTEXT = "Ui"


def install_qt_translations(app: QApplication) -> QTranslator | None:
    """Install Qt's own translation for the current language, when available.

    Qt draws the standard button labels (``OK``, ``Save``, ``Cancel``) and the
    titles of its own dialogs from ``qtbase_<language>.qm``. Without this
    translator those labels stay English in every locale. Returns the installed
    translator so the caller can keep a reference, or ``None`` for English or
    when Qt ships no catalogue for the language.
    """
    locale = translation_manager.current_locale
    base = locale.split("_")[0]
    if base == "en":
        return None

    directory = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    for candidate in (locale, base):
        translator = QTranslator(app)
        if translator.load(f"qtbase_{candidate}", directory):
            app.installTranslator(translator)
            return translator
    return None


def translate_widgets(root: QWidget) -> None:
    """Translate the texts of ``root`` and all widgets below it, in place."""
    _translate_widget(root)
    for widget in root.findChildren(QWidget):
        _translate_widget(widget)
    for action in root.findChildren(QAction):
        if action.text():
            action.setText(_translated(action.text()))


def _translated(text: str) -> str:
    return translation_manager.translate(CONTEXT, text)


def _translate_widget(widget: QWidget) -> None:
    title = widget.windowTitle()
    if title:
        widget.setWindowTitle(_translated(title))

    if isinstance(widget, QGroupBox):
        widget.setTitle(_translated(widget.title()))

    if isinstance(
        widget, (QLabel, QPushButton, QCheckBox, QRadioButton, QToolButton)
    ) and widget.text():
        widget.setText(_translated(widget.text()))

    if isinstance(widget, (QLineEdit, QTextEdit, QPlainTextEdit)):
        placeholder = widget.placeholderText()
        if placeholder:
            widget.setPlaceholderText(_translated(placeholder))

    if isinstance(widget, QTabWidget):
        for index in range(widget.count()):
            widget.setTabText(index, _translated(widget.tabText(index)))

    if isinstance(widget, QComboBox):
        for index in range(widget.count()):
            widget.setItemText(index, _translated(widget.itemText(index)))

    if isinstance(widget, QMenu) and widget.title():
        widget.setTitle(_translated(widget.title()))
