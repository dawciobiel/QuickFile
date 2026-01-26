import os
import sys
import zlib
import pytest
from unittest.mock import MagicMock

# Dodajemy główny katalog projektu do ścieżki
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Importujemy nowe fixtury i klasy
from app.task_queue_manager import Task, TaskType
from tests.conftest import async_plugin_test_env # Importujemy fixturę z conftest
from tests.plugin_helpers import get_latest_plugin_path

def test_join_files_success(tmp_path, async_plugin_test_env):
    """
    Testuje logikę łączenia plików z wykorzystaniem asynchronicznej architektury pluginów.
    """
    plugin_manager, background_task_manager, async_test_helper_factory = async_plugin_test_env
    async_helper = async_test_helper_factory("org.quickfile.file_splitter")

    # 1. Przygotowanie pliku źródłowego i podział
    source_content = b"A" * 1024 + b"B" * 1024
    source_file = tmp_path / "original.bin"
    source_file.write_bytes(source_content)
    
    dest_dir_split = tmp_path / "parts_split"
    dest_dir_split.mkdir()
    
    # Dzielimy na kawałki po 1024 bajty -> 2 części
    options_split = {
        "chunk_size": 1024,
        "generate_checksum": True,
        "plugin_id": "org.quickfile.file_splitter"
    }
    
    task_split = Task(TaskType.SPLIT_FILE, source_paths=[str(source_file)], destination_path=str(dest_dir_split), options=options_split)
    
    async_helper.run_plugin_method_async(
        task_split,
        "split_file",
        source_path=str(source_file),
        dest_dir=str(dest_dir_split),
        options=options_split
    )
    
    # 2. Test łączenia
    join_dest = tmp_path / "joined"
    join_dest.mkdir()
    
    # Scenariusz A: Łączenie wskazując plik .001
    part1 = dest_dir_split / "original.bin.001"
    options_join_a = {
        "output_filename": "joined_from_part.bin",
        "plugin_id": "org.quickfile.file_splitter"
    }
    task_join_a = Task(TaskType.JOIN_FILES, source_paths=[str(part1)], destination_path=str(join_dest), options=options_join_a)
    
    async_helper.run_plugin_method_async(
        task_join_a,
        "join_files",
        source_path=str(part1),
        dest_dir=str(join_dest),
        options=options_join_a
    )
    
    joined_file_a = join_dest / "joined_from_part.bin"
    assert joined_file_a.exists()
    assert joined_file_a.read_bytes() == source_content

    # Scenariusz B: Łączenie wskazując plik .crc32
    crc_file = dest_dir_split / "original.bin.crc32"
    options_join_b = {
        "output_filename": "joined_from_crc.bin",
        "plugin_id": "org.quickfile.file_splitter"
    }
    task_join_b = Task(TaskType.JOIN_FILES, source_paths=[str(crc_file)], destination_path=str(join_dest), options=options_join_b)
    
    async_helper.run_plugin_method_async(
        task_join_b,
        "join_files",
        source_path=str(crc_file),
        dest_dir=str(join_dest),
        options=options_join_b
    )
    
    joined_file_b = join_dest / "joined_from_crc.bin"
    assert joined_file_b.exists()
    assert joined_file_b.read_bytes() == source_content


def test_join_files_crc_mismatch(tmp_path, async_plugin_test_env):
    """
    Testuje łączenie plików z niezgodną sumą kontrolną w asynchronicznym pluginie.
    """
    plugin_manager, background_task_manager, async_test_helper_factory = async_plugin_test_env
    async_helper = async_test_helper_factory("org.quickfile.file_splitter")

    # Symulacja uszkodzonego pliku
    dest_dir = tmp_path / "parts_corrupt"
    dest_dir.mkdir()
    
    # Tworzymy "część" ręcznie
    (dest_dir / "data.bin.001").write_bytes(b"CORRUPT_DATA")
    # Tworzymy plik CRC z sumą dla innej zawartości (np. b"VALID")
    valid_crc = zlib.crc32(b"VALID") & 0xFFFFFFFF
    (dest_dir / "data.bin.crc32").write_text(f"filename=data.bin\ncrc32={valid_crc:08X}\n", encoding='utf-8')
    
    options_join = {
        "output_filename": "out.bin",
        "plugin_id": "org.quickfile.file_splitter"
    }
    task_join = Task(TaskType.JOIN_FILES, source_paths=[str(dest_dir / "data.bin.crc32")], destination_path=str(dest_dir), options=options_join)
    
    with pytest.raises(Exception) as excinfo:
        async_helper.run_plugin_method_async(
            task_join,
            "join_files",
            source_path=str(dest_dir / "data.bin.crc32"),
            dest_dir=str(dest_dir),
            options=options_join
        )
    assert "CRC32 mismatch" in str(excinfo.value)


def test_join_files_from_part_without_crc(tmp_path, async_plugin_test_env):
    """
    Testuje łączenie plików gdy plik .crc32 nie istnieje w asynchronicznym pluginie.
    """
    plugin_manager, background_task_manager, async_test_helper_factory = async_plugin_test_env
    async_helper = async_test_helper_factory("org.quickfile.file_splitter")

    source_content = b"DATA" * 100
    source_file = tmp_path / "nocrc.bin"
    source_file.write_bytes(source_content)
    
    dest_dir_split = tmp_path / "parts_nocrc_split"
    dest_dir_split.mkdir()
    
    # Dzielimy bez generowania sumy kontrolnej
    options_split = {
        "chunk_size": 100,
        "generate_checksum": False,
        "plugin_id": "org.quickfile.file_splitter"
    }
    task_split = Task(TaskType.SPLIT_FILE, source_paths=[str(source_file)], destination_path=str(dest_dir_split), options=options_split)
    
    async_helper.run_plugin_method_async(
        task_split,
        "split_file",
        source_path=str(source_file),
        dest_dir=str(dest_dir_split),
        options=options_split
    )

    # Łączymy wskazując .001
    part1 = dest_dir_split / "nocrc.bin.001"
    options_join = {
        "output_filename": "joined.bin",
        "plugin_id": "org.quickfile.file_splitter"
    }
    task_join = Task(TaskType.JOIN_FILES, source_paths=[str(part1)], destination_path=str(tmp_path), options=options_join)
    
    async_helper.run_plugin_method_async(
        task_join,
        "join_files",
        source_path=str(part1),
        dest_dir=str(tmp_path),
        options=options_join
    )
    
    joined_file = tmp_path / "joined.bin"
    assert joined_file.exists()
    assert joined_file.read_bytes() == source_content


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

def test_join_files_missing_part_detected(tmp_path, async_plugin_test_env):
    """
    Testuje czy brakująca część jest wykrywana dzięki parts_count w .crc32 w asynchronicznym pluginie.
    """
    plugin_manager, background_task_manager, async_test_helper_factory = async_plugin_test_env
    async_helper = async_test_helper_factory("org.quickfile.file_splitter")

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
    
    options_join = {
        "output_filename": "out.bin",
        "plugin_id": "org.quickfile.file_splitter"
    }
    task_join = Task(TaskType.JOIN_FILES, source_paths=[str(dest_dir / "data.bin.crc32")], destination_path=str(dest_dir), options=options_join)
    
    with pytest.raises(Exception) as excinfo:
        async_helper.run_plugin_method_async(
            task_join,
            "join_files",
            source_path=str(dest_dir / "data.bin.crc32"),
            dest_dir=str(dest_dir),
            options=options_join
        )
    assert "Missing part 2" in str(excinfo.value)
