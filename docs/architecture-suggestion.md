Proponuję następującą architekturę aplikacji wykorzystującą wzorzec projektowy Model-View-Controller (MVC) z wykorzystaniem systemu sygnałów i slotów Qt:



```python
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import os, shutil

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.file_controller = FileController()
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Tworzenie paneli
        panels_widget = QWidget()
        panels_layout = QHBoxLayout(panels_widget)
        self.left_panel = FilePanel("Panel lewy")
        self.right_panel = FilePanel("Panel prawy")
        panels_layout.addWidget(self.left_panel)
        panels_layout.addWidget(self.right_panel)
        
        # Panel funkcyjny
        self.function_panel = FunctionPanel()
        
        # Dodawanie do głównego layoutu
        layout.addWidget(panels_widget)
        layout.addWidget(self.function_panel)
        
        # Połączenia sygnałów
        self.function_panel.copy_requested.connect(self.file_controller.copy_files)
        self.function_panel.move_requested.connect(self.file_controller.move_files)
        self.function_panel.delete_requested.connect(self.file_controller.delete_files)

class FilePanel(QWidget):
    file_selected = pyqtSignal(str)  # Sygnał wysyłany przy wyborze pliku
    
    def __init__(self, name):
        super().__init__()
        self.current_path = ""
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        self.file_list = QListWidget()
        layout.addWidget(self.file_list)
        
    def get_selected_path(self):
        return os.path.join(self.current_path, self.file_list.currentItem().text())

class FunctionPanel(QWidget):
    copy_requested = pyqtSignal()
    move_requested = pyqtSignal()
    delete_requested = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout(self)
        # Przyciski funkcyjne
        self.create_function_buttons()
        
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F5:
            self.copy_requested.emit()
        elif event.key() == Qt.Key_F6:
            self.move_requested.emit()
        elif event.key() == Qt.Key_F8:
            self.delete_requested.emit()

class FileController(QObject):
    def __init__(self):
        super().__init__()
        
    def copy_files(self):
        source_panel = self.sender().parent().left_panel
        target_panel = self.sender().parent().right_panel
        source_path = source_panel.get_selected_path()
        target_path = target_panel.current_path
        
        if os.path.isfile(source_path):
            shutil.copy2(source_path, target_path)
        else:
            shutil.copytree(source_path, target_path)
            
    def move_files(self):
        # Podobna implementacja jak copy_files
        pass
        
    def delete_files(self):
        # Implementacja usuwania
        pass

```

Kluczowe elementy architektury:

1. Komunikacja między modułami oparta na sygnałach i slotach Qt:
- Panele emitują sygnały o akcjach
- FileController odbiera sygnały i wykonuje operacje
- MainWindow łączy sygnały z odpowiednimi slotami

2. Rozdzielenie logiki:
- FilePanel - odpowiada za wyświetlanie i wybór plików
- FunctionPanel - obsługa klawiszy funkcyjnych
- FileController - wykonywanie operacji na plikach

3. Przepływ danych:
- FunctionPanel emituje sygnał o akcji
- MainWindow przekazuje żądanie do FileController
- FileController pobiera dane z odpowiednich paneli i wykonuje operację


- - - 



