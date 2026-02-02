# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import time
import zlib
import traceback
from quickfile.app.plugin_system.api import AbstractTask

class SplitFileTask(AbstractTask):
    def __init__(self, source_path, dest_dir, options):
        super().__init__()
        self.source_path = source_path
        self.dest_dir = dest_dir
        self.options = options

    def run(self):
        chunk_size = self.options.get("chunk_size")
        generate_checksum = self.options.get("generate_checksum", False)
        
        if not os.path.exists(self.dest_dir):
            os.makedirs(self.dest_dir)
            
        file_size = os.path.getsize(self.source_path)
        base_name = os.path.basename(self.source_path)
        
        bytes_read = 0
        part_num = 1
        crc32 = 0
        
        last_progress_update = 0
        last_pct = -1
        
        f_in = None
        try:
            with open(self.source_path, 'rb') as f_in:
                while True:
                    if self.context.is_cancelled():
                        raise InterruptedError("Split operation cancelled by user.")
                    self.context.wait_if_paused()
                    
                    part_ext = f".{part_num:03d}"
                    part_path = os.path.join(self.dest_dir, base_name + part_ext)
                    
                    with open(part_path, 'wb') as f_out:
                        chunk_written = 0
                        while chunk_written < chunk_size:
                            if self.context.is_cancelled():
                                raise InterruptedError("Split operation cancelled by user.")
                            self.context.wait_if_paused()
                            
                            read_size = min(64 * 1024, chunk_size - chunk_written)
                            data = f_in.read(read_size)
                            if not data:
                                break
                            
                            f_out.write(data)
                            if generate_checksum: crc32 = zlib.crc32(data, crc32)
                            chunk_written += len(data)
                            bytes_read += len(data)
                            
                            if file_size > 0: 
                                pct = int(bytes_read * 100 / file_size)
                                if pct != last_pct and (time.time() - last_progress_update > 0.1):
                                    self.emit_progress(pct)
                                    last_pct = pct
                                    last_progress_update = time.time()
                            
                        if chunk_written == 0:
                            os.remove(part_path)
                            break
                    part_num += 1
                    if bytes_read >= file_size:
                        break
            
            if generate_checksum:
                crc_path = os.path.join(self.dest_dir, base_name + ".crc32")
                with open(crc_path, 'w', encoding='utf-8') as f_crc:
                    f_crc.write(f"filename={base_name}\n")
                    f_crc.write(f"filenameutf8={base_name}\n")
                    f_crc.write(f"size={file_size}\n")
                    f_crc.write(f"crc32={crc32 & 0xFFFFFFFF:08X}\n")
                    f_crc.write(f"parts_count={part_num - 1}\n")

        except InterruptedError:
            raise
        except Exception as e:
            raise Exception(f"Error in split_file: {e}")
        finally:
            if f_in:
                f_in.close()

class JoinFilesTask(AbstractTask):
    def __init__(self, source_path, dest_dir, options):
        super().__init__()
        self.source_path = source_path
        self.dest_dir = dest_dir
        self.options = options

    def run(self):
        output_filename = self.options.get("output_filename")
        output_path = os.path.join(self.dest_dir, output_filename)
        
        base_dir = os.path.dirname(self.source_path)
        source_basename = os.path.basename(self.source_path)
        
        # Determine parts logic
        parts = []
        expected_crc = None
        part_base = None
        expected_parts_count = None
        
        if source_basename.endswith(".crc32"):
            try:
                with open(self.source_path, 'r', encoding='utf-8-sig') as f:
                    for line in f:
                        line = line.rstrip('\n')
                        if line.startswith("crc32="):
                            expected_crc = int(line.split("=", 1)[1], 16)
                        elif line.startswith("parts_count="):
                            expected_parts_count = int(line.split("=", 1)[1])
                        elif line.startswith("filenameutf8="):
                            part_base = line.split("=", 1)[1]
                        elif line.startswith("filename=") and part_base is None:
                            part_base = line.split("=", 1)[1]
            except Exception:
                pass 
                
            if part_base is None:
                part_base = source_basename[:-6]
            
            first_part_path = os.path.join(base_dir, f"{part_base}.001")
            if not os.path.exists(first_part_path):
                fallback_base = source_basename[:-6]
                if fallback_base != part_base:
                    if os.path.exists(os.path.join(base_dir, f"{fallback_base}.001")):
                        part_base = fallback_base
        elif source_basename.endswith(".001"):
            part_base = source_basename[:-4]
            crc_path = os.path.join(base_dir, str(part_base) + ".crc32")
            if os.path.exists(crc_path):
                try:
                    with open(crc_path, 'r', encoding='utf-8-sig') as f:
                        for line in f:
                            if line.startswith("crc32="):
                                expected_crc = int(line.split("=", 1)[1], 16)
                except Exception:
                    pass
        else:
            part_base = source_basename

        if expected_parts_count is not None:
            for i in range(1, expected_parts_count + 1):
                part_name = f"{part_base}.{i:03d}"
                part_file = os.path.join(base_dir, part_name)
                if not os.path.exists(part_file):
                    raise FileNotFoundError(f"Missing part {i}: {part_name}")
                parts.append(part_file)
        else:
            part_num = 1
            while True:
                part_name = f"{part_base}.{part_num:03d}"
                part_file = os.path.join(base_dir, part_name)
                if os.path.exists(part_file):
                    parts.append(part_file)
                    part_num += 1
                else:
                    break
        
        if not parts:
            raise FileNotFoundError("No parts found to join.")

        crc32 = 0
        total_size = sum(os.path.getsize(p) for p in parts)
        bytes_written = 0
        
        last_progress_update = 0
        last_pct = -1
        
        with open(output_path, 'wb') as f_out:
            for part in parts:
                if self.context.is_cancelled():
                    raise InterruptedError("Join operation cancelled by user.")
                self.context.wait_if_paused()
                
                with open(part, 'rb') as f_in:
                    while True:
                        if self.context.is_cancelled():
                            raise InterruptedError("Join operation cancelled by user.")
                        self.context.wait_if_paused()
                        
                        chunk = f_in.read(64 * 1024)
                        if not chunk: break
                        
                        f_out.write(chunk)
                        crc32 = zlib.crc32(chunk, crc32)
                        bytes_written += len(chunk)
                        
                        if total_size > 0:
                            pct = int(bytes_written * 100 / total_size)
                            if pct != last_pct and (time.time() - last_progress_update > 0.1):
                                self.emit_progress(pct)
                                last_pct = pct
                                last_progress_update = time.time()
                            
        if expected_crc is not None:
            calculated_crc = crc32 & 0xFFFFFFFF
            if calculated_crc != expected_crc:
                raise ValueError(f"CRC32 mismatch! Expected: {expected_crc:08X}, Calculated: {calculated_crc:08X}")
