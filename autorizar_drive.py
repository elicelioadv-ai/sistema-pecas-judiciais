"""
autorizar_drive.py - Autoriza o acesso ao Google Drive (uma vez so).

Isso gera o "refresh token": a credencial que o sistema usa para enviar os
arquivos de trabalho ao seu Google Drive (que depois sincroniza pro seu PC).

Como usar:
  1. Baixe o arquivo JSON do cliente OAuth (client_secret....json) no Google Cloud.
  2. Rode (no Prompt/terminal):  python autorizar_drive.py
     (ou passe o caminho: python autorizar_drive.py "C:\\Users\\...\\client_secret.json")
  3. O navegador abrira; faca login com elicelio.adv@gmail.com e clique em Permitir.
  4. No final, sera criado o arquivo "token_drive.json" com os 3 valores.

IMPORTANTE (token que nao expira toda semana):
  No Google Cloud, em "OAuth consent screen", depois de testar, clique em
  "PUBLISH APP" para deixar o app em PRODUCAO. Enquanto estiver em "Testing",
  o Google invalida o refresh token a cada 7 dias.

  O escopo usado abaixo (drive.file) e NAO-sensivel: o app so enxerga os
  arquivos que ele mesmo cria. Nao precisa de verificacao e nao mostra tela
  de "app nao verificado".
"""
import json
import os
import sys
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

SCOPE = "https://www.googleapis.com/auth/drive.file"
PORTA = 8765
REDIRECT = f"http://localhost:{PORTA}/"

_caixa = {}


def achar_cliente():
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        return sys.argv[1]
    pasta = os.path.dirname(os.path.abspath(__file__))
    candidatos = [os.path.join(pasta, "client_secret.json")]
    for area in ("Desktop", "Downloads"):
        base = os.path.join(os.path.expanduser("~"), area)
        if os.path.isdir(base):
            achados = [os.path.join(base, n) for n in os.listdir(base)
                       if n.lower().startswith("client_secret") and n.lower().endswith(".json")]
            achados.sort(key=os.path.getmtime, reverse=True)
            candidatos.extend(achados)
    for c in candidatos:
        if os.path.isfile(c):
            return c
    return None


def carregar(cliente_path):
    with open(cliente_path, encoding="utf-8") as f:
        dados = json.load(f)
    info = dados.get("installed") or dados.get("web") or dados
    return info["client_id"], info["client_secret"]


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if "code" in params:
            _caixa["code"] = params["code"][0]
            msg = "Autorizacao concluida! Pode fechar esta aba e voltar ao sistema."
        else:
            msg = "Nao recebi o codigo. Tente novamente executando o programa de novo."
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(f"<html><body><h2>{msg}</h2></body></html>".encode("utf-8"))

    def log_message(self, *args):
        pass


def main():
    cliente_path = achar_cliente()
    if not cliente_path:
        print("Nao encontrei o arquivo JSON do cliente OAuth (client_secret....json).")
        print('Coloque-o na Area de Trabalho ou em Downloads, ou passe o caminho: python autorizar_drive.py "C:\\...\\client_secret.json"')
        return 1

    client_id, client_secret = carregar(cliente_path)
    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    print("Abrindo o navegador para autorizar... Se nao abrir, cole este link:")
    print(url)
    webbrowser.open(url)

    servidor = HTTPServer(("localhost", PORTA), Handler)
    servidor.handle_request()

    code = _caixa.get("code")
    if not code:
        print("Nao recebi o codigo de autorizacao.")
        return 1

    corpo = urllib.parse.urlencode({
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT,
        "grant_type": "authorization_code",
    }).encode("utf-8")
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=corpo)
    with urllib.request.urlopen(req, timeout=60) as resp:
        token = json.loads(resp.read().decode("utf-8"))

    refresh = token.get("refresh_token")
    if not refresh:
        print("Nao veio refresh_token. Detalhes:", token)
        return 1

    saida = {
        "GOOGLE_CLIENT_ID": client_id,
        "GOOGLE_CLIENT_SECRET": client_secret,
        "GOOGLE_REFRESH_TOKEN": refresh,
    }
    caminho_saida = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token_drive.json")
    with open(caminho_saida, "w", encoding="utf-8") as f:
        json.dump(saida, f, ensure_ascii=False, indent=2)
    print("TUDO CERTO! Dados salvos em:", caminho_saida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
