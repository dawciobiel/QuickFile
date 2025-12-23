import os

class UIStateProvider:
    """A dedicated class to provide information about the UI state."""

    def __init__(self, folder_browser):
        self.folder_browser = folder_browser

    def get_active_panel_widget(self):
        """
        Returns the currently active PanelWidget.
        If no panel is explicitly active, defaults to the left panel.
        """
        active_panel = self.folder_browser.active_panel_widget
        if active_panel:
            return active_panel
        # Fallback to the left panel if no panel has focus
        return self.folder_browser.get_left_panel_widget()

    def get_active_panel_path(self):
        """Returns the current path of the active panel."""
        active_panel = self.get_active_panel_widget()
        if active_panel:
            return active_panel.file_view.get_current_path()
        return None

    def get_inactive_panel_path(self):
        """Returns the current path of the inactive panel."""
        inactive_panel = self.folder_browser.get_inactive_panel_widget()
        if inactive_panel:
            return inactive_panel.file_view.get_current_path()
        return None

    def get_selected_paths(self):
        """Returns a list of all selected paths in the active panel."""
        return self.folder_browser.get_selected_paths()

    def get_current_selected_path(self):
        """Returns the path of the single currently selected item."""
        return self.folder_browser.get_current_selected_path()

    def get_selected_file_path(self):
        """Returns the path of the single selected file in the active panel, or None."""
        selected_path = self.get_current_selected_path()
        if selected_path and os.path.isfile(selected_path):
            return selected_path
        return None
