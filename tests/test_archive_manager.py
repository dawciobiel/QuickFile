import pytest
import os
import zipfile
import tarfile
import shutil
from unittest.mock import MagicMock, patch
import io

# Import the ArchiveManager class and its exceptions
from file_operations.archive_manager import ArchiveManager, ArchiveManagerError, UnrarNotInstalledError

@pytest.fixture
def temp_dir(tmp_path):
    """Tworzy tymczasowy katalog do testów i zwraca jego ścieżkę."""
    return tmp_path

def create_dummy_file(path, content="test content"):
    """Tworzy plik z przykładową zawartością, upewniając się, że katalog nadrzędny istnieje."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)

def create_dummy_directory(path):
    """Tworzy pusty katalog."""
    os.makedirs(path, exist_ok=True)

# --- Testy tworzenia archiwów ZIP ---

def test_create_zip_from_file(temp_dir):
    file_path = temp_dir / "test_file.txt"
    create_dummy_file(file_path)
    archive_path = temp_dir / "test_archive.zip"

    manager = ArchiveManager()
    manager.create_zip_archive([str(file_path)], str(archive_path))

    assert archive_path.exists()
    with zipfile.ZipFile(archive_path, 'r') as zipf:
        assert "test_file.txt" in zipf.namelist()
        assert zipf.read("test_file.txt").decode() == "test content"

def test_create_zip_from_directory(temp_dir):
    dir_path = temp_dir / "test_dir"
    create_dummy_directory(dir_path)
    create_dummy_file(dir_path / "file1.txt", "content1")
    create_dummy_file(dir_path / "subdir" / "file2.txt", "content2")
    archive_path = temp_dir / "test_dir_archive.zip"

    manager = ArchiveManager()
    manager.create_zip_archive([str(dir_path)], str(archive_path))

    assert archive_path.exists()
    with zipfile.ZipFile(archive_path, 'r') as zipf:
        namelist = zipf.namelist()
        assert "test_dir/file1.txt" in namelist
        assert os.path.join("test_dir", "subdir", "file2.txt") in namelist

# --- Testy wypakowywania archiwów ZIP ---

def test_extract_zip_archive(temp_dir):
    archive_path = temp_dir / "archive_to_extract.zip"
    extract_path = temp_dir / "extracted_zip"
    
    with zipfile.ZipFile(archive_path, 'w') as zipf:
        zipf.writestr("file_in_zip.txt", "zip content")
        zipf.writestr("sub/another_file.txt", "more zip content")

    manager = ArchiveManager()
    manager.extract_zip_archive(str(archive_path), str(extract_path))

    assert (extract_path / "file_in_zip.txt").exists()
    assert (extract_path / "sub" / "another_file.txt").exists()
    assert (extract_path / "file_in_zip.txt").read_text() == "zip content"
    assert (extract_path / "sub" / "another_file.txt").read_text() == "more zip content"

# --- Testy tworzenia archiwów TAR ---

def test_create_tar_from_file(temp_dir):
    file_path = temp_dir / "tar_file.txt"
    create_dummy_file(file_path)
    archive_path = temp_dir / "test_archive.tar"

    manager = ArchiveManager()
    manager.create_tar_archive(str(file_path), str(archive_path))

    assert archive_path.exists()
    with tarfile.open(archive_path, 'r') as tarf:
        assert "tar_file.txt" in tarf.getnames()

def test_create_tar_from_directory(temp_dir):
    dir_path = temp_dir / "tar_dir"
    create_dummy_directory(dir_path)
    create_dummy_file(dir_path / "fileA.txt", "contentA")
    create_dummy_file(dir_path / "subtar" / "fileB.txt", "contentB")
    archive_path = temp_dir / "test_dir_archive.tar"

    manager = ArchiveManager()
    manager.create_tar_archive(str(dir_path), str(archive_path))

    assert archive_path.exists()
    with tarfile.open(archive_path, 'r') as tarf:
        namelist = tarf.getnames()
        assert "tar_dir/fileA.txt" in namelist
        assert os.path.join("tar_dir", "subtar", "fileB.txt") in namelist

def test_create_tar_gz_from_file(temp_dir):
    file_path = temp_dir / "tar_gz_file.txt"
    create_dummy_file(file_path)
    archive_path = temp_dir / "test_archive.tar.gz"

    manager = ArchiveManager()
    manager.create_tar_archive(str(file_path), str(archive_path), compression="gz")

    assert archive_path.exists()
    with tarfile.open(archive_path, 'r:gz') as tarf:
        assert "tar_gz_file.txt" in tarf.getnames()

# --- Testy wypakowywania archiwów TAR ---

def test_extract_tar_archive(temp_dir):
    archive_path = temp_dir / "archive_to_extract.tar"
    extract_path = temp_dir / "extracted_tar"
    
    tar_source_dir = temp_dir / "tar_source"
    (tar_source_dir).mkdir()
    create_dummy_file(tar_source_dir / "file_in_tar.txt", "tar content")
    (tar_source_dir / "sub_tar").mkdir()
    create_dummy_file(tar_source_dir / "sub_tar" / "another_file.txt", "more tar content")

    with tarfile.open(archive_path, 'w') as tarf:
        tarf.add(str(tar_source_dir), arcname=".")

    manager = ArchiveManager()
    manager.extract_tar_archive(str(archive_path), str(extract_path))

    assert (extract_path / "file_in_tar.txt").exists()
    assert (extract_path / "sub_tar" / "another_file.txt").exists()

def test_extract_tar_gz_archive(temp_dir):
    archive_path = temp_dir / "archive_to_extract.tar.gz"
    extract_path = temp_dir / "extracted_tar_gz"
    
    tar_gz_source_file = temp_dir / "tar_gz_source.txt"
    create_dummy_file(tar_gz_source_file, "tar gz content")

    with tarfile.open(archive_path, 'w:gz') as tarf:
        tarf.add(str(tar_gz_source_file), arcname="file_in_tar_gz.txt")

    manager = ArchiveManager()
    manager.extract_tar_archive(str(archive_path), str(extract_path))

    assert (extract_path / "file_in_tar_gz.txt").exists()

# --- Testy wypakowywania archiwów RAR ---

@patch('shutil.which')
@patch('rarfile.RarFile')
def test_extract_rar_archive_success(mock_rar_file, mock_shutil_which, temp_dir):
    mock_shutil_which.return_value = "/usr/bin/unrar" # Simulate unrar being installed
    
    archive_path = temp_dir / "test.rar"
    extract_path = temp_dir / "extracted_rar"
    
    # Create a dummy RAR file (rarfile needs a real file to open, even if mocked)
    create_dummy_file(archive_path)

    manager = ArchiveManager()
    
    # Configure the mock RarFile instance
    mock_rar_instance = MagicMock()
    mock_rar_file.return_value.__enter__.return_value = mock_rar_instance

    result = manager.extract_rar_archive(str(archive_path), str(extract_path))

    mock_shutil_which.assert_called_once_with('unrar')
    mock_rar_file.assert_called_once_with(str(archive_path), 'r')
    mock_rar_instance.extractall.assert_called_once_with(str(extract_path))
    assert "Wypakowano archiwum RAR do:" in result

@patch('shutil.which')
def test_extract_rar_archive_unrar_not_installed(mock_shutil_which, temp_dir):
    mock_shutil_which.return_value = None # Simulate unrar not being installed
    
    archive_path = temp_dir / "test.rar"
    extract_path = temp_dir / "extracted_rar"

    manager = ArchiveManager()
    with pytest.raises(UnrarNotInstalledError, match="The 'unrar' tool is not installed or not in the system's PATH."):
        manager.extract_rar_archive(str(archive_path), str(extract_path))
    
    mock_shutil_which.assert_called_once_with('unrar')

@patch('shutil.which')
@patch('rarfile.RarFile')
def test_extract_rar_archive_error(mock_rar_file, mock_shutil_which, temp_dir):
    mock_shutil_which.return_value = "/usr/bin/unrar" # Simulate unrar being installed
    
    archive_path = temp_dir / "corrupted.rar"
    extract_path = temp_dir / "extracted_rar_error"
    
    create_dummy_file(archive_path) # Create a dummy file for rarfile to try and open

    # Simulate an error during RarFile opening or extraction
    mock_rar_file.side_effect = Exception("Simulated RAR extraction error")

    manager = ArchiveManager()
    with pytest.raises(ArchiveManagerError, match="Error extracting RAR archive: Simulated RAR extraction error"):
        manager.extract_rar_archive(str(archive_path), str(extract_path))
    
    mock_shutil_which.assert_called_once_with('unrar')
    mock_rar_file.assert_called_once_with(str(archive_path), 'r')


# --- Testy obsługi błędów ---

def test_create_zip_archive_error(temp_dir):
    non_existent_path = temp_dir / "non_existent.txt"
    archive_path = temp_dir / "error_archive.zip"

    manager = ArchiveManager()
    with pytest.raises(ArchiveManagerError):
        manager.create_zip_archive([str(non_existent_path)], str(archive_path))

def test_extract_zip_archive_error(temp_dir):
    corrupted_archive_path = temp_dir / "corrupted.zip"
    create_dummy_file(corrupted_archive_path, "not a zip file")
    extract_path = temp_dir / "error_extract"

    manager = ArchiveManager()
    with pytest.raises(ArchiveManagerError):
        manager.extract_zip_archive(str(corrupted_archive_path), str(extract_path))

def test_create_tar_archive_error(temp_dir):
    non_existent_path = temp_dir / "non_existent_tar.txt"
    archive_path = temp_dir / "error_archive.tar"

    manager = ArchiveManager()
    with pytest.raises(ArchiveManagerError):
        manager.create_tar_archive(str(non_existent_path), str(archive_path))

def test_extract_tar_archive_error(temp_dir):
    corrupted_archive_path = temp_dir / "corrupted.tar"
    create_dummy_file(corrupted_archive_path, "not a tar file")
    extract_path = temp_dir / "error_extract_tar"

    manager = ArchiveManager()
    with pytest.raises(ArchiveManagerError):
        manager.extract_tar_archive(str(corrupted_archive_path), str(extract_path))
