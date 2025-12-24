from PyQt6.QtCore import QObject

class ProgressBarManager(QObject):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.hide_progress()

    def show_progress(self, text="Operation in progress..."):
        self.main_window.progress_label.setText(text)
        self.main_window.progress_label.setVisible(True)
        self.main_window.progressBar.setVisible(True)
        self.main_window.cancel_button.setVisible(True)
        self.main_window.progressBar.setValue(0)

    def update_progress(self, value):
        self.main_window.progressBar.setValue(value)

    def hide_progress(self):
        self.main_window.progress_label.setVisible(False)
        self.main_window.progressBar.setVisible(False)
        self.main_window.cancel_button.setVisible(False)
