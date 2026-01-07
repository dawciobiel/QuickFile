# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import logging
import os
import shutil

from app.translation_manager import translation_manager


class FileManagerError(Exception):
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

    def _get_total_size(self, paths):
        total_size = 0
        for path in paths:
            if os.path.isdir(path):
                for dirpath, dirnames, filenames in os.walk(path):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        if not os.path.islink(fp):
                            try:
                                total_size += os.path.getsize(fp)
                            except OSError:
                                pass
            else:
                if not os.path.islink(path):
                    try:
                        total_size += os.path.getsize(path)
                    except OSError:
                        pass
        return total_size

    def copy_items_with_options(self, source_paths, destination_path, options, task):
        total_size = self._get_total_size(source_paths)
        copied_size = 0

        for src_path in source_paths:
            if task.status == "CANCELLED":
                break
            
            base_name = os.path.basename(src_path)
            dest_full_path = os.path.join(destination_path, base_name)

            if os.path.exists(dest_full_path) and not options.get("overwrite"):
                continue

            if os.path.isdir(src_path):
                # We need to manually walk and copy to update overall progress
                for dirpath, dirnames, filenames in os.walk(src_path):
                    if task.status == "CANCELLED":
                        break

                    # Create corresponding directories in destination
                    relative_dir = os.path.relpath(dirpath, src_path)
                    dest_dir = os.path.join(dest_full_path, relative_dir)
                    os.makedirs(dest_dir, exist_ok=True)

                    for filename in filenames:
                        if task.status == "CANCELLED":
                            break
                        
                        src_file = os.path.join(dirpath, filename)
                        dest_file = os.path.join(dest_dir, filename)
                        
                        copied_size = self._copy_file_with_progress(src_file, dest_file, task, total_size, copied_size)
            else:
                copied_size = self._copy_file_with_progress(src_path, dest_full_path, task, total_size, copied_size)

    def _copy_file_with_progress(self, src, dst, task, total_size, copied_size):
        try:
            file_size = os.path.getsize(src)
        except OSError:
            return copied_size # Skip if file size can't be determined

        task.set_details(f"Copying: {os.path.basename(src)}")
        
        with open(src, 'rb') as fsrc, open(dst, 'wb') as fdst:
            copied = 0
            while True:
                if task.status == "CANCELLED":
                    break
                buf = fsrc.read(16 * 1024)
                if not buf:
                    break
                fdst.write(buf)
                copied += len(buf)
                
                if file_size > 0:
                    task.set_progress(int(copied * 100 / file_size))
                
                if total_size > 0:
                    overall_copied = copied_size + copied
                    task.set_overall_progress(int(overall_copied * 100 / total_size))

        shutil.copymode(src, dst)
        return copied_size + file_size

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
        file_path = None
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
            path_info = file_path if file_path else "unknown path"
            logging.exception(f"Error creating file {path_info}: {e}")
            raise FileManagerError(translation_manager.translate("FileManager", f"Error creating file: {e}"))

    def create_directory(self, parent_directory, directory_name):
        directory_path = None
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
            path_info = directory_path if directory_path else "unknown path"
            logging.exception(f"Error creating directory {path_info}: {e}")
            raise FileManagerError(translation_manager.translate("FileManager", f"Error creating directory: {e}"))
