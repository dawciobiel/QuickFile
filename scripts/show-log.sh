#!/bin/bash
# ==============================================================================
# Project: QuickFile
# Script: show-log.sh
# Description: Opens the main application log file using a log viewer.
#
# Author: Dawid Bielecki "dawciobiel"
# GitHub: https://github.com/dawciobiel/QuickFile
# License: GPL 3.0
# Date: 2025-12-25
# ==============================================================================

# Terminal GUI
# lnav ../logs/main.log

# Desktop GUI
ksystemlog ../logs/main.log &
