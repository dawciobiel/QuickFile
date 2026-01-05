import sys
import os

def get_resource_path(relative_path):
    """ 
    Get absolute path to resource, works for dev and for PyInstaller.
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        # This is the case for --onefile mode.
        base_path = sys._MEIPASS
    elif getattr(sys, 'frozen', False):
        # In --onedir mode, the executable is in the root of the distribution directory.
        # Resources are in subdirectories relative to the executable.
        base_path = os.path.dirname(sys.executable)
    else:
        # Not frozen, running from source.
        # The project root is two levels up from this file's location (utils/resource_path.py)
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    return os.path.join(base_path, relative_path)
