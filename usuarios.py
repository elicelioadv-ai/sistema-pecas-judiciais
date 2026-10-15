"""
usuarios.py - contas de acesso (multi-usuário) com cadastro pelo próprio app.

As contas ficam num arquivo JSON guardado no repositório PRIVADO de backup
(contas/usuarios.json), por meio da camada "nuvem". Assim sobrevivem aos
reinícios do app na nuvem (o servidor "esquece" arquivos locais).

Sem nuvem configurada (uso local/desenvolvimento), usa um arquivo local em
"contas/usuarios.json" dentro da pasta do sistema.

Segurança: as senhas NUNCA são guardadas em texto puro - usamos "hash" PBKDF2
(HMAC-SHA256, 200.000 iterações) com um "salt" aleatório por conta.

Só usa a biblioteca padrão do Python.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime
from pathlib import Path

PASTA = Path(__file__).parent
_SUBPASTA = "contas"
_ARQUIVO = "usuarios.json"
_CAMINHO_REPO = f"{_SUBPASTA}/{_ARQUIVO}"

_ITERACOES = 200_000

OK = "ok"
PENDENTE = "pendente"
INVALIDO = "invalido"


def _caminho_local() -> Path:
    pasta = PASTA / _SUBPASTA
    pasta.mkdir(exist_ok=True)
    return pasta / _ARQUIVO


def _usar_nuvem() -> bool:
    try:
        import nuvem

        return nuvem.disponivel()
    except Exception:
        return False


def _carregar() -> dict:
    bruto = None
    if _usar_nuvem():
        try:
            import nuvem

            bruto = nuvem.ler_texto(_CAMINHO_REPO)
        except Exception:
            bruto = None
    if bruto is None:
        local = _caminho_local()
        if local.exists():
            bruto = local.read_text(encoding="utf-8")
    if not bruto:
        return {"usuarios": []}
    try:
        dados = json.loads(bruto)
    except Exception:
        return {"usuarios": []}
    if not isinstance(dados, dict) or not isinstance(dados.get("usuarios"), list):
        return {"usuarios": []}
    return dados


def _salvar(dados: dict) -> None:
    texto = json.dumps(dados, ensure_ascii=False, indent=2)
    _caminho_local().write_text(texto, encoding="utf-8")
    if _usar_nuvem():
        try:
            import nuvem

            nuvem.enviar_texto(_ARQUIVO, texto, _SUBPASTA)
        except Exception:
            # guarda local mesmo se a nuvem falhar
            pass


def _hash_senha(senha: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", (senha or "").encode("utf-8"), bytes.fromhex(salt), _ITERACOES
    ).hex()


def _achar(dados: dict, usuario: str):
    alvo = (usuario or "").strip().casefold()
    for u in dados.get("usuarios", []):
        if str(u.get("usuario", "")).strip().casefold() == alvo:
            return u
    return None


def listar() -> list:
    """Todas as contas (sem os hashes, por segurança)."""
    return [
        {k: v for k, v in u.items() if k not in ("hash", "salt")}
        for u in _carregar().get("usuarios", [])
    ]


def listar_status(status: str):
    return [u for u in listar() if u.get("status") == status]


def listar_pendentes():
    return listar_status(PENDENTE)


def listar_ativos():
    return listar_status("ativo")


def obter(usuario: str):
    return _achar(_carregar(), usuario)


def existe(usuario: str) -> bool:
    return obter(usuario) is not None


def criar(nome: str, usuario: str, senha: str) -> bool:
    usuario = (usuario or "").strip()
    nome = (nome or "").strip()
    senha = senha or ""
    if len(usuario) < 3:
        raise ValueError("Informe um usuário ou e-mail (mínimo 3 caracteres).")
    if len(senha) < 6:
        raise ValueError("A senha precisa ter ao menos 6 caracteres.")
    dados = _carregar()
    if _achar(dados, usuario):
        raise ValueError("Já existe uma conta com esse usuário/e-mail.")
    salt = secrets.token_hex(16)
    dados["usuarios"].append(
        {
            "usuario": usuario,
            "nome": nome,
            "salt": salt,
            "hash": _hash_senha(senha, salt),
            "status": PENDENTE,
            "criado": datetime.now().isoformat(timespec="seconds"),
        }
    )
    _salvar(dados)
    return True


def autenticar(usuario: str, senha: str) -> str:
    """Devolve OK, PENDENTE ou INVALIDO."""
    u = _achar(_carregar(), usuario)
    if not u or not u.get("salt") or not u.get("hash"):
        return INVALIDO
    calc = _hash_senha(senha or "", u["salt"])
    if not hmac.compare_digest(calc, u["hash"]):
        return INVALIDO
    return OK if u.get("status") == "ativo" else PENDENTE


def definir_status(usuario: str, status: str) -> bool:
    dados = _carregar()
    u = _achar(dados, usuario)
    if not u:
        return False
    u["status"] = status
    _salvar(dados)
    return True


def aprovar(usuario: str) -> bool:
    return definir_status(usuario, "ativo")


def redefinir_senha(usuario: str, nova_senha: str) -> bool:
    """Troca a senha de uma conta (usado pelo administrador)."""
    nova_senha = nova_senha or ""
    if len(nova_senha) < 6:
        raise ValueError("A senha precisa ter ao menos 6 caracteres.")
    dados = _carregar()
    u = _achar(dados, usuario)
    if not u:
        raise ValueError("Conta não encontrada.")
    salt = secrets.token_hex(16)
    u["salt"] = salt
    u["hash"] = _hash_senha(nova_senha, salt)
    u["alterado"] = datetime.now().isoformat(timespec="seconds")
    _salvar(dados)
    return True


def remover(usuario: str) -> bool:
    dados = _carregar()
    alvo = (usuario or "").strip().casefold()
    antes = len(dados.get("usuarios", []))
    dados["usuarios"] = [
        u for u in dados.get("usuarios", [])
        if str(u.get("usuario", "")).strip().casefold() != alvo
    ]
    if len(dados["usuarios"]) == antes:
        return False
    _salvar(dados)
    return True
