# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import logging
import os
import shutil
import sys
import time

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

    def _copy_file_with_progress(self, src, dst, progress_callback=None, total_size=0, copied_so_far=0, task_context=None, task=None,
                                 global_total_size=0, global_copied_so_far=0, send_trace=None):
        try:
            buffer_size = 4 * 1024 * 1024  # 4MB
            bytes_read = copied_so_far
            bytes_written = copied_so_far
            
            # Local tracking for this file
            local_bytes_processed = 0
            
            last_update_time = time.time()
            bytes_since_last_update = 0
            current_speed = 0

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
                        
                        chunk_len = len(buf)
                        bytes_read += chunk_len
                        bytes_since_last_update += chunk_len
                        local_bytes_processed += chunk_len
                        
                        current_time = time.time()
                        time_diff = current_time - last_update_time
                        
                        if time_diff >= 0.5: # Update speed every 0.5 seconds
                            current_speed = bytes_since_last_update / time_diff
                            last_update_time = current_time
                            bytes_since_last_update = 0

                        if progress_callback and total_size > 0:
                            read_pct = int((bytes_read / total_size) * 100)
                            write_pct = int((bytes_written / total_size) * 100)
                            progress_callback.emit((read_pct, write_pct, current_speed))
                        
                        if task and global_total_size > 0:
                            current_global_copied = global_copied_so_far + local_bytes_processed
                            overall_pct = int((current_global_copied / global_total_size) * 100)
                            task.set_overall_progress(overall_pct)

                        fdst.write(buf)

                        bytes_written += len(buf)
                        
                        if progress_callback and total_size > 0:
                            read_pct = int((bytes_read / total_size) * 100)
                            write_pct = int((bytes_written / total_size) * 100)
                            progress_callback.emit((read_pct, write_pct, current_speed))

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

    def _copy_item_with_options(self, source_path, destination_path, options, progress_callback=None, task_context=None, task=None,
                                global_total_size=0, global_copied_so_far=0, send_trace=None):
        destination_full_path = None
        bytes_copied_in_this_call = 0
        try:
            self._validate_path(source_path, must_exist=True, name="Source path")
            self._validate_path(destination_path, must_exist=True, is_directory=True, name="Destination path")

            base_name = os.path.basename(source_path)
            destination_full_path = os.path.join(destination_path, base_name)
            source_is_dir = os.path.isdir(source_path)

            self._handle_destination_exists(destination_full_path, source_is_dir, options.get("overwrite"), base_name)

            if source_is_dir:
                total_size = 0
                # We don't need to calculate total size here if we rely on global_total_size passed from copy_items
                # But we need it for the file progress bar (if we want it to show progress for the whole folder being copied as one item)
                # However, usually file progress bar shows progress for the current FILE.
                # Let's stick to file progress bar = current file progress.
                
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
                        
                        file_size = os.path.getsize(src_file)
                        
                        self._copy_file_with_progress(src_file, dst_file, progress_callback, file_size, 0,
                                                                    task_context, task, 
                                                                    global_total_size, global_copied_so_far + bytes_copied_in_this_call)
                        bytes_copied_in_this_call += file_size
            else:
                if task:
                    task.set_details(base_name)
                file_size = os.path.getsize(source_path)
                self._copy_file_with_progress(source_path, destination_full_path, progress_callback, file_size, 0, task_context, task,
                                              global_total_size, global_copied_so_far)
                bytes_copied_in_this_call += file_size

            if task:
                task.emit_directory_changed(destination_path)

            return bytes_copied_in_this_call

        except (ValueError, FileNotFoundError, FileExistsError, NotADirectoryError, IsADirectoryError, OperationCancelledError) as e:
            raise e
        except OSError as e:
            dest_info = destination_full_path if destination_full_path else "unknown destination"
            logging.exception(f"Error copying item from {source_path} to {dest_info}: {e}")
            raise Exception(translation_manager.translate("FileManager", f"Error copying item: {e}"))

    def copy_items(self, source_paths: list[str], destination_path: str, options: dict, progress_callback=None, task_context=None,
                   task=None, send_trace=None):
        
        # Calculate total size first for smooth overall progress
        global_total_size = 0
        if task:
            task.set_details("Calculating total size...")
        
        try:
            # Re-use _get_paths_and_total_size logic but just for size
            _, _, global_total_size = self._get_paths_and_total_size(source_paths, task_context, None)
        except Exception as e:
            logging.warning(f"Could not calculate total size: {e}")
            global_total_size = 0

        global_copied_so_far = 0
        
        for i, source_path in enumerate(source_paths):
            if task:
                task.set_details(f"Copying: {os.path.basename(source_path)}")
            if task_context:
                if task_context.is_cancelled:
                    raise OperationCancelledError("Operation cancelled by user.")
                task_context.wait_if_paused()
            try:
                # Pass the progress_callback down
                bytes_copied = self._copy_item_with_options(source_path, destination_path, options, progress_callback, task_context, task,
                                             global_total_size, global_copied_so_far)
                global_copied_so_far += bytes_copied
                
            except OperationCancelledError:
                raise
            except Exception as e:
                logging.error(f"Failed to copy {source_path}: {e}")
        
        if task:
            task.set_overall_progress(100)
            
        return f"Batch copy completed."

    def _move_item_with_options(self, source_path, destination_path, options, progress_callback=None, task_context=None, task=None,
                                global_total_size=0, global_copied_so_far=0, send_trace=None):
        destination_full_path = None
        bytes_moved_in_this_call = 0
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

            # Check if on same device
            if os.stat(source_path).st_dev != os.stat(destination_path).st_dev:
                # Pass the progress_callback down for cross-device move (which is copy+delete)
                bytes_moved_in_this_call = self._copy_item_with_options(source_path, destination_path, options, progress_callback, task_context, task,
                                             global_total_size, global_copied_so_far)

                if task_context and task_context.is_cancelled:
                    raise OperationCancelledError("Operation cancelled by user.")

                if os.path.isdir(source_path):
                    shutil.rmtree(source_path)
                else:
                    os.remove(source_path)
            else:
                # Same device move is instant, but we should update progress
                if task_context and task_context.is_cancelled:
                    raise OperationCancelledError("Operation cancelled by user.")
                
                # Calculate size for progress update if we are in a batch move
                try:
                    if source_is_dir:
                        # This is slow, maybe skip size calc for same-device move?
                        # Or just assume it's done instantly.
                        # For smooth progress, we should add its size to copied_so_far
                        # But we don't know its size unless we calculated it before.
                        # Let's assume global_total_size includes it.
                        pass
                    else:
                        pass
                except:
                    pass

                shutil.move(source_path, destination_full_path)
                
                # For same device move, we can't track bytes progress easily inside shutil.move
                # We just jump the progress.
                # To do this correctly, we'd need to know the size of this item.
                # Let's try to get size before move.
                try:
                    # This is a bit expensive for folders, but needed for accurate progress
                    # If we already calculated global_total_size, we can use that.
                    # But here we need size of THIS item.
                    # Let's approximate or re-calculate.
                    # Since move is fast, maybe we don't care about byte-level progress for same-device move?
                    # But we need to update global_copied_so_far for the NEXT items.
                    
                    # Optimization: If we are here, we probably calculated size in move_items
                    # We can re-calculate size of this item to add to global counter.
                    if source_is_dir:
                        size = 0
                        for dirpath, _, filenames in os.walk(source_path):
                            for f in filenames:
                                size += os.path.getsize(os.path.join(dirpath, f))
                        bytes_moved_in_this_call = size
                    else:
                        bytes_moved_in_this_call = os.path.getsize(source_path)
                except:
                    bytes_moved_in_this_call = 0

            if task:
                task.emit_directory_changed(source_dir)
                task.emit_directory_changed(destination_path)

            return bytes_moved_in_this_call

        except (ValueError, FileNotFoundError, FileExistsError, NotADirectoryError, IsADirectoryError, OperationCancelledError) as e:
            raise e
        except OSError as e:
            dest_info = destination_full_path if destination_full_path else "unknown destination"
            logging.exception(f"Error moving item from {source_path} to {dest_info}: {e}")
            raise Exception(translation_manager.translate("FileManager", f"Error moving item: {e}"))

    def move_items(self, source_paths: list[str], destination_path: str, options: dict, progress_callback=None, task_context=None,
                   task=None, send_trace=None):
        
        # Calculate total size first
        global_total_size = 0
        if task:
            task.set_details("Calculating total size...")
        
        try:
            _, _, global_total_size = self._get_paths_and_total_size(source_paths, task_context, None)
        except Exception as e:
            logging.warning(f"Could not calculate total size: {e}")
            global_total_size = 0

        global_copied_so_far = 0

        for i, source_path in enumerate(source_paths):
            if task:
                task.set_details(f"Moving: {os.path.basename(source_path)}")
            if task_context:
                if task_context.is_cancelled:
                    raise OperationCancelledError("Operation cancelled by user.")
                task_context.wait_if_paused()
            try:
                # Pass the progress_callback down
                bytes_moved = self._move_item_with_options(source_path, destination_path, options, progress_callback, task_context, task,
                                             global_total_size, global_copied_so_far)
                global_copied_so_far += bytes_moved
                
                if task and global_total_size > 0:
                     overall_pct = int((global_copied_so_far / global_total_size) * 100)
                     task.set_overall_progress(overall_pct)
                     
            except OperationCancelledError:
                raise
            except Exception as e:
                logging.error(f"Failed to move {source_path}: {e}")
        
        if task:
            task.set_overall_progress(100)

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

    def delete_items(self, item_paths: list[str], options: dict, progress_callback=None, task_context=None, task=None, send_trace=None):
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
                    task.emit_directory_changed(dir_path)

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
                    task.emit_directory_changed(dir_path)

            return "Items permanently deleted."

        except (ValueError, FileNotFoundError, OperationCancelledError) as e:
            raise e
        except OSError as e:
            logging.exception(f"Error during permanent deletion: {e}")
            raise Exception(f"Error during permanent deletion: {e}")
