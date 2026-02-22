# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

from enum import Enum, auto


class TaskStatus(Enum):
    PENDING = auto()
    IN_PROGRESS = auto()
    PAUSED = auto()
    FINISHED = auto()
    CANCELLED = auto()
    ERROR = auto()


class TaskType(Enum):
    COPY = "copy_items"
    MOVE = "move_items"
    DELETE = "delete_items"
    SYNC = "synchronize"
    CREATE_ARCHIVE = "create_archive"
    EXTRACT_ARCHIVE = "extract_archive"
    CHECKSUM = "calculate_checksum"
    SEARCH = "search"
    CALCULATE_SIZE = "calculate_directory_size"
    SPLIT_FILE = "split_file"
    JOIN_FILES = "join_files"
