import os
import sys
import zlib
import pytest
from unittest.mock import MagicMock

# Dodajemy główny katalog projektu do ścieżki
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from tests.plugin_helpers import get_latest_plugin_path

# Add the path to the latest version of the plugin
try:
    plugin_path = get_latest_plugin_path('org.quickfile', 'file_splitter')
    sys.path.insert(0, plugin_path)
except Exception as e:
    pytest.fail(f"Could not find plugin 'file_splitter': {e}")

try:
    from plugin import FileSplitterPlugin
except ImportError as e:
    pytest.fail(f"Nie można zaimportować pluginu FileSplitter: {e}")

@pytest.fixture
def splitter_plugin():
    return FileSplitterPlugin()

def test_join_files_success(tmp_path, splitter_plugin):
    # 1. Przygotowanie pliku źródłowego i podział
    source_content = b"A" * 1024 + b"B" * 1024
    source_file = tmp_path / "original.bin"
    source_file.write_bytes(source_content)
    
    dest_dir = tmp_path / "parts"
    dest_dir.mkdir()
    
    # Dzielimy na kawałki po 1024 bajty -> 2 części
    options_split = {"chunk_size": 1024, "generate_checksum": True}
    mock_context = MagicMock()
    mock_context.is_cancelled = False
    mock_task = MagicMock()
    
    splitter_plugin.split_file(str(source_file), str(dest_dir), options_split, MagicMock(), mock_context, mock_task)
    
    # 2. Test łączenia
    join_dest = tmp_path / "joined"
    join_dest.mkdir()
    
    # Scenariusz A: Łączenie wskazując plik .001
    part1 = dest_dir / "original.bin.001"
    options_join = {"output_filename": "joined_from_part.bin"}
    
    splitter_plugin.join_files(str(part1), str(join_dest), options_join, MagicMock(), mock_context, mock_task)
    
    joined_file = join_dest / "joined_from_part.bin"
    assert joined_file.exists()
    assert joined_file.read_bytes() == source_content
    # Weryfikacja czy sprawdzono sumę kontrolną (bo plik .crc32 istniał obok)
    mock_task.set_details.assert_any_call("Join complete. Checksum verified OK.")
    
    # Scenariusz B: Łączenie wskazując plik .crc32
    crc_file = dest_dir / "original.bin.crc32"
    options_join_crc = {"output_filename": "joined_from_crc.bin"}
    
    splitter_plugin.join_files(str(crc_file), str(join_dest), options_join_crc, MagicMock(), mock_context, mock_task)
    
    joined_file_crc = join_dest / "joined_from_crc.bin"
    assert joined_file_crc.exists()
    assert joined_file_crc.read_bytes() == source_content
    # Weryfikacja czy sprawdzono sumę kontrolną
    mock_task.set_details.assert_any_call("Join complete. Checksum verified OK.")

def test_join_files_crc_mismatch(tmp_path, splitter_plugin):
    # Symulacja uszkodzonego pliku
    dest_dir = tmp_path / "parts_corrupt"
    dest_dir.mkdir()
    
    # Tworzymy "część" ręcznie
    (dest_dir / "data.bin.001").write_bytes(b"CORRUPT_DATA")
    # Tworzymy plik CRC z sumą dla innej zawartości (np. b"VALID")
    valid_crc = zlib.crc32(b"VALID") & 0xFFFFFFFF
    (dest_dir / "data.bin.crc32").write_text(f"filename=data.bin\ncrc32={valid_crc:08X}\n", encoding='utf-8')
    
    mock_context = MagicMock()
    mock_context.is_cancelled = False
    
    with pytest.raises(ValueError, match="CRC32 mismatch"):
        splitter_plugin.join_files(str(dest_dir / "data.bin.crc32"), str(dest_dir), {"output_filename": "out.bin"}, MagicMock(), mock_context, MagicMock())

def test_join_files_from_part_without_crc(tmp_path, splitter_plugin):
    """Testuje łączenie plików gdy plik .crc32 nie istnieje."""
    source_content = b"DATA" * 100
    source_file = tmp_path / "nocrc.bin"
    source_file.write_bytes(source_content)
    
    dest_dir = tmp_path / "parts_nocrc"
    dest_dir.mkdir()
    
    # Dzielimy bez generowania sumy kontrolnej
    options_split = {"chunk_size": 100, "generate_checksum": False}
    mock_context = MagicMock()
    mock_context.is_cancelled = False
    mock_task = MagicMock()
    
    splitter_plugin.split_file(str(source_file), str(dest_dir), options_split, MagicMock(), mock_context, mock_task)
    
    # Łączymy wskazując .001
    part1 = dest_dir / "nocrc.bin.001"
    options_join = {"output_filename": "joined.bin"}
    
    splitter_plugin.join_files(str(part1), str(tmp_path), options_join, MagicMock(), mock_context, mock_task)
    
    joined_file = tmp_path / "joined.bin"
    assert joined_file.exists()
    assert joined_file.read_bytes() == source_content
    mock_task.set_details.assert_any_call("Join complete. No checksum to verify.")

def test_join_dialog_logic_guess_filename(tmp_path):
    """Testuje logikę zgadywania nazwy pliku (symulacja zachowania JoinDialog)."""
    # Przygotowanie środowiska
    part_file = tmp_path / "movie.001"
    part_file.write_bytes(b"data")
    
    crc_file = tmp_path / "movie.crc32"
    crc_file.write_text("filename=RealMovieName.mkv\n", encoding='utf-8')
    
    # Symulacja logiki z JoinDialog (uproszczona)
    source_file = str(part_file)
    suggested_name = None
    crc_path = source_file[:-4] + ".crc32"
    
    if os.path.exists(crc_path):
        with open(crc_path, 'r', encoding='utf-8-sig') as f:
            for line in f:
                line = line.rstrip('\n')
                if line.startswith("filename="):
                    suggested_name = line.split("=", 1)[1]
    
    assert suggested_name == "RealMovieName.mkv"

def test_join_files_missing_part_detected(tmp_path, splitter_plugin):
    """Testuje czy brakująca część jest wykrywana dzięki parts_count w .crc32."""
    dest_dir = tmp_path / "parts_missing"
    dest_dir.mkdir()
    
    # Tworzymy plik .crc32 sugerujący 3 części
    crc_content = (
        "filename=data.bin\n"
        "parts_count=3\n"
        "crc32=00000000\n"
    )
    (dest_dir / "data.bin.crc32").write_text(crc_content, encoding='utf-8')
    
    # Tworzymy tylko część 1 i 3 (brak części 2)
    (dest_dir / "data.bin.001").write_bytes(b"A")
    (dest_dir / "data.bin.003").write_bytes(b"C")
    
    with pytest.raises(FileNotFoundError, match="Missing part 2"):
        splitter_plugin.join_files(str(dest_dir / "data.bin.crc32"), str(dest_dir), {"output_filename": "out.bin"}, MagicMock(), MagicMock(), MagicMock())
