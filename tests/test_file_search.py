# test_file_search.py

import unittest
from unittest.mock import MagicMock

# Assuming the main application structure and necessary modules are accessible
# For a real test, we might need to mock more or import from the actual application

class TestFileSearch(unittest.TestCase):

    def setUp(self):
        # Mocking necessary components
        self.mock_main_window = MagicMock()
        self.mock_file_manager = MagicMock()
        self.mock_folder_browser = MagicMock()
        self.mock_search_dialog = MagicMock()
        self.mock_qdialog = MagicMock()
        self.mock_qdialog.exec.return_value = QDialog.DialogCode.Accepted # Simulate accepting the dialog

        # Mocking the structure of folder_browser and main_window
        self.mock_main_window.folder_browser = self.mock_folder_browser
        self.mock_main_window.file_manager = self.mock_file_manager
        self.mock_main_window.search_input = MagicMock()
        self.mock_main_window.search_input.text.return_value = "nohup.out"
        self.mock_main_window.search_input.returnPressed.connect = MagicMock() # Mock the connect method

        # Mocking current_paths and active_panel_widget
        self.mock_folder_browser.current_paths = {
            "mock_panel_widget": "/some/test/path"
        }
        self.mock_folder_browser.active_panel_widget = "mock_panel_widget" # This should be the actual widget instance, but a string will do for mock

        # Mocking the SearchDialog creation
        # Need to import QDialog if it's used in the actual SearchDialog class
        from PyQt6.QtWidgets import QDialog
        unittest.mock.patch('utils.search_dialog.SearchDialog', return_value=self.mock_qdialog).start()
        unittest.mock.patch('core.main_window.SearchDialog', return_value=self.mock_qdialog).start()
        
        # Need to mock QCoreApplication if it is used in the actual code
        from PyQt6.QtCore import QCoreApplication
        unittest.mock.patch('PyQt6.QtCore.QCoreApplication', MagicMock())

    def tearDown(self):
        unittest.mock.patch.stopall()

    def test_file_search_with_valid_path(self):
        # Simulate the setup in main_window.py where active_panel_widget is correctly set
        # This test case assumes the fix in core/main_window.py is applied.
        
        # Mock the file_manager.search_files call to return some results
        self.mock_file_manager.search_files.return_value = ["/some/test/path/nohup.out"]
        
        # Call the method that initiates the search
        # This would typically be called by a signal, e.g., returnPressed
        # We need to call the method directly as if it were triggered
        self.mock_main_window.start_file_search()

        # Assert that file_manager.search_files was called with the correct path and pattern
        self.mock_file_manager.search_files.assert_called_once_with("/some/test/path", "nohup.out")
        
        # Assert that the SearchDialog was created and shown
        self.mock_search_dialog.assert_called_once()
        self.mock_qdialog.exec.assert_called_once()

    def test_file_search_with_none_path(self):
        # This test simulates the error condition before the fix.
        # We need to mock the folder_browser to return None for the active_panel_widget
        self.mock_folder_browser.current_paths = {}
        self.mock_folder_browser.active_panel_widget = None
        
        # Expecting the file_manager.search_files to be called with None path
        # and for the error message to be shown.
        # Mocking show_error_message to check if it's called
        mock_show_error = unittest.mock.patch('utils.dialogs.show_error_message').start()

        self.mock_main_window.start_file_search()

        # Assert that file_manager.search_files was NOT called because path was None
        self.mock_file_manager.search_files.assert_not_called()
        # Assert that the error message was shown
        mock_show_error.assert_called_once_with(self.mock_main_window, "Search Error", "Starting path ‘None’ is invalid or does not exist.")

if __name__ == '__main__':
    unittest.main()
