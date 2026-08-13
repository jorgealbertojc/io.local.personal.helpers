#!/usr/bin/env python3

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apt import run_apt_update
from help import show_help


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] in {"help", "--help", "-h"}:
        show_help()
        return

    if len(sys.argv) > 1 and sys.argv[1] in {"update", "apt-update"}:
        verbose = any(a in sys.argv for a in ("-v", "--verbose"))
        sys.exit(run_apt_update(verbose=verbose))


if __name__ == "__main__":
    main()
