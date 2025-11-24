import logging
import os
import shutil
from utils.dialogs import show_error_message


class FileManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.clipboard = None
        self.is_cut_operation = False

    def copy_item_with_options(self, source_path, destination_path, options):
        """Copies a file/folder with options."""
        if not source_path or not os.path.exists(source_path):
            show_error_message(self.main_window, "Copy Error", f"Source path '{source_path}' is invalid or does not exist.")
            return

        if not destination_path or not os.path.exists(destination_path):
            show_error_message(self.main_window, "Copy Error", f"Destination path '{destination_path}' does not exist.")
            return

        try:
            base_name = os.path.basename(source_path)
            destination_full_path = os.path.join(destination_path, base_name)

            if os.path.exists(destination_full_path) and not options.get("overwrite"):
                show_error_message(self.main_window, "Copy Error", f"File '{base_name}' already exists in the destination. Check 'Overwrite' to replace it.")
                return

            copy_function = shutil.copy2 if options.get("preserve_timestamp") else shutil.copy
            
            if os.path.isdir(source_path):
                if os.path.exists(destination_full_path):
                    shutil.rmtree(destination_full_path)
                shutil.copytree(source_path, destination_full_path, copy_function=copy_function)
            else:
                copy_function(source_path, destination_full_path)

            self.main_window.status_bar.showMessage(f"Copied '{base_name}' to '{destination_path}'")
            self.main_window.folder_browser.refresh_view()

        except Exception as e:
            logging.exception(f"Error copying item from {source_path} to {destination_path}: {e}")
            show_error_message(self.main_window, "Copy Error", str(e))

    def move_item_with_options(self, source_path, destination_path, options):
        """Moves a file/folder with options."""
        if not source_path or not os.path.exists(source_path):
            show_error_message(self.main_window, "Move Error", f"Source path '{source_path}' is invalid or does not exist.")
            return

        if not destination_path or not os.path.exists(destination_path):
            show_error_message(self.main_window, "Move Error", f"Destination path '{destination_path}' does not exist.")
            return

        try:
            base_name = os.path.basename(source_path)
            destination_full_path = os.path.join(destination_path, base_name)

            if os.path.exists(destination_full_path):
                if not options.get("overwrite"):
                    show_error_message(self.main_window, "Move Error", f"File '{base_name}' already exists in the destination. Check 'Overwrite' to replace it.")
                    return
                else:
                    if os.path.isdir(destination_full_path):
                        shutil.rmtree(destination_full_path)
                    else:
                        os.remove(destination_full_path)

            self.main_window.status_bar.showMessage(f"Moved '{base_name}' to '{destination_full_path}'")
            self.main_window.folder_browser.refresh_view()

        except Exception as e:
            logging.exception(f"Error moving item from {source_path} to {destination_path}: {e}")
            show_error_message(self.main_window, "Move Error", str(e))

    def delete_item_with_confirmation(self, item_path):
        """Deletes a file/folder after confirmation."""
        if not item_path or not os.path.exists(item_path):
            show_error_message(self.main_window, "Deletion Error", f"Path '{item_path}' is invalid or does not exist.")
            return

        try:
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
            self.main_window.status_bar.showMessage(f"Deleted: {item_path}")
            self.main_window.folder_browser.refresh_view()
        except Exception as e:
            logging.exception(f"Error deleting item {item_path}: {e}")
            show_error_message(self.main_window, "Deletion Error", str(e))

    def copy_item(self, path):
        if not path or not os.path.exists(path):
            show_error_message(self.main_window, "Copy Error", f"Path '{path}' is invalid or does not exist.")
            return
        self.clipboard = path
        self.is_cut_operation = False
        self.main_window.status_bar.showMessage(f"Copied: {path}")
    def cut_item(self, path):
        if not path or not os.path.exists(path):
            show_error_message(self.main_window, "Cut Error", f"Path '{path}' is invalid or does not exist.")
            return
        self.clipboard = path
        self.is_cut_operation = True
        self.main_window.status_bar.showMessage(f"Cut: {path}")
    def paste_item(self, destination_path):
        if not self.clipboard:
            show_error_message(self.main_window, "Paste Error", "Clipboard is empty.")
            return

        if not os.path.exists(destination_path):
            show_error_message(self.main_window, "Paste Error", f"Destination path '{destination_path}' does not exist.")
            return

        try:
            base_name = os.path.basename(self.clipboard)
            destination_full_path = os.path.join(destination_path, base_name)

            if self.is_cut_operation:
                shutil.move(self.clipboard, destination_full_path)
                self.main_window.status_bar.showMessage(f"Moved '{base_name}' to '{destination_full_path}'")
            else:
                if os.path.isdir(self.clipboard):
                    shutil.copytree(self.clipboard, destination_full_path)
                else:
                    shutil.copy2(self.clipboard, destination_full_path)
                self.main_window.status_bar.showMessage(f"Copied '{base_name}' to '{destination_full_path}'")

        except Exception as e:
            logging.exception(f"Error pasting item to {destination_path}: {e}")
            show_error_message(self.main_window, "Paste Error", str(e))
        finally:
            self.clipboard = None
            self.is_cut_operation = False

    def delete_item(self, path):
        if not path or not os.path.exists(path):
            show_error_message(self.main_window, "Deletion Error", f"Path '{path}' is invalid or does not exist.")
            return

        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            self.main_window.status_bar.showMessage(f"Deleted: {path}")
        except Exception as e:
            logging.exception(f"Error deleting item {path}: {e}")
            show_error_message(self.main_window, "Deletion Error", str(e))

    def rename_item(self, old_path, new_name):
        if not old_path or not os.path.exists(old_path):
            show_error_message(self.main_window, "Rename Error", f"Path '{old_path}' is invalid or does not exist.")
            return

        if not new_name:
            show_error_message(self.main_window, "Rename Error", "New name cannot be empty.")
            return

        try:
            directory = os.path.dirname(old_path)
            new_path = os.path.join(directory, new_name)
            os.rename(old_path, new_path)
            self.main_window.status_bar.showMessage(f"Renamed to: {new_name}")
        except Exception as e:
            logging.exception(f"Error renaming item {old_path} to {new_name}: {e}")
            show_error_message(self.main_window, "Rename Error", str(e))

    def create_file(self, directory, file_name):
        """Creates a new, empty file."""
        if not directory or not os.path.exists(directory):
            show_error_message(self.main_window, "File Creation Error", f"Directory '{directory}' is invalid or does not exist.")
            return

        if not file_name:
            show_error_message(self.main_window, "File Creation Error", "File name cannot be empty.")
            return

        file_path = os.path.join(directory, file_name)
        if os.path.exists(file_path):
            show_error_message(self.main_window, "File Creation Error", f"File '{file_name}' already exists.")
            return

        try:
            with open(file_path, 'w') as f:
                pass  # Creates an empty file
            self.main_window.status_bar.showMessage(f"File created: {file_path}")
        except Exception as e:
            logging.exception(f"Error creating file {file_path}: {e}")
            show_error_message(self.main_window, "File Creation Error", str(e))

    def create_directory(self, parent_directory, directory_name):
        """Creates a new folder."""
        if not parent_directory or not os.path.exists(parent_directory):
            show_error_message(self.main_window, "Folder Creation Error", f"Parent directory '{parent_directory}' is invalid or does not exist.")
            return

        if not directory_name:
            show_error_message(self.main_window, "Folder Creation Error", "Folder name cannot be empty.")
            return

        directory_path = os.path.join(parent_directory, directory_name)
        if os.path.exists(directory_path):
            show_error_message(self.main_window, "Folder Creation Error", f"Folder '{directory_name}' already exists.")
            return

        try:
            os.makedirs(directory_path)
            self.main_window.status_bar.showMessage(f"Folder created: {directory_path}")
        except Exception as e:
            logging.exception(f"Error creating directory {directory_path}: {e}")
            show_error_message(self.main_window, "Folder Creation Error", str(e))

    def search_files(self, root_path, pattern):
        """Searches for files and folders matching the pattern in the given path."""
        if not root_path or not os.path.exists(root_path):
            show_error_message(self.main_window, "Search Error", f"Starting path '{root_path}' is invalid or does not exist.")
            return []

        found_items = []
        for dirpath, dirnames, filenames in os.walk(root_path):
            for name in dirnames + filenames:
                if pattern.lower() in name.lower():
                    found_items.append(os.path.join(dirpath, name))
        
        if found_items:
            self.main_window.status_bar.showMessage(f"Found {len(found_items)} items for '{pattern}'.")
        else:
            self.main_window.status_bar.showMessage(f"No items found for '{pattern}'.")
        
        return found_items
