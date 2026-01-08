# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import zipfile
import logging
from plugins.base import ArchivePlugin

class ZipPlugin(ArchivePlugin):
    @property
    def name(self) -> str:
        return "Standard ZIP Archiver"

    @property
    def description(self) -> str:
        return "Provides support for creating and extracting ZIP archives."

    def get_supported_extensions(self) -> list[str]:
        return ['.zip']

    def create_archive(self, source_paths: list[str], destination_path: str, options: dict, progress_callback=None, task_context=None, task=None):
        if not source_paths:
            raise ValueError("No source paths provided.")

        try:
            with zipfile.ZipFile(destination_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                total_files = 0
                
                for source_path in source_paths:
                    if task_context and task_context.is_cancelled: return
                    if task_context: task_context.wait_if_paused()

                    if os.path.isdir(source_path):
                        for root, dirs, files in os.walk(source_path):
                            for file in files:
                                if task_context and task_context.is_cancelled: return
                                if task_context: task_context.wait_if_paused()
                                
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, os.path.dirname(source_path))
                                
                                if task: task.set_details(f"Archiving: {arcname}")
                                zipf.write(file_path, arcname)
                    else:
                        if task: task.set_details(f"Archiving: {os.path.basename(source_path)}")
                        zipf.write(source_path, os.path.basename(source_path))
            
            if task:
                task.directory_changed.emit(os.path.dirname(destination_path))
                        
            return f"Archive created: {destination_path}"
        except Exception as e:
            logging.exception(f"Error creating ZIP archive: {e}")
            raise

    def extract_archive(self, archive_path: str, destination_path: str, options: dict, progress_callback=None, task_context=None, task=None):
        try:
            with zipfile.ZipFile(archive_path, 'r') as zipf:
                file_list = zipf.namelist()
                total_files = len(file_list)
                
                for i, file in enumerate(file_list):
                    if task_context and task_context.is_cancelled: return
                    if task_context: task_context.wait_if_paused()
                    
                    if task: task.set_details(f"Extracting: {file}")
                    zipf.extract(file, destination_path)
                    
                    if progress_callback:
                        progress_callback.emit(int((i + 1) / total_files * 100))
            
            if task:
                task.directory_changed.emit(destination_path)
                        
            return f"Archive extracted to: {destination_path}"
        except Exception as e:
            logging.exception(f"Error extracting ZIP archive: {e}")
            raise
