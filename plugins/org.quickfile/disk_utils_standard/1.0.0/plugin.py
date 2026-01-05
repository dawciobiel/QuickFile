import shutil
from plugins.base import DiskUtilsPlugin

class StandardDiskUtilsPlugin(DiskUtilsPlugin):
    @property
    def name(self) -> str:
        return "Standard Disk Utils"

    @property
    def description(self) -> str:
        return "Provides standard disk utility functions using Python's shutil module."

    def get_disk_usage(self, path: str) -> tuple[int, int, int] | None:
        try:
            usage = shutil.disk_usage(path)
            return usage.total, usage.used, usage.free
        except Exception:
            return None
