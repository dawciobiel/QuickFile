# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import pytest
import json
from app.theme_manager import ThemeManager
from unittest.mock import MagicMock

@pytest.fixture
def mock_themes_dir(tmp_path):
    """Fixture to create a temporary directory structure for themes."""
    themes_dir = tmp_path / "themes"
    themes_dir.mkdir()
    
    # Create a valid 'dark' theme
    dark_theme_dir = themes_dir / "dark"
    dark_theme_dir.mkdir()
    with open(dark_theme_dir / "palette.json", "w") as f:
        json.dump({"background": "#000", "foreground": "#FFF"}, f)
    with open(dark_theme_dir / "file_styles.json", "w") as f:
        json.dump({"file_styles": {"txt": {"foreground_color": "#AAA"}}}, f)
    with open(dark_theme_dir / "style.qss", "w") as f:
        f.write("QWidget { color: @@foreground@@; }")
        
    # Create an 'empty' theme
    (themes_dir / "empty").mkdir()
    
    return themes_dir

@pytest.fixture
def theme_manager(mocker, mock_themes_dir):
    """Fixture to create a ThemeManager with a mocked themes directory."""
    # Mock the function that determines the themes directory path
    mocker.patch('app.theme_manager.get_resource_path', return_value=mock_themes_dir)
    
    # Mock settings manager as it's a dependency
    mock_settings_manager = MagicMock()
    return ThemeManager(mock_settings_manager)

def test_discover_themes(theme_manager):
    """Test that themes are correctly discovered from the directory structure."""
    # Note: The order is not guaranteed, so we use a set for comparison
    assert set(theme_manager.get_themes()) == {"dark", "empty"}

def test_apply_valid_theme(theme_manager, mocker):
    """Test applying a valid theme loads all its data correctly."""
    mock_app = mocker.patch('app.theme_manager.QApplication.instance')
    mock_app.return_value.setStyleSheet = MagicMock()

    theme_manager.apply_theme("dark")

    assert theme_manager.current_theme_name == "dark"
    theme_data = theme_manager.get_current_theme_data()
    
    # Check data from palette.json
    assert theme_data["background"] == "#000"
    # Check data from file_styles.json
    assert theme_data["file_styles"]["txt"]["foreground_color"] == "#AAA"
    
    # Check if stylesheet was applied with placeholders replaced
    mock_app.return_value.setStyleSheet.assert_called_once_with("QWidget { color: #FFF; }")

def test_apply_non_existent_theme(theme_manager):
    """Test that applying a non-existent theme does nothing and logs a warning."""
    theme_manager.apply_theme("non_existent")
    assert theme_manager.current_theme_name is None

def test_apply_theme_with_missing_files(theme_manager, mocker):
    """Test applying a theme that is missing palette or style files."""
    mock_app = mocker.patch('app.theme_manager.QApplication.instance')
    mock_app.return_value.setStyleSheet = MagicMock()

    theme_manager.apply_theme("empty")
    
    # Should still apply the theme name, but data will be empty
    assert theme_manager.current_theme_name == "empty"
    # It will have file_styles and special_types as empty dicts
    assert theme_manager.get_current_theme_data() == {'file_styles': {}, 'special_types': {}}
    # setStyleSheet should not be called if style.qss is missing
    mock_app.return_value.setStyleSheet.assert_not_called()
