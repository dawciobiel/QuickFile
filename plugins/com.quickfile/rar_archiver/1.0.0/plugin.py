import os
import subprocess
import logging
import re
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
            # unrar x -y -p- <archive> <destination>
            # -y: assume yes on all queries
            # -p-: do not query password
            cmd = ["unrar", "x", "-y", archive_path, destination_path]
            
            # Start the process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )

            # Regex to capture progress percentage from unrar output
            # unrar output format varies, but often includes " ..% "
            progress_pattern = re.compile(r"(\d+)%")

            while True:
                if task_context:
                    if task_context.is_cancelled:
                        process.terminate()
                        raise Exception("Operation cancelled by user.")
                    task_context.wait_if_paused()

                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                
                if output:
                    # Update details with current file being processed
                    # unrar output: "Extracting  path/to/file   OK"
                    if output.strip().startswith("Extracting"):
                        filename = output.strip().split("Extracting")[1].strip().split("OK")[0].strip()
                        if task: task.set_details(f"Extracting: {filename}")

                    # Try to parse progress
                    # Note: unrar might use backspace characters to update progress on the same line,
                    # which readline might not handle perfectly for all versions.
                    # This is a best-effort implementation.
                    match = progress_pattern.search(output)
                    if match and progress_callback:
                        progress = int(match.group(1))
                        progress_callback.emit(progress)

            rc = process.poll()
            if rc != 0:
                stderr = process.stderr.read()
                raise RuntimeError(f"unrar exited with code {rc}: {stderr}")

            return f"Archive extracted to: {destination_path}"

        except Exception as e:
            logging.exception(f"Error extracting RAR archive: {e}")
            raise

    def _is_unrar_installed(self) -> bool:
        return shutil.which("unrar") is not None

import shutil
