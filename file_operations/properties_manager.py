import os
import stat
import datetime
import platform

def get_file_properties(path):
    """
    Pobiera właściwości pliku lub folderu, dostosowując się do systemu operacyjnego.

    :param path: Ścieżka do pliku lub folderu.
    :return: Słownik z właściwościami.
    """
    if not os.path.exists(path):
        return None

    properties = {}
    try:
        # Informacje wspólne dla wszystkich systemów
        stat_info = os.stat(path)
        properties['Pełna ścieżka'] = os.path.abspath(path)
        properties['Rozmiar'] = f"{stat_info.st_size} bajtów"
        properties['Data modyfikacji'] = datetime.datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        properties['Data utworzenia'] = datetime.datetime.fromtimestamp(stat_info.st_ctime).strftime('%Y-%m-%d %H:%M:%S')

        # Informacje specyficzne dla systemu
        system = platform.system()
        if system == "Linux" or system == "Darwin": # dla Linux i macOS
            mode = stat_info.st_mode
            permissions = stat.filemode(mode)
            properties['Uprawnienia'] = permissions
            try:
                import pwd
                import grp
                owner = pwd.getpwuid(stat_info.st_uid).pw_name
                group = grp.getgrgid(stat_info.st_gid).gr_name
                properties['Właściciel'] = owner
                properties['Grupa'] = group
            except (ImportError, KeyError):
                properties['Właściciel'] = stat_info.st_uid
                properties['Grupa'] = stat_info.st_gid

        elif system == "Windows":
            is_readonly = bool(stat_info.st_mode & stat.S_IREAD)
            is_hidden = bool(stat_info.st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN)
            properties['Tylko do odczytu'] = "Tak" if is_readonly else "Nie"
            properties['Ukryty'] = "Tak" if is_hidden else "Nie"

    except Exception as e:
        # W razie problemów z pobraniem szczegółowych informacji, zwracamy podstawowe
        properties['Błąd'] = f"Nie można było pobrać wszystkich właściwości: {e}"

    return properties
