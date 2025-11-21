import pytest
import os
import zipfile
import tarfile
import shutil
from unittest.mock import Mock
import io # Dodaj import io

# Import the ArchiveManager class
from file_operations.archive_manager import ArchiveManager

@pytest.fixture
def temp_dir(tmp_path):
    """Tworzy tymczasowy katalog do testów i zwraca jego ścieżkę."""
    return tmp_path

@pytest.fixture
def mock_main_window():
    """Tworzy mock obiektu main_window z paskiem statusu."""
    mock_window = Mock()
    mock_window.status_bar = Mock()
    mock_window.status_bar.showMessage = Mock()
    return mock_window

def create_dummy_file(path, content="test content"):
    """Tworzy plik z przykładową zawartością, upewniając się, że katalog nadrzędny istnieje."""
    os.makedirs(os.path.dirname(path), exist_ok=True) # Upewnij się, że katalog nadrzędny istnieje
    with open(path, "w") as f:
        f.write(content)

def create_dummy_directory(path):
    """Tworzy pusty katalog."""
    os.makedirs(path, exist_ok=True)

# --- Testy tworzenia archiwów ZIP ---

def test_create_zip_from_file(temp_dir, mock_main_window):
    file_path = temp_dir / "test_file.txt"
    create_dummy_file(file_path)
    archive_path = temp_dir / "test_archive.zip"

    manager = ArchiveManager(mock_main_window)
    manager.create_zip_archive(str(file_path), str(archive_path))

    assert archive_path.exists()
    with zipfile.ZipFile(archive_path, 'r') as zipf:
        assert "test_file.txt" in zipf.namelist()
        assert zipf.read("test_file.txt").decode() == "test content"
    mock_main_window.status_bar.showMessage.assert_called_with(f"Utworzono archiwum: {archive_path}")

def test_create_zip_from_directory(temp_dir, mock_main_window):
    dir_path = temp_dir / "test_dir"
    create_dummy_directory(dir_path)
    create_dummy_file(dir_path / "file1.txt", "content1")
    create_dummy_file(dir_path / "subdir" / "file2.txt", "content2") # Tworzenie podkatalogu
    archive_path = temp_dir / "test_dir_archive.zip"

    manager = ArchiveManager(mock_main_window)
    manager.create_zip_archive(str(dir_path), str(archive_path))

    assert archive_path.exists()
    with zipfile.ZipFile(archive_path, 'r') as zipf:
        namelist = zipf.namelist()
        assert "test_dir/file1.txt" in namelist
        assert "test_dir/subdir/file2.txt" in namelist
        assert zipf.read("test_dir/file1.txt").decode() == "content1"
        assert zipf.read("test_dir/subdir/file2.txt").decode() == "content2"
    mock_main_window.status_bar.showMessage.assert_called_with(f"Utworzono archiwum: {archive_path}")

# --- Testy wypakowywania archiwów ZIP ---

def test_extract_zip_archive(temp_dir, mock_main_window):
    archive_path = temp_dir / "archive_to_extract.zip"
    extract_path = temp_dir / "extracted_zip"
    
    with zipfile.ZipFile(archive_path, 'w') as zipf:
        zipf.writestr("file_in_zip.txt", "zip content")
        zipf.writestr("sub/another_file.txt", "more zip content")

    manager = ArchiveManager(mock_main_window)
    manager.extract_zip_archive(str(archive_path), str(extract_path))

    assert (extract_path / "file_in_zip.txt").exists()
    assert (extract_path / "sub" / "another_file.txt").exists()
    assert (extract_path / "file_in_zip.txt").read_text() == "zip content"
    assert (extract_path / "sub" / "another_file.txt").read_text() == "more zip content"
    mock_main_window.status_bar.showMessage.assert_called_with(f"Wypakowano archiwum do: {extract_path}")

# --- Testy tworzenia archiwów TAR ---

def test_create_tar_from_file(temp_dir, mock_main_window):
    file_path = temp_dir / "tar_file.txt"
    create_dummy_file(file_path)
    archive_path = temp_dir / "test_archive.tar"

    manager = ArchiveManager(mock_main_window)
    manager.create_tar_archive(str(file_path), str(archive_path))

    assert archive_path.exists()
    with tarfile.open(archive_path, 'r') as tarf:
        assert "tar_file.txt" in tarf.getnames()
    mock_main_window.status_bar.showMessage.assert_called_with(f"Utworzono archiwum TAR: {archive_path}")

def test_create_tar_from_directory(temp_dir, mock_main_window):
    dir_path = temp_dir / "tar_dir"
    create_dummy_directory(dir_path)
    create_dummy_file(dir_path / "fileA.txt", "contentA")
    create_dummy_file(dir_path / "subtar" / "fileB.txt", "contentB")
    archive_path = temp_dir / "test_dir_archive.tar"

    manager = ArchiveManager(mock_main_window)
    manager.create_tar_archive(str(dir_path), str(archive_path))

    assert archive_path.exists()
    with tarfile.open(archive_path, 'r') as tarf:
        namelist = tarf.getnames()
        assert "tar_dir/fileA.txt" in namelist
        assert "tar_dir/subtar/fileB.txt" in namelist
    mock_main_window.status_bar.showMessage.assert_called_with(f"Utworzono archiwum TAR: {archive_path}")

