import os
import sys
import subprocess
import platform

def build():
    # Determine paths
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    main_script = os.path.join(project_root, "main.py")
    dist_dir = os.path.join(project_root, "dist")
    build_dir = os.path.join(project_root, "build")
    
    # PyInstaller arguments
    args = [
        "pyinstaller",
        "--noconfirm",
        "--clean",
        "--name=QuickFile",
        "--onedir",  # Use onedir initially for easier debugging
        "--windowed", # Hide console for GUI app
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        
        # Add data (resources)
        # Format: src:dest (separator depends on OS)
        f"--add-data={os.path.join(project_root, 'ui')}{os.pathsep}ui",
        f"--add-data={os.path.join(project_root, 'resources')}{os.pathsep}resources",
        f"--add-data={os.path.join(project_root, 'themes')}{os.pathsep}themes",
        f"--add-data={os.path.join(project_root, 'translations')}{os.pathsep}translations",
        f"--add-data={os.path.join(project_root, 'config')}{os.pathsep}config",
        f"--add-data={os.path.join(project_root, 'plugins')}{os.pathsep}plugins",
        
        # Hidden imports (crucial for dynamic plugin loading)
        "--hidden-import=PyQt6.QtCore",
        "--hidden-import=PyQt6.QtGui",
        "--hidden-import=PyQt6.QtWidgets",
        "--hidden-import=shutil",
        "--hidden-import=psutil",
        "--hidden-import=send2trash",
        "--hidden-import=webbrowser", # Used by feedback plugin
        "--hidden-import=browser",
        
        # Main script
        main_script
    ]

    print("Starting build process...")
    print(f"Command: {' '.join(args)}")
    
    try:
        subprocess.check_call(args)
        print("Build completed successfully!")
        print(f"Executable can be found in: {os.path.join(dist_dir, 'QuickFile')}")
    except subprocess.CalledProcessError as e:
        print(f"Build failed with error code {e.returncode}")
        sys.exit(1)

if __name__ == "__main__":
    build()
