from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QLabel, QTabWidget

from app.translation_manager import translation_manager


class CompareDialog(QDialog):
    def __init__(self, parent=None, report=None, path1="", path2=""):
        super().__init__(parent)
        self.setWindowTitle(translation_manager.translate("CompareDialog", "Comparison Results") + f": {path1} vs {path2}")
        self.setGeometry(100, 100, 800, 600)

        self.report = report if report else {}
        self.path1 = path1
        self.path2 = path2

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)

        path_label = QLabel(translation_manager.translate("CompareDialog", "Comparing:") + f"\n{translation_manager.translate('CompareDialog', 'Left')}: {self.path1}\n{translation_manager.translate('CompareDialog', 'Right')}: {self.path2}")
        main_layout.addWidget(path_label)

        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        self._populate_tabs(self.tab_widget, self.report)

    def _populate_tabs(self, parent_tab_widget, report_data):
        self._add_report_tab(parent_tab_widget, "Different Files", report_data.get("diff_files", []))
        self._add_report_tab(parent_tab_widget, "Left Only", report_data.get("left_only", []))
        self._add_report_tab(parent_tab_widget, "Right Only", report_data.get("right_only", []))
        self._add_report_tab(parent_tab_widget, "Same Files", report_data.get("same_files", []))
        self._add_report_tab(parent_tab_widget, "Common Dirs", report_data.get("common_dirs", []))
        self._add_report_tab(parent_tab_widget, "Common Funny", report_data.get("common_funny", []))

        if "subdirs" in report_data:
            for subdir_name, subdir_report in report_data["subdirs"].items():
                subdir_tab_widget = QTabWidget()
                self._populate_tabs(subdir_tab_widget, subdir_report)
                parent_tab_widget.addTab(subdir_tab_widget, subdir_name)

    def _add_report_tab(self, tab_widget, title_key, items):
        if not items:
            return

        translated_title = translation_manager.translate("CompareDialog", title_key)
        tree = QTreeWidget()
        tree.setHeaderLabels([translated_title])

        for item in items:
            QTreeWidgetItem(tree, [item])

        tab_widget.addTab(tree, translated_title)