def test_create_tar_gz_from_file(temp_dir, mock_main_window):
    file_path = temp_dir / "tar_gz_file.txt"
    create_dummy_file(file_path)
    archive_path = temp_dir / "test_archive.tar.gz"

    manager = ArchiveManager(mock_main_window)
    manager.create_tar_archive(str(file_path), str(archive_path), compression="gz")

    assert archive_path.exists()
    with tarfile.open(archive_path, 'r:gz') as tarf:
        assert "tar_gz_file.txt" in tarf.getnames()
    mock_main_window.status_bar.showMessage.assert_called_with(f"Utworzono archiwum TAR: {archive_path}")

# --- Testy wypakowywania archiwów TAR ---

def test_extract_tar_archive(temp_dir, mock_main_window):
    archive_path = temp_dir / "archive_to_extract.tar"
    extract_path = temp_dir / "extracted_tar"
    
    # Utwórz rzeczywiste pliki i katalogi na dysku
    tar_source_dir = temp_dir / "tar_source"
    (tar_source_dir).mkdir()
    create_dummy_file(tar_source_dir / "file_in_tar.txt", "tar content")
    (tar_source_dir / "sub_tar").mkdir()
    create_dummy_file(tar_source_dir / "sub_tar" / "another_file.txt", "more tar content")

    with tarfile.open(archive_path, 'w') as tarf:
        tarf.add(str(tar_source_dir), arcname=".") # Dodaj katalog źródłowy do archiwum

    manager = ArchiveManager(mock_main_window)
    manager.extract_tar_archive(str(archive_path), str(extract_path))

    assert (extract_path / "file_in_tar.txt").exists()
    assert (extract_path / "sub_tar" / "another_file.txt").exists()
    assert (extract_path / "file_in_tar.txt").read_text() == "tar content"
    assert (extract_path / "sub_tar" / "another_file.txt").read_text() == "more tar content"
    mock_main_window.status_bar.showMessage.assert_called_with(f"Wypakowano archiwum do: {extract_path}")

def test_extract_tar_gz_archive(temp_dir, mock_main_window):
    archive_path = temp_dir / "archive_to_extract.tar.gz"
    extract_path = temp_dir / "extracted_tar_gz"
    
    # Utwórz rzeczywisty plik na dysku
    tar_gz_source_file = temp_dir / "tar_gz_source.txt"
    create_dummy_file(tar_gz_source_file, "tar gz content")

    with tarfile.open(archive_path, 'w:gz') as tarf:
        tarf.add(str(tar_gz_source_file), arcname="file_in_tar_gz.txt") # Dodaj plik do archiwum

    manager = ArchiveManager(mock_main_window)
    manager.extract_tar_archive(str(archive_path), str(extract_path))

    assert (extract_path / "file_in_tar_gz.txt").exists()
    assert (extract_path / "file_in_tar_gz.txt").read_text() == "tar gz content"
    mock_main_window.status_bar.showMessage.assert_called_with(f"Wypakowano archiwum do: {extract_path}")

# --- Testy obsługi błędów ---

def test_create_zip_archive_error(temp_dir, mock_main_window):
    # Próba utworzenia archiwum z nieistniejącego źródła
    non_existent_path = temp_dir / "non_existent.txt"
    archive_path = temp_dir / "error_archive.zip"

    manager = ArchiveManager(mock_main_window)
    manager.create_zip_archive(str(non_existent_path), str(archive_path))
    
    mock_main_window.status_bar.showMessage.assert_called_once()
    actual_message = mock_main_window.status_bar.showMessage.call_args[0][0]
    assert "Błąd podczas tworzenia archiwum ZIP: [Errno 2] No such file or directory:" in actual_message

def test_extract_zip_archive_error(temp_dir, mock_main_window):
    # Próba wypakowania uszkodzonego archiwum
    corrupted_archive_path = temp_dir / "corrupted.zip"
    create_dummy_file(corrupted_archive_path, "not a zip file")
    extract_path = temp_dir / "error_extract"

    manager = ArchiveManager(mock_main_window)
    manager.extract_zip_archive(str(corrupted_archive_path), str(extract_path))

    mock_main_window.status_bar.showMessage.assert_called_once()
    actual_message = mock_main_window.status_bar.showMessage.call_args[0][0]
    assert "Błąd podczas wypakowywania archiwum ZIP: File is not a zip file" in actual_message

def test_create_tar_archive_error(temp_dir, mock_main_window):
    # Próba utworzenia archiwum z nieistniejącego źródła
    non_existent_path = temp_dir / "non_existent_tar.txt"
    archive_path = temp_dir / "error_archive.tar"

    manager = ArchiveManager(mock_main_window)
    manager.create_tar_archive(str(non_existent_path), str(archive_path))
    
    mock_main_window.status_bar.showMessage.assert_called_once()
    actual_message = mock_main_window.status_bar.showMessage.call_args[0][0]
    assert "Błąd podczas tworzenia archiwum TAR: [Errno 2] No such file or directory:" in actual_message

def test_extract_tar_archive_error(temp_dir, mock_main_window):
    # Próba wypakowania uszkodzonego archiwum
    corrupted_archive_path = temp_dir / "corrupted.tar"
    create_dummy_file(corrupted_archive_path, "not a tar file")
    extract_path = temp_dir / "error_extract_tar"

    manager = ArchiveManager(mock_main_window)
    manager.extract_tar_archive(str(corrupted_archive_path), str(extract_path))

    mock_main_window.status_bar.showMessage.assert_called_once()
    actual_message = mock_main_window.status_bar.showMessage.call_args[0][0]
    assert "Błąd podczas wypakowywania archiwum TAR: file could not be opened successfully:" in actual_message
