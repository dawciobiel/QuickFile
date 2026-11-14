# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import sys


def get_resource_path(relative_path):
    """
    Return the absolute path of a bundled resource.

    Resources live inside the ``resources`` package so that they are shipped
    with the wheel and found by PyInstaller. Historically they sat at the
    project root (``translations/``, ``themes/``, ``config/``, ``docs/about/``),
    so both layouts are accepted during the transition.

    Works for a source checkout (dev), a pip-installed package and PyInstaller.
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
        # Not frozen: the project root is the parent of the utils package.
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    bundled = os.path.join(base_path, "resources", relative_path)
    if os.path.exists(bundled):
        return bundled

    return os.path.join(base_path, relative_path)
