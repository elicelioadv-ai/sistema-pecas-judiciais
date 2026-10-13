"""
drive.py - envia os arquivos de trabalho (casos, peças e bases) para o Google Drive
do próprio usuário, servindo de backup que o "Google Drive para Desktop" sincroniza
automaticamente para a pasta do PC.

Como funciona:
  - O app roda no servidor (nuvem), mas envia os arquivos para a sua conta do Google
    (via OAuth). O Google Drive para Desktop, instalado no seu PC, baixa tudo sozinho.
  - Se o PC estiver desligado/offline, a sincronização acontece quando ele reconectar.
  - Usa apenas a biblioteca padrão do Python (sem dependências novas).

Configuração (nos "Secrets" do Streamlit):
  GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN

Opcional:
  DRIVE_FOLDER_ID  (se vazio, usa/cria a pasta "Sistema de Peças Judiciais" na raiz)

Se as variáveis não estiverem definidas, tudo fica desativado (no-op).

Escopo: usa "drive.file" (NÃO-sensível). O app só vê/cria os arquivos dele
mesmo, então não pede verificação e o token não expira a cada 7 dias quando o
app está publicado em produção no Google Cloud.
"""
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

TOKEN_URL = "https://oauth2.googleapis.com/token"
API = "https://www.googleapis.com/drive/v3"
UPLOAD = "https://www.googleapis.com/upload/drive/v3"

_token = {"valor": None, "expira": 0.0}
_cache_pastas: dict[tuple[str, str], str] = {}


def _cfg():
    return {
        "client_id": os.getenv("GOOGLE_CLIENT_ID", "").strip(),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", "").strip(),
        "refresh_token": os.getenv("GOOGLE_REFRESH_TOKEN", "").strip(),
        "folder_id": os.getenv("DRIVE_FOLDER_ID", "").strip(),
    }


def disponivel() -> bool:
    c = _cfg()
    return bool(c["client_id"] and c["client_secret"] and c["refresh_token"])


def _access_token() -> str:
    if _token["valor"] and time.time() < _token["expira"] - 60:
        return _token["valor"]
    c = _cfg()
    corpo = urllib.parse.urlencode({
        "client_id": c["client_id"],
        "client_secret": c["client_secret"],
        "refresh_token": c["refresh_token"],
        "grant_type": "refresh_token",
    }).encode("utf-8")
    req = urllib.request.Request(TOKEN_URL, data=corpo)
    with urllib.request.urlopen(req, timeout=60) as resp:
        tok = json.loads(resp.read().decode("utf-8"))
    _token["valor"] = tok["access_token"]
    _token["expira"] = time.time() + int(tok.get("expires_in", 3600))
    return _token["valor"]


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {_access_token()}"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _post_json(url: str, corpo: dict) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(corpo).encode("utf-8"), method="POST",
        headers={"Authorization": f"Bearer {_access_token()}",
                 "Content-Type": "application/json; charset=UTF-8"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _id_pasta(nome: str, pai_id: str) -> str:
    chave = (pai_id, nome)
    if chave in _cache_pastas:
        return _cache_pastas[chave]
    q = (f"name = '{nome}' and '{pai_id}' in parents and "
         "mimeType = 'application/vnd.google-apps.folder' and trashed = false")
    url = f"{API}/files?" + urllib.parse.urlencode(
        {"q": q, "fields": "files(id)", "spaces": "drive"})
    itens = _get_json(url).get("files", [])
    if itens:
        fid = itens[0]["id"]
    else:
        fid = _post_json(f"{API}/files?fields=id", {
            "name": nome,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [pai_id],
        })["id"]
    _cache_pastas[chave] = fid
    return fid


def _pasta_raiz() -> str:
    c = _cfg()
    if c["folder_id"]:
        return c["folder_id"]
    return _id_pasta("Sistema de Peças Judiciais", "root")


def _id_arquivo(nome: str, pai_id: str):
    q = f"name = '{nome}' and '{pai_id}' in parents and trashed = false"
    url = f"{API}/files?" + urllib.parse.urlencode({"q": q, "fields": "files(id)", "spaces": "drive"})
    itens = _get_json(url).get("files", [])
    return itens[0]["id"] if itens else None


def _upload(metadados: dict, conteudo: bytes, mimetype: str, file_id=None) -> dict:
    boundary = "======socketado" + uuid.uuid4().hex
    pedacos = [
        f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n".encode("utf-8"),
        json.dumps(metadados).encode("utf-8"),
        b"\r\n",
        f"--{boundary}\r\nContent-Type: {mimetype}\r\n\r\n".encode("utf-8"),
        conteudo,
        f"\r\n--{boundary}--\r\n".encode("utf-8"),
    ]
    corpo = b"".join(pedacos)
    if file_id:
        url = f"{UPLOAD}/files/{file_id}?uploadType=multipart&fields=id,webViewLink"
        metodo = "PATCH"
    else:
        url = f"{UPLOAD}/files?uploadType=multipart&fields=id,webViewLink"
        metodo = "POST"
    req = urllib.request.Request(url, data=corpo, method=metodo, headers={
        "Authorization": f"Bearer {_access_token()}",
        "Content-Type": f"multipart/related; boundary={boundary}",
    })
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode("utf-8"))


