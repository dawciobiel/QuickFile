import os
import logging
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
        query_lower = query.lower()
        
        logging.debug(f"SearchPlugin: Starting search in {root_path} for '{query}'")
        
        try:
            for dirpath, dirnames, filenames in os.walk(root_path):
                if task_context:
                    if task_context.is_cancelled:
                        logging.info("Search cancelled by user.")
                        break
                    task_context.wait_if_paused()
                
                if task:
                    # Update details less frequently to avoid flooding UI updates?
                    # For now, let's update on every directory change
                    task.set_details(f"Scanning: {os.path.basename(dirpath)}")

                # Check directories
                for dirname in dirnames:
                    if query_lower in dirname.lower():
                        full_path = os.path.join(dirpath, dirname)
                        found_items.append(full_path)
                        logging.debug(f"Found directory: {full_path}")
                
                # Check files
                for filename in filenames:
                    if query_lower in filename.lower():
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
