"""Alle Quelldateien laden (fehlende; mit --neu alle) und Prüfsummen kontrollieren: siehe `quellen.download`.

python -m rsg2030.quellen [--neu]   (gleich: python -m rsg2030 download)
"""

from __future__ import annotations

import sys

from rsg2030.quellen.download import main

if __name__ == "__main__":
    sys.exit(main())
