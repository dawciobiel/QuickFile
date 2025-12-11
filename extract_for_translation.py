#!/usr/bin/env python3
import os
import xml.etree.ElementTree as ET

# --- Configuration ---
TS_FILE_PATH = "translations/app_pl.ts"
OUTPUT_TXT_PATH = "translations/to_translate_pl.txt"
# -------------------

def extract_untranslated_strings():
    """Parses the .ts file and extracts strings that need translation."""
    print(f"--- Parsing {TS_FILE_PATH} for untranslated strings ---")
    if not os.path.exists(TS_FILE_PATH):
        print(f"Error: Translation source file not found at '{TS_FILE_PATH}'")
        print("Please run './update_translations.sh' first.")
        return

    try:
        tree = ET.parse(TS_FILE_PATH)
        root = tree.getroot()
        
        untranslated_sources = []
        
        # Find all <message> tags
        for message in root.findall(".//message"):
            source_tag = message.find("source")
            translation_tag = message.find("translation")
            
            if source_tag is not None and translation_tag is not None and source_tag.text is not None:
                # Check if translation is missing or marked as unfinished
                is_unfinished = translation_tag.get("type") == "unfinished"
                is_empty = not translation_tag.text
                
                if is_unfinished or is_empty:
                    untranslated_sources.append(source_tag.text)

        if not untranslated_sources:
            print("No new strings to translate. Everything is up to date!")
            # Ensure the output file is empty if there's nothing to do
            if os.path.exists(OUTPUT_TXT_PATH):
                with open(OUTPUT_TXT_PATH, "w", encoding="utf-8") as f:
                    pass
            return

        # Write unique strings to the output file
        unique_sources = sorted(list(dict.fromkeys(untranslated_sources)))
        
        with open(OUTPUT_TXT_PATH, "w", encoding="utf-8") as f:
            for text in unique_sources:
                f.write(text + "\n")
        
        print(f"\nSuccessfully extracted {len(unique_sources)} unique strings to '{OUTPUT_TXT_PATH}'.")
        print("Please translate the content of this file using the 'Original === Translation' format.")

    except ET.ParseError as e:
        print(f"Error parsing XML file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    extract_untranslated_strings()
