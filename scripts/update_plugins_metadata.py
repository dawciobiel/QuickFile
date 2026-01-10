#!/usr/bin/env python3
"""
Skrypt do automatycznej aktualizacji plików metadata.json we wszystkich pluginach.
Dodaje brakujące pola 'class_name' oraz 'platforms'.
"""
import json
import os

def update_plugins_metadata():
    # Ustal ścieżkę do katalogu plugins względem lokalizacji skryptu
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    plugins_dir = os.path.join(project_root, "plugins")

    if not os.path.exists(plugins_dir):
        print(f"Błąd: Nie znaleziono katalogu plugins: {plugins_dir}")
        return

    print(f"Skanowanie pluginów w: {plugins_dir}")
    count = 0

    for root, dirs, files in os.walk(plugins_dir):
        if "metadata.json" in files:
            metadata_path = os.path.join(root, "metadata.json")
            try:
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                modified = False

                # 1. Uzupełnij class_name na podstawie entry_point
                if "class_name" not in metadata:
                    if "entry_point" in metadata:
                        # Format entry_point to zazwyczaj "plugin:ClassName"
                        entry_point = metadata["entry_point"]
                        if ":" in entry_point:
                            class_name = entry_point.split(":")[1]
                            metadata["class_name"] = class_name
                            modified = True
                            print(f"[{metadata.get('id')}] Dodano class_name: {class_name}")

                # 2. Uzupełnij platforms
                if "platforms" not in metadata:
                    plugin_id = metadata.get("id", "").lower()
                    
                    # Prosta heurystyka na podstawie ID
                    if "windows" in plugin_id:
                        platforms = ["windows"]
                    elif "linux" in plugin_id:
                        platforms = ["linux"]
                    elif "macos" in plugin_id:
                        platforms = ["macos"]
                    else:
                        # Domyślnie wspieramy wszystkie
                        platforms = ["windows", "linux", "macos"]
                    
                    metadata["platforms"] = platforms
                    modified = True
                    print(f"[{metadata.get('id')}] Dodano platforms: {platforms}")

                if modified:
                    with open(metadata_path, 'w', encoding='utf-8') as f:
                        json.dump(metadata, f, indent=2)
                    count += 1
                    print(f"Zapisano zmiany w {metadata_path}")

            except Exception as e:
                print(f"Błąd podczas przetwarzania {metadata_path}: {e}")

    print(f"\nZakończono. Zaktualizowano {count} plików metadata.json.")

if __name__ == "__main__":
    update_plugins_metadata()