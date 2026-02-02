import logging
import os
import subprocess
import sys
from typing import List, Dict, Optional


class PluginDependencyManager:
    """
    Manages dependencies for plugins, installing them into a dedicated 'libs' directory
    within the plugin's folder.
    """

    def __init__(self):
        self.logger = logging.getLogger("PluginDependencyManager")

    def ensure_dependencies(self, plugin_path: str, metadata: Dict) -> Optional[str]:
        """
        Ensures that the dependencies specified in metadata are installed.
        Returns the path to the 'libs' directory containing the dependencies, or None if no dependencies
        are specified or installation fails.
        """
        dependencies = metadata.get("python_dependencies", [])
        if not dependencies:
            return None

        libs_dir = os.path.join(plugin_path, "libs")

        # Check if we need to install anything
        if not self._are_dependencies_installed(libs_dir, dependencies):
            self.logger.info(f"Installing dependencies for plugin at {plugin_path}...")
            if self._install_dependencies(libs_dir, dependencies):
                self.logger.info(f"Dependencies installed successfully in {libs_dir}")
            else:
                self.logger.error(f"Failed to install dependencies for plugin at {plugin_path}")
                return None

        return libs_dir

    def _are_dependencies_installed(self, libs_dir: str, dependencies: List[str]) -> bool:
        """
        Checks if the dependencies are already installed in the target directory.
        This is a basic check; for production, we might need a more robust verification
        (e.g., checking dist-info folders).
        """
        if not os.path.exists(libs_dir):
            return False

        # Simple heuristic: if the directory is empty, dependencies are missing.
        # A more complex check would involve parsing installed packages.
        return len(os.listdir(libs_dir)) > 0

    def _install_dependencies(self, target_dir: str, dependencies: List[str]) -> bool:
        """
        Installs the given list of dependencies into the target directory using pip.
        """
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        # Construct the pip command
        # We use the current python executable to run pip
        cmd = [
                  sys.executable, "-m", "pip", "install",
                  "--target", target_dir,
                  "--upgrade"  # Ensure we get the latest compatible versions
              ] + dependencies

        try:
            # Run pip installation
            result = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.logger.debug(f"Pip output: {result.stdout}")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Pip installation failed: {e.stderr}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during dependency installation: {e}")
            return False
