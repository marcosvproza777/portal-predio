"""Grava static/version.txt uma vez na inicialização do servidor.

Render reinicia o processo a cada deploy → novo timestamp → JS detecta
a mudança e exibe o banner de atualização para usuários com o app aberto.
"""
import os
import time

_VERSION_FILE = os.path.join(os.path.dirname(__file__), "static", "version.txt")

try:
    os.makedirs(os.path.dirname(_VERSION_FILE), exist_ok=True)
    with open(_VERSION_FILE, "w") as _f:
        _f.write(str(int(time.time())))
except Exception:
    pass
