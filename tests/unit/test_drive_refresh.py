import pytest
from unittest.mock import MagicMock, patch
from browser.folder_browser import PanelWidget

@pytest.fixture
def mock_dependencies():
    """Tworzy atrapy zależności wymaganych przez PanelWidget."""
    settings = MagicMock()
    theme = MagicMock()
    plugin = MagicMock()
    # Mockujemy plugin widoku, aby nie tworzył skomplikowanych widgetów
    plugin.get_view_mode_plugin.return_value = None
    # Mockujemy plugin dyskowy
    plugin.get_disk_utils_plugin.return_value = None
    notification = MagicMock()
    return settings, theme, plugin, notification

def test_drive_refresh_on_popup(qtbot, mock_dependencies):
    """
    Testuje, czy lista napędów odświeża się po wyemitowaniu sygnału
    popup_about_to_show (symulacja kliknięcia w dropdown).
    """
    settings, theme, plugin, notification = mock_dependencies

    # Patchujemy metodę _get_available_drives, aby kontrolować, jakie dyski "widzi" system
    with patch('browser.folder_browser.PanelWidget._get_available_drives') as mock_get_drives:
        # KROK 1: Stan początkowy - tylko root
        mock_get_drives.return_value = ['/']

        # Inicjalizacja panelu
        panel = PanelWidget(settings, None, theme, plugin, notification)
        qtbot.addWidget(panel)

        # Sprawdzenie stanu początkowego
        assert panel.drive_combo.count() == 1
        assert panel.drive_combo.itemText(0) == '/'

        # KROK 2: Symulacja podłączenia pendrive'a
        mock_get_drives.return_value = ['/', '/mnt/usb_drive']

        # Symulujemy otwarcie dropdowna (emitujemy sygnał ręcznie)
        panel.drive_combo.popup_about_to_show.emit()

        # Sprawdzenie czy lista się zaktualizowała
        assert panel.drive_combo.count() == 2
        items = [panel.drive_combo.itemText(i) for i in range(panel.drive_combo.count())]
        assert '/mnt/usb_drive' in items

        # KROK 3: Symulacja odłączenia
        mock_get_drives.return_value = ['/']
        
        # Ponowne otwarcie dropdowna
        panel.drive_combo.popup_about_to_show.emit()

        # Sprawdzenie czy napęd zniknął
        assert panel.drive_combo.count() == 1
        assert panel.drive_combo.itemText(0) == '/'