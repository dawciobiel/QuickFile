import os
import logging
import fnmatch
from plugins.base import SearchPlugin

class StandardSearchPlugin(SearchPlugin):
    @property
    def name(self) -> str:
        return "Standard File Search"

    @property
    def description(self) -> str:
        return "Provides standard file search functionality using recursive directory scanning."

    def search(self, root_path: str, query: str, options: dict, progress_callback=None, task_context=None, task=None) -> list[str]:
        if not root_path or not os.path.exists(root_path):
            raise ValueError(f"Invalid root path: {root_path}")

        found_items = []
        
        # Extract options
        file_name_pattern = options.get("file_name", "*")
        if not file_name_pattern:
            file_name_pattern = "*" 
            
        file_name_case_sensitive = options.get("file_name_case_sensitive", False)
        
        extension = options.get("extension", "")
        extension_case_sensitive = options.get("extension_case_sensitive", False)
        
        exclude_paths = options.get("exclude_paths", [])
        exclude_paths = [os.path.abspath(p) for p in exclude_paths if p.strip()]

        logging.debug(f"SearchPlugin: Starting search in {root_path}")
        logging.debug(f"Pattern: {file_name_pattern} (Case: {file_name_case_sensitive}), Ext: {extension} (Case: {extension_case_sensitive}), Exclude: {exclude_paths}")
        
        try:
            for dirpath, dirnames, filenames in os.walk(root_path):
                if task_context:
                    if task_context.is_cancelled:
                        logging.info("Search cancelled by user.")
                        break
                    task_context.wait_if_paused()
                
                if task:
                    task.set_details(f"Scanning: {os.path.basename(dirpath)}")

                # Handle exclusions
                for i in range(len(dirnames) - 1, -1, -1):
                    full_dir_path = os.path.abspath(os.path.join(dirpath, dirnames[i]))
                    for excluded in exclude_paths:
                        if full_dir_path.startswith(excluded):
                            logging.debug(f"Skipping excluded directory: {full_dir_path}")
                            del dirnames[i]
                            break

                # Check files
                for filename in filenames:
                    if self._matches_criteria(filename, file_name_pattern, file_name_case_sensitive, extension, extension_case_sensitive):
                        full_path = os.path.join(dirpath, filename)
                        found_items.append(full_path)
                        logging.debug(f"Found file: {full_path}")
                        
        except Exception as e:
            if str(e) == "Operation cancelled":
                raise
            logging.exception(f"Error during search in {root_path}: {e}")
            raise

        logging.debug(f"SearchPlugin: Finished. Found {len(found_items)} items.")
        return found_items

    def _matches_criteria(self, filename, pattern, pattern_case_sensitive, extension, extension_case_sensitive):
        # Check extension first (faster)
        if extension:
            if extension_case_sensitive:
                if not filename.endswith(f".{extension}"):
                    return False
            else:
                if not filename.lower().endswith(f".{extension.lower()}"):
                    return False

        # Check filename pattern
        if pattern_case_sensitive:
            return fnmatch.fnmatchcase(filename, pattern)
        else:
            # Force case-insensitive match by lowercasing both
            return fnmatch.fnmatchcase(filename.lower(), pattern.lower())
