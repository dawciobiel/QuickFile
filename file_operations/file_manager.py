import logging
import os
import shutil
import send2trash
from app.translation_manager import translation_manager

class FileManagerError(Exception):
    pass

class OperationCancelledError(Exception):
    """Exception raised when an operation is cancelled by the user."""
    pass

class FileManager:
    def __init__(self):
        self.clipboard = None
        self.is_cut_operation = False

    def _validate_path(self, path, must_exist=True, is_directory=False, is_file=False, name="Path"):
        if not path:
            raise ValueError(translation_manager.translate("FileManager", f"{name} cannot be empty."))
        if must_exist and not os.path.exists(path):
            raise FileNotFoundError(translation_manager.translate("FileManager", f"{name} '{path}' does not exist."))
        if os.path.exists(path):
            if is_directory and not os.path.isdir(path):
                raise NotADirectoryError(translation_manager.translate("FileManager", f"{name} '{path}' is not a directory."))
            if is_file and not os.path.isfile(path):
                raise IsADirectoryError(translation_manager.translate("FileManager", f"{name} '{path}' is not a file."))
        return path

    def _handle_destination_exists(self, destination_full_path, source_is_dir, overwrite_option, item_name):
        if os.path.exists(destination_full_path):
            if source_is_dir and os.path.isfile(destination_full_path):
                raise IsADirectoryError(translation_manager.translate("FileManager", f"Cannot move/copy directory '{item_name}' to existing file '{destination_full_path}'."))
            elif not overwrite_option:
                raise FileExistsError(translation_manager.translate("FileManager", f"Item '{item_name}' already exists in the destination."))
            else:
                if os.path.isdir(destination_full_path):
                    shutil.rmtree(destination_full_path)
                else:
                    os.remove(destination_full_path)
                logging.info(f"Removed existing item at {destination_full_path} for overwrite.")

    def _copy_file_with_progress(self, src, dst, progress_callback=None, total_size=0, copied_so_far=0, task_context=None, task=None):
        try:
            with open(src, 'rb') as fsrc:
                with open(dst, 'wb') as fdst:
                    while True:
                        if task_context:
                            if task_context.is_cancelled:
                                raise OperationCancelledError("Operation cancelled by user.")
                            task_context.wait_if_paused()
                        
                        buf = fsrc.read(1024 * 1024)
                        if not buf:
                            break
                        fdst.write(buf)
                        if progress_callback and total_size > 0:
                            copied_so_far += len(buf)
                            progress = int((copied_so_far / total_size) * 100)
                            progress_callback.emit(progress)
            shutil.copystat(src, dst)
            return copied_so_far
        except OperationCancelledError:
            if os.path.exists(dst):
                try:
                    os.remove(dst)
                except OSError:
                    pass
            raise
        except Exception as e:
            raise OSError(f"Error copying file {src} to {dst}: {e}")

    def copy_item_with_options(self, source_path, destination_path, options, progress_callback=None, task_context=None, task=None):
        try:
            self._validate_path(source_path, must_exist=True, name="Source path")
            self._validate_path(destination_path, must_exist=True, is_directory=True, name="Destination path")

            base_name = os.path.basename(source_path)
            destination_full_path = os.path.join(destination_path, base_name)
            source_is_dir = os.path.isdir(source_path)

            self._handle_destination_exists(destination_full_path, source_is_dir, options.get("overwrite"), base_name)

            if source_is_dir:
                total_size = 0
                for dirpath, _, filenames in os.walk(source_path):
                    for filename in filenames:
                        total_size += os.path.getsize(os.path.join(dirpath, filename))
                
                copied_size = 0
                
                os.makedirs(destination_full_path, exist_ok=True)
                shutil.copystat(source_path, destination_full_path)

                for dirpath, dirnames, filenames in os.walk(source_path):
                    if task_context:
                        if task_context.is_cancelled:
                            raise OperationCancelledError("Operation cancelled by user.")
                        task_context.wait_if_paused()

                    rel_path = os.path.relpath(dirpath, source_path)
                    dest_dir = os.path.join(destination_full_path, rel_path)
                    os.makedirs(dest_dir, exist_ok=True)
                    shutil.copystat(dirpath, dest_dir)

                    for filename in filenames:
                        if task_context:
                            if task_context.is_cancelled:
                                raise OperationCancelledError("Operation cancelled by user.")
                            task_context.wait_if_paused()
                        
                        if task:
                            task.set_details(filename)

                        src_file = os.path.join(dirpath, filename)
                        dst_file = os.path.join(dest_dir, filename)
                        copied_size = self._copy_file_with_progress(src_file, dst_file, progress_callback, total_size, copied_size, task_context, task)
            else:
                if task:
                    task.set_details(base_name)
                total_size = os.path.getsize(source_path)
                self._copy_file_with_progress(source_path, destination_full_path, progress_callback, total_size, 0, task_context, task)

            return translation_manager.translate("FileManager", f"Copied '{base_name}' to '{destination_path}'")

        except (ValueError, FileNotFoundError, FileExistsError, NotADirectoryError, IsADirectoryError, OperationCancelledError) as e:
            raise e
        except OSError as e:
            logging.exception(f"Error copying item from {source_path} to {destination_full_path}: {e}")
            raise FileManagerError(translation_manager.translate("FileManager", f"Error copying item: {e}"))

    def copy_items_batch(self, source_paths, destination_path, options, progress_callback=None, task_context=None, task=None):
        total_items = len(source_paths)
        for i, source_path in enumerate(source_paths):
            if task:
                task.set_details(f"({i+1}/{total_items}) {os.path.basename(source_path)}")
            if task_context:
                if task_context.is_cancelled:
                    raise OperationCancelledError("Operation cancelled by user.")
                task_context.wait_if_paused()
            try:
                self.copy_item_with_options(source_path, destination_path, options, task_context=task_context, task=task)
                if progress_callback:
                    progress_callback.emit(int((i + 1) / total_items * 100))
            except OperationCancelledError:
                raise
            except Exception as e:
                logging.error(f"Failed to copy {source_path}: {e}")
        return f"Batch copy completed."

    def move_item_with_options(self, source_path, destination_path, options, progress_callback=None, task_context=None, task=None):
        try:
            self._validate_path(source_path, must_exist=True, name="Source path")
            self._validate_path(destination_path, must_exist=True, is_directory=True, name="Destination path")

            base_name = os.path.basename(source_path)
            destination_full_path = os.path.join(destination_path, base_name)
            source_is_dir = os.path.isdir(source_path)

            self._handle_destination_exists(destination_full_path, source_is_dir, options.get("overwrite"), base_name)
            
            if task:
                task.set_details(base_name)

            if os.stat(source_path).st_dev != os.stat(destination_path).st_dev:
                self.copy_item_with_options(source_path, destination_path, options, progress_callback, task_context, task)
                
                if task_context and task_context.is_cancelled:
                     raise OperationCancelledError("Operation cancelled by user.")

                if os.path.isdir(source_path):
                    shutil.rmtree(source_path)
                else:
                    os.remove(source_path)
            else:
                if task_context and task_context.is_cancelled:
                     raise OperationCancelledError("Operation cancelled by user.")
                
                shutil.move(source_path, destination_full_path)
                if progress_callback:
                    progress_callback.emit(100)

            return translation_manager.translate("FileManager", f"Moved '{base_name}' to '{destination_full_path}'")

        except (ValueError, FileNotFoundError, FileExistsError, NotADirectoryError, IsADirectoryError, OperationCancelledError) as e:
            raise e
        except OSError as e:
            logging.exception(f"Error moving item from {source_path} to {destination_full_path}: {e}")
            raise FileManagerError(translation_manager.translate("FileManager", f"Error moving item: {e}"))

    def move_items_batch(self, source_paths, destination_path, options, progress_callback=None, task_context=None, task=None):
        total_items = len(source_paths)
        for i, source_path in enumerate(source_paths):
            if task:
                task.set_details(f"({i+1}/{total_items}) {os.path.basename(source_path)}")
            if task_context:
                if task_context.is_cancelled:
                    raise OperationCancelledError("Operation cancelled by user.")
                task_context.wait_if_paused()
            try:
                self.move_item_with_options(source_path, destination_path, options, task_context=task_context, task=task)
                if progress_callback:
                    progress_callback.emit(int((i + 1) / total_items * 100))
            except OperationCancelledError:
                raise
            except Exception as e:
                logging.error(f"Failed to move {source_path}: {e}")
        return f"Batch move completed."

    def delete_item(self, item_path, move_to_trash=True):
        try:
            self._validate_path(item_path, must_exist=True, name="Item path")

            if move_to_trash:
                try:
                    send2trash.send2trash(item_path)
                    return translation_manager.translate("FileManager", f"Moved to Trash: {item_path}")
                except Exception as e:
                    logging.warning(f"Error moving {item_path} to trash, deleting permanently: {e}")
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

    def delete_items_batch(self, item_paths, move_to_trash=True, progress_callback=None, task_context=None, task=None):
        total_items = len(item_paths)
        for i, item_path in enumerate(item_paths):
            if task:
                task.set_details(f"({i+1}/{total_items}) {os.path.basename(item_path)}")
            if task_context:
                if task_context.is_cancelled:
                    raise OperationCancelledError("Operation cancelled by user.")
                task_context.wait_if_paused()
            try:
                self.delete_item(item_path, move_to_trash)
                if progress_callback:
                    progress_callback.emit(int((i + 1) / total_items * 100))
            except Exception as e:
                logging.error(f"Failed to delete {item_path}: {e}")
        return f"Batch delete completed."

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
            
            if os.path.exists(destination_full_path):
                if self.is_cut_operation:
                    if os.path.isdir(destination_full_path):
                        shutil.rmtree(destination_full_path)
                    else:
                        os.remove(destination_full_path)
                    logging.info(f"Removed existing item at {destination_full_path} for cut-paste overwrite.")
                else:
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
        try:
            self._validate_path(directory, must_exist=True, name="Directory")
            if not file_name:
                raise ValueError(translation_manager.translate("FileManager", "File name cannot be empty."))

            file_path = os.path.join(directory, file_name)
            if os.path.exists(file_path):
                raise FileExistsError(translation_manager.translate("FileManager", f"File '{file_name}' already exists."))

            with open(file_path, 'w') as f:
                pass
            return translation_manager.translate("FileManager", f"File created: {file_path}")
        except (ValueError, FileNotFoundError, FileExistsError, NotADirectoryError, IsADirectoryError) as e:
            raise e
        except OSError as e:
            logging.exception(f"Error creating file {file_path}: {e}")
            raise FileManagerError(translation_manager.translate("FileManager", f"Error creating file: {e}"))

    def create_directory(self, parent_directory, directory_name):
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
