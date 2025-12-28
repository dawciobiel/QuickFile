import os
import re
import xml.etree.ElementTree as ET

# --- Patterns and Whitelists ---

# Regex to find simple string literals in Python code.
PY_STRING_LITERAL_RE = re.compile(r"""(['"])(.*?)\1""")

# Common widget classes and methods that take user-facing strings.
PY_UI_METHODS = [
    'setText', 'setWindowTitle', 'setPlaceholderText', 'setToolTip',
    'setTitle', 'setText', 'setTabText', 'addItem', 'setWhatsThis',
    'setStatusTip', 'showMessage'
]
PY_UI_WIDGETS = [
    'QMessageBox', 'QInputDialog', 'QLabel', 'QPushButton',
    'QCheckBox', 'QRadioButton', 'QGroupBox', 'QAction'
]

# Functions and methods where string literals are acceptable and not for translation.
PY_SAFE_FUNCTIONS = [
    'setObjectName', 'os.path.join', 'open', 'loadUi', 'uic.loadUi',
    'get_setting', 'set_setting', 're.compile', 're.findall', 're.match',
    're.search', 'startswith', 'endswith', 'os.path.dirname', 'os.path.basename',
    'findChild', 'findData', 'setCurrentIndex', 'setCurrentWidget',
    'addTab', 'indexOf', 'setFileMode', 'setOption', 'connect', 'pyqtSignal',
    'emit', 'format', 'replace', 'log_action', 'logging.', 'print', 'tr',
    '__version__', 'encode', 'decode', 'get', 'addItems'
]

# Directories to ignore
IGNORED_DIRS = [
    'logs', 'experiments', 'tests', 'venv', '__pycache__', '.git', '.idea', 'build', 'dist', 'config', 'resources'
]

# --- Helper Functions ---

def is_string_ignorable(s):
    """Check if a string is likely not a UI string."""
    s = s.strip()
    if not s:
        return True
    if len(s) < 3 and " " not in s: # Ignore very short strings without spaces
        return True
    if re.match(r'^[a-zA-Z0-9_.\-/*#]+$', s): # Looks like a key, path, or identifier
        return True
    if s in ['r', 'w', 'rb', 'wb', 'utf-8']:
        return True
    if s.lower().endswith(('.py', '.ui', '.json', '.md', '.qss', '.rcc', '.log')):
        return True
    if re.match(r'^v\d+\.\d+\.\d+$', s):
        return True
    return False

def check_py_file(file_path):
    """Scans a Python file for hardcoded, user-facing strings."""
    found_issues = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line_num, line in enumerate(lines, 1):
                # Skip comments and translation lines
                if line.strip().startswith('#') or 'translation_manager.translate' in line:
                    continue

                # Check if the line contains a UI method/widget call
                if any(ui_call in line for ui_call in PY_UI_METHODS + PY_UI_WIDGETS):
                    for match in PY_STRING_LITERAL_RE.finditer(line):
                        literal = match.group(2)

                        if is_string_ignorable(literal):
                            continue

                        is_safe = False
                        for safe_func in PY_SAFE_FUNCTIONS:
                            if f'{safe_func}(' in line and literal in line:
                                is_safe = True
                                break
                        if is_safe:
                            continue
                        
                        # Check for f-strings with variables
                        if re.search(r'\{[a-zA-Z0-9_]+\}', literal):
                            continue

                        issue = (file_path, line_num, literal.strip())
                        if issue not in found_issues:
                            found_issues.append(issue)

    except Exception as e:
        print(f"Error processing Python file {file_path}: {e}")
    return found_issues

def check_ui_file(file_path):
    """Scans a .ui file for hardcoded strings in <string> properties."""
    found_issues = []
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        for prop in root.findall('.//property/string'):
            if prop.text and prop.text.strip():
                if not is_string_ignorable(prop.text):
                    parent_property = prop.find('..')
                    parent_widget = parent_property.find('..')
                    widget_class = parent_widget.get('class', 'N/A')
                    widget_name = parent_widget.get('name', 'N/A')
                    property_name = parent_property.get('name', 'N/A')

                    if property_name in ['text', 'title', 'windowTitle', 'placeholderText', 'toolTip']:
                        issue = (file_path, 'XML', f"Widget: {widget_class} ('{widget_name}'), Property: '{property_name}', Text: '{prop.text.strip()}'")
                        if issue not in found_issues:
                            found_issues.append(issue)
    except Exception as e:
        print(f"Error processing UI file {file_path}: {e}")
    return found_issues


def main():
    """Main function to run the check."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    all_issues = []

    print("--- Hardcoded String Check ---")
    print(f"Scanning project root: {project_root}\n")

    for root, dirs, files in os.walk(project_root):
        # Modify dirs in-place to skip ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith('.')]
        
        for file in files:
            file_path = os.path.join(root, file)
            if file.endswith('.py'):
                all_issues.extend(check_py_file(file_path))
            elif file.endswith('.ui'):
                all_issues.extend(check_ui_file(file_path))

    if all_issues:
        print(f"Found {len(all_issues)} potential hardcoded strings:\n")
        for file, line, text in all_issues:
            if line == 'XML':
                print(f"File: {file}\n  {text}\n")
            else:
                print(f"File: {file}, Line: {line}\n  Text: '{text}'\n")
    else:
        print("Scan complete. No obvious hardcoded UI strings found.")


if __name__ == "__main__":
    main()
