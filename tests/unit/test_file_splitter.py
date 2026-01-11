import os
import sys
import zlib
import pytest
from unittest.mock import MagicMock

# Dodajemy główny katalog projektu do ścieżki, aby móc importować moduły aplikacji
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Dodajemy ścieżkę do pluginu, aby móc go zaimportować bezpośrednio
plugin_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../plugins/org.quickfile/file_splitter/1.1.0'))
sys.path.insert(0, plugin_path)

try:
    from plugin import FileSplitterPlugin
except ImportError as e:
    pytest.fail(f"Nie można zaimportować pluginu FileSplitter: {e}")

@pytest.fixture
def splitter_plugin():
    return FileSplitterPlugin()

def test_split_file_logic(tmp_path, splitter_plugin):
    """
    Testuje logikę dzielenia pliku na części oraz generowanie sumy kontrolnej.
    """
    # 1. Przygotowanie pliku źródłowego (1 KB danych)
    source_file = tmp_path / "test_data.bin"
    content = b"A" * 1024
    source_file.write_bytes(content)
    
    # 2. Katalog docelowy
    dest_dir = tmp_path / "output"
    
    # 3. Opcje: dzielimy na kawałki po 256 bajtów (powinno wyjść dokładnie 4 pliki)
    chunk_size = 256
    options = {
        "chunk_size": chunk_size,
        "generate_checksum": True
    }
    
    # 4. Mocki dla kontekstu zadania (symulacja środowiska TaskQueueManager)
    mock_progress = MagicMock()
    mock_context = MagicMock()
    mock_context.is_cancelled = False
    mock_task = MagicMock()
    
    # 5. Uruchomienie podziału
    splitter_plugin.split_file(str(source_file), str(dest_dir), options, mock_progress, mock_context, mock_task)
    
    # 6. Weryfikacja wyników
    assert dest_dir.exists()
    files = sorted(list(dest_dir.glob("*")))
    
    # Oczekujemy plików: .001, .002, .003, .004 oraz .crc32
    part_files = sorted([f for f in files if f.suffix != '.crc32'])
    checksum_files = [f for f in files if f.suffix == '.crc32']
    
    assert len(part_files) == 4, f"Oczekiwano 4 części, znaleziono {len(part_files)}"
    assert len(checksum_files) == 1, "Nie znaleziono pliku sumy kontrolnej"
    
    # Sprawdzenie zawartości pliku .crc32
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
    
    # Sprawdzenie czy status zadania był aktualizowany
    mock_task.set_details.assert_called()

def test_split_file_cancellation(tmp_path, splitter_plugin):
    """Testuje czy operacja reaguje na flagę anulowania."""
    source_file = tmp_path / "cancel.bin"
    source_file.write_bytes(b"B" * 100)
    dest_dir = tmp_path / "cancel_out"
    
    mock_context = MagicMock()
    mock_context.is_cancelled = True  # Symulacja anulowania przed startem
    
    splitter_plugin.split_file(str(source_file), str(dest_dir), {"chunk_size": 10}, MagicMock(), mock_context, MagicMock())
    
    # Jeśli anulowano na początku, katalog może powstać, ale nie powinno być w nim plików
    if dest_dir.exists():
        assert len(list(dest_dir.glob("*"))) == 0