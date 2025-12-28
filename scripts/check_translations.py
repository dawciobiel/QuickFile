import os
import re
import json
import xml.etree.ElementTree as ET

def find_translation_keys_in_py(file_path):
    keys = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Regex to find translation_manager.translate("Context", "Key")
            matches = re.findall(r'translation_manager\.translate\s*\(\s*"(?P<context>[^"]+)"\s*,\s*"(?P<key>[^"]+)"', content)
            for context, key in matches:
                keys.add(f"{context}.{key}")
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return keys

def find_translation_keys_in_ui(file_path):
    keys = set()
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        for element in root.iter():
            if 'translatable' in element.attrib and element.attrib['translatable'] == 'true':
                if element.text and element.text.strip():
                    # This is a simplification. Real .ui files might have more complex structures.
                    # We assume the key is the text itself for now.
                    # A better approach would be to have explicit keys in the .ui file.
                    print(f"Warning: Found translatable text without explicit key in {file_path}: {element.text.strip()}")

    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
    return keys

def get_existing_keys(json_path):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return set(json.load(f).keys())
    except FileNotFoundError:
        return set()
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {json_path}")
        return set()

def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    all_code_keys = set()

    for root, _, files in os.walk(project_root):
        for file in files:
            path = os.path.join(root, file)
            if file.endswith('.py'):
                all_code_keys.update(find_translation_keys_in_py(path))
            elif file.endswith('.ui'):
                # UI file parsing is more complex and not fully implemented here.
                # We focus on .py files for now as they contain most of the explicit keys.
                pass

    print("--- Translation Check ---")
    
    for lang_file in ['en_US.json', 'pl_PL.json']:
        print(f"\nChecking {lang_file}...")
        lang_path = os.path.join(project_root, 'translations', lang_file)
        existing_keys = get_existing_keys(lang_path)
        
        missing_keys = all_code_keys - existing_keys
        
        if missing_keys:
            print(f"  Missing keys ({len(missing_keys)}):")
            for key in sorted(list(missing_keys)):
                print(f"    - {key}")
        else:
            print("  All keys are present.")
            
        # Check for obsolete keys
        obsolete_keys = existing_keys - all_code_keys
        if obsolete_keys:
            print(f"  Obsolete keys ({len(obsolete_keys)}):")
            for key in sorted(list(obsolete_keys)):
                print(f"    - {key}")

if __name__ == "__main__":
    main()
