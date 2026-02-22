{
  description = "QuickFile development environment (Python + Qt6 + tools)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
      in {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            # Python (bez pipowych zależności!)
            pkgs.python312
            # Wersja 3.12 jest stabilina na wszystkich systemach [ Windows, linux, MacOS ]
            # Nie ma problemów z zależnościami:
            # PyQt6
            # pluggy
            # pluggy
            # psutil
            # requests
            # rarfile
            # Send2Trash
            # PyInstaller
            # pytest
            # ruff

            # PyQt6 + Qt6 runtime
            pkgs.python312Packages.pyqt6
            pkgs.qt6.qtbase
            pkgs.qt6.qtsvg
            pkgs.qt6.qtwayland
            pkgs.qt6.qtdeclarative

            # OpenGL + X11 + fonty + glib
            pkgs.libglvnd
            pkgs.xorg.libX11
            pkgs.xorg.libXext
            pkgs.xorg.libXrender
            pkgs.xorg.libxcb
            pkgs.libxkbcommon
            pkgs.freetype
            pkgs.fontconfig
            pkgs.glib
            pkgs.zlib
            pkgs.zstd
            pkgs.dbus
            pkgs.stdenv.cc.cc.lib
            pkgs.mesa   # <- biblioteki OpenGL, libGL.so.1

            # Narzędzia developerskie
            pkgs.ruff
            pkgs.pyright
            pkgs.git
            pkgs.which
          ];

          shellHook = ''
            echo "QuickFile devShell activated"
            echo "Python: $(which python)"
            echo "Qt6 + PyQt6 ready"

            # NIE ustawiamy PYTHONPATH
            # pip + .venv zrobią to poprawnie
          '';
        };
      });
}
