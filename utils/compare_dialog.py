# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QLabel, QTabWidget, QWidget
from PyQt6.QtCore import Qt
from app.translation_manager import translation_manager # Import our new manager
import os

class CompareDialog(QDialog):
    def __init__(self, parent=None, report=None, path1="", path2=""):
        super().__init__(parent)
        self.setWindowTitle(translation_manager.translate("CompareDialog", "Comparison Results") + f": {path1} vs {path2}")
        self.setGeometry(100, 100, 800, 600)

        self.report = report
        self.path1 = path1
        self.path2 = path2

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # Display paths
        path_label = QLabel(translation_manager.translate("CompareDialog", "Comparing:") + f"\n{translation_manager.translate('CompareDialog', 'Left')}: {self.path1}\n{translation_manager.translate('CompareDialog', 'Right')}: {self.path2}")
        main_layout.addWidget(path_label)

        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        self._add_tab(translation_manager.translate("CompareDialog", "Different Files"), self.report.get("diff_files", []))
        self._add_tab(translation_manager.translate("CompareDialog", "Left Only"), self.report.get("left_only", []))
        self._add_tab(translation_manager.translate("CompareDialog", "Right Only"), self.report.get("right_only", []))
        self._add_tab(translation_manager.translate("CompareDialog", "Same Files"), self.report.get("same_files", []))
        self._add_tab(translation_manager.translate("CompareDialog", "Common Dirs"), self.report.get("common_dirs", []))
        self._add_tab(translation_manager.translate("CompareDialog", "Common Funny"), self.report.get("common_funny", []))

        # Handle subdirectories recursively
        if self.report.get("subdirs"):
            self._add_subdir_tabs(self.report["subdirs"], self.tab_widget, f"{self.path1}/", f"{self.path2}/")

    def _add_tab(self, title, items):
        if not items:
            return

        tab = QWidget()
        layout = QVBoxLayout(tab)
        tree = QTreeWidget()
        tree.setHeaderLabels([title])

        for item in items:
            QTreeWidgetItem(tree, [item])
        
        layout.addWidget(tree)
        self.tab_widget.addTab(tab, title)

    def _add_subdir_tabs(self, subdirs_report, parent_tab_widget, current_path1, current_path2):
        for subdir_name, subdir_report in subdirs_report.items():
            subdir_path1 = os.path.join(current_path1, subdir_name)
            subdir_path2 = os.path.join(current_path2, subdir_name)

            subdir_tab = QWidget()
            subdir_layout = QVBoxLayout(subdir_tab)
            
            subdir_label = QLabel(translation_manager.translate("CompareDialog", "Subdirectory:") + f" {subdir_name}")
            subdir_layout.addWidget(subdir_label)

            subdir_tab_widget = QTabWidget()
            subdir_layout.addWidget(subdir_tab_widget)

            self._add_tab_to_widget(subdir_tab_widget, translation_manager.translate("CompareDialog", "Different Files"), subdir_report.get("diff_files", []))
            self._add_tab_to_widget(subdir_tab_widget, translation_manager.translate("CompareDialog", "Left Only"), subdir_report.get("left_only", []))
            self._add_tab_to_widget(subdir_tab_widget, translation_manager.translate("CompareDialog", "Right Only"), subdir_report.get("right_only", []))
            self._add_tab_to_widget(subdir_tab_widget, translation_manager.translate("CompareDialog", "Same Files"), subdir_report.get("same_files", []))
            self._add_tab_to_widget(subdir_tab_widget, translation_manager.translate("CompareDialog", "Common Dirs"), subdir_report.get("common_dirs", []))
            self._add_tab_to_widget(subdir_tab_widget, translation_manager.translate("CompareDialog", "Common Funny"), subdir_report.get("common_funny", []))

            if subdir_report.get("subdirs"):
                self._add_subdir_tabs(subdir_report["subdirs"], subdir_tab_widget, subdir_path1, subdir_path2)

            parent_tab_widget.addTab(subdir_tab, subdir_name)

    def _add_tab_to_widget(self, tab_widget, title, items):
        if not items:
            return

        tab = QWidget()
        layout = QVBoxLayout(tab)
        tree = QTreeWidget()
        tree.setHeaderLabels([title])

        for item in items:
            QTreeWidgetItem(tree, [item])
        
        layout.addWidget(tree)
        tab_widget.addTab(tab, title)
