{
  description = "QuickFile dev environment (PyQt6 + Qt6 + NVIDIA + tests)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };

        python = pkgs.python312;

        pythonEnv = python.withPackages (ps: [
          # z requirements.txt (bez PyQt6 / PyQt6-Qt6 / PyQt6_sip)
          ps.docopt
          ps.psutil
          ps.requests
          ps.urllib3
          ps.idna
          ps.charset-normalizer
          ps.certifi
          ps.packaging
          ps.pluggy
          ps.typing-extensions
          # ps.pipreqs # Package not existing in nixos-24.11.
          # rarfile, Send2Trash, yarg są w pip, nie w nixpkgs – zostawimy je dla pip w razie potrzeby
        ]);

      in {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            pythonEnv

            # PyQt6 z Nix (stabilne na NixOS)
            pkgs.python312Packages.pyqt6

            # Qt runtime
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
          ];

          # tu możesz dodać narzędzia dev: pytest, mypy, black, itp.
          shellHook = ''
            echo "QuickFile devShell activated"
            echo "Python: $(which python)"
            echo "PyQt6 from Nix, Qt6 runtime, GL, X11 – ready."

            # upewniamy się, że lokalny katalog jest na PYTHONPATH (importy typu `from app...`)
            export PYTHONPATH=$PWD:$PYTHONPATH
          '';
        };
      });
}

