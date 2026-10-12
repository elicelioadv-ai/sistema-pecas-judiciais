"""Liga o Sistema de Peças Judiciais SEM janela preta e abre a página no navegador."""
import os
import socket
import subprocess
import sys
import time
import webbrowser

PASTA = os.path.dirname(os.path.abspath(__file__))
PORTA = 8501


def porta_aberta():
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", PORTA)) == 0


if not porta_aberta():
    py = sys.executable
    if py.lower().endswith("pythonw.exe"):
        py = py[:-len("pythonw.exe")] + "python.exe"
    log = open(os.path.join(PASTA, "gerador.log"), "w", encoding="utf-8")
    subprocess.Popen(
        [py, "-m", "streamlit", "run", "app.py",
         "--server.headless", "true", "--server.port", str(PORTA)],
        cwd=PASTA, stdout=log, stderr=log, stdin=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    for _ in range(60):          # espera até 60 segundos o programa ligar
        if porta_aberta():
            break
        time.sleep(1)

webbrowser.open(f"http://localhost:{PORTA}")