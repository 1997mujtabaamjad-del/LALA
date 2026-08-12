"""Entry point for python -m bishu execution with automatic src path resolution."""

import os
import sys

# Auto-insert 'src' directory into sys.path
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from bishu.app import main

if __name__ == "__main__":
    raise SystemExit(main())
