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

        # Single source of truth for Python dependencies.
        # No pip, no virtualenv: this interpreter already has everything.
        python = pkgs.python312.withPackages (ps: with ps; [
          # Runtime
          pyqt6
          pygments
          psutil
          rarfile
          send2trash
          packaging
          pillow # used by scripts/slice_spritesheet.py

          # Tests
          pytest
          pytest-mock
          pytest-order
          pytest-qt

          # Packaging
          build
          pyinstaller
        ]);
      in {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            python

            # Qt6 runtime libraries (PyQt6 from nixpkgs links against these)
            pkgs.qt6.qtbase
            pkgs.qt6.qtsvg
            pkgs.qt6.qtwayland
            pkgs.qt6.qtdeclarative

            # OpenGL + X11 + fonts + glib
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
            pkgs.mesa # libGL.so.1

            # Developer tools
            pkgs.ruff
            pkgs.pyright
            pkgs.git
            pkgs.which
          ];

          shellHook = ''
            echo "QuickFile devShell activated"
            echo "Python: $(which python) ($(python -V 2>&1))"
            echo "PyQt6 + Qt6 ready"
            echo "Tests:  python -m pytest tests/unit"
            # No PYTHONPATH and no pip: the interpreter above is complete.
          '';
        };
      });
}
