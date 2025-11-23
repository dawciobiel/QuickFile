from PyQt6.QtWidgets import QMessageBox


def show_error_message(parent, title, message):
    """Wyświetla okno dialogowe z komunikatem o błędzie."""
    error_dialog = QMessageBox(parent)
    error_dialog.setIcon(QMessageBox.Icon.Critical)
    error_dialog.setText(title)
    error_dialog.setInformativeText(message)
    error_dialog.setWindowTitle("Błąd")
    error_dialog.exec()
