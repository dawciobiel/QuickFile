# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import stat
import datetime
import platform

def get_file_properties(path):
    """
    Retrieves properties of a file or folder, adapting to the operating system.

    :param path: Path to the file or folder.
    :return: Dictionary of properties.
    """
    if not os.path.exists(path):
        return None

    properties = {}
    try:
        # Common information for all systems
        stat_info = os.stat(path)
        properties['Full path'] = os.path.abspath(path)
        properties['Size'] = f"{stat_info.st_size} bajtów"
        properties['Modification date'] = datetime.datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        properties['Creation date'] = datetime.datetime.fromtimestamp(stat_info.st_ctime).strftime('%Y-%m-%d %H:%M:%S')

        # System-specific information
        system = platform.system()
        if system == "Linux" or system == "Darwin": # for Linux and macOS
            mode = stat_info.st_mode
            permissions = stat.filemode(mode)
            properties['Permissions'] = permissions
            try:
                import pwd
                import grp
                owner = pwd.getpwuid(stat_info.st_uid).pw_name
                group = grp.getgrgid(stat_info.st_gid).gr_name
                properties['Owner'] = owner
                properties['Group'] = group
            except (ImportError, KeyError):
                properties['Owner'] = stat_info.st_uid
                properties['Group'] = stat_info.st_gid

        elif system == "Windows":
            is_readonly = bool(stat_info.st_mode & stat.S_IREAD)
            is_hidden = bool(stat_info.st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN)
            properties['Read-only'] = "Yes" if is_readonly else "No"
            properties['Hidden'] = "Yes" if is_hidden else "No"

    except Exception as e:
        # In case of problems retrieving detailed information, basic info is returned
        properties['Error'] = f"Could not retrieve all properties: {e}"

    return properties
