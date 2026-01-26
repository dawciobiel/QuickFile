# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import logging
import os
import time
import zlib
import sys
import traceback
# noinspection PyPackageRequirements
from typing import LiteralString

from plugins.base import MenuActionPlugin


# noinspection PyPackageRequirements


class FileSplitterPlugin(MenuActionPlugin):
    @property
    def name(self):
        return "File Splitter"

    @property
    def description(self):
        return "Splits large files into smaller parts and joins them back."

    def get_menu_actions(self):
        return [
            {
                "text": "Split File...",
                "menu": "file",
                "action_id": "split_file",
                "dialog_module": "ui.split_join_dialogs",
                "dialog_class": "SplitDialog",
                "task_type": "SPLIT_FILE"
            },
            {
                "text": "Join Files...",
                "menu": "file",
                "action_id": "join_files",
                "dialog_module": "ui.split_join_dialogs",
                "dialog_class": "JoinDialog",
                "task_type": "JOIN_FILES"
            }
        ]

    def split_file(self, source_path, dest_dir, options, progress_callback, task_context, task, send_trace):
        send_trace(f"Starting split_file: {source_path} -> {dest_dir}")
        chunk_size = options.get("chunk_size")
        generate_checksum = options.get("generate_checksum", False)
        
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
            
        file_size = os.path.getsize(source_path)
        base_name = os.path.basename(source_path)
        
        send_trace(f"File size: {file_size}, Chunk size: {chunk_size}")

        task.set_details(f"Splitting {base_name}...")
        
        bytes_read = 0
        part_num = 1
        crc32 = 0
        
        last_progress_update = 0
        last_status_check = 0
        last_pct = -1
        
        f_in = None
        try:
            with open(source_path, 'rb') as f_in:
                while True:
                    send_trace(f"Outer loop, part {part_num}")
                    # Check status more frequently
                    if task_context.is_cancelled: 
                        raise InterruptedError("Split operation cancelled by user.")
                    # task_context.wait_if_paused() # Still commented out
                    
                    part_ext = f".{part_num:03d}"
                    # noinspection PyTypeChecker
                    part_path = os.path.join(dest_dir, base_name + part_ext)
                    
                    with open(part_path, 'wb') as f_out:
                        chunk_written = 0
                        while chunk_written < chunk_size:
                            # Check status more frequently
                            if task_context.is_cancelled: 
                                raise InterruptedError("Split operation cancelled by user.")
                            # task_context.wait_if_paused() # Still commented out
                            
                            read_size = min(64 * 1024, chunk_size - chunk_written)
                            data = f_in.read(read_size)
                            if not data:
                                send_trace("No more data from source file.")
                                break
                            
                            f_out.write(data)
                            if generate_checksum: crc32 = zlib.crc32(data, crc32)
                            chunk_written += len(data)
                            bytes_read += len(data)
                            
                            if file_size > 0: 
                                pct = int(bytes_read * 100 / file_size)
                                # Update progress only if changed and at least 0.1s passed
                                if pct != last_pct and (time.time() - last_progress_update > 0.1):
                                    send_trace(f"Progress: {pct}%")
                                    progress_callback(pct)
                                    last_pct = pct
                                    last_progress_update = time.time()
                            
                        if chunk_written == 0:
                            send_trace("No data written to part, removing empty file.")
                            os.remove(part_path)
                            break
                    part_num += 1
                    if bytes_read >= file_size:
                        send_trace("All bytes read, breaking outer loop.")
                        break
            
            if generate_checksum:
                crc_path = os.path.join(dest_dir, base_name + ".crc32")
                with open(crc_path, 'w', encoding='utf-8') as f_crc:
                    f_crc.write(f"filename={base_name}\n")
                    f_crc.write(f"filenameutf8={base_name}\n")
                    f_crc.write(f"size={file_size}\n")
                    f_crc.write(f"crc32={crc32 & 0xFFFFFFFF:08X}\n")
                    f_crc.write(f"parts_count={part_num - 1}\n")
                send_trace(f"Checksum file created at {crc_path}")

            send_trace("Split finished.")
        except InterruptedError:
            send_trace("Split operation cancelled.")
            raise
        except Exception as e:
            send_trace(f"Exception in split_file: {e}\n{traceback.format_exc()}")
            raise
        finally:
            if f_in:
                f_in.close()

    def join_files(self, source_path, dest_dir, options, progress_callback, task_context, task, send_trace):
        output_filename = options.get("output_filename")
        output_path = os.path.join(dest_dir, output_filename)
        
        base_dir = os.path.dirname(source_path)
        source_basename = os.path.basename(source_path)
        
        # Determine parts
        parts = []
        expected_crc = None
        part_base = None
        expected_parts_count = None
        
        # If .crc32 file is selected, try to read metadata
        if source_basename.endswith(".crc32"):
            try:
                with open(source_path, 'r', encoding='utf-8-sig') as f:
                    for line in f:
                        line = line.rstrip('\n')
                        if line.startswith("crc32="):
                            expected_crc = int(line.split("=", 1)[1], 16)
                        elif line.startswith("parts_count="):
                            expected_parts_count = int(line.split("=", 1)[1])
                        elif line.startswith("filenameutf8="):
                            part_base = line.split("=", 1)[1]
                        elif line.startswith("filename=") and part_base is None:
                            # Try to find parts based on filename in crc
                            part_base = line.split("=", 1)[1]
            except Exception as e:
                send_trace(f"Failed to parse .crc32 file: {e}")
                
            # If we couldn't determine base name from crc, assume it's the crc filename without extension
            if part_base is None:
                part_base = source_basename[:-6] # remove .crc32
            
            # Check if parts exist for the determined part_base. If not, fallback to filename derived from .crc32 file.
            first_part_path = os.path.join(base_dir, f"{part_base}.001")
            if not os.path.exists(first_part_path):
                fallback_base = source_basename[:-6]
                if fallback_base != part_base:
                    if os.path.exists(os.path.join(base_dir, f"{fallback_base}.001")):
                        part_base = fallback_base
        elif source_basename.endswith(".001"):
            part_base = source_basename[:-4]
            # Try to find crc32 file for verification
            crc_path = os.path.join(base_dir, part_base + ".crc32")
            if os.path.exists(crc_path):
                try:
                    with open(crc_path, 'r', encoding='utf-8-sig') as f:
                        for line in f:
                            line = line.rstrip('\n')
                            if line.startswith("crc32="):
                                expected_crc = int(line.split("=", 1)[1], 16)
                except Exception as e:
                    send_trace(f"Failed to parse auto-detected .crc32 file: {e}")
        else:
            # Try to guess
            part_base = source_basename

        # Find parts
        if expected_parts_count is not None:
            # We know exactly how many parts to expect
            for i in range(1, expected_parts_count + 1):
                part_name = f"{part_base}.{i:03d}"
                part_file = os.path.join(base_dir, part_name)
                if not os.path.exists(part_file):
                    raise FileNotFoundError(f"Missing part {i}: {part_name}")
                parts.append(part_file)
        else:
            # Auto-discover parts until a gap is found
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

        task.set_details(f"Joining {len(parts)} parts into {output_filename}...")
        
        crc32 = 0
        total_size = sum(os.path.getsize(p) for p in parts)
        bytes_written = 0
        
        last_progress_update = 0
        last_status_check = 0
        last_pct = -1
        
        with open(output_path, 'wb') as f_out:
            for part in parts:
                if task_context.is_cancelled: # Check cancellation more frequently
                    raise InterruptedError("Join operation cancelled by user.")
                # task_context.wait_if_paused() # Still commented out
                
                with open(part, 'rb') as f_in:
                    while True:
                        if task_context.is_cancelled: # Check cancellation more frequently
                            raise InterruptedError("Join operation cancelled by user.")
                        # task_context.wait_if_paused() # Still commented out
                        
                        chunk = f_in.read(64 * 1024)
                        if not chunk: break
                        
                        f_out.write(chunk)
                        crc32 = zlib.crc32(chunk, crc32)
                        bytes_written += len(chunk)
                        
                        if total_size > 0:
                            pct = int(bytes_written * 100 / total_size)
                            if pct != last_pct and (time.time() - last_progress_update > 0.1):
                                progress_callback(pct)  # Direct call
                                last_pct = pct
                                last_progress_update = time.time()
                            
        if expected_crc is not None:
            calculated_crc = crc32 & 0xFFFFFFFF
            if calculated_crc != expected_crc:
                raise ValueError(f"CRC32 mismatch! Expected: {expected_crc:08X}, Calculated: {calculated_crc:08X}")
            else:
                task.set_details("Join complete. Checksum verified OK.")
        else:
            task.set_details("Join complete. No checksum to verify.")
