import logging
import os
import shutil

class FileManagerError(Exception):
    """Custom exception for FileManager errors."""
    pass

class FileManager:
    def __init__(self):
        self.clipboard = None
        self.is_cut_operation = False

    def copy_item_with_options(self, source_path, destination_path, options):
        """Copies a file/folder with options."""
        if not source_path or not os.path.exists(source_path):
            raise FileNotFoundError(f"Source path '{source_path}' is invalid or does not exist.")

        if not destination_path or not os.path.exists(destination_path):
            raise FileNotFoundError(f"Destination path '{destination_path}' does not exist.")

        try:
            base_name = os.path.basename(source_path)
            destination_full_path = os.path.join(destination_path, base_name)

            if os.path.exists(destination_full_path):
                if not options.get("overwrite"):
                    raise FileExistsError(f"File '{base_name}' already exists in the destination.")
                else:
                    # If overwriting, remove existing item first
                    if os.path.isdir(destination_full_path):
                        shutil.rmtree(destination_full_path)
                    else:
                        os.remove(destination_full_path)
                    logging.info(f"Removed existing item at {destination_full_path} for overwrite.")

            copy_function = shutil.copy2 if options.get("preserve_timestamp") else shutil.copy
            
            if os.path.isdir(source_path):
                shutil.copytree(source_path, destination_full_path, copy_function=copy_function)
            else:
                copy_function(source_path, destination_full_path)

            return f"Copied '{base_name}' to '{destination_path}'"

        except FileExistsError:
            raise # Re-raise specific error
        except FileNotFoundError:
            raise # Re-raise specific error
        except Exception as e:
            logging.exception(f"Error copying item from {source_path} to {destination_full_path}: {e}")
            raise FileManagerError(f"Error copying item: {e}")

    def move_item_with_options(self, source_path, destination_path, options):
        """Moves a file/folder with options."""
        if not source_path or not os.path.exists(source_path):
            raise FileNotFoundError(f"Source path '{source_path}' is invalid or does not exist.")

        if not destination_path or not os.path.exists(destination_path):
            raise FileNotFoundError(f"Destination path '{destination_path}' does not exist.")

        try:
            base_name = os.path.basename(source_path)
            destination_full_path = os.path.join(destination_path, base_name)

            if os.path.isdir(source_path):
                if os.path.exists(destination_full_path):
                    if os.path.isfile(destination_full_path):
                        raise IsADirectoryError(f"Cannot move directory '{base_name}' to existing file '{destination_full_path}'.")
                    elif not options.get("overwrite"):
                        raise FileExistsError(f"Directory '{base_name}' already exists in the destination.")
                    else:
                        shutil.rmtree(destination_full_path)
                        logging.info(f"Removed existing directory at {destination_full_path} for overwrite.")
                
                shutil.move(source_path, destination_full_path)
            else: # Moving a file
                if os.path.exists(destination_full_path):
                    if not options.get("overwrite"):
                        raise FileExistsError(f"File '{base_name}' already exists in the destination.")
                    else:
                        os.remove(destination_full_path)
                        logging.info(f"Removed existing file at {destination_full_path} for overwrite.")
                
                shutil.move(source_path, destination_full_path)

            return f"Moved '{base_name}' to '{destination_full_path}'"

        except (FileExistsError, FileNotFoundError, IsADirectoryError):
            raise # Re-raise specific errors
        except Exception as e:
            logging.exception(f"Error moving item from {source_path} to {destination_full_path}: {e}")
            raise FileManagerError(f"Error moving item: {e}")

    def delete_item(self, item_path):
        """Deletes a file/folder."""
        if not item_path or not os.path.exists(item_path):
            raise FileNotFoundError(f"Path '{item_path}' is invalid or does not exist.")

        try:
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
            return f"Deleted: {item_path}"
        except Exception as e:
            logging.exception(f"Error deleting item {item_path}: {e}")
            raise FileManagerError(f"Error deleting item: {e}")

    def copy_to_clipboard(self, path):
        if not path or not os.path.exists(path):
            raise FileNotFoundError(f"Path '{path}' is invalid or does not exist.")
        self.clipboard = path
        self.is_cut_operation = False
        return f"Copied: {path}"

    def cut_to_clipboard(self, path):
        if not path or not os.path.exists(path):
            raise FileNotFoundError(f"Path '{path}' is invalid or does not exist.")
        self.clipboard = path
        self.is_cut_operation = True
        return f"Cut: {path}"

    def paste_item(self, destination_path):
        if not self.clipboard:
            raise ValueError("Clipboard is empty.")

        if not os.path.exists(destination_path):
            raise FileNotFoundError(f"Destination path '{destination_path}' does not exist.")

        try:
            base_name = os.path.basename(self.clipboard)
            destination_full_path = os.path.join(destination_path, base_name)

            if self.is_cut_operation:
                shutil.move(self.clipboard, destination_full_path)
                message = f"Moved '{base_name}' to '{destination_full_path}'"
            else:
                if os.path.isdir(self.clipboard):
                    shutil.copytree(self.clipboard, destination_full_path)
                else:
                    shutil.copy2(self.clipboard, destination_full_path)
                message = f"Copied '{base_name}' to '{destination_full_path}'"

            return message

        except (ValueError, FileNotFoundError):
            raise # Re-raise specific errors
        except Exception as e:
            logging.exception(f"Error pasting item to {destination_path}: {e}")
            raise FileManagerError(f"Error pasting item: {e}")
        finally:
            self.clipboard = None
            self.is_cut_operation = False

    def rename_item(self, old_path, new_name):
        if not old_path or not os.path.exists(old_path):
            raise FileNotFoundError(f"Path '{old_path}' is invalid or does not exist.")

        if not new_name:
            raise ValueError("New name cannot be empty.")

        try:
            directory = os.path.dirname(old_path)
            new_path = os.path.join(directory, new_name)
            if os.path.exists(new_path):
                raise FileExistsError(f"An item named '{new_name}' already exists in '{directory}'.")
            os.rename(old_path, new_path)
            return f"Renamed to: {new_name}"
        except (ValueError, FileNotFoundError, FileExistsError):
            raise # Re-raise specific errors
        except Exception as e:
            logging.exception(f"Error renaming item {old_path} to {new_name}: {e}")
            raise FileManagerError(f"Error renaming item: {e}")

    def create_file(self, directory, file_name):
        """Creates a new, empty file."""
        if not directory or not os.path.exists(directory):
            raise FileNotFoundError(f"Directory '{directory}' is invalid or does not exist.")

        if not file_name:
            raise ValueError("File name cannot be empty.")

        file_path = os.path.join(directory, file_name)
        if os.path.exists(file_path):
            raise FileExistsError(f"File '{file_name}' already exists.")

        try:
            with open(file_path, 'w') as f:
                pass  # Creates an empty file
            return f"File created: {file_path}"
        except (ValueError, FileNotFoundError, FileExistsError):
            raise # Re-raise specific errors
        except Exception as e:
            logging.exception(f"Error creating file {file_path}: {e}")
            raise FileManagerError(f"Error creating file: {e}")

    def create_directory(self, parent_directory, directory_name):
        """Creates a new folder."""
        if not parent_directory or not os.path.exists(parent_directory):
            raise FileNotFoundError(f"Parent directory '{parent_directory}' is invalid or does not exist.")

        if not directory_name:
            raise ValueError("Folder name cannot be empty.")

        directory_path = os.path.join(parent_directory, directory_name)
        if os.path.exists(directory_path):
            raise FileExistsError(f"Folder '{directory_name}' already exists.")

        try:
            os.makedirs(directory_path)
            return f"Folder created: {directory_path}"
        except (ValueError, FileNotFoundError, FileExistsError):
            raise # Re-raise specific errors
        except Exception as e:
            logging.exception(f"Error creating directory {directory_path}: {e}")
            raise FileManagerError(f"Error creating directory: {e}")

    def search_files(self, root_path, pattern):
        """Searches for files and folders matching the pattern in the given path."""
        if not root_path or not os.path.exists(root_path):
            raise FileNotFoundError(f"Starting path '{root_path}' is invalid or does not exist.")

        found_items = []
        try:
            for dirpath, dirnames, filenames in os.walk(root_path):
                for name in dirnames + filenames:
                    if pattern.lower() in name.lower():
                        found_items.append(os.path.join(dirpath, name))
            
            message = f"Found {len(found_items)} items for '{pattern}'." if found_items else f"No items found for '{pattern}'."
            return found_items, message
        except Exception as e:
            logging.exception(f"Error searching files in {root_path} with pattern {pattern}: {e}")
            raise FileManagerError(f"Error during file search: {e}")
