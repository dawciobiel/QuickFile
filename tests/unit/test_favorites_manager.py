# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import pytest
import json
from favorites.favorites_manager import FavoritesManager

@pytest.fixture
def mock_favorites_file(tmp_path):
    """Fixture to create a temporary favorites file path."""
    return tmp_path / "favorites.json"

@pytest.fixture
def favorites_manager(mocker, mock_favorites_file):
    """Fixture to create a FavoritesManager instance with a mocked favorites file."""
    # Mock migration logic to prevent side effects
    mocker.patch('favorites.favorites_manager.os.path.exists', return_value=False)
    
    # Let the manager initialize normally (it will point to a real config path)
    fm = FavoritesManager()
    
    # NOW, patch the instance's file path to our temporary one
    fm.favorites_file = str(mock_favorites_file)
    # Reset favorites list as it might have loaded from a real file
    fm.favorites = []
    
    return fm

def test_initialization_with_no_file(favorites_manager):
    """Test that favorites list is empty when no file exists."""
    assert favorites_manager.get_favorites() == []

def test_add_favorite(favorites_manager):
    """Test adding a new favorite path."""
    path = "/home/user/documents"
    favorites_manager.add_favorite(path)
    assert favorites_manager.get_favorites() == [path]

def test_add_duplicate_favorite(favorites_manager):
    """Test that adding a duplicate favorite does not change the list."""
    path = "/home/user/pictures"
    favorites_manager.add_favorite(path)
    favorites_manager.add_favorite(path) # Add again
    assert favorites_manager.get_favorites() == [path]

def test_remove_favorite(favorites_manager):
    """Test removing an existing favorite."""
    path1 = "/home/user/music"
    path2 = "/home/user/videos"
    favorites_manager.add_favorite(path1)
    favorites_manager.add_favorite(path2)
    
    favorites_manager.remove_favorite(path1)
    
    assert favorites_manager.get_favorites() == [path2]

def test_remove_non_existent_favorite(favorites_manager):
    """Test that removing a non-existent favorite does nothing."""
    path = "/home/user/downloads"
    favorites_manager.add_favorite(path)
    
    favorites_manager.remove_favorite("/non/existent/path")
    
    assert favorites_manager.get_favorites() == [path]

def test_favorites_are_saved_to_file(favorites_manager, mock_favorites_file):
    """Test that changes are correctly saved to the file."""
    path = "/home/user/desktop"
    favorites_manager.add_favorite(path)
    
    with open(mock_favorites_file, 'r') as f:
        saved_favorites = json.load(f)
    
    assert saved_favorites == [path]
    
    favorites_manager.remove_favorite(path)
    
    with open(mock_favorites_file, 'r') as f:
        saved_favorites_after_remove = json.load(f)
        
    assert saved_favorites_after_remove == []

def test_loading_from_existing_file(mocker, mock_favorites_file):
    """Test that favorites are correctly loaded from an existing file."""
    initial_favorites = ["/path/one", "/path/two"]
    with open(mock_favorites_file, 'w') as f:
        json.dump(initial_favorites, f)

    # We need to patch exists to return True for this specific test
    def exists_side_effect(path):
        return str(path) == str(mock_favorites_file)

    mocker.patch('favorites.favorites_manager.os.path.exists', side_effect=exists_side_effect)
    
    # Let the manager initialize normally
    fm = FavoritesManager()
    # And then patch its file path
    fm.favorites_file = str(mock_favorites_file)
    # Manually call load_favorites again to load from our mock file
    fm.favorites = fm.load_favorites()
    
    assert fm.get_favorites() == initial_favorites
