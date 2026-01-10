
import os
import json
import re

def check_theme(theme_path):
    print(f"Checking theme: {theme_path}")
    palette_path = os.path.join(theme_path, "palette.json")
    style_path = os.path.join(theme_path, "style.qss")

    if not os.path.exists(palette_path) or not os.path.exists(style_path):
        print("  Missing palette.json or style.qss")
        return

    with open(palette_path, 'r') as f:
        palette = json.load(f)
    
    with open(style_path, 'r') as f:
        style = f.read()

    # Find all placeholders in style.qss
    placeholders = set(re.findall(r'@@(\w+)@@', style))
    
    # Check if they exist in palette
    missing = []
    for p in placeholders:
        if p not in palette:
            missing.append(p)
    
    if missing:
        print(f"  ERROR: Missing keys in palette.json for placeholders: {missing}")
    else:
        print("  OK: All placeholders found in palette.")

base_dir = "/home/dawciobiel/PycharmProjects/QuickFile/themes"
for theme in os.listdir(base_dir):
    theme_path = os.path.join(base_dir, theme)
    if os.path.isdir(theme_path):
        check_theme(theme_path)
