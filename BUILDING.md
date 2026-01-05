# Building QuickFile from Source

This document provides instructions on how to build a standalone executable version of QuickFile from the source code using `PyInstaller`.

## Prerequisites

1.  **Python**: A compatible version of Python (e.g., 3.11+) must be installed.
2.  **Virtual Environment**: It is highly recommended to use a virtual environment to manage dependencies.
3.  **Dependencies**: All required development dependencies must be installed.

## Setup

1.  **Clone the repository**:
    ```sh
    git clone https://github.com/dawciobiel/QuickFile.git
    cd QuickFile
    ```

2.  **Create and activate a virtual environment**:
    *   On Linux/macOS:
        ```sh
        python3 -m venv .venv
        source .venv/bin/activate
        ```
    *   On Windows:
        ```sh
        python -m venv .venv
        .venv\Scripts\activate
        ```

3.  **Install dependencies**:
    Install all necessary packages, including `PyInstaller`, using the development requirements file.
    ```sh
    pip install -r requirements-dev.txt
    ```

## Building the Application

The project includes a dedicated build script that handles the `PyInstaller` configuration.

1.  **Run the build script**:
    From the root of the project directory, execute the following command:
    ```sh
    python scripts/packaging/build_app.py
    ```

2.  **Locate the output**:
    The script will create two directories:
    *   `build/`: Contains temporary files used by `PyInstaller`. This can be safely deleted after the build.
    *   `dist/`: Contains the final application bundle.

3.  **Run the application**:
    Navigate to the distribution directory. The executable application will be inside a folder named `QuickFile`.
    *   On Linux/macOS:
        ```sh
        cd dist/QuickFile
        ./QuickFile
        ```
    *   On Windows:
        ```sh
        cd dist\QuickFile
        QuickFile.exe
        ```

## Build Script Details

The `scripts/packaging/build_app.py` script automates the process by passing the correct arguments to `PyInstaller`. This includes:
*   Specifying the main entry point (`main.py`).
*   Bundling all necessary data files (UI files, icons, themes, translations, configs, and bundled plugins) using the `--add-data` flag.
*   Including hidden imports that `PyInstaller` might miss due to dynamic loading (e.g., in `PluginManager`).
*   Setting the application name and output directories.

If the build process fails, check the output for any `ModuleNotFoundError` or `FileNotFoundError` messages, as they may indicate that a new dependency or data file needs to be added to the build script.
