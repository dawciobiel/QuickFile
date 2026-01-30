import os
import sys
import zlib
import pytest
import time
from PyQt6.QtCore import QEventLoop, QTimer
from unittest.mock import MagicMock

# Dodajemy główny katalog projektu do ścieżki, aby móc importować moduły aplikacji
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Importujemy nowe fixtury i klasy
from app.enums import TaskType
from app.task_queue_manager import Task
from app.background_task_manager import TaskContext # Importujemy TaskContext
# Importujemy AsyncTestHelper z conftest.py (niejawnie, pytest to załatwi)
from tests.plugin_helpers import get_latest_plugin_path

def test_split_file_logic(tmp_path, async_plugin_test_env):
    """
    Testuje logikę dzielenia pliku na części oraz generowanie sumy kontrolnej
    z wykorzystaniem asynchronicznej architektury pluginów.
    """
    plugin_manager, background_task_manager, async_test_helper_factory = async_plugin_test_env
    async_helper = async_test_helper_factory("org.quickfile.file_splitter")

    # 1. Przygotowanie pliku źródłowego (1 KB danych)
    source_file = tmp_path / "test_data.bin"
    content = b"A" * 1024
    source_file.write_bytes(content)
    
    # 2. Katalog docelowy
    dest_dir = tmp_path / "output"
    dest_dir.mkdir() # Upewniamy się, że katalog istnieje

    # 3. Opcje: dzielimy na kawałki po 256 bajtów (powinno wyjść dokładnie 4 pliki)
    chunk_size = 256
    options = {
        "chunk_size": chunk_size,
        "generate_checksum": True,
        "plugin_id": "org.quickfile.file_splitter" # Ważne dla TaskQueueManager
    }
    
    # 4. Tworzenie obiektu Task
    task = Task(TaskType.SPLIT_FILE, source_paths=[str(source_file)], destination_path=str(dest_dir), options=options)
    
    # Rejestrujemy zadanie w BTM
    background_task_manager.register_plugin_task(task, async_helper.plugin_wrapper)

    # 5. Uruchomienie podziału asynchronicznie
    async_helper.plugin_wrapper.execute_task(
        task_id=task.id,
        action_id="split_file",
        source_path=str(source_file),
        dest_dir=str(dest_dir),
        options=options
    )
    
    # Czekamy na zakończenie
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: async_helper.task_finished_event.exit(3))
    timer.start(5000)
    
    exit_code = async_helper.task_finished_event.exec()
    timer.stop()
    
    if exit_code == 3:
        pytest.fail("Timeout waiting for task completion")
    elif exit_code != 0:
        pytest.fail(f"Task failed with code {exit_code}: {async_helper.failed_error}")
    
    # 6. Weryfikacja wyników
    assert dest_dir.exists()
    files = sorted(list(dest_dir.glob("*")))
    
    # Oczekujemy plików: .001, .002, .003, .004 oraz .crc32
    part_files = sorted([f for f in files if f.suffix != '.crc32'])
    checksum_files = [f for f in files if f.suffix == '.crc32']
    
    assert len(part_files) == 4, f"Oczekiwano 4 części, znaleziono {len(part_files)}"
    
    # Jeśli plik sumy kontrolnej istnieje, sprawdzamy jego zawartość
    if len(checksum_files) == 1:
        crc_content = checksum_files[0].read_text(encoding='utf-8')
        expected_crc = f"{zlib.crc32(content) & 0xFFFFFFFF:08X}"
        assert f"filename={source_file.name}" in crc_content
        assert f"filenameutf8={source_file.name}" in crc_content
        assert f"size={len(content)}" in crc_content
        assert f"crc32={expected_crc}" in crc_content
        assert "parts_count=4" in crc_content
    
    # Sprawdzenie nazw plików
    assert part_files[0].name.endswith(".001")
    assert part_files[-1].name.endswith(".004")

    # Sprawdzenie rozmiarów
    for p in part_files:
        assert p.stat().st_size == 256, f"Plik {p.name} ma nieprawidłowy rozmiar"
        
    # Sprawdzenie zawartości pierwszego pliku
    assert part_files[0].read_bytes() == b"A" * 256


def test_split_file_cancellation(tmp_path, async_plugin_test_env):
    """Testuje czy operacja reaguje na flagę anulowania w asynchronicznym pluginie."""
    plugin_manager, background_task_manager, async_test_helper_factory = async_plugin_test_env
    async_helper = async_test_helper_factory("org.quickfile.file_splitter")

    source_file = tmp_path / "cancel.bin"
    # Zwiększamy rozmiar pliku do 500MB, aby operacja trwała dłużej
    with open(source_file, "wb") as f:
        f.seek(500 * 1024 * 1024 - 1)
        f.write(b"\0")
        
    dest_dir = tmp_path / "cancel_out"
    dest_dir.mkdir()

    options = {
        "chunk_size": 1024 * 1024, # 1MB chunks
        "generate_checksum": False,
        "plugin_id": "org.quickfile.file_splitter"
    }
    
    task = Task(TaskType.SPLIT_FILE, source_paths=[str(source_file)], destination_path=str(dest_dir), options=options)
    
    background_task_manager.register_plugin_task(task, async_helper.plugin_wrapper)
    
    async_helper.plugin_wrapper.execute_task(
        task_id=task.id,
        action_id="split_file",
        source_path=str(source_file),
        dest_dir=str(dest_dir),
        options=options
    )

    # Dajemy chwilę na rozpoczęcie operacji
    time.sleep(0.05)

    # Anulujemy zadanie
    background_task_manager.cancel_task(task.id)

    # Czekamy na zakończenie zadania
    async_helper.finished_result = None
    async_helper.failed_error = None
    
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: async_helper.task_finished_event.exit(3)) # Timeout
    timer.start(5000) # 5 sekund na anulowanie

    exit_code = async_helper.task_finished_event.exec()
    timer.stop()

    if exit_code == 3:
        pytest.fail("Timeout waiting for task cancellation")
    elif exit_code == 0:
        pytest.fail("Task finished successfully instead of being cancelled")
    elif exit_code == 1:
        task_id, error, traceback_str = async_helper.failed_error
        assert "cancelled" in error.lower() or "InterruptedError" in error
    elif exit_code == 2:
        pytest.fail(f"Critical error during cancellation: {async_helper.failed_error}")

    # Jeśli anulowano, katalog docelowy powinien być pusty lub nie istnieć
    if dest_dir.exists():
        # Może zostać kilka plików, jeśli anulowanie nie było natychmiastowe,
        # ale nie powinno być ich 500 (tyle ile chunków)
        assert len(list(dest_dir.glob("*"))) < 500
