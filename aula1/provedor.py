"""provedor.py — wrapper para o provedor compartilhado da raiz do projeto.

Garante suporte a Zen, Ollama e OpenAI com fallback automático tanto ao rodar
a partir da raiz (`python -m aula1.agente5`) quanto de dentro do diretório (`python agente5.py`).
"""
import os
import sys

_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _raiz not in sys.path:
    sys.path.insert(0, _raiz)

from provedor import *  # noqa: F401, F403