#!/usr/bin/env python3
"""
WeebCentral Downloader - Modern PyQt6 GUI
Run this script to launch the application.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui import run_gui

if __name__ == "__main__":
    run_gui()
