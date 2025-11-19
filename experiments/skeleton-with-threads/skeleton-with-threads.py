from PyQt5.QtWidgets import QApplication, QMainWindow, QMenuBar, QMenu, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QSplitter, QListView, QFileDialog, QMessageBox, QInputDialog
from PyQt5.QtCore import Qt, QDir, QThread, pyqtSignal
import os
import shutil

class FileManagerApp(QApplication):
    def __init__(self, sys_argv):
        super().__init__(sys_argv)
        self.main_window = MainWindow()
        self.main_window.show()

class FileManagerThread(QThread):
    progress = pyqtSignal(str)
    error = pyqtSignal(str)
    success = pyqtSignal(str)

    def __init__(self, operation, *args):
        super().__init__()
        self.operation = operation
        self.args = args

    def run(self):
        try:
            if self.operation == "copy":
                source, destination = self.args
                if os.path.isfile(source):
                    shutil.copy(source, destination)
                elif os.path.isdir(source):
                    shutil.copytree(source, os.path.join(destination, os.path.basename(source)))
                self.success.emit("Files copied successfully!")
            elif self.operation == "delete":
                path, = self.args
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
                self.success.emit("Files deleted successfully!")
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Manager")
        self.setGeometry(100, 100, 800, 600)

        # Menu bar setup
        self.menu_bar = self.menuBar()
        self.setup_menu_bar()

        # Main layout setup
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # File panels
        self.splitter = QSplitter(Qt.Horizontal)
        self.left_panel = FilePanel()
        self.right_panel = FilePanel()
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.right_panel)
        self.layout.addWidget(self.splitter)

        # Button panel
        self.button_panel = ButtonPanel()
        self.button_panel.copy_button.clicked.connect(self.copy_files)
        self.button_panel.delete_button.clicked.connect(self.delete_files)
        self.button_panel.view_button.clicked.connect(self.view_file)
        self.button_panel.rename_button.clicked.connect(self.rename_file)
        self.button_panel.new_folder_button.clicked.connect(self.create_new_folder)

        # Add button panel at the bottom
        self.layout.addWidget(self.button_panel)
        self.layout.setAlignment(self.button_panel, Qt.AlignBottom)

    def setup_menu_bar(self):
        file_menu = self.menu_bar.addMenu("File")
        view_menu = self.menu_bar.addMenu("View")
        help_menu = self.menu_bar.addMenu("Help")

        # File menu actions
        file_menu.addAction("Exit", self.close)

        # View menu actions
        view_menu.addAction("Refresh")

        # Help menu actions
        help_menu.addAction("About")

    def copy_files(self):
        source = self.left_panel.get_selected_path()
        destination = QFileDialog.getExistingDirectory(self, "Select Destination Folder")
        if source and destination:
            self.run_in_thread("copy", source, destination)

    def delete_files(self):
        path = self.left_panel.get_selected_path()
        if path:
            reply = QMessageBox.question(self, "Confirm Delete", f"Are you sure you want to delete {path}?", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.run_in_thread("delete", path)

    def view_file(self):
        path = self.left_panel.get_selected_path()
        if path and os.path.isfile(path):
            try:
                with open(path, 'r') as file:
                    content = file.read()
                QMessageBox.information(self, "File Content", content)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to read file: {e}")

    def rename_file(self):
        path = self.left_panel.get_selected_path()
        if path:
            new_name, ok = QInputDialog.getText(self, "Rename File", "Enter new name:")
            if ok and new_name:
                try:
                    new_path = os.path.join(os.path.dirname(path), new_name)
                    os.rename(path, new_path)
                    QMessageBox.information(self, "Success", "File renamed successfully!")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to rename file: {e}")

    def create_new_folder(self):
        directory = self.left_panel.get_selected_path()
        if os.path.isdir(directory):
            folder_name, ok = QInputDialog.getText(self, "New Folder", "Enter folder name:")
            if ok and folder_name:
                try:
                    new_folder_path = os.path.join(directory, folder_name)
                    os.mkdir(new_folder_path)
                    QMessageBox.information(self, "Success", "Folder created successfully!")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to create folder: {e}")

    def run_in_thread(self, operation, *args):
        self.thread = FileManagerThread(operation, *args)
        self.thread.success.connect(lambda message: QMessageBox.information(self, "Success", message))
        self.thread.error.connect(lambda message: QMessageBox.critical(self, "Error", message))
        self.thread.start()

class FilePanel(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.file_list = QListView()
        self.layout.addWidget(self.file_list)
        self.current_path = QDir.currentPath()

    def get_selected_path(self):
        # Placeholder for actual selection logic
        # Replace with logic to get the currently selected file/folder path
        return self.current_path

class ButtonPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QHBoxLayout(self)

        # Define buttons and their labels
        self.rename_button = QPushButton("F2: Rename")
        self.view_button = QPushButton("F3: View")
        self.edit_button = QPushButton("F4: Edit")
        self.copy_button = QPushButton("F5: Copy")
        self.move_button = QPushButton("F6: Move")
        self.new_folder_button = QPushButton("F7: New Folder")
        self.delete_button = QPushButton("F8: Delete")
        self.menu_button = QPushButton("F9: Menu")
        self.quit_button = QPushButton("F10: Quit")

        buttons = [
            self.rename_button, self.view_button, self.edit_button, self.copy_button,
            self.move_button, self.new_folder_button, self.delete_button,
            self.menu_button, self.quit_button
        ]

        for button in buttons:
            self.layout.addWidget(button)

if __name__ == "__main__":
    import sys
    app = FileManagerApp(sys.argv)
    sys.exit(app.exec_())
