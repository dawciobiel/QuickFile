# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import logging
import os
import shutil
import sys

import send2trash

# Add current directory to sys.path to allow importing sibling modules if needed
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from plugins.base import StandardOperationsPlugin
from app.translation_manager import translation_manager

class OperationCancelledError(Exception):
    """Exception raised when an operation is cancelled by the user."""
    pass

class StandardOperationsPluginImpl(StandardOperationsPlugin):

    @property
    def name(self) -> str:
        return "Standard File Operations"

    @property
    def description(self) -> str:
        return "Provides standard file operations like copy, move, and delete."

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
                raise IsADirectoryError(translation_manager.translate("FileManager",
                                                                      f"Cannot move/copy directory '{item_name}' to existing file '{destination_full_path}'."))
            elif not overwrite_option:
                raise FileExistsError(
                    translation_manager.translate("FileManager", f"Item '{item_name}' already exists in the destination."))
            else:
                if os.path.isdir(destination_full_path):
                    shutil.rmtree(destination_full_path)
                else:
                    os.remove(destination_full_path)
                logging.info(f"Removed existing item at {destination_full_path} for overwrite.")

    def _copy_file_with_progress(self, src, dst, progress_callback=None, total_size=0, copied_so_far=0, task_context=None, task=None):
        try:
            buffer_size = 4 * 1024 * 1024  # 4MB
            bytes_read = copied_so_far
            bytes_written = copied_so_far

            with open(src, 'rb') as fsrc:
                with open(dst, 'wb') as fdst:
                    while True:
                        if task_context:
                            if task_context.is_cancelled:
                                raise OperationCancelledError("Operation cancelled by user.")
                            task_context.wait_if_paused()

                        buf = fsrc.read(buffer_size)
                        if not buf:
                            break

                        bytes_read += len(buf)
                        if progress_callback and total_size > 0:
                            read_pct = int((bytes_read / total_size) * 100)
                            write_pct = int((bytes_written / total_size) * 100)
                            progress_callback.emit((read_pct, write_pct))

                        fdst.write(buf)

                        bytes_written += len(buf)
                        if progress_callback and total_size > 0:
                            read_pct = int((bytes_read / total_size) * 100)
                            write_pct = int((bytes_written / total_size) * 100)
                            progress_callback.emit((read_pct, write_pct))

            shutil.copystat(src, dst)
            return bytes_written
        except OperationCancelledError:
            if os.path.exists(dst):
                try:
                    os.remove(dst)
                except OSError:
                    pass
            raise
        except Exception as e:
            raise OSError(f"Error copying file {src} to {dst}: {e}")

    def _copy_item_with_options(self, source_path, destination_path, options, progress_callback=None, task_context=None, task=None):
        destination_full_path = None
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
                        copied_size = self._copy_file_with_progress(src_file, dst_file, progress_callback, total_size, copied_size,
                                                                    task_context, task)
            else:
                if task:
                    task.set_details(base_name)
                total_size = os.path.getsize(source_path)
                self._copy_file_with_progress(source_path, destination_full_path, progress_callback, total_size, 0, task_context, task)

            if task:
                task.directory_changed.emit(destination_path)

            return translation_manager.translate("FileManager", f"Copied '{base_name}' to '{destination_path}'")

        except (ValueError, FileNotFoundError, FileExistsError, NotADirectoryError, IsADirectoryError, OperationCancelledError) as e:
            raise e
        except OSError as e:
            dest_info = destination_full_path if destination_full_path else "unknown destination"
            logging.exception(f"Error copying item from {source_path} to {dest_info}: {e}")
            raise Exception(translation_manager.translate("FileManager", f"Error copying item: {e}"))

    def copy_items(self, source_paths: list[str], destination_path: str, options: dict, progress_callback=None, task_context=None,
                   task=None):
        total_items = len(source_paths)
        for i, source_path in enumerate(source_paths):
            if task:
                task.set_details(f"({i + 1}/{total_items}) {os.path.basename(source_path)}")
            if task_context:
                if task_context.is_cancelled:
                    raise OperationCancelledError("Operation cancelled by user.")
                task_context.wait_if_paused()
            try:
                # Pass the progress_callback down
                self._copy_item_with_options(source_path, destination_path, options, progress_callback, task_context, task)
                if progress_callback:
                    # For batch operations, we currently only report item count progress
                    # To support dual progress bar here, we'd need to calculate total size of all items first
                    progress_callback.emit(int((i + 1) / total_items * 100))
            except OperationCancelledError:
                raise
            except Exception as e:
                logging.error(f"Failed to copy {source_path}: {e}")
        return f"Batch copy completed."

    def _move_item_with_options(self, source_path, destination_path, options, progress_callback=None, task_context=None, task=None):
        destination_full_path = None
        try:
            source_dir = os.path.dirname(source_path)
            self._validate_path(source_path, must_exist=True, name="Source path")
            self._validate_path(destination_path, must_exist=True, is_directory=True, name="Destination path")

            base_name = os.path.basename(source_path)
            destination_full_path = os.path.join(destination_path, base_name)
            source_is_dir = os.path.isdir(source_path)

            self._handle_destination_exists(destination_full_path, source_is_dir, options.get("overwrite"), base_name)

            if task:
                task.set_details(base_name)

            if os.stat(source_path).st_dev != os.stat(destination_path).st_dev:
                # Pass the progress_callback down for cross-device move
                self._copy_item_with_options(source_path, destination_path, options, progress_callback, task_context, task)

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
                if task:
                    task.set_progress(100)

            if task:
                task.directory_changed.emit(source_dir)
                task.directory_changed.emit(destination_path)

            return translation_manager.translate("FileManager", f"Moved '{base_name}' to '{destination_full_path}'")

        except (ValueError, FileNotFoundError, FileExistsError, NotADirectoryError, IsADirectoryError, OperationCancelledError) as e:
            raise e
        except OSError as e:
            dest_info = destination_full_path if destination_full_path else "unknown destination"
            logging.exception(f"Error moving item from {source_path} to {dest_info}: {e}")
            raise Exception(translation_manager.translate("FileManager", f"Error moving item: {e}"))

    def move_items(self, source_paths: list[str], destination_path: str, options: dict, progress_callback=None, task_context=None,
                   task=None):
        total_items = len(source_paths)
        for i, source_path in enumerate(source_paths):
            if task:
                task.set_details(f"({i + 1}/{total_items}) {os.path.basename(source_path)}")
            if task_context:
                if task_context.is_cancelled:
                    raise OperationCancelledError("Operation cancelled by user.")
                task_context.wait_if_paused()
            try:
                # Pass the progress_callback down
                self._move_item_with_options(source_path, destination_path, options, progress_callback, task_context, task)
                if task:
                    task.set_overall_progress(int((i + 1) / total_items * 100))
            except OperationCancelledError:
                raise
            except Exception as e:
                logging.error(f"Failed to move {source_path}: {e}")
        return f"Batch move completed."

    def _get_paths_and_total_size(self, item_paths, task_context=None, task=None):
        total_size = 0
        all_files = []
        all_dirs = []

        if task:
            task.set_details("Scanning files...")

        for path in item_paths:
            if task_context and task_context.is_cancelled:
                raise OperationCancelledError("Scan cancelled by user.")

            if os.path.isdir(path):
                for dirpath, dirnames, filenames in os.walk(path):
                    if task_context and task_context.is_cancelled:
                        raise OperationCancelledError("Scan cancelled by user.")

                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        if not os.path.islink(fp):
                            try:
                                size = os.path.getsize(fp)
                                total_size += size
                                all_files.append((fp, size))
                            except OSError:
                                pass
                    all_dirs.append(dirpath)
            elif os.path.isfile(path):
                try:
                    size = os.path.getsize(path)
                    total_size += size
                    all_files.append((path, size))
                except OSError:
                    pass

        all_dirs.sort(key=lambda x: x.count(os.sep), reverse=True)

        return all_files, all_dirs, total_size

    def delete_items(self, item_paths: list[str], options: dict, progress_callback=None, task_context=None, task=None):
        move_to_trash = options.get("move_to_trash", True)

        affected_dirs = set()
        for path in item_paths:
            affected_dirs.add(os.path.dirname(path))

        if move_to_trash:
            total_items = len(item_paths)
            if task:
                task.set_progress(0)
            for i, path in enumerate(item_paths):
                if task_context and task_context.is_cancelled:
                    raise OperationCancelledError("Operation cancelled by user.")
                if task:
                    task.set_details(f"({i + 1}/{total_items}) {os.path.basename(path)}")
                
                send2trash.send2trash(path)

                if task:
                    task.set_progress(int((i + 1) / total_items * 100))

            if task:
                for dir_path in affected_dirs:
                    task.directory_changed.emit(dir_path)

            return "Items moved to trash."

        try:
            all_files, all_dirs, total_size = self._get_paths_and_total_size(item_paths, task_context, task)

            deleted_size = 0
            if task:
                task.set_progress(0)

            for i, (file_path, file_size) in enumerate(all_files):
                if task_context and task_context.is_cancelled:
                    raise OperationCancelledError("Operation cancelled by user.")
                if task:
                    task.set_details(f"({i + 1}/{len(all_files)}) {os.path.basename(file_path)}")
                
                os.remove(file_path)
                deleted_size += file_size
                if task and total_size > 0:
                    progress = int((deleted_size / total_size) * 100)
                    task.set_progress(progress)

            for dir_path in all_dirs:
                if task_context and task_context.is_cancelled:
                    raise OperationCancelledError("Operation cancelled by user.")
                try:
                    os.rmdir(dir_path)
                except OSError:
                    pass

            if task:
                for dir_path in affected_dirs:
                    task.directory_changed.emit(dir_path)

            return "Items permanently deleted."

        except (ValueError, FileNotFoundError, OperationCancelledError) as e:
            raise e
        except OSError as e:
            logging.exception(f"Error during permanent deletion: {e}")
            raise Exception(f"Error during permanent deletion: {e}")
