"""Drewgent sitecustomize — auto-load customize layer at Python startup.

Insert ~/.drewgent/customize/ at sys.path[0] so 'from hermes_cli.gateway'
loads OUR gateway.py first (before hermes's own).
"""
import os
import sys
from pathlib import Path

CUSTOMIZE = Path.home() / ".drewgent" / "customize"
if CUSTOMIZE.exists() and str(CUSTOMIZE) not in sys.path:
    sys.path.insert(0, str(CUSTOMIZE))
