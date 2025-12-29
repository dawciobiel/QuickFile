#!/usr/bin/env python3
# ==============================================================================
# Project: QuickFile
# Script: replay_actions.py
# Description: Replays user actions from a log file for debugging purposes.
#
# Author: Dawid Bielecki "dawciobiel"
# GitHub: https://github.com/dawciobiel/QuickFile
# License: GPL 3.0
# Date: 2025-12-25
# ==============================================================================

import argparse
import os
import sys

# Add project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from app.action_replayer import ActionReplayer
from file_operations.file_manager import FileManager
from file_operations.directory_synchronizer import DirectorySynchronizer
from utils.logger import setup_logging

def main():
    parser = argparse.ArgumentParser(description="Replay user actions from a log file for debugging.")
    parser.add_argument(
        "logfile",
        nargs='?',
        default=os.path.join(project_root, "logs", "actions.log"),
        help="Path to the actions.log file. Defaults to 'logs/actions.log' in the project directory."
    )
    args = parser.parse_args()

    setup_logging()

    file_manager = FileManager()
    dir_synchronizer = DirectorySynchronizer()

    replayer = ActionReplayer(
        log_path=args.logfile,
        file_manager=file_manager,
        dir_synchronizer=dir_synchronizer
    )
    
    replayer.run()

if __name__ == "__main__":
    main()
