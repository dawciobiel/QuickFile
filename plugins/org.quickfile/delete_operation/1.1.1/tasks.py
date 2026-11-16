# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import time

import send2trash

from app.plugin_system.api import PluginTask


class TrashUnavailableError(RuntimeError):
    """The platform cannot move an item to the Trash.

    Raised before anything is deleted, so the user can retry without the
    "Move to Trash" option instead of losing files silently.
    """


class DeleteTask(PluginTask):
    def __init__(self, item_paths, options):
        self.item_paths = item_paths
        self.options = options
        self.total_items = 0
        self.deleted_items = 0
        self.last_progress_update = 0
        self.last_pct = -1

    def run(self, ctx):
        if self.options.get("move_to_trash", True):
            self._trash_items(ctx)
        else:
            self._delete_permanently(ctx)

    def _trash_items(self, ctx):
        """Moves each item to the Trash; never falls back to deletion silently."""
        paths = [path for path in self.item_paths if os.path.lexists(path)]
        total = len(paths)
        permanent_fallback = self.options.get("permanent_fallback", False)

        for index, path in enumerate(paths, start=1):
            self._check_cancelled(ctx)

            try:
                send2trash.send2trash(path)
            except OSError as error:
                if not permanent_fallback:
                    raise TrashUnavailableError(
                        f"Could not move '{path}' to the Trash: {error}. "
                        "Nothing was deleted; uncheck 'Move to Trash' to delete "
                        "it permanently."
                    ) from error

                ctx.log(
                    "warning",
                    f"Trash is unavailable for '{path}' ({error}); deleting permanently.",
                )
                self._delete_path(ctx, path)

            self._report_item_progress(ctx, index, total)

    def _report_item_progress(self, ctx, done, total):
        if total <= 0:
            return
        pct = int(done * 100 / total)
        if pct != self.last_pct:
            ctx.progress(pct)
            self.last_pct = pct

    def _delete_permanently(self, ctx):
        self._count_items(ctx)

        for path in self.item_paths:
            self._check_cancelled(ctx)
            if os.path.lexists(path):
                self._delete_path(ctx, path)

    def _count_items(self, ctx):
        for path in self.item_paths:
            self._check_cancelled(ctx)
            if not os.path.lexists(path):
                continue

            self.total_items += 1
            # A symlink to a directory must count as one item, not as the tree
            # it points at: os.walk would otherwise list the target's contents.
            if os.path.isdir(path) and not os.path.islink(path):
                for _root, dirs, files in os.walk(path):
                    self._check_cancelled(ctx)
                    self.total_items += len(dirs) + len(files)

    def _check_cancelled(self, ctx):
        ctx.check_cancelled()
        ctx.wait_if_paused()

    def _delete_path(self, ctx, path):
        """Deletes one path, treating symlinks as leaves, never as directories."""
        if os.path.islink(path) or not os.path.isdir(path):
            os.remove(path)
            self._update_progress(ctx)
        else:
            self._delete_tree(ctx, path)

    def _delete_tree(self, ctx, path):
        # Walk bottom-up so files are removed before their directories. os.walk
        # lists symlinks to directories in ``dirs`` but does not descend into
        # them, so they have to be unlinked instead of rmdir'd.
        for root, dirs, files in os.walk(path, topdown=False):
            for name in files:
                self._check_cancelled(ctx)
                os.remove(os.path.join(root, name))
                self._update_progress(ctx)

            for name in dirs:
                self._check_cancelled(ctx)
                entry = os.path.join(root, name)
                if os.path.islink(entry):
                    os.remove(entry)
                else:
                    os.rmdir(entry)
                self._update_progress(ctx)

        if os.path.lexists(path):
            os.rmdir(path)
            self._update_progress(ctx)

    def _update_progress(self, ctx):
        self.deleted_items += 1
        if self.total_items > 0:
            pct = int(self.deleted_items * 100 / self.total_items)
            if pct != self.last_pct and (time.time() - self.last_progress_update > 0.1):
                ctx.progress(pct)
                self.last_pct = pct
                self.last_progress_update = time.time()
