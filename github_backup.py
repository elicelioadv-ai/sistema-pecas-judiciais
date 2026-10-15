"""
github_backup.py - envia os arquivos de trabalho (casos, peças e bases) para um
repositório PRIVADO no GitHub do próprio usuário. O "GitHub Desktop" (ou um
"git pull") traz tudo para a pasta do PC.

Por que GitHub (e não o Google Drive)?  O token do GitHub pode ser criado SEM
validade ("No expiration"), então o backup nunca para por expiração de
credencial. (No Google Drive, enquanto o app estiver em fase de "teste" e não
puder ser publicado, o token expira a cada 7 dias.)

Como funciona:
  - O app roda no servidor (nuvem) e grava os arquivos no repositório privado
    via API do GitHub. O GitHub Desktop, instalado no seu PC, baixa tudo.
  - Se o PC estiver desligado/offline, a sincronização acontece quando ele
    reconectar.

Configuração (nos "Secrets" do Streamlit ou no .env):
  GITHUB_BACKUP_TOKEN   - token "fine-grained" com permissão de ESCRITA em
                          "Contents" apenas no repositório de backup.
  GITHUB_BACKUP_REPO    - "usuario/repositorio" (ex.: elicelio/backup-pecas).
  GITHUB_BACKUP_BRANCH  - opcional (se vazio, usa "main").

Se as variáveis não estiverem definidas, tudo fica desativado (no-op).

Usa apenas a biblioteca padrão do Python (sem dependências novas).
"""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

API = "https://api.github.com"


def _cfg() -> dict:
    return {
        "token": os.getenv("GITHUB_BACKUP_TOKEN", "").strip(),
        "repo": os.getenv("GITHUB_BACKUP_REPO", "").strip().strip("/"),
        "branch": os.getenv("GITHUB_BACKUP_BRANCH", "").strip() or "main",
    }


def disponivel() -> bool:
    c = _cfg()
    return bool(c["token"] and "/" in c["repo"])


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_cfg()['token']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "sistema-pecas-backup",
    }


def _url_conteudo(caminho: str) -> str:
    c = _cfg()
    seguro = urllib.parse.quote(caminho, safe="/")
    return f"{API}/repos/{c['repo']}/contents/{seguro}"


def _sha_arquivo(caminho: str):
    """Devolve o sha do arquivo (para atualizar) ou None se ainda não existir."""
    c = _cfg()
    url = _url_conteudo(caminho) + "?ref=" + urllib.parse.quote(c["branch"], safe="")
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8")).get("sha")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def _gravar(caminho: str, conteudo: bytes, mensagem: str) -> dict:
    c = _cfg()
    corpo = {
        "message": mensagem,
        "content": base64.b64encode(conteudo).decode("ascii"),
        "branch": c["branch"],
    }
    sha = _sha_arquivo(caminho)
    if sha:
        corpo["sha"] = sha
    req = urllib.request.Request(
        _url_conteudo(caminho),
        data=json.dumps(corpo).encode("utf-8"),
        method="PUT",
        headers={**_headers(), "Content-Type": "application/json; charset=UTF-8"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _destino(nome: str, subpasta: str) -> str:
    return f"{subpasta}/{nome}" if subpasta else nome


def enviar(caminho_local, subpasta: str = "pecas", substituir: bool = True):
    """Envia (ou atualiza) um arquivo para o repositório. Devolve o link ou None."""
    if not disponivel():
        return None
    caminho_local = Path(caminho_local)
    if not caminho_local.exists():
        return None
    destino = _destino(caminho_local.name, subpasta)
    info = _gravar(destino, caminho_local.read_bytes(), f"backup: {destino}")
    return (info.get("content") or {}).get("html_url")


def enviar_texto(nome: str, texto: str, subpasta: str = "outros"):
    """Envia um conteúdo de texto simples (ex.: backups de JSON)."""
    if not disponivel():
        return None
    destino = _destino(nome, subpasta)
    info = _gravar(destino, (texto or "").encode("utf-8"), f"backup: {destino}")
    return (info.get("content") or {}).get("html_url")


def ler_texto(caminho: str):
    """Lê o conteúdo (texto) de um arquivo do repositório. None se não existir."""
    if not disponivel():
        return None
    c = _cfg()
    url = _url_conteudo(caminho) + "?ref=" + urllib.parse.quote(c["branch"], safe="")
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            dados = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    if not isinstance(dados, dict):
        return None
    conteudo = dados.get("content")
    if not conteudo:
        return None
    return base64.b64decode(conteudo).decode("utf-8")


def listar(caminho_dir: str):
    """Lista (nome, tipo) dos itens numa pasta do repositório. [] se não existir."""
    if not disponivel():
        return []
    c = _cfg()
    caminho_dir = (caminho_dir or "").strip("/")
    url = _url_conteudo(caminho_dir) + "?ref=" + urllib.parse.quote(c["branch"], safe="")
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            dados = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return []
        raise
    if not isinstance(dados, list):
        return []
    return [(item.get("name"), item.get("type")) for item in dados]



def remover(nome: str, subpasta: str = "casos") -> bool:
    """Remove do repositório o arquivo com esse nome (se existir)."""
    if not disponivel():
        return False
    try:
        c = _cfg()
        destino = _destino(nome, subpasta)
        sha = _sha_arquivo(destino)
        if not sha:
            return False
        req = urllib.request.Request(
            _url_conteudo(destino),
            data=json.dumps({"message": f"remove backup: {destino}",
                             "sha": sha, "branch": c["branch"]}).encode("utf-8"),
            method="DELETE",
            headers={**_headers(), "Content-Type": "application/json; charset=UTF-8"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status in (200, 204)
    except Exception:
        return False


def status() -> dict:
    """Situação do backup, para mostrar na tela. Nunca levanta exceção."""
    c = _cfg()
    return {
        "ativo": disponivel(),
        "provedor": "GitHub",
        "repo": c["repo"],
        "branch": c["branch"],
        "tem_token": bool(c["token"]),
    }


def testar():
    """Envia um arquivo pequeno de teste. Devolve (ok, mensagem)."""
    if not disponivel():
        return False, ("Backup não configurado (faltam GITHUB_BACKUP_TOKEN e/ou "
                       "GITHUB_BACKUP_REPO).")
    try:
        marca = datetime.now().strftime("%Y%m%d_%H%M%S")
        link = enviar_texto(
            f"teste_backup_{marca}.txt",
            f"Backup funcionando. Teste em {datetime.now():%d/%m/%Y %H:%M:%S}.",
            "testes",
        )
        if link:
            return True, f"Backup OK! Arquivo de teste enviado ao GitHub: {link}"
        return False, "O envio não retornou link. Verifique o token e o repositório."
    except Exception as e:
        return False, f"Falhou ao enviar: {e}"
