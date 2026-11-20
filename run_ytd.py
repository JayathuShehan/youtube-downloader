"""PyInstaller entry script (keeps the ytd package imports absolute)."""

import sys

from ytd.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
