"""
nuvem.py - camada de backup na nuvem com provedores plugáveis.

Provedores disponíveis:
  - GitHub  (github_backup.py): token que NÃO expira -> opção principal.
  - Google Drive (drive.py): OAuth -> reserva (pode expirar em 7 dias enquanto o
    app do Google estiver em fase de "teste").

Regra: se o GitHub estiver configurado, ele tem prioridade; senão, usa o Drive.

Todos os módulos (motor.py, app.py) falam só com esta camada, então trocar de
provedor é só mudar os "Secrets"/.env - sem mexer no resto do sistema.
"""
from __future__ import annotations


def _github():
    try:
        import github_backup

        return github_backup if github_backup.disponivel() else None
    except Exception:
        return None


def _drive():
    try:
        import drive

        return drive if drive.disponivel() else None
    except Exception:
        return None


def ativo():
    """Devolve o módulo do provedor ativo (GitHub tem prioridade) ou None."""
    return _github() or _drive()


def disponivel() -> bool:
    return ativo() is not None


def provedor_nome() -> str:
    p = ativo()
    if p is None:
        return ""
    return "GitHub" if getattr(p, "__name__", "") == "github_backup" else "Google Drive"


def enviar(caminho, subpasta: str = "pecas"):
    p = ativo()
    return p.enviar(caminho, subpasta) if p else None


def enviar_texto(nome: str, texto: str, subpasta: str = "outros"):
    p = ativo()
    return p.enviar_texto(nome, texto, subpasta) if p else None


def ler_texto(caminho: str):
    """Lê um arquivo de texto do provedor ativo (por caminho completo). None se não houver."""
    p = ativo()
    if p and hasattr(p, "ler_texto"):
        return p.ler_texto(caminho)
    return None


def listar(caminho_dir: str):
    """Lista (nome, tipo) de uma pasta do provedor ativo. [] se não houver."""
    p = ativo()
    if p and hasattr(p, "listar"):
        return p.listar(caminho_dir)
    return []



def remover(nome: str, subpasta: str = "casos") -> bool:
    p = ativo()
    return bool(p.remover(nome, subpasta)) if p else False


def status() -> dict:
    """Situação do backup para a tela. Nunca levanta exceção."""
    try:
        p = ativo()
    except Exception:
        p = None
    if p is None:
        return {"ativo": False, "provedor": ""}
    try:
        d = dict(p.status())
    except Exception:
        d = {"ativo": False}
    d["provedor"] = provedor_nome()
    return d


def testar():
    """Envia um arquivo de teste pelo provedor ativo. Devolve (ok, mensagem)."""
    p = ativo()
    if p is None:
        return False, ("Backup não configurado. Defina GITHUB_BACKUP_TOKEN + "
                       "GITHUB_BACKUP_REPO (recomendado) ou as chaves do Google.")
    return p.testar()
