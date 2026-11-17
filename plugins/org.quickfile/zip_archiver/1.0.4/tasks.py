# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import shutil
import zipfile

from app.plugin_system.api import PluginTask


COMPRESSION_METHODS = {
    "deflate": zipfile.ZIP_DEFLATED,
    "store": zipfile.ZIP_STORED,
}


class CreateZipTask(PluginTask):
    def __init__(self, source_paths, destination_path, options):
        self.source_paths = source_paths
        self.destination_path = destination_path
        self.options = options
        self.total_files = 0
        self.processed_files = 0
        self.last_progress_update = 0
        self.last_pct = -1

    def run(self, ctx):
        compression = self._compression()
        compresslevel = self.options.get("compresslevel", -1)

        # Phase 1: Count files for progress reporting
        for src_path in self.source_paths:
            ctx.check_cancelled()
            if os.path.isdir(src_path):
                for root, _, files in os.walk(src_path):
                    self.total_files += len(files)
            else:
                self.total_files += 1

        # Phase 2: Create archive
        ctx.check_cancelled()
        with zipfile.ZipFile(self.destination_path, 'w', compression=compression, compresslevel=compresslevel) as zipf:
            for src_path in self.source_paths:
                ctx.check_cancelled()

                if os.path.isdir(src_path):
                    base_dir = os.path.dirname(src_path)
                    for root, _, files in os.walk(src_path):
                        for file in files:
                            ctx.check_cancelled()
                            ctx.wait_if_paused()

                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, base_dir)
                            zipf.write(file_path, arcname)
                            self._update_progress(ctx)
                else:  # It's a file
                    ctx.check_cancelled()
                    ctx.wait_if_paused()

                    arcname = os.path.basename(src_path)
                    zipf.write(src_path, arcname)
                    self._update_progress(ctx)

        return {"archive_path": self.destination_path}

    def _compression(self):
        """Translate the schema value into a ``zipfile`` constant.

        Older callers may still pass the numeric constant directly, so both
        shapes are accepted.
        """
        method = self.options.get("compression", "deflate")
        if not isinstance(method, str):
            return method

        try:
            return COMPRESSION_METHODS[method.lower()]
        except KeyError:
            raise ValueError(
                f"Unknown ZIP compression method: {method!r}; "
                f"expected one of {sorted(COMPRESSION_METHODS)}"
            ) from None

    def _update_progress(self, ctx):
        self.processed_files += 1
        if self.total_files > 0:
            pct = int(self.processed_files * 100 / self.total_files)
            if pct != self.last_pct:
                ctx.progress(pct)
                self.last_pct = pct


class ExtractZipTask(PluginTask):
    def __init__(self, source_path, dest_dir, options):
        self.source_path = source_path
        self.dest_dir = dest_dir
        self.options = options
        self.total_files = 0
        self.processed_files = 0
        self.last_pct = -1

    def run(self, ctx):
        os.makedirs(self.dest_dir, exist_ok=True)

        with zipfile.ZipFile(self.source_path) as archive:
            members = archive.infolist()
            self.total_files = len(members)

            for member in members:
                ctx.check_cancelled()
                ctx.wait_if_paused()

                target = self._safe_target(member.filename)
                if member.is_dir():
                    os.makedirs(target, exist_ok=True)
                else:
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with archive.open(member) as source, open(target, "wb") as destination:
                        shutil.copyfileobj(source, destination)

                self._update_progress(ctx)

        return {"extract_path": self.dest_dir}

    def _safe_target(self, member_name):
        """Resolve an archive member inside ``dest_dir``.

        ZIP entry names come from an untrusted file. Without this check a name
        like ``../evil`` or an absolute path would write outside the directory
        the user selected (the "zip slip" bug).
        """
        root = os.path.realpath(self.dest_dir)
        relative = member_name.replace("\\", "/")
        target = os.path.realpath(os.path.join(root, relative))

        try:
            inside = os.path.commonpath([root, target]) == root
        except ValueError:
            inside = False

        if not inside:
            raise ValueError(
                f"Archive member {member_name!r} escapes the destination directory"
            )
        return target

    def _update_progress(self, ctx):
        self.processed_files += 1
        if self.total_files > 0:
            pct = int(self.processed_files * 100 / self.total_files)
            if pct != self.last_pct:
                ctx.progress(pct)
                self.last_pct = pct
