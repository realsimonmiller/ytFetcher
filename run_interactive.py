#!/usr/bin/env python3
"""
Interactive launcher for YouTube Channel Video Fetcher
This script runs the program in interactive mode by default.
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.main import main

if __name__ == "__main__":
    # Set up sys.argv to run in interactive mode
    sys.argv = [sys.argv[0], "--interactive"]
    main() 