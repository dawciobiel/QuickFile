# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import hashlib
import os
import zlib

from app.plugin_system.api import PluginTask


class ChecksumTask(PluginTask):
    def __init__(self, file_path, algorithms):
        self.file_path = file_path
        self.algorithms = algorithms

    def run(self, ctx):
        chunk_size = 65536  # 64k
        hashes = {alg: hashlib.new(alg) for alg in self.algorithms if alg != 'crc32'}
        crc = 0
        has_crc32 = 'crc32' in self.algorithms

        file_size = os.path.getsize(self.file_path)
        bytes_read = 0

        with open(self.file_path, 'rb') as f:
            while True:
                ctx.check_cancelled()
                ctx.wait_if_paused()

                chunk = f.read(chunk_size)
                if not chunk:
                    break

                if has_crc32:
                    crc = zlib.crc32(chunk, crc)

                for alg in hashes:
                    hashes[alg].update(chunk)

                bytes_read += len(chunk)
                if file_size > 0:
                    ctx.progress(int(bytes_read * 100 / file_size))

        results = {alg: h.hexdigest() for alg, h in hashes.items()}
        if has_crc32:
            results['crc32'] = f"{crc & 0xFFFFFFFF:08x}"

        return results
