#!/usr/bin/env python3
import os
import subprocess
import xml.etree.ElementTree as ET

# --- Configuration ---
TS_FILE_PATH = "translations/app_pl.ts"
INPUT_TXT_PATH = "translations/to_translate_pl.txt"
COMPILE_SCRIPT_PATH = "./compile_translations.sh"
# -------------------

def apply_translations():
    """Reads translations from the text file and injects them into the .ts file."""
    print(f"--- Applying translations from {INPUT_TXT_PATH} to {TS_FILE_PATH} ---")
    
    if not os.path.exists(INPUT_TXT_PATH):
        print(f"Error: Translated text file not found at '{INPUT_TXT_PATH}'.")
        print("Please run the extraction script first and translate the file.")
        return False

    # 1. Read the user's translations into a dictionary
    translations_map = {}
    malformed_lines = []
    try:
        with open(INPUT_TXT_PATH, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                
                if "===" not in line:
                    malformed_lines.append((i + 1, line))
                    continue
                
                parts = line.split("===", 1)
                source_text = parts[0].strip()
                translated_text = parts[1].strip()
                
                if source_text and translated_text:
                    translations_map[source_text] = translated_text
                else:
                    print(f"Warning: Skipping line {i+1} due to empty source or translation.")

    except FileNotFoundError:
        print(f"Error: Input file '{INPUT_TXT_PATH}' not found.")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while reading the translation file: {e}")
        return False

    if malformed_lines:
        print("\nError: Found malformed lines in the translation file. Please use '===' as a separator.")
        for line_num, line_content in malformed_lines:
            print(f"- Line {line_num}: {line_content}")
        # Do not proceed if there are malformed lines
        return False

    if not translations_map:
        print("No valid translations found in the input file. Nothing to apply.")
        return True

    # 2. Parse the .ts file and update it
    try:
        tree = ET.parse(TS_FILE_PATH)
        root = tree.getroot()
        
        applied_count = 0
        
        for message in root.findall(".//message"):
            source_tag = message.find("source")
            translation_tag = message.find("translation")
            
            if source_tag is not None and source_tag.text in translations_map:
                source_text = source_tag.text
                
                # Update the translation tag
                translation_tag.text = translations_map[source_text]
                
                # Remove the 'unfinished' type attribute if it exists
                if 'type' in translation_tag.attrib:
                    del translation_tag.attrib['type']
                
                applied_count += 1
                # To avoid applying the same translation to different contexts with the same source text,
                # we can remove the key after its first use.
                # del translations_map[source_text] # This can be problematic if the same source is in multiple contexts

        tree.write(TS_FILE_PATH, encoding="utf-8", xml_declaration=True)
        
        print(f"Successfully applied {applied_count} translation(s).")
        
        # This warning is less useful now, as we expect multiple contexts.
        # if translations_map:
        #     print("\nInfo: Some translations were applied multiple times (for different contexts).")

        return True

    except ET.ParseError as e:
        print(f"Error parsing XML file '{TS_FILE_PATH}': {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while updating the .ts file: {e}")
        return False

def run_compile_script():
    """Runs the compile_translations.sh script."""
    print(f"\n--- Running compile script: {COMPILE_SCRIPT_PATH} ---")
    if not os.path.exists(COMPILE_SCRIPT_PATH):
        print(f"Error: Compile script not found at '{COMPILE_SCRIPT_PATH}'")
        return False
    
    try:
        os.chmod(COMPILE_SCRIPT_PATH, 0o755)
        result = subprocess.run([COMPILE_SCRIPT_PATH], check=True, capture_output=True, text=True)
        print("Compile script finished successfully.")
        print(f"Output:\n{result.stdout}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Error running compile script: {e}")
        if isinstance(e, subprocess.CalledProcessError):
            print(f"Stderr:\n{e.stderr}")
        return False

if __name__ == "__main__":
    if apply_translations():
        run_compile_script()
    else:
        print("\nCompile step skipped due to errors in applying translations.")
