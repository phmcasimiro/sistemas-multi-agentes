"""provedor.py — wrapper para o provedor compartilhado da raiz do projeto."""
import os
import sys

_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _raiz not in sys.path:
    sys.path.insert(0, _raiz)

from provedor import *  # noqa: F401, F403
