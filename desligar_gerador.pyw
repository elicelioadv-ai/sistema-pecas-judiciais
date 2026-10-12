"""Desliga o Sistema de Peças Judiciais que está rodando escondido."""
import ctypes
import subprocess

PORTA = "8501"
SEM_JANELA = subprocess.CREATE_NO_WINDOW

saida = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                       creationflags=SEM_JANELA).stdout
pids = set()
for linha in saida.splitlines():
    p = linha.split()
    # linha de porta "escutando": endereço remoto é 0.0.0.0:0 ou [::]:0
    if len(p) >= 5 and p[0] == "TCP" and p[1].endswith(":" + PORTA) and p[2] in ("0.0.0.0:0", "[::]:0"):
        pids.add(p[-1])

for pid in pids:
    subprocess.run(["taskkill", "/F", "/T", "/PID", pid], creationflags=SEM_JANELA,
                   capture_output=True)

msg = "Sistema desligado." if pids else "O Sistema já estava desligado."
ctypes.windll.user32.MessageBoxW(0, msg, "Sistema de Peças Judiciais", 0x40)