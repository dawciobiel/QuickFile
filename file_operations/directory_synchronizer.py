import logging
import os
import shutil
import filecmp

class DirectorySynchronizerError(Exception):
    """Custom exception for DirectorySynchronizer errors."""
    pass

class DirectorySynchronizer:
    def __init__(self):
        self.total_items = 0
        self.processed_items = 0

    def synchronize(self, dir1, dir2, options, progress_callback=None, task_context=None, task=None):
        try:
            # First, count total items for progress calculation
            self.total_items = self._count_items(dir1, dir2, options)
            self.processed_items = 0

            if options.get("two_way"):
                self._synchronize_two_way(dir1, dir2, options, progress_callback, task_context, task)
            else: # One-way
                source, dest = (dir1, dir2) if options.get("left_to_right") else (dir2, dir1)
                self._synchronize_one_way(source, dest, options, progress_callback, task_context, task)
            
            return "Synchronization completed successfully."
        except Exception as e:
            logging.exception(f"Error during synchronization between {dir1} and {dir2}: {e}")
            raise DirectorySynchronizerError(f"Error during synchronization: {e}")

    def _count_items(self, dir1, dir2, options):
        # This is a simplified counting and might not be perfectly accurate
        # but gives a good estimate for progress bar without too much overhead.
        count = 0
        comparison = filecmp.dircmp(dir1, dir2)
        count += len(comparison.left_only) + len(comparison.right_only) + len(comparison.diff_files)
        if options.get("include_subdirs"):
            for common_dir in comparison.common_dirs:
                count += self._count_items(os.path.join(dir1, common_dir), os.path.join(dir2, common_dir), options)
        return count

    def _update_progress(self, progress_callback):
        self.processed_items += 1
        if progress_callback and self.total_items > 0:
            progress = int((self.processed_items / self.total_items) * 100)
            progress_callback.emit(progress)

    def _synchronize_one_way(self, source, dest, options, progress_callback=None, task_context=None, task=None):
        if task_context and task_context.is_cancelled: return
        if task_context: task_context.wait_if_paused()

        comparison = filecmp.dircmp(source, dest)
        
        for item in comparison.left_only:
            if task_context and task_context.is_cancelled: return
            if task: task.set_details(f"Copying: {item}")
            shutil.copy2(os.path.join(source, item), os.path.join(dest, item))
            self._update_progress(progress_callback)

        for item in comparison.diff_files:
            if task_context and task_context.is_cancelled: return
            if task: task.set_details(f"Updating: {item}")
            shutil.copy2(os.path.join(source, item), os.path.join(dest, item))
            self._update_progress(progress_callback)

        if options.get("delete"):
            for item in comparison.right_only:
                if task_context and task_context.is_cancelled: return
                if task: task.set_details(f"Deleting: {item}")
                path = os.path.join(dest, item)
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                self._update_progress(progress_callback)

        if options.get("include_subdirs"):
            for common_dir in comparison.common_dirs:
                self._synchronize_one_way(os.path.join(source, common_dir), os.path.join(dest, common_dir), options, progress_callback, task_context, task)

    def _synchronize_two_way(self, dir1, dir2, options, progress_callback=None, task_context=None, task=None):
        if task_context and task_context.is_cancelled: return
        if task_context: task_context.wait_if_paused()

        comparison = filecmp.dircmp(dir1, dir2)

        for item in comparison.left_only:
            if task_context and task_context.is_cancelled: return
            if task: task.set_details(f"Copying to right: {item}")
            shutil.copy2(os.path.join(dir1, item), os.path.join(dir2, item))
            self._update_progress(progress_callback)

        for item in comparison.right_only:
            if task_context and task_context.is_cancelled: return
            if task: task.set_details(f"Copying to left: {item}")
            shutil.copy2(os.path.join(dir2, item), os.path.join(dir1, item))
            self._update_progress(progress_callback)

        for item in comparison.diff_files:
            if task_context and task_context.is_cancelled: return
            path1 = os.path.join(dir1, item)
            path2 = os.path.join(dir2, item)
            if os.path.getmtime(path1) > os.path.getmtime(path2):
                if task: task.set_details(f"Updating right: {item}")
                shutil.copy2(path1, path2)
            else:
                if task: task.set_details(f"Updating left: {item}")
                shutil.copy2(path2, path1)
            self._update_progress(progress_callback)
        
        if options.get("include_subdirs"):
            for common_dir in comparison.common_dirs:
                self._synchronize_two_way(os.path.join(dir1, common_dir), os.path.join(dir2, common_dir), options, progress_callback, task_context, task)
