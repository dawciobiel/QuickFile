from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QRadioButton, QPushButton

class SettingsDialog(QDialog):
    def __init__(self, parent, current_view_mode):
        super().__init__(parent)
        self.setWindowTitle("Ustawienia Aplikacji")
        self.current_view_mode = current_view_mode
        self.selected_view_mode = current_view_mode
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # Group box for view mode
        view_mode_group = QGroupBox("Tryb Widoku Folderów")
        view_mode_layout = QVBoxLayout()

        self.flat_view_radio = QRadioButton("Widok płaski (tylko bieżący katalog, z opcją '..')")
        self.tree_view_radio = QRadioButton("Widok drzewa (cała partycja, rozwijane katalogi)")

        if self.current_view_mode == "flat":
            self.flat_view_radio.setChecked(True)
        else:
            self.tree_view_radio.setChecked(True)

        self.flat_view_radio.toggled.connect(lambda: self._set_selected_view_mode("flat"))
        self.tree_view_radio.toggled.connect(lambda: self._set_selected_view_mode("tree"))

        view_mode_layout.addWidget(self.flat_view_radio)
        view_mode_layout.addWidget(self.tree_view_radio)
        view_mode_group.setLayout(view_mode_layout)
        main_layout.addWidget(view_mode_group)

        # Buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Zapisz")
        self.cancel_button = QPushButton("Anuluj")
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        main_layout.addLayout(button_layout)

        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def _set_selected_view_mode(self, mode):
        self.selected_view_mode = mode

    def get_selected_view_mode(self):
        return self.selected_view_mode
