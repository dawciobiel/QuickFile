import os
import json

class BookmarksManager:
    def __init__(self, bookmarks_file):
        self.bookmarks_file = bookmarks_file
        self.bookmarks = self.load_bookmarks()

    def load_bookmarks(self):
        if os.path.exists(self.bookmarks_file):
            with open(self.bookmarks_file, 'r') as f:
                return json.load(f)
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
