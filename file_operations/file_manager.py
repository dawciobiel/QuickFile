import logging
import os
import shutil
import send2trash # Import send2trash
from app.translation_manager import translation_manager # Import our new manager

class FileManagerError(Exception):
    """Custom exception for FileManager errors."""
    pass

class FileManager:
    def __init__(self):
        self.clipboard = None
        self.is_cut_operation = False

    def _validate_path(self, path, must_exist=True, is_directory=False, is_file=False, name="Path"):
        """
        Validates a given path based on specified criteria.
        Raises appropriate exceptions with translated messages.
        """
        if not path:
            raise ValueError(translation_manager.translate("FileManager", f"{name} cannot be empty."))

        if must_exist and not os.path.exists(path):
            raise FileNotFoundError(translation_manager.translate("FileManager", f"{name} '{path}' does not exist."))
        
        if os.path.exists(path): # Only check type if path exists
            if is_directory and not os.path.isdir(path):
                raise NotADirectoryError(translation_manager.translate("FileManager", f"{name} '{path}' is not a directory."))
            if is_file and not os.path.isfile(path):
                raise IsADirectoryError(translation_manager.translate("FileManager", f"{name} '{path}' is not a file."))
        
        return path

    def _handle_destination_exists(self, destination_full_path, source_is_dir, overwrite_option, item_name):
        """
        Handles the scenario where the destination path already exists.
        Removes the existing item if overwrite is allowed, otherwise raises an error.
        """
        if os.path.exists(destination_full_path):
            if source_is_dir and os.path.isfile(destination_full_path):
                raise IsADirectoryError(translation_manager.translate("FileManager", f"Cannot move/copy directory '{item_name}' to existing file '{destination_full_path}'."))
            elif not overwrite_option:
                raise FileExistsError(translation_manager.translate("FileManager", f"Item '{item_name}' already exists in the destination."))
            else:
                # If overwriting, remove existing item first
                if os.path.isdir(destination_full_path):
                    shutil.rmtree(destination_full_path)
                else:
                    os.remove(destination_full_path)
                logging.info(f"Removed existing item at {destination_full_path} for overwrite.")

    def copy_item_with_options(self, source_path, destination_path, options):
        """Copies a file/folder with options."""
        try:
            self._validate_path(source_path, must_exist=True, name="Source path")
            self._validate_path(destination_path, must_exist=True, is_directory=True, name="Destination path")

            base_name = os.path.basename(source_path)
            destination_full_path = os.path.join(destination_path, base_name)
            source_is_dir = os.path.isdir(source_path)

            self._handle_destination_exists(destination_full_path, source_is_dir, options.get("overwrite"), base_name)

            copy_function = shutil.copy2 if options.get("preserve_timestamp") else shutil.copy
            
            if source_is_dir:
                shutil.copytree(source_path, destination_full_path, copy_function=copy_function)
            else:
                copy_function(source_path, destination_full_path)

            return translation_manager.translate("FileManager", f"Copied '{base_name}' to '{destination_path}'")

        except (ValueError, FileNotFoundError, FileExistsError, NotADirectoryError, IsADirectoryError) as e:
            raise e # Re-raise specific errors for caller to handle
        except OSError as e:
            logging.exception(f"Error copying item from {source_path} to {destination_full_path}: {e}")
            raise FileManagerError(translation_manager.translate("FileManager", f"Error copying item: {e}"))

    def move_item_with_options(self, source_path, destination_path, options):
        """Moves a file/folder with options."""
        try:
            self._validate_path(source_path, must_exist=True, name="Source path")
            self._validate_path(destination_path, must_exist=True, is_directory=True, name="Destination path")

            base_name = os.path.basename(source_path)
            destination_full_path = os.path.join(destination_path, base_name)
            source_is_dir = os.path.isdir(source_path)

            self._handle_destination_exists(destination_full_path, source_is_dir, options.get("overwrite"), base_name)
                
            shutil.move(source_path, destination_full_path)

            return translation_manager.translate("FileManager", f"Moved '{base_name}' to '{destination_full_path}'")

        except (ValueError, FileNotFoundError, FileExistsError, NotADirectoryError, IsADirectoryError) as e:
            raise e # Re-raise specific errors for caller to handle
        except OSError as e:
            logging.exception(f"Error moving item from {source_path} to {destination_full_path}: {e}")
            raise FileManagerError(translation_manager.translate("FileManager", f"Error moving item: {e}"))

    def delete_item(self, item_path, move_to_trash=True):
        """
        Deletes a file/folder or moves it to the system trash.
        If move_to_trash is True, attempts to move to trash. Otherwise, deletes permanently.
        """
        try:
            self._validate_path(item_path, must_exist=True, name="Item path")

            if move_to_trash:
                try:
                    send2trash.send2trash(item_path)
                    return translation_manager.translate("FileManager", f"Moved to Trash: {item_path}")
                except send2trash.TrashPermissionError as e:
                    logging.warning(f"Permission error moving {item_path} to trash, deleting permanently: {e}")
                    # Fallback to permanent delete if trash fails due to permissions
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                    return translation_manager.translate("FileManager", f"Deleted permanently (trash failed): {item_path}")
                except Exception as e:
                    logging.warning(f"Error moving {item_path} to trash, deleting permanently: {e}")
                    # Fallback to permanent delete for other trash errors
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                    return translation_manager.translate("FileManager", f"Deleted permanently (trash failed): {item_path}")
            else:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
                return translation_manager.translate("FileManager", f"Deleted permanently: {item_path}")
        except (ValueError, FileNotFoundError, NotADirectoryError, IsADirectoryError) as e:
            raise e
        except OSError as e:
            logging.exception(f"Error deleting item {item_path}: {e}")
            raise FileManagerError(translation_manager.translate("FileManager", f"Error deleting item: {e}"))

    def copy_to_clipboard(self, path):
        try:
            self._validate_path(path, must_exist=True, name="Path")
            self.clipboard = path
            self.is_cut_operation = False
            return translation_manager.translate("FileManager", f"Copied: {path}")
        except (ValueError, FileNotFoundError, NotADirectoryError, IsADirectoryError) as e:
            raise e
        except OSError as e:
            logging.exception(f"Error copying to clipboard {path}: {e}")
            raise FileManagerError(translation_manager.translate("FileManager", f"Error copying to clipboard: {e}"))

    def cut_to_clipboard(self, path):
        try:
            self._validate_path(path, must_exist=True, name="Path")
            self.clipboard = path
            self.is_cut_operation = True
            return translation_manager.translate("FileManager", f"Cut: {path}")
        except (ValueError, FileNotFoundError, NotADirectoryError, IsADirectoryError) as e:
            raise e
        except OSError as e:
            logging.exception(f"Error cutting to clipboard {path}: {e}")
            raise FileManagerError(translation_manager.translate("FileManager", f"Error cutting to clipboard: {e}"))

    def paste_item(self, destination_path):
        if not self.clipboard:
            raise ValueError(translation_manager.translate("FileManager", "Clipboard is empty."))

        try:
            self._validate_path(destination_path, must_exist=True, is_directory=True, name="Destination path")

            base_name = os.path.basename(self.clipboard)
            destination_full_path = os.path.join(destination_path, base_name)

            # For paste, we assume overwrite is always true if it's a cut operation,
            # or if the user explicitly allows it for copy.
            # For simplicity here, we'll just check if it exists and handle it.
            # A more complex UI might ask for overwrite confirmation.
            # For now, let's assume paste implies overwrite if the item is cut.
            # If it's a copy, we might need an options dict for paste too.
            # For now, let's keep it simple and assume no overwrite for copy-paste if exists.
            
            # Simplified overwrite logic for paste:
            if os.path.exists(destination_full_path):
                if self.is_cut_operation: # If cut, always overwrite
                    if os.path.isdir(destination_full_path):
                        shutil.rmtree(destination_full_path)
                    else:
                        os.remove(destination_full_path)
                    logging.info(f"Removed existing item at {destination_full_path} for cut-paste overwrite.")
                else: # If copy, raise error if exists
                    raise FileExistsError(translation_manager.translate("FileManager", f"Item '{base_name}' already exists in the destination."))


            if self.is_cut_operation:
                shutil.move(self.clipboard, destination_full_path)
                message = translation_manager.translate("FileManager", f"Moved '{base_name}' to '{destination_full_path}'")
            else:
                if os.path.isdir(self.clipboard):
                    shutil.copytree(self.clipboard, destination_full_path)
                else:
                    shutil.copy2(self.clipboard, destination_full_path)
                message = translation_manager.translate("FileManager", f"Copied '{base_name}' to '{destination_full_path}'")

            return message

        except (ValueError, FileNotFoundError, FileExistsError, NotADirectoryError, IsADirectoryError) as e:
            raise e
        except OSError as e:
            logging.exception(f"Error pasting item to {destination_path}: {e}")
            raise FileManagerError(translation_manager.translate("FileManager", f"Error pasting item: {e}"))
        finally:
            self.clipboard = None
            self.is_cut_operation = False

    def rename_item(self, old_path, new_name):
        try:
            self._validate_path(old_path, must_exist=True, name="Old path")
            if not new_name:
                raise ValueError(translation_manager.translate("FileManager", "New name cannot be empty."))

            directory = os.path.dirname(old_path)
            new_path = os.path.join(directory, new_name)
            if os.path.exists(new_path):
                raise FileExistsError(translation_manager.translate("FileManager", f"An item named '{new_name}' already exists in '{directory}'."))
            os.rename(old_path, new_path)
            return translation_manager.translate("FileManager", f"Renamed to: {new_name}")
        except (ValueError, FileNotFoundError, FileExistsError, NotADirectoryError, IsADirectoryError) as e:
            raise e
        except OSError as e:
            logging.exception(f"Error renaming item {old_path} to {new_name}: {e}")
            raise FileManagerError(translation_manager.translate("FileManager", f"Error renaming item: {e}"))

    def create_file(self, directory, file_name):
        """Creates a new, empty file."""
        try:
            self._validate_path(directory, must_exist=True, name="Directory")
            if not file_name:
                raise ValueError(translation_manager.translate("FileManager", "File name cannot be empty."))

            file_path = os.path.join(directory, file_name)
            if os.path.exists(file_path):
                raise FileExistsError(translation_manager.translate("FileManager", f"File '{file_name}' already exists."))

            with open(file_path, 'w') as f:
                pass  # Creates an empty file
            return translation_manager.translate("FileManager", f"File created: {file_path}")
        except (ValueError, FileNotFoundError, FileExistsError, NotADirectoryError, IsADirectoryError) as e:
            raise e
        except OSError as e:
            logging.exception(f"Error creating file {file_path}: {e}")
            raise FileManagerError(translation_manager.translate("FileManager", f"Error creating file: {e}"))

    def create_directory(self, parent_directory, directory_name):
        """Creates a new folder."""
        try:
            self._validate_path(parent_directory, must_exist=True, name="Parent directory")
            if not directory_name:
                raise ValueError(translation_manager.translate("FileManager", "Folder name cannot be empty."))

            directory_path = os.path.join(parent_directory, directory_name)
            if os.path.exists(directory_path):
                raise FileExistsError(translation_manager.translate("FileManager", f"Folder '{directory_name}' already exists."))

            os.makedirs(directory_path)
            return translation_manager.translate("FileManager", f"Folder created: {directory_path}")
        except (ValueError, FileNotFoundError, FileExistsError, NotADirectoryError, IsADirectoryError) as e:
            raise e
        except OSError as e:
            logging.exception(f"Error creating directory {directory_path}: {e}")
            raise FileManagerError(translation_manager.translate("FileManager", f"Error creating directory: {e}"))

    def search_files(self, root_path, pattern):
        """Searches for files and folders matching the pattern in the given path."""
        try:
            self._validate_path(root_path, must_exist=True, is_directory=True, name="Starting path")

            found_items = []
            for dirpath, dirnames, filenames in os.walk(root_path):
                for name in dirnames + filenames:
                    if pattern.lower() in name.lower():
                        found_items.append(os.path.join(dirpath, name))
            
            message = translation_manager.translate("FileManager", f"Found {len(found_items)} items for '{pattern}'.") if found_items else translation_manager.translate("FileManager", f"No items found for '{pattern}'.")
            return found_items, message
        except (ValueError, FileNotFoundError, NotADirectoryError, IsADirectoryError) as e:
            raise e
        except OSError as e:
            logging.exception(f"Error searching files in {root_path} with pattern {pattern}: {e}")
            raise FileManagerError(translation_manager.translate("FileManager", f"Error during file search: {e}"))