def enviar(caminho_local, subpasta: str = "pecas", substituir: bool = True):
    """Envia (ou atualiza) um arquivo para o Drive. Devolve o link ou None."""
    if not disponivel():
        return None
    caminho_local = Path(caminho_local)
    if not caminho_local.exists():
        return None
    raiz = _pasta_raiz()
    destino = _id_pasta(subpasta, raiz) if subpasta else raiz
    nome = caminho_local.name
    file_id = _id_arquivo(nome, destino) if substituir else None
    if file_id:
        info = _upload({}, caminho_local.read_bytes(), "application/octet-stream", file_id=file_id)
    else:
        info = _upload({"name": nome, "parents": [destino]},
                       caminho_local.read_bytes(), "application/octet-stream")
    return info.get("webViewLink")


def enviar_texto(nome: str, texto: str, subpasta: str = "outros"):
    """Envia um conteúdo de texto simples para o Drive (ex.: backups de JSON)."""
    if not disponivel():
        return None
    raiz = _pasta_raiz()
    destino = _id_pasta(subpasta, raiz) if subpasta else raiz
    conteudo = (texto or "").encode("utf-8")
    file_id = _id_arquivo(nome, destino)
    if file_id:
        info = _upload({}, conteudo, "text/plain", file_id=file_id)
    else:
        info = _upload({"name": nome, "parents": [destino]}, conteudo, "text/plain")
    return info.get("webViewLink")


def _delete(url: str):
    req = urllib.request.Request(url, method="DELETE",
                                 headers={"Authorization": f"Bearer {_access_token()}"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.status


def remover(nome: str, subpasta: str = "casos") -> bool:
    """Manda para a lixeira do Drive o arquivo com esse nome (se existir)."""
    if not disponivel():
        return False
    try:
        raiz = _pasta_raiz()
        destino = _id_pasta(subpasta, raiz) if subpasta else raiz
        file_id = _id_arquivo(nome, destino)
        if not file_id:
            return False
        _delete(f"{API}/files/{file_id}")
        return True
    except Exception:
        return False


def status() -> dict:
    """Situação do backup, para mostrar na tela. Nunca levanta exceção."""
    c = _cfg()
    return {
        "ativo": disponivel(),
        "tem_client": bool(c["client_id"] and c["client_secret"]),
        "tem_token": bool(c["refresh_token"]),
        "pasta_id": c["folder_id"],
    }


def testar():
    """Envia um arquivo pequeno de teste. Devolve (ok, mensagem)."""
    if not disponivel():
        return False, "Backup não configurado (faltam GOOGLE_CLIENT_ID / _SECRET / _REFRESH_TOKEN)."
    try:
        marca = datetime.now().strftime("%Y%m%d_%H%M%S")
        link = enviar_texto(f"teste_backup_{marca}.txt",
                            f"Backup funcionando. Teste em {datetime.now():%d/%m/%Y %H:%M:%S}.", "testes")
        if link:
            return True, f"Backup OK! Arquivo de teste enviado ao Drive: {link}"
        return False, "O envio não retornou link. Verifique as credenciais."
    except Exception as e:
        return False, f"Falhou ao enviar: {e}"
