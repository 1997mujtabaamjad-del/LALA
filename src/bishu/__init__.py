"""Bishu application package with automatic path resolution."""

import os
import sys

# Auto-insert 'src' package directory into sys.path
pkg_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if pkg_dir not in sys.path:
    sys.path.insert(0, pkg_dir)

__version__ = "1.0.0"
