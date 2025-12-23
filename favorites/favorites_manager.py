import os
import json
import shutil

class FavoritesManager:
    def __init__(self):
        config_dir = os.path.join(os.path.expanduser("~"), ".config", "QuickFile")
        os.makedirs(config_dir, exist_ok=True)
        self.favorites_file = os.path.join(config_dir, "favorites.json")

        # Migrate old bookmarks file if it exists
        old_bookmarks_file = os.path.join(os.path.expanduser("~"), ".quickfile_bookmarks.json")
        if os.path.exists(old_bookmarks_file) and not os.path.exists(self.favorites_file):
            shutil.move(old_bookmarks_file, self.favorites_file)
        
        # Also check for old bookmarks.json
        old_bookmarks_json = os.path.join(config_dir, "bookmarks.json")
        if os.path.exists(old_bookmarks_json) and not os.path.exists(self.favorites_file):
            shutil.move(old_bookmarks_json, self.favorites_file)

        self.favorites = self.load_favorites()

    def load_favorites(self):
        if os.path.exists(self.favorites_file):
            try:
                with open(self.favorites_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []

    def save_favorites(self):
        with open(self.favorites_file, 'w') as f:
            json.dump(self.favorites, f, indent=4)

    def add_favorite(self, path):
        if path not in self.favorites:
            self.favorites.append(path)
            self.save_favorites()

    def remove_favorite(self, path):
        if path in self.favorites:
            self.favorites.remove(path)
            self.save_favorites()

    def get_favorites(self):
        return self.favorites
