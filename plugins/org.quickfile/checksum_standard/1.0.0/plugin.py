# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import hashlib
import logging
from plugins.base import ChecksumPlugin

class StandardChecksumPlugin(ChecksumPlugin):
    @property
    def name(self) -> str:
        return "Standard Checksum Algorithms"

    @property
    def description(self) -> str:
        return "Provides support for calculating MD5, SHA1, SHA256, and SHA512 checksums."

    def get_supported_algorithms(self) -> list[str]:
        return ['md5', 'sha1', 'sha256', 'sha512']

    def calculate_checksum(self, file_path: str, algorithm: str, progress_callback=None, task_context=None) -> str:
        if algorithm not in self.get_supported_algorithms():
            raise ValueError(f"Unsupported algorithm: {algorithm}")

        logging.debug(f"ChecksumPlugin: Starting {algorithm} for {file_path}")
        try:
            hash_func = getattr(hashlib, algorithm)()
            
            import os
            total_size = os.path.getsize(file_path)
            processed_size = 0
            
            logging.debug(f"ChecksumPlugin: Opening file {file_path}")
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096 * 1024), b""): # 4MB chunks
                    if task_context:
                        if task_context.is_cancelled:
                            logging.debug(f"ChecksumPlugin: Cancellation requested for {file_path}")
                            raise Exception("Operation cancelled")
                        task_context.wait_if_paused()
                    
                    hash_func.update(chunk)
                    
                    if progress_callback:
                        processed_size += len(chunk)
                        progress = int((processed_size / total_size) * 100)
                        progress_callback.emit(progress)
            
            digest = hash_func.hexdigest()
            logging.debug(f"ChecksumPlugin: Finished {algorithm} for {file_path}. Result: {digest}")
            return digest
            
        except Exception as e:
            logging.exception(f"Error calculating {algorithm} for {file_path}: {e}")
            raise