```python
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QListWidget, QPushButton, QLabel, QMessageBox)
from PyQt5.QtCore import pyqtSignal, QObject
import os
import shutil
from typing import Optional

class FileOperationEvent:
    def __init__(self, source_path: str, target_path: str):
        self.source_path = source_path
        self.target_path = target_path

class FilePanel(QWidget):
    item_selected = pyqtSignal(str)
    
    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self.current_path = ""
        self.selected_item: Optional[str] = None
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Panel nagłówka z obecną ścieżką
        self.path_label = QLabel(self.current_path)
        layout.addWidget(self.path_label)
        
        # Lista plików
        self.file_list = QListWidget()
        self.file_list.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.file_list)
        
    def _on_selection_changed(self):
        current_item = self.file_list.currentItem()
        if current_item:
            self.selected_item = current_item.text()
            full_path = os.path.join(self.current_path, self.selected_item)
            self.item_selected.emit(full_path)
            
    def get_selected_path(self) -> Optional[str]:
        if self.selected_item:
            return os.path.join(self.current_path, self.selected_item)
        return None
    
    def set_path(self, path: str):
        self.current_path = path
        self.path_label.setText(path)
        self._refresh_file_list()
        
    def _refresh_file_list(self):
        self.file_list.clear()
        try:
            items = os.listdir(self.current_path)
            self.file_list.addItems(items)
        except Exception as e:
            QMessageBox.warning(self, "Błąd", f"Nie można odczytać katalogu: {str(e)}")

class FunctionPanel(QWidget):
    copy_requested = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self._init_ui()
        
    def _init_ui(self):
        layout = QHBoxLayout(self)
        
        # Przycisk F5 (kopiowanie)
        self.copy_btn = QPushButton("F5 - Kopiuj")
        self.copy_btn.clicked.connect(self.copy_requested.emit)
        layout.addWidget(self.copy_btn)
        
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F5:
            self.copy_requested.emit()

class FileOperationController(QObject):
    operation_started = pyqtSignal(str)  # Sygnał z opisem operacji
    operation_completed = pyqtSignal(bool, str)  # Status i opis wyniku
    
    def copy_files(self, event: FileOperationEvent):
        try:
            self.operation_started.emit(f"Kopiowanie: {event.source_path} -> {event.target_path}")
            
            if os.path.isfile(event.source_path):
                target_file = os.path.join(event.target_path, os.path.basename(event.source_path))
                shutil.copy2(event.source_path, target_file)
            else:
                target_dir = os.path.join(event.target_path, os.path.basename(event.source_path))
                shutil.copytree(event.source_path, target_dir)
                
            self.operation_completed.emit(True, "Kopiowanie zakończone pomyślnie")
            
        except Exception as e:
            self.operation_completed.emit(False, f"Błąd kopiowania: {str(e)}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.file_controller = FileOperationController()
        self._init_ui()
        self._connect_signals()
        
    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Panele plików
        panels_widget = QWidget()
        panels_layout = QHBoxLayout(panels_widget)
        self.left_panel = FilePanel("Lewy panel")
        self.right_panel = FilePanel("Prawy panel")
        panels_layout.addWidget(self.left_panel)
        panels_layout.addWidget(self.right_panel)
        
        # Panel funkcyjny
        self.function_panel = FunctionPanel()
        
        layout.addWidget(panels_widget)
        layout.addWidget(self.function_panel)
        
        # Status bar do wyświetlania informacji
        self.statusBar().showMessage("Gotowy")
        
    def _connect_signals(self):
        # Łączenie sygnału kopiowania
        self.function_panel.copy_requested.connect(self._handle_copy_request)
        
        # Łączenie sygnałów kontrolera
        self.file_controller.operation_started.connect(
            lambda msg: self.statusBar().showMessage(msg))
        self.file_controller.operation_completed.connect(self._handle_operation_completed)
        
    def _handle_copy_request(self):
        source_path = self.left_panel.get_selected_path()
        target_path = self.right_panel.current_path
        
        if not source_path or not target_path:
            QMessageBox.warning(self, "Błąd", "Wybierz plik źródłowy i folder docelowy")
            return
            
        event = FileOperationEvent(source_path, target_path)
        self.file_controller.copy_files(event)
        
    def _handle_operation_completed(self, success: bool, message: str):
        self.statusBar().showMessage(message)
        if success:
            self.right_panel._refresh_file_list()  # Odśwież panel docelowy

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

```

Główne elementy implementacji:

1. FilePanel - zarządza wyświetlaniem i wyborem plików
2. FunctionPanel - obsługuje przyciski i klawisze funkcyjne
3. FileOperationController - wykonuje operacje na plikach
4. FileOperationEvent - przekazuje dane między komponentami
5. MainWindow - koordynuje pracę wszystkich komponentów

Komunikacja odbywa się przez sygnały pyqtSignal, a operacje są wykonywane asynchronicznie z informacją zwrotną o statusie.