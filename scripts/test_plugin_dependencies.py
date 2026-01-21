import logging
import os
import shutil
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.plugin_manager import PluginManager

# Configure logging
logging.basicConfig(level=logging.DEBUG)


def test_dependencies():
    print("🚀 Starting dependency test...")

    # Define plugin path
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    plugin_path = os.path.join(base_dir, "plugins", "org.quickfile", "standard_editor", "1.1.0")
    libs_dir = os.path.join(plugin_path, "libs")

    # Clean up previous test run
    if os.path.exists(libs_dir):
        print(f"🧹 Cleaning up existing libs directory: {libs_dir}")
        shutil.rmtree(libs_dir)

    # Initialize PluginManager (this should trigger dependency installation)
    print("🔌 Initializing PluginManager...")
    # We point it to the bundled plugins directory for this test
    plugin_dirs = [os.path.join(base_dir, "plugins")]
    manager = PluginManager(plugin_dirs=plugin_dirs)

    # Verify results
    print(f"🔍 Verifying installation in: {libs_dir}")

    if not os.path.exists(libs_dir):
        print("❌ FAILED: 'libs' directory was not created.")
        return

    installed_files = os.listdir(libs_dir)
    print(f"📂 Files in libs: {installed_files}")

    if "requests" in installed_files:
        print("✅ SUCCESS: 'requests' package found in libs directory.")
    else:
        print("❌ FAILED: 'requests' package NOT found in libs directory.")


if __name__ == "__main__":
    test_dependencies()
