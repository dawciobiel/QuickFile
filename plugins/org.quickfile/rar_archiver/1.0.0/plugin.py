# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import subprocess
import logging
import re
import shutil
from plugins.base import ArchivePlugin

class RarPlugin(ArchivePlugin):
    @property
    def name(self) -> str:
        return "RAR Archiver"

    @property
    def description(self) -> str:
        return "Provides support for extracting RAR archives using system 'unrar' utility."

    def get_supported_extensions(self) -> list[str]:
        return ['.rar']

    def create_archive(self, source_paths: list[str], destination_path: str, options: dict, progress_callback=None, task_context=None, task=None):
        raise NotImplementedError("Creating RAR archives is not supported. Please use ZIP format.")

    def extract_archive(self, archive_path: str, destination_path: str, options: dict, progress_callback=None, task_context=None, task=None):
        if not self._is_unrar_installed():
            raise RuntimeError("'unrar' utility is not installed or not found in PATH.")

        try:
            cmd = ["unrar", "x", "-y", archive_path, destination_path]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )

            progress_pattern = re.compile(r"(\d+)%")

            for output in process.stdout:
                if task_context:
                    if task_context.is_cancelled:
                        process.terminate()
                        raise Exception("Operation cancelled by user.")
                    task_context.wait_if_paused()

                if output:
                    if output.strip().startswith("Extracting"):
                        filename = output.strip().split("Extracting")[1].strip().split("OK")[0].strip()
                        if task: task.set_details(f"Extracting: {filename}")

                    match = progress_pattern.search(output)
                    if match and progress_callback:
                        progress = int(match.group(1))
                        progress_callback.emit(progress)

            # Wait for the process to terminate and get the return code
            process.wait()
            rc = process.poll()

            if rc != 0:
                stderr = process.stderr.read()
                raise RuntimeError(f"unrar exited with code {rc}: {stderr}")

            if task:
                task.directory_changed.emit(destination_path)

            return f"Archive extracted to: {destination_path}"

        except Exception as e:
            logging.exception(f"Error extracting RAR archive: {e}")
            raise

    def _is_unrar_installed(self) -> bool:
        return shutil.which("unrar") is not None
