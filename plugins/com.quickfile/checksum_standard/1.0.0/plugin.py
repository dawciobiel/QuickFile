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

        try:
            hash_func = getattr(hashlib, algorithm)()
            
            # Read file in chunks to avoid memory issues and allow progress tracking
            # We don't know the total size here easily without os.path.getsize, 
            # but usually this method is called by a manager that handles total progress.
            # However, for a single large file, internal progress is useful.
            
            import os
            total_size = os.path.getsize(file_path)
            processed_size = 0
            
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096 * 1024), b""): # 4MB chunks
                    if task_context:
                        if task_context.is_cancelled:
                            raise Exception("Operation cancelled")
                        task_context.wait_if_paused()
                    
                    hash_func.update(chunk)
                    
                    if progress_callback:
                        processed_size += len(chunk)
                        progress = int((processed_size / total_size) * 100)
                        progress_callback.emit(progress)
                        
            return hash_func.hexdigest()
            
        except Exception as e:
            logging.exception(f"Error calculating {algorithm} for {file_path}: {e}")
            raise
