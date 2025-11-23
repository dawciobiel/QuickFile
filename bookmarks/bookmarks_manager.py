import os
import json
import shutil

class BookmarksManager:
    def __init__(self):
        config_dir = os.path.join(os.path.expanduser("~"), ".config", "QuickFile")
        os.makedirs(config_dir, exist_ok=True)
        self.bookmarks_file = os.path.join(config_dir, "bookmarks.json")

        # Migrate old bookmarks file if it exists
        old_bookmarks_file = os.path.join(os.path.expanduser("~"), ".quickfile_bookmarks.json")
        if os.path.exists(old_bookmarks_file) and not os.path.exists(self.bookmarks_file):
            shutil.move(old_bookmarks_file, self.bookmarks_file)

        self.bookmarks = self.load_bookmarks()

    def load_bookmarks(self):
        if os.path.exists(self.bookmarks_file):
            try:
                with open(self.bookmarks_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []

    def save_bookmarks(self):
        with open(self.bookmarks_file, 'w') as f:
            json.dump(self.bookmarks, f, indent=4)

    def add_bookmark(self, path):
        if path not in self.bookmarks:
            self.bookmarks.append(path)
            self.save_bookmarks()

    def remove_bookmark(self, path):
        if path in self.bookmarks:
            self.bookmarks.remove(path)
            self.save_bookmarks()
