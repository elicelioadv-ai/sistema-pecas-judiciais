"""
app.py - a TELA do programa (Streamlit).

Fluxo: Caso -> Fatos -> Peça -> Conferência, além de histórico e editor da base legal.
Para abrir:  streamlit run app.py
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import html
import importlib
import json
import random
import re

import pandas as pd
import streamlit as st

# Ponte: na nuvem, copia os "Secrets" para variáveis de ambiente, para que
# motor.py e drive.py (backup no Google Drive) enxerguem as credenciais.
import os

try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, (str, int, float)):
            os.environ.setdefault(str(_k), str(_v))
except Exception:
    pass

import streamlit.components.v1 as components

import decisoes
import motor
import usuarios

# O Streamlit guarda os módulos importados em cache entre execuções. Recarregamos
# `decisoes` a cada execução para garantir que as funções mais novas do arquivo
# (ex.: links_processo_nome) estejam disponíveis logo após um novo deploy.
importlib.reload(decisoes)


def _links_processo(alias, numero, grau=None, com_detalhe=True):
    """Links oficiais do processo; tolera um `decisoes` antigo em cache.

    ``com_detalhe`` liga a busca do link DIRETO do PJe (página de detalhe).
    """
    fn = getattr(decisoes, "links_processo", None)
    if not fn:
        return [("🔗 Abrir no site do tribunal", decisoes.link_processo(alias, numero))]
    detalhe = _pje_detalhe(alias, numero, grau) if com_detalhe else None
    return fn(alias, numero, grau, pje_detalhe=detalhe)


@st.cache_data(ttl=3 * 3600, show_spinner=False)
def _pje_detalhe(alias, numero, grau=None):
    """Cache do link direto do PJe (página de detalhe); tolera `decisoes` antigo."""
    fn = getattr(decisoes, "detalhe_pje", None)
    return fn(alias, numero, grau) if fn else None


def _links_processo_nome(alias, nome):
    """Links oficiais de busca por nome; tolera um `decisoes` antigo em cache."""
    fn = getattr(decisoes, "links_processo_nome", None)
    if fn:
        return fn(alias, nome)
    return [("🔎 Buscar por nome no site do tribunal", decisoes.link_processo_nome(alias, nome))]


def _buscar_nome_esaj(alias, nome):
    """Consulta o e-SAJ pelo nome; tolera um `decisoes` antigo em cache."""
    fn = getattr(decisoes, "buscar_nome_esaj", None)
    return fn(alias, nome) if fn else None

st.set_page_config(page_title="Sistema de Peças Judiciais", page_icon="⚖️", layout="wide")

_CSS_LEIS = """
<style>
.lei-grid { display: flex; flex-wrap: wrap; gap: 8px; }
.lei-grid a {
    display: inline-block;
    background: #1f6feb;
    color: #ffffff !important;
    text-decoration: none;
    padding: 9px 14px;
    border-radius: 8px;
    font-size: 0.92rem;
    font-weight: 600;
    border: 1px solid #1057c4;
    line-height: 1.2;
}
.lei-grid a:hover { background: #1057c4; }
</style>
"""

_CSS_LOGIN = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;1,600&display=swap');
.stApp, [data-testid="stAppViewContainer"] {
    background-color: #0093AE !important;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1907 870'%3E%3Crect width='1907' height='870' fill='%230093AE'/%3E%3Crect width='1907' height='165' fill='%2300849F'/%3E%3Crect y='470' width='1907' height='62' fill='%2300849F'/%3E%3Crect y='835' width='1907' height='35' fill='%2300849F'/%3E%3Crect x='420' y='27' width='1680' height='80' rx='40' fill='%230093AE'/%3E%3Crect x='-200' y='530' width='450' height='305' rx='150' fill='%230093AE'/%3E%3Crect x='600' y='530' width='1500' height='305' rx='150' fill='%230093AE'/%3E%3Ccircle cx='447' cy='682' r='152' fill='%2384C2CF'/%3E%3C/svg%3E") !important;
    background-size: cover !important;
    background-position: center top !important;
    background-repeat: no-repeat !important;
    background-attachment: fixed !important;
}
[data-testid="stHeader"] { background: transparent !important; }
.login-head { margin: 0 auto 6px auto; text-align: center; }
.login-logo { font-size: clamp(60px, 14vw, 88px); line-height: 1; margin-bottom: 2px; }
.login-head .login-title, .login-title {
    margin: 0; font-size: 1.7rem; font-weight: 800; letter-spacing: .2px;
    color: #1F4E78 !important;
}
.login-saudacao { font-size: 2.1rem; font-weight: 700; color: #1F4E78; margin: 18px 0 6px 0; font-family: 'Playfair Display', Georgia, 'Times New Roman', serif; }
.login-sub { color: #000000; font-size: 0.95rem; margin: 2px 0 0 0; }
.login-msg { color: #000000; font-size: 0.88rem; font-style: italic; margin: 12px 0 2px 0; }
div[data-testid="stForm"] {
    max-width: 470px; margin: 16px auto 0 auto; background: transparent;
    border: none; border-radius: 0; padding: 0; box-shadow: none;
}
.st-key-login_campos, .st-key-cad_campos {
    max-width: 470px; margin: 16px auto 0 auto;
    background: #ffffff;
    border: 1px solid #d5d9de; border-top: 5px solid #1F4E78; border-radius: 14px;
    padding: 24px 26px 20px 26px;
    box-shadow: 0 14px 34px rgba(15, 23, 42, 0.10);
}
div[data-testid="stForm"] label,
.st-key-login_campos label { color: #000000 !important; font-weight: 600; }
div[data-testid="stForm"] [data-testid="stTextInputRootElement"],
div[data-testid="stForm"] div[data-baseweb="input"],
.st-key-login_campos [data-testid="stTextInputRootElement"],
.st-key-login_campos div[data-baseweb="input"] {
    background: #ffffff !important; border: 1px solid #cbd2d9 !important;
    border-radius: 10px !important;
}
div[data-testid="stForm"] [data-testid="stTextInputRootElement"]:focus-within,
div[data-testid="stForm"] div[data-baseweb="input"]:focus-within,
.st-key-login_campos [data-testid="stTextInputRootElement"]:focus-within,
.st-key-login_campos div[data-baseweb="input"]:focus-within {
    background: #ffffff !important; border-color: #cbd2d9 !important;
}
div[data-testid="stForm"] input,
div[data-testid="stForm"] [data-testid="stTextInputRootElement"] input,
div[data-testid="stForm"] div[data-baseweb="input"] input,
.st-key-login_campos input,
.st-key-login_campos [data-testid="stTextInputRootElement"] input,
.st-key-login_campos div[data-baseweb="input"] input {
    background: #ffffff !important; color: #000000 !important;
    -webkit-text-fill-color: #000000 !important; caret-color: #000000 !important;
}
div[data-testid="stForm"] input:focus,
div[data-testid="stForm"] input:active,
div[data-testid="stForm"] input:hover,
.st-key-login_campos input:focus,
.st-key-login_campos input:active,
.st-key-login_campos input:hover {
    background: #ffffff !important; color: #000000 !important;
    -webkit-text-fill-color: #000000 !important;
}
div[data-testid="stForm"] input:-webkit-autofill,
div[data-testid="stForm"] input:-webkit-autofill:hover,
div[data-testid="stForm"] input:-webkit-autofill:focus,
div[data-testid="stForm"] input:-webkit-autofill:active,
.st-key-login_campos input:-webkit-autofill,
.st-key-login_campos input:-webkit-autofill:hover,
.st-key-login_campos input:-webkit-autofill:focus,
.st-key-login_campos input:-webkit-autofill:active {
    -webkit-text-fill-color: #000000 !important;
    -webkit-box-shadow: 0 0 0 1000px #ffffff inset !important;
    box-shadow: 0 0 0 1000px #ffffff inset !important;
}
div[data-testid="stForm"] ::selection,
.st-key-login_campos ::selection { background: #cfe2ff; color: #000000; }
div[data-testid="stForm"] button,
.st-key-login_entrar button {
    border-radius: 10px; font-weight: 700; background: #1F4E78; color: #ffffff; border: none;
}
div[data-testid="stForm"] button:hover,
.st-key-login_entrar button:hover { background: #2d6aa3; color: #ffffff; }
div[data-testid="stForm"] [data-testid="stTextInputRootElement"] button,
div[data-testid="stForm"] [data-testid="stTextInputRootElement"] button *,
div[data-testid="stForm"] [data-testid="stTextInputRootElement"] [data-baseweb="button"],
div[data-testid="stForm"] [data-testid="stTextInputRootElement"] [role="button"],
div[data-testid="stForm"] [data-baseweb="input"] button,
div[data-testid="stForm"] [data-baseweb="input"] [role="button"],
.st-key-login_campos [data-testid="stTextInputRootElement"] button,
.st-key-login_campos [data-testid="stTextInputRootElement"] button *,
.st-key-login_campos [data-testid="stTextInputRootElement"] [data-baseweb="button"],
.st-key-login_campos [data-testid="stTextInputRootElement"] [role="button"],
.st-key-login_campos [data-baseweb="input"] button,
.st-key-login_campos [data-baseweb="input"] [role="button"] {
    background: transparent !important; background-color: transparent !important;
    border: 0 !important; border-radius: 0 !important; box-shadow: none !important;
    outline: none !important; min-height: 0 !important; height: auto !important;
    min-width: 0 !important; padding: 0 4px !important; color: #000000 !important;
}
/* Esconde o "olhinho"/opções de senha (Streamlit e navegador) */
div[data-testid="stForm"] [data-testid="stTextInputRootElement"] button,
div[data-testid="stForm"] [data-testid="stTextInputRootElement"] [role="button"],
.st-key-login_campos [data-testid="stTextInputRootElement"] button,
.st-key-login_campos [data-testid="stTextInputRootElement"] [role="button"],
input[type="password"]::-ms-reveal,
input[type="password"]::-ms-clear,
input[type="password"]::-webkit-credentials-auto-fill-button,
input[type="password"]::-webkit-strong-password-auto-fill-button,
input[type="password"]::-webkit-textfield-decoration-container {
    display: none !important; visibility: hidden !important;
}
/* Campo de senha do login: mascarado, mas sem o navegador tratar como senha
   (evita o "gerenciador de senhas" do Google aparecer) */
.st-key-login_senha input,
.st-key-login_campos input[aria-label="Senha de acesso"],
div[data-testid="stForm"] input[aria-label="Senha de acesso"] {
    -webkit-text-security: disc; letter-spacing: 2px;
}
/* Olhinho: mostrar/ocultar a senha */
.st-key-login_senha [data-baseweb="input"],
.st-key-login_senha [data-testid="stTextInputRootElement"] { position: relative !important; }
.st-key-login_senha input { padding-right: 42px !important; }
.olho-login {
    position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
    width: 26px; height: 26px; display: flex; align-items: center; justify-content: center;
    cursor: pointer; color: #555555; border-radius: 6px; z-index: 5;
}
.olho-login:hover { background: rgba(31, 78, 120, 0.10); }
.olho-login svg { width: 20px; height: 20px; display: block; }
/* "Esqueceu a senha?": apenas o texto com o símbolo, sem caixa */
div[data-testid="stForm"] [data-testid="stExpander"],
div[data-testid="stForm"] [data-testid="stExpander"] details,
.st-key-login_campos [data-testid="stExpander"],
.st-key-login_campos [data-testid="stExpander"] details {
    border: none !important; background: transparent !important; box-shadow: none !important;
}
div[data-testid="stForm"] [data-testid="stExpander"] summary,
.st-key-login_campos [data-testid="stExpander"] summary {
    justify-content: center !important; padding: 2px 0 !important;
    color: #1F4E78 !important; font-weight: 600 !important; font-size: 0.9rem !important;
}
div[data-testid="stForm"] [data-testid="stExpander"] summary svg,
.st-key-login_campos [data-testid="stExpander"] summary svg { display: none !important; }
div[data-testid="stForm"] [data-testid="stExpander"] summary:hover,
.st-key-login_campos [data-testid="stExpander"] summary:hover { color: #2d6aa3 !important; }
/* seletor Entrar/Criar conta: dentro do cartão, abaixo da frase */
.st-key-login_modo { margin: 2px 0 6px 0; }
.st-key-login_modo [role="radiogroup"] { justify-content: center !important; gap: 22px !important; }
.st-key-login_campos .login-logo { font-size: clamp(46px, 11vw, 66px); }
.st-key-login_campos .login-saudacao { font-size: 1.6rem; margin: 10px 0 4px 0; }
.st-key-login_campos .login-title { font-size: 1.45rem; }
.st-key-login_campos input::placeholder { color: #ccd3d9 !important; opacity: 0.6; font-size: 0.60rem; }
.st-key-login_campos input:focus::placeholder { opacity: 0.15; }
/* campo escondido que leva o token de sessao do navegador para o servidor */
.st-key-login_token, .st-key-login_token [data-testid="stTextInputRootElement"] {
    position: absolute !important; width: 1px !important; height: 1px !important;
    overflow: hidden !important; clip-path: inset(50%) !important; opacity: 0 !important;
    margin: 0 !important; padding: 0 !important; border: 0 !important;
}
/* captcha de figuras (dentro do cartão, abaixo da senha) */
.cap-titulo { color: #1F4E78 !important; font-weight: 700; font-size: 0.95rem; margin: 10px 0 4px 0; }
.cap-pergunta { color: #000000 !important; font-size: 0.92rem; margin: 2px 0 8px 0; }
/* "Não sou um robô" (discreto) */
.st-key-captcha_humano_btn button {
    justify-content: flex-start !important; width: auto !important; min-height: 32px !important;
    background: #fafafa !important; color: #555555 !important;
    border: 1px solid #e4e4e4 !important; border-radius: 4px !important;
    font-weight: 400 !important; padding: 3px 10px !important;
    box-shadow: none !important;
}
.st-key-captcha_humano_btn button::before {
    content: ''; width: 15px; height: 15px; border: 1.5px solid #cfcfcf; border-radius: 3px;
    background: #ffffff; margin-right: 8px; display: inline-block; flex-shrink: 0;
}
.st-key-captcha_humano_btn button p { color: #666666 !important; font-size: 0.78rem !important; }
.st-key-captcha_humano_btn button:hover { background: #f2f2f2 !important; }
/* grade de figuras */
.st-key-captcha_nativo [data-testid="stHorizontalBlock"] { gap: 8px !important; }
.st-key-captcha_nativo [data-testid="stButton"] { margin: 0 !important; }
.st-key-captcha_nativo button {
    width: 100% !important; aspect-ratio: 1 / 1; padding: 0 !important;
    min-height: 0 !important; border-radius: 6px !important; line-height: 1 !important;
}
.st-key-captcha_nativo button p { font-size: 28px !important; margin: 0 !important; line-height: 1 !important; }
.st-key-captcha_nativo button[data-testid^="stBaseButton-secondary"] {
    background: #eef2f6 !important; color: #222222 !important; border: 2px solid #cfd8e3 !important;
}
.st-key-captcha_nativo button[data-testid^="stBaseButton-secondary"]:hover { background: #e2ebf3 !important; }
.st-key-captcha_nativo button[data-testid^="stBaseButton-primary"] {
    background: #d7eef3 !important; color: #222222 !important; border: 2px solid #0093AE !important;
    box-shadow: inset 0 0 0 2px #0093AE !important;
}
</style>
"""


_CSS_TEMA = """
<style>
:root {
    --azul-escuro:#003F65; --azul-aviso:#004164; --azul-petroleo:#00658A;
    --vermelho:#B2101D; --roxo:#694467; --amarelo:#F5AF00;
    --fundo:#F8F9F9; --header:#2B576E; --botao:#E4E9EC; --botao-busca:#C3D1D9;
    --aba-ativa:#D2D4D5; --aba:#DCDEDF;
    --texto-menu:#FFFFFF; --texto-menu-sec:#EEF3F6; --texto-aba:#575756; --link:#3B5C7D; --placeholder:#6C757D;
    --botao-menu:rgba(255,255,255,0.08); --botao-menu-ativo:rgba(255,255,255,0.15);
}
/* fundo do interior */
.stApp, [data-testid="stAppViewContainer"] { background: var(--fundo) !important; }
/* barra lateral (menu) */
[data-testid="stSidebar"] {
    background: var(--header) !important;
    border-right: 1px solid rgba(255,255,255,0.18) !important;
}
[data-testid="stSidebar"] * { color: var(--texto-menu); }
[data-testid="stSidebar"] a { color: #FFFFFF !important; }
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.18) !important; }
[data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] p,
[data-testid="stSidebar"] div, [data-testid="stSidebar"] span { color: var(--texto-menu-sec) !important; }
/* títulos */
h1, h2, h3 { color: var(--azul-escuro) !important; }
/* links */
[data-testid="stMarkdownContainer"] a { color: var(--link) !important; }
hr { border-color: var(--botao-busca) !important; }
/* campos do menu lateral: fundo branco com LETRA PRETA.
   No Streamlit 1.65 o "select" virou .react-aria-ComboBox (input), entao
   precisa do novo seletor senao a letra fica branca sobre a caixa branca. */
[data-testid="stSidebar"] div[data-baseweb="select"] > div,
[data-testid="stSidebar"] div[data-baseweb="input"],
[data-testid="stSidebar"] .react-aria-ComboBox,
[data-testid="stSidebar"] .react-aria-ComboBox > div,
[data-testid="stSidebar"] [role="combobox"] {
    background: #F7F9FA !important; border: 1px solid rgba(255,255,255,0.35) !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.08);
}
[data-testid="stSidebar"] div[data-baseweb="select"] *,
[data-testid="stSidebar"] div[data-baseweb="input"] *,
[data-testid="stSidebar"] .react-aria-ComboBox *,
[data-testid="stSidebar"] [role="combobox"] {
    color: #1F2933 !important;
}
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] textarea {
    color: #1F2933 !important; -webkit-text-fill-color: #1F2933 !important;
    background: #FFFFFF !important;
}
[data-testid="stSidebar"] input::placeholder,
[data-testid="stSidebar"] textarea::placeholder {
    color: #55606B !important; -webkit-text-fill-color: #55606B !important;
}
/* etiqueta de status (ex.: "verificado") na lista da base legal do menu */
[data-testid="stSidebar"] code {
    color: #1F2933 !important; background: #ECEFF1 !important;
}
/* campos brancos */
div[data-baseweb="input"], div[data-baseweb="select"] > div,
div[data-baseweb="base-input"], div[data-baseweb="textarea"] textarea,
[data-testid="stNumberInputContainer"] {
    background: #FFFFFF !important; border-color: var(--botao-busca) !important;
}
input::placeholder, textarea::placeholder { color: var(--placeholder) !important; }
/* aba Fatos: fundo cinza-claro nos campos de leitura/escrita (menos branco, mais confortável) */
[data-testid="stAudioInput"] > div:last-child { background: #ECEFF1 !important; }
.st-key-narrativa div[data-baseweb="textarea"] textarea,
.st-key-fatos_edit div[data-baseweb="textarea"] textarea,
[class*="st-key-resp_"] div[data-baseweb="textarea"] textarea {
    background: #ECEFF1 !important;
}
/* editor formatado do Relato (igual ao Word: negrito, itálico, listas...) */
.st-key-narrativa .__spj_com_editor__ textarea { display: none !important; }
.st-key-narrativa .__spj_editor__ {
    min-height: 150px; max-height: 430px; overflow-y: auto;
    background: #ECEFF1 !important; border: 1px solid var(--botao-busca) !important;
    border-radius: 8px; padding: 10px 12px; color: #1F2933 !important;
    font-size: 1rem; line-height: 1.55; font-family: inherit;
    white-space: pre-wrap; word-break: break-word; outline: none;
}
.st-key-narrativa .__spj_editor__ b, .st-key-narrativa .__spj_editor__ strong { font-weight: 700; }
.st-key-narrativa .__spj_editor__ mark { background: #FFF59D !important; color: #1F2933; }
.st-key-narrativa .__spj_editor__ blockquote {
    border-left: 4px solid #90A4AE; margin: 6px 0; padding: 2px 10px; color: #37474F;
}
.st-key-narrativa .__spj_editor__ h2 { font-size: 1.15rem; margin: 6px 0; }
.st-key-narrativa .__spj_editor__ ul, .st-key-narrativa .__spj_editor__ ol { padding-left: 22px; }
.st-key-narrativa .__spj_editor__:empty:before {
    content: "Digite seu texto aqui"; color: var(--placeholder); pointer-events: none;
}
/* abas */
[data-baseweb="tab-list"] {
    background: var(--aba) !important; border-radius: 8px 8px 0 0; padding: 5px 6px; gap: 4px;
    border-bottom: 1px solid var(--botao-busca) !important;
}
[data-baseweb="tab"] { color: var(--texto-aba) !important; border-radius: 6px !important; }
[data-baseweb="tab"][aria-selected="true"] {
    color: var(--texto-menu) !important; background: var(--aba-ativa) !important; font-weight: 600 !important;
}
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] { background: transparent !important; }
/* cartelas/expansores */
[data-testid="stExpander"] details {
    border: 1px solid var(--botao-busca) !important; border-radius: 8px !important;
    background: #ECEFF1 !important;
}
[data-testid="stExpander"] summary { color: var(--azul-escuro) !important; font-weight: 600 !important; }
/* expansores da barra lateral: cabeçalho azul com letra branca */
[data-testid="stSidebar"] [data-testid="stExpander"] details {
    background: transparent !important; border: none !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary {
    background: var(--azul-escuro) !important; color: #FFFFFF !important;
    border: 1px solid rgba(255,255,255,0.25) !important;
    border-radius: 8px !important; font-weight: 600 !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary:hover {
    background: var(--azul-petroleo) !important; border-color: rgba(255,255,255,0.35) !important;
    color: #FFFFFF !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary,
[data-testid="stSidebar"] [data-testid="stExpander"] summary * {
    color: #FFFFFF !important; fill: #FFFFFF !important;
}
/* ícone do expansor "Contas" (bonequinhos) em amarelo, como o símbolo do Direito */
[data-testid="stSidebar"] [data-testid="stExpander"] summary [data-testid="stIconMaterial"] {
    color: var(--amarelo) !important; fill: var(--amarelo) !important;
}
/* botões: azul corporativo com letra branca (mirado pelo data-testid no Streamlit 1.65+) */
button[data-testid^="stBaseButton-"],
a[data-testid^="stBaseLinkButton-"] {
    background: var(--azul-escuro) !important; color: #FFFFFF !important;
    border: 1px solid var(--azul-aviso) !important;
    border-radius: 8px !important; font-weight: 600 !important;
    text-decoration: none !important;
}
button[data-testid^="stBaseButton-"]:hover,
a[data-testid^="stBaseLinkButton-"]:hover {
    background: var(--azul-petroleo) !important; border-color: var(--azul-petroleo) !important;
    color: #FFFFFF !important;
}
/* barra lateral: mesmos botões azuis com letra branca */
[data-testid="stSidebar"] button[data-testid^="stBaseButton-"] {
    background: var(--azul-escuro) !important; color: #FFFFFF !important;
    border: 1px solid rgba(255,255,255,0.25) !important;
    border-radius: 8px !important; font-weight: 600 !important;
}
[data-testid="stSidebar"] button[data-testid^="stBaseButton-"]:hover {
    background: var(--azul-petroleo) !important; border-color: rgba(255,255,255,0.35) !important;
    color: #FFFFFF !important;
}
/* barra de formatação do texto (tipo Word) */
.__spj_barra__ {
    display: flex; flex-wrap: wrap; gap: 4px; align-items: center;
    background: #ECEFF1; border: 1px solid var(--botao-busca); border-radius: 6px;
    padding: 4px 6px; margin: 0 0 6px 0;
}
.__spj_barra__ button {
    min-width: 30px; height: 28px; padding: 0 6px; line-height: 1;
    border: 1px solid var(--botao-busca); border-radius: 4px;
    background: #FFFFFF; color: var(--azul-escuro); font-size: 14px;
    cursor: pointer; font-family: inherit;
}
.__spj_barra__ button:hover { background: var(--aba-ativa); border-color: var(--azul-escuro); }
.__spj_barra__ button:active { background: var(--botao-busca); }
/* aviso de recuperacao do texto */
.__spj_aviso__ {
    background: #FFF8E1; border: 1px solid #F5AF00; color: #6B4B00;
    border-radius: 6px; padding: 6px 10px; margin: 0 0 6px 0; font-size: 0.85rem;
}
</style>
"""


MENSAGENS_ABERTURA = [
    "Bem-vindo(a) de volta! Que seu trabalho hoje flua leve e produtivo.",
    "Pronto(a) para transformar fatos em uma peça impecável? Vamos começar!",
    "Deixe a parte chata com o sistema e concentre-se no Direito.",
    "Cada peça bem feita constrói a sua reputação. Bons trabalhos!",
    "Organização agora, tranquilidade depois. Mãos à obra!",
    "Um ótimo trabalho começa com uma boa ferramenta nas mãos.",
    "Foco, clareza e agilidade: você cuida do caso, o sistema cuida da forma.",
]


def _saudacao():
    hora = datetime.now(timezone(timedelta(hours=-3))).hour
    if 5 <= hora < 12:
        return "Bom dia"
    if 12 <= hora < 18:
        return "Boa tarde"
    return "Boa noite"


def _carregar_municipios():
    caminho = Path(__file__).resolve().parent / "dados" / "ibge_municipios.json"
    try:
        with open(caminho, encoding="utf-8-sig") as arq:
            return json.load(arq)
    except Exception:
        return {}


MUNICIPIOS = _carregar_municipios()

ESTADOS = [
    ("AC", "Acre"), ("AL", "Alagoas"), ("AP", "Amapá"), ("AM", "Amazonas"), ("BA", "Bahia"),
    ("CE", "Ceará"), ("DF", "Distrito Federal"), ("ES", "Espírito Santo"), ("GO", "Goiás"),
    ("MA", "Maranhão"), ("MT", "Mato Grosso"), ("MS", "Mato Grosso do Sul"), ("MG", "Minas Gerais"),
    ("PA", "Pará"), ("PB", "Paraíba"), ("PR", "Paraná"), ("PE", "Pernambuco"), ("PI", "Piauí"),
    ("RJ", "Rio de Janeiro"), ("RN", "Rio Grande do Norte"), ("RS", "Rio Grande do Sul"),
    ("RO", "Rondônia"), ("RR", "Roraima"), ("SC", "Santa Catarina"), ("SP", "São Paulo"),
    ("SE", "Sergipe"), ("TO", "Tocantins"),
]
OPCOES_UF = ["—"] + [f"{sigla} – {nome}" for sigla, nome in ESTADOS]
SIGLA_UF = {f"{sigla} – {nome}": sigla for sigla, nome in ESTADOS}
CAMPOS_ENDERECO = ("rua", "num", "bairro", "cep", "cidade", "uf", "cidade_livre", "compl")

DEFAULTS = {
    "dados": "", "narrativa": "", "fatos_edit": "", "peca_edit": "",
    "pend": "", "respostas": "", "alertas": [], "usadas": [], "juris_sugerida": "",
    "analise_doc": "", "analise_alertas": [],
    "f_juizo": "", "f_outros": "", "f_rotulo": "Requerente / Requerido",
    "mem_ruas": [], "mem_bairros": [], "mem_ceps": [],
    "req_nome": "", "req_civil": "", "req_prof": "",
    "req_cpf": "", "req_cnpj": "", "req_rg": "",
    "rdo_nome": "", "rdo_civil": "", "rdo_prof": "",
    "rdo_cpf": "", "rdo_cnpj": "", "rdo_rg": "",
    **{f"req_{c}": "" for c in CAMPOS_ENDERECO},
    **{f"rdo_{c}": "" for c in CAMPOS_ENDERECO},
}
for chave, inicial in DEFAULTS.items():
    st.session_state.setdefault(chave, inicial)
st.session_state.setdefault("chat_hist", [])

# aplica valores definidos por botões (antes de criar os campos, para não dar erro)
for _campo, _pendente in (("fatos_edit", "_p_fatos"), ("peca_edit", "_p_peca"),
                          ("pend", "_p_pend"), ("respostas", "_p_respostas")):
    if _pendente in st.session_state:
        st.session_state[_campo] = st.session_state.pop(_pendente)

if st.session_state.pop("_limpar_respostas", False):
    for _k in [k for k in st.session_state if str(k).startswith("resp_")]:
        del st.session_state[_k]


# ---------------------------------------------------------------- portão de acesso (senha)
_SELO_PC = "pecas_acesso_ok"


def _selo_pc_ok():
    try:
        return (st.context.cookies.get(_SELO_PC) or "").strip() == "ok"
    except Exception:
        return False


def _captcha_html():
    """Captcha no estilo reCAPTCHA (como no controle de frota): caixa 'Não sou um robô'
    que abre uma grade de figuras para marcar. Ao acertar, grava o selo no navegador."""
    return """
<style>
  html, body { margin:0; padding:0; background:transparent;
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif; }
  .recaptcha { background:#f9f9f9; border:1px solid #d3d3d3; border-radius:4px;
    padding:10px; max-width:300px; margin:0 auto; box-shadow:0 1px 3px rgba(0,0,0,.08); }
  .recaptcha-topo { display:flex; align-items:center; gap:10px; width:100%;
    background:none; border:none; cursor:pointer; padding:4px 2px; font-family:inherit; }
  .recaptcha-caixa { width:24px; height:24px; border:2px solid #c1c1c1; border-radius:3px;
    background:#fff; display:inline-block; flex-shrink:0; }
  .recaptcha-texto { font-size:14px; color:#333; }
  .recaptcha-marca { margin-left:auto; font-size:10px; color:#9aa0a6;
    text-transform:uppercase; letter-spacing:1px; }
  .recaptcha-desafio { margin-top:10px; }
  .recaptcha-pergunta { font-size:14px; font-weight:600; color:#1F4E78; margin:0 0 8px 0; }
  .recaptcha-grade { display:grid; grid-template-columns:repeat(3,1fr); gap:6px; }
  .recaptcha-tile { aspect-ratio:1/1; font-size:30px; background:#eef2f6;
    border:2px solid #cfd8e3; border-radius:6px; cursor:pointer; line-height:1;
    display:flex; align-items:center; justify-content:center; }
  .recaptcha-tile:hover { background:#e2ebf3; }
  .recaptcha-tile.selecionado { border-color:#0093AE; background:#d7eef3;
    box-shadow:inset 0 0 0 2px #0093AE; }
  .recaptcha-dica { display:block; margin-top:8px; color:#777; font-size:12px; }
  .recaptcha-erro { color:#B2101D; font-size:13px; font-weight:600; margin:8px 0 0 0; }
  .recaptcha-btn { margin-top:10px; width:100%; background:#1F4E78; color:#fff;
    border:none; border-radius:6px; padding:9px; font-weight:700; font-size:14px; cursor:pointer; }
  .recaptcha-btn:hover { background:#2d6aa3; }
</style>
<div class="recaptcha">
  <button type="button" class="recaptcha-topo" id="topo" onclick="abrir()">
    <span class="recaptcha-caixa"></span>
    <span class="recaptcha-texto">Não sou um robô</span>
    <span class="recaptcha-marca">segurança</span>
  </button>
  <div class="recaptcha-desafio" id="desafio" style="display:none;">
    <p class="recaptcha-pergunta" id="pergunta"></p>
    <div class="recaptcha-grade" id="grade"></div>
    <small class="recaptcha-dica">Clique em todas as imagens certas e depois em Confirmar.</small>
    <p class="recaptcha-erro" id="erro" style="display:none;">Verificação incorreta. Tente novamente.</p>
    <button type="button" class="recaptcha-btn" onclick="confirmar()">Confirmar</button>
  </div>
</div>
<script>
  var IMAGENS = [["🚚","o caminhão"],["🚗","o carro"],["🚌","o ônibus"],["🚲","a bicicleta"],
                 ["⭐","a estrela"],["✈️","o avião"],["🏠","a casa"],["🌳","a árvore"],
                 ["⚖️","a balança"],["📚","os livros"],["🔨","o martelo"],["🏛️","o tribunal"]];
  var corretos = [];
  function ajustar(){ try{ window.frameElement.style.height=(document.body.scrollHeight+18)+'px'; }catch(e){} }
  function gerar(){
    var i = Math.floor(Math.random()*IMAGENS.length);
    var alvo = IMAGENS[i][0], nome = IMAGENS[i][1];
    var outros = IMAGENS.filter(function(x){ return x[0]!==alvo; }).map(function(x){ return x[0]; });
    var pos = [0,1,2,3,4,5,6,7,8];
    pos.sort(function(){ return Math.random()-0.5; });
    var qtd = 2 + Math.floor(Math.random()*2);
    corretos = pos.slice(0,qtd).sort(function(a,b){ return a-b; });
    var g = document.getElementById('grade');
    g.innerHTML = '';
    for (var k=0;k<9;k++){
      (function(k){
        var t = document.createElement('button');
        t.type = 'button'; t.className = 'recaptcha-tile'; t.setAttribute('data-i', k);
        t.textContent = corretos.indexOf(k)>=0 ? alvo : outros[Math.floor(Math.random()*outros.length)];
        t.onclick = function(){ t.classList.toggle('selecionado'); };
        g.appendChild(t);
      })(k);
    }
    document.getElementById('pergunta').innerHTML = 'Clique nas imagens que mostram <b>'+nome+'</b>:';
    document.getElementById('erro').style.display = 'none';
    ajustar();
  }
  function abrir(){
    document.getElementById('topo').style.display = 'none';
    document.getElementById('desafio').style.display = 'block';
    if (!corretos.length) gerar();
    ajustar();
  }
  function confirmar(){
    var sel = [];
    var ts = document.querySelectorAll('.recaptcha-tile.selecionado');
    for (var i=0;i<ts.length;i++){ sel.push(parseInt(ts[i].getAttribute('data-i'),10)); }
    sel.sort(function(a,b){ return a-b; });
    if (JSON.stringify(sel)===JSON.stringify(corretos)){
      try{ document.cookie='pecas_acesso_ok=ok; max-age=31536000; path=/; SameSite=Lax'; }catch(e){}
      try{ window.parent.document.cookie='pecas_acesso_ok=ok; max-age=31536000; path=/; SameSite=Lax'; }catch(e){}
      window.parent.location.reload();
    } else {
      document.getElementById('erro').style.display = 'block';
      gerar();
    }
  }
  ajustar();
  window.addEventListener('load', ajustar);
</script>
"""


def _gravar_selo_pc():
    """Marca este navegador como já verificado (não pede o captcha de novo aqui)."""
    components.html(
        """
        <script>
        try { document.cookie = 'pecas_acesso_ok=ok; max-age=31536000; path=/; SameSite=Lax'; } catch (e) {}
        try { window.parent.document.cookie = 'pecas_acesso_ok=ok; max-age=31536000; path=/; SameSite=Lax'; } catch (e) {}
        </script>
        """,
        height=0,
    )


_CAPTCHA_FIGURAS = [
    ("🚚", "o caminhão"), ("🚗", "o carro"), ("🚌", "o ônibus"),
    ("🚲", "a bicicleta"), ("⭐", "a estrela"), ("✈️", "o avião"),
    ("🏠", "a casa"), ("🌳", "a árvore"), ("⚖️", "a balança"),
    ("📚", "os livros"), ("🔨", "o martelo"), ("🏛️", "o tribunal"),
]


def _captcha_novo_desafio():
    emoji, nome = random.choice(_CAPTCHA_FIGURAS)
    outros = [e for e, _ in _CAPTCHA_FIGURAS if e != emoji]
    certos = sorted(random.sample(range(9), random.randint(2, 3)))
    st.session_state["captcha_alvo"] = nome
    st.session_state["captcha_corretos"] = certos
    st.session_state["captcha_tiles"] = [
        emoji if k in certos else random.choice(outros) for k in range(9)
    ]
    st.session_state["captcha_sel"] = []


def _captcha_render():
    """Verificação de segurança dentro do cartão: 'Não sou um robô' abre as figuras."""
    st.markdown("<div class='cap-titulo'>Verificação de segurança</div>", unsafe_allow_html=True)
    if not st.session_state.get("captcha_humano"):
        if st.button("Não sou um robô", key="captcha_humano_btn"):
            st.session_state["captcha_humano"] = True
            _captcha_novo_desafio()
            st.rerun()
        return
    with st.container(key="captcha_nativo"):
        st.markdown(
            "<p class='cap-pergunta'>Marque as figuras que mostram <b>"
            f"{st.session_state.get('captcha_alvo', '')}</b>:</p>",
            unsafe_allow_html=True,
        )
        sel = set(st.session_state.get("captcha_sel", []))
        tiles = st.session_state.get("captcha_tiles", [])
        for linha in range(3):
            colunas = st.columns(3)
            for c in range(3):
                i = linha * 3 + c
                with colunas[c]:
                    if st.button(tiles[i], key=f"captcha_tile_{i}",
                                 type=("primary" if i in sel else "secondary")):
                        nova = set(sel)
                        nova.symmetric_difference_update({i})
                        st.session_state["captcha_sel"] = sorted(nova)
                        st.rerun()


def _captcha_necessario():
    # Pede a verificação de segurança sempre, em todo login.
    return True


def _captcha_valido():
    sel = set(st.session_state.get("captcha_sel", []))
    corretos = set(st.session_state.get("captcha_corretos", []))
    return bool(corretos) and sel == corretos


def _definir_idioma():
    """Marca a página como português para o navegador não oferecer tradução."""
    if st.session_state.get("_idioma_pt"):
        return
    components.html(
        "<script>"
        "try { var h = window.parent.document.documentElement;"
        " h.setAttribute('lang', 'pt-BR'); h.setAttribute('xml:lang', 'pt-BR'); }"
        " catch (e) {}"
        "</script>",
        height=0,
    )
    st.session_state["_idioma_pt"] = True


_definir_idioma()


# ------------------------------------------------- sessao que sobrevive a atualizacao
# Quando o sistema e atualizado (ou a pagina e recarregada), o app volta para a
# tela de entrada e o trabalho some. Para resolver, o navegador guarda um
# "cookie de sessao" assinado: ao voltar, o app entra sozinho.
_COOKIE_SESSAO = "pecas_sessao"
_DIAS_SESSAO = 30
_BUILD = "editor-word-sessao-2026-10-21"


def _cookies_recebidas():
    """Todos os cookies que o navegador mandou para o servidor."""
    try:
        return dict(st.context.cookies)
    except Exception:
        return {}


def _token_sessao(usuario, admin):
    return motor.token_sessao(usuario, admin, _DIAS_SESSAO)


def _ler_token_sessao(token):
    """Devolve {usuario, admin} se o cookie for valido; senao None."""
    return motor.ler_token_sessao(token)


def _cookie_sessao():
    try:
        if os.environ.get("SPJ_SEM_COOKIE"):
            # apenas para teste: finge que o servidor nao recebe cookies
            # (igual acontece na nuvem, onde o proxy nao os repassa)
            return ""
        return (st.context.cookies.get(_COOKIE_SESSAO) or "").strip()
    except Exception:
        return ""


def _token_do_widget():
    """Token de sessao que o navegador escreveu no campo escondido."""
    try:
        return (st.session_state.get("_token_widget") or "").strip()
    except Exception:
        return ""


# O navegador (ve _JS_SESSAO) le o token guardado no cookie/localStorage e
# escreve num campo escondido. Isso e necessario porque, na nuvem, o proxy do
# Streamlit nao repassa os cookies para o servidor: so assim o app consegue
# lembrar quem entrou depois de dar F5.
_JS_SESSAO = r"""<script>
(function () {
  var P = window.parent;
  var doc = P.document;
  var NOME = "__NOME__";
  var CHAVE = "__CHAVE__";

  function doCookie(qual) {
    try {
      var c = qual.cookie || "";
      var partes = c.split(";");
      for (var i = 0; i < partes.length; i++) {
        var p = partes[i].trim();
        if (p.indexOf(NOME + "=") === 0) return p.substring(NOME.length + 1);
      }
    } catch (e) {}
    return "";
  }

  function doLocal() {
    try {
      var v = P.localStorage.getItem(CHAVE);
      if (v) return v;
    } catch (e) {}
    try {
      var v2 = window.localStorage.getItem(CHAVE);
      if (v2) return v2;
    } catch (e) {}
    return "";
  }

  function token() {
    return doCookie(doc) || doCookie(window.document) || doLocal();
  }

  function campo() {
    var c1 = doc.querySelector(".st-key-_token_widget input");
    if (c1) return c1;
    var cont = doc.querySelector('[data-testid="st-key-_token_widget"]');
    if (cont) return cont.querySelector("input");
    var cont2 = doc.querySelector(".st-key-login_token input");
    if (cont2) return cont2;
    return null;
  }

  function tentar() {
    var inp = campo();
    if (!inp) return false;
    if (inp.value && inp.value.length > 20) return true;
    var t = token();
    if (!t || t.length < 20) return false;
    try {
      var setter = Object.getOwnPropertyDescriptor(P.HTMLInputElement.prototype, "value").set;
      setter.call(inp, t);
      inp.dispatchEvent(new P.Event("input", {bubbles: true}));
      inp.focus();
      setTimeout(function () { try { inp.blur(); } catch (e) {} }, 80);
    } catch (e) { return false; }
    return true;
  }

  if (tentar()) { setTimeout(tentar, 800); }
  setInterval(tentar, 1500);
})();
</script>"""


def _gravar_cookie_sessao(usuario, admin):
    """Manda o navegador lembrar do acesso (30 dias)."""
    token = _token_sessao(usuario, admin)
    valor = (_COOKIE_SESSAO + "=" + token + "; max-age=" + str(_DIAS_SESSAO * 24 * 3600)
             + "; path=/; SameSite=Lax")
    # escreve no iframe, no pai e na pagina de fora: assim funciona mesmo se o
    # navegador bloquear o cookie dentro de um dos frames
    js = ("<script>(function(){var c=" + json.dumps(valor) + ";"
          "try{document.cookie=c;}catch(e){}"
          "try{var p=window.parent;for(var i=0;i<6&&p;i++){"
          "p.document.cookie=c;try{p=p.parent;}catch(x){break;}}}catch(e){}"
          "})();</script>")
    try:
        components.html(js, height=0)
    except Exception:
        pass
    # guarda tambem no localStorage: e o que salva a sessao quando o servidor da
    # nuvem nao consegue ler os cookies (o proxy nao os repassa)
    try:
        components.html(
            "<script>(function(){try{"
            "window.parent.localStorage.setItem(" + json.dumps("spj_token") + ","
            + json.dumps(token) + ");}catch(e){}})();</script>",
            height=0,
        )
    except Exception:
        pass


def _apagar_cookie_sessao():
    """Esquece o acesso guardado (botao 'Sair do sistema')."""
    try:
        components.html(
            "<script>try { document.cookie = '" + _COOKIE_SESSAO
            + "=; max-age=0; path=/; SameSite=Lax'; } catch (e) {}</script>"
            "<script>try { window.parent.localStorage.removeItem('spj_token'); } catch (e) {}</script>",
            height=0,
        )
    except Exception:
        pass


def _marcar_cookie(usuario, admin):
    """Anota para gravar o cookie na proxima execucao (apos o rerun do login)."""
    st.session_state["_cookie_pendente"] = (str(usuario or "").strip(), bool(admin))


# o botao "Sair do sistema" pede para esquecer o acesso guardado
_apagando = st.session_state.pop("_cookie_apagar", False)
if _apagando:
    _apagar_cookie_sessao()
    # limpa o token guardado no campo escondido (senao entraria sozinho de novo)
    try:
        st.session_state["_token_widget"] = ""
    except Exception:
        pass
else:
    # ja voltou com o cookie? entao entra direto, sem pedir a senha
    if not st.session_state.get("autenticado"):
        _sessao = _ler_token_sessao(_cookie_sessao())
        if not _sessao:
            # na nuvem o proxy nao repassa os cookies: o token vem pelo campo
            # escondido, escrito pelo navegador (ver _JS_SESSAO)
            _sessao = _ler_token_sessao(_token_do_widget())
        if _sessao:
            st.session_state.update(autenticado=True, usuario=_sessao["usuario"],
                                    admin=_sessao["admin"])
            _gravar_cookie_sessao(_sessao["usuario"], _sessao["admin"])


if not st.session_state.setdefault("autenticado", False):
    # campo escondido: e por ele que o navegador entrega o token de sessao
    # quando o servidor nao consegue ler os cookies (nuvem)
    with st.container(key="login_token"):
        st.text_input("sessao", key="_token_widget", label_visibility="collapsed",
                      placeholder="")
    try:
        components.html(
            _JS_SESSAO.replace("__NOME__", _COOKIE_SESSAO).replace("__CHAVE__", "spj_token"),
            height=0,
        )
    except Exception:
        pass
    if "msg_abertura" not in st.session_state:
        st.session_state["msg_abertura"] = random.choice(MENSAGENS_ABERTURA)
    st.markdown(_CSS_LOGIN, unsafe_allow_html=True)
    with st.container(key="login_campos"):
        st.markdown(
            "<div class='login-head'>"
            "<div class='login-logo'>⚖️</div>"
            "<h1 class='login-title'>Sistema de Peças Judiciais</h1>"
            f"<div class='login-saudacao'>{_saudacao()}!</div>"
            f"<p class='login-msg'>{html.escape(st.session_state['msg_abertura'])}</p>"
            "<p class='login-sub'>Acesse com seu usuário e senha.</p>"
            "</div>",
            unsafe_allow_html=True,
        )

        _precisa_captcha = _captcha_necessario()

        modo_login = st.radio("Acesso", ["Entrar", "Criar conta"], horizontal=True,
                              key="login_modo", label_visibility="collapsed")

        if modo_login == "Entrar":
            usuario_entrada = st.text_input("Usuário (ou e-mail)", key="login_usuario",
                                            placeholder="Usuário (ou e-mail)")
            senha_entrada = st.text_input("Senha de acesso", key="login_senha",
                                          placeholder="Senha de acesso")
            if _precisa_captcha:
                _captcha_render()
            entrar = st.button("Entrar", type="primary", key="login_entrar", width="stretch")
            with st.expander("🔑 Esqueceu a senha?"):
                st.markdown(
                    "Sem problema. Sua senha não pode ser enviada por e-mail, mas pode ser "
                    "**redefinida**:\n\n"
                    "- **Usuário do sistema:** peça ao **administrador** para criar uma nova "
                    "senha para você (ele faz em **👥 Contas**).\n"
                    "- **Administrador:** se você esqueceu a sua, redefina em "
                    "**Streamlit → Manage app → Settings → Secrets** (variável "
                    "`SENHA_ACESSO`)."
                )

            if not motor.senha_ativa() or not motor.usuario_acesso():
                st.info("Primeiro acesso do administrador: defina abaixo o usuário e a senha.")
                with st.form("primeira_senha"):
                    u_novo = st.text_input("Usuário (ex.: admin)", key="u_novo")
                    s1 = st.text_input("Nova senha (mínimo 4 caracteres)", type="password", key="s1")
                    s2 = st.text_input("Repita a nova senha", type="password", key="s2")
                    definir = st.form_submit_button("Definir acesso e entrar")
                    if definir:
                        if not s1 or s1 != s2:
                            st.error("As senhas não conferem.")
                        else:
                            try:
                                motor.definir_acesso(u_novo, s1)
                                st.session_state.update(autenticado=True, usuario=u_novo.strip(), admin=True)
                                _marcar_cookie(u_novo.strip(), True)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Não deu para definir o acesso: {e}")
        else:
            st.caption("Crie sua conta. Ela será liberada depois que o administrador aprovar.")
            with st.form("cadastro_form"):
                cad_nome = st.text_input("Nome completo", key="cad_nome")
                cad_usuario = st.text_input("E-mail (será seu usuário)", key="cad_usuario")
                cad_s1 = st.text_input("Senha (mínimo 6 caracteres)", type="password", key="cad_s1")
                cad_s2 = st.text_input("Repita a senha", type="password", key="cad_s2")
                criar = st.form_submit_button("Criar conta", type="primary", width="stretch")

        components.html(
            """
            <script>
            (function () {
              var ABERTO = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
              var FECHADO = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><path d="M14.12 14.12A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><line x1="1" y1="1" x2="23" y2="23"/></svg>';
              function ajustar() {
                try {
                  var d = window.parent.document;
                  d.querySelectorAll('.st-key-login_senha input, input[aria-label="Senha de acesso"]')
                    .forEach(function (el) {
                      el.setAttribute('autocomplete', 'off');
                      el.setAttribute('name', 'senha_' + Math.random().toString(36).slice(2));
                      el.setAttribute('type', 'text');
                      el.style.setProperty('-webkit-text-security', 'disc', 'important');
                      el.style.setProperty('letter-spacing', '2px', 'important');
                    });
                  var campo = d.querySelector('.st-key-login_senha input') || d.querySelector('input[aria-label="Senha de acesso"]');
                  if (!campo) return;
                  var caixa = campo.closest('[data-baseweb="input"]') || campo.closest('[data-testid="stTextInputRootElement"]') || campo.parentElement;
                  if (!caixa || caixa.querySelector('.olho-login')) return;
                  caixa.style.position = 'relative';
                  var b = d.createElement('span');
                  b.className = 'olho-login';
                  b.title = 'Mostrar senha';
                  b.innerHTML = ABERTO;
                  var mostrando = false;
                  b.onclick = function () {
                    mostrando = !mostrando;
                    campo.style.setProperty('-webkit-text-security', mostrando ? 'none' : 'disc', 'important');
                    campo.style.setProperty('letter-spacing', mostrando ? 'normal' : '2px', 'important');
                    b.innerHTML = mostrando ? FECHADO : ABERTO;
                    b.title = mostrando ? 'Ocultar senha' : 'Mostrar senha';
                  };
                  caixa.appendChild(b);
                } catch (e) {}
              }
              ajustar();
              setTimeout(ajustar, 500);
              setTimeout(ajustar, 1500);
            })();
            </script>
            """,
            height=0,
        )

    if modo_login == "Entrar" and entrar:
        if _precisa_captcha and not _captcha_valido():
            st.error("Para entrar, marque as figuras corretas na verificação de segurança.")
        elif motor.verificar_acesso(usuario_entrada, senha_entrada):
            _usuario_admin = motor.usuario_acesso() or usuario_entrada.strip()
            st.session_state.update(autenticado=True, admin=True, usuario=_usuario_admin)
            _marcar_cookie(_usuario_admin, True)
            st.rerun()
        else:
            resultado = usuarios.autenticar(usuario_entrada, senha_entrada)
            if resultado == usuarios.OK:
                st.session_state.update(autenticado=True, admin=False, usuario=usuario_entrada.strip())
                _marcar_cookie(usuario_entrada.strip(), False)
                st.rerun()
            elif resultado == usuarios.PENDENTE:
                st.warning("Sua conta foi criada, mas ainda aguarda a **aprovação** do administrador.")
            else:
                st.error("Usuário ou senha incorretos.")
    elif modo_login == "Criar conta" and criar:
        if cad_s1 != cad_s2:
            st.error("As senhas não conferem.")
        else:
            try:
                usuarios.criar(cad_nome, cad_usuario, cad_s1)
                st.success("Conta criada! Aguarde a aprovação do administrador para entrar.")
            except ValueError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Não foi possível criar a conta: {e}")

    # marcacao da versao + diagnostico ( invisivel para o usuario normal)
    st.markdown("<div style='display:none' data-build='" + _BUILD + "'></div>",
                unsafe_allow_html=True)
    _ck = _cookies_recebidas()
    if _ck.get("spj_diag") or st.query_params.get("diag"):
        _tok = _token_do_widget()
        st.info("DIAG build=" + _BUILD + " | cookies recebidos: "
                + (", ".join(sorted(_ck)) or "(nenhum)")
                + " | token no campo oculto: "
                + (("sim (%d)" % len(_tok)) if _tok else "(nao)"))

    st.stop()

# grava o cookie de sessao (agora que o app ja entrou): assim, ao atualizar a
# pagina ou o sistema, ele volta direto para dentro, sem pedir a senha de novo
_pendente_cookie = st.session_state.pop("_cookie_pendente", None)
if _pendente_cookie:
    _gravar_cookie_sessao(_pendente_cookie[0], _pendente_cookie[1])
    st.session_state["_cookie_conferido"] = False
elif st.session_state.get("_cookie_conferido") is False:
    # na execucao seguinte o cookie ja deveria ter chegado no servidor
    st.session_state["_cookie_conferido"] = True
    if not _cookie_sessao():
        st.warning(
            "⚠️ O seu navegador está bloqueando cookies: se você atualizar a página, "
            "vai ter que entrar de novo. Permita cookies para este site "
            "(cadeado ao lado do endereço) e entre mais uma vez.",
            icon="⚠️",
        )

# tema visual do interior (aplicado só depois do login)
st.markdown(_CSS_TEMA, unsafe_allow_html=True)


def alerta(nivel, msg):
    icone = {"erro": "❌", "aviso": "⚠️", "ok": "✅"}.get(nivel, "•")
    st.markdown(f"{icone} {msg}")


# ------------------------------------------------- barra de formatação (tipo Word)
# A caixa de texto do Streamlit é "crua". Esta barra injeta botões (negrito,
# itálico, lista...) que marcam o texto selecionado, como no Word. As marcas
# (**negrito**, _itálico_...) vão junto para a IA e aparecem formatadas na
# pré-visualização.
_JS_BARRA = r"""<script>
(function () {
  var ALVO = "__ALVO__";
  var CHAVE = "__CHAVE__";
  var P = window.parent;
  var doc = P.document;
  var MEU = "spj" + Math.random().toString(36).slice(2, 9);
  var ultimo = null;
  var ultimoHtml = null;
  var restaurado = false;
  var BTNS = [
    {t:"Negrito",           i:"<b>N</b>",  cmd:"bold"},
    {t:"Itálico",           i:"<i>I</i>",  cmd:"italic"},
    {t:"Sublinhado",        i:"<u>S</u>",  cmd:"underline"},
    {t:"Tachado",           i:"<s>T</s>",  cmd:"strikeThrough"},
    {t:"Destaque",          i:"<mark>A</mark>", tag:"mark"},
    {t:"Título",            i:"H",        bloco:"h2"},
    {t:"Lista",             i:"&#8226;",  cmd:"insertUnorderedList"},
    {t:"Lista numerada",    i:"1.",       cmd:"insertOrderedList"},
    {t:"Citação",           i:"&#10077;", bloco:"blockquote"},
    {t:"Desfazer",          i:"&#8630;",  cmd:"undo"},
    {t:"Refazer",           i:"&#8631;",  cmd:"redo"},
    {t:"Limpar formatação", i:"&#129534;", limpar:true}
  ];

  function achar() {
    var areas = doc.querySelectorAll(".stTextArea");
    var achado = null;
    for (var i = 0; i < areas.length; i++) {
      var lbl = areas[i].querySelector("label");
      if (lbl && lbl.textContent.indexOf(ALVO) === 0) {
        if (!achado) achado = areas[i];
        var r = areas[i].getBoundingClientRect();
        if (r.width > 0 && r.height > 0) return areas[i];
      }
    }
    return achado;
  }

  function caixa() {
    var c = achar();
    return c ? c.querySelector("textarea") : null;
  }

  function editor() {
    var c = achar();
    return c ? c.querySelector(".__spj_editor__") : null;
  }

  function sel(ta) { return {i: ta.selectionStart, f: ta.selectionEnd, v: ta.value}; }

  function setValor(ta, novo) {
    try {
      var setter = Object.getOwnPropertyDescriptor(P.HTMLTextAreaElement.prototype, "value").set;
      setter.call(ta, novo);
      ta.dispatchEvent(new P.Event("input", {bubbles: true}));
    } catch (e) { ta.value = novo; }
  }

  // manda o texto para o servidor sem tirar o foco do campo
  function comitar(ta) {
    try { ta.dispatchEvent(new P.Event("focusout", {bubbles: true})); } catch (e) {}
  }

  // ---------------- editor formatado (igual ao Word) --------------------
  // texto antigo (com marcadores **) vira HTML de verdade
  function mdParaHtml(t) {
    if (!t) return "";
    if (/<[a-zA-Z][^>]*>/.test(t)) return t;
    var s = String(t);
    if (!/(\*\*|__|~~|==|^\s*#|^\s*[-*+]\s|^\s*&gt;\s)/m.test(s)) return s;
    s = s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    s = s.replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>");
    s = s.replace(/(^|[^*\w])\*([^*\n]+)\*/g, "$1<i>$2</i>");
    s = s.replace(/__([^_]+)__/g, "<u>$1</u>");
    s = s.replace(/~~([^~]+)~~/g, "<s>$1</s>");
    s = s.replace(/==([^=]+)==/g, "<mark>$1</mark>");
    var linhas = s.split(/\r?\n/);
    var saida = "", emLista = false;
    for (var i = 0; i < linhas.length; i++) {
      var l = linhas[i];
      if (/^\s*&gt;\s/.test(l)) {
        l = "<blockquote>" + l.replace(/^\s*&gt;\s*/, "") + "</blockquote>";
      } else if (/^\s*#\s/.test(l)) {
        l = "<h2>" + l.replace(/^\s*#\s*/, "") + "</h2>";
      } else if (/^\s*[-*+]\s/.test(l)) {
        l = "<li>" + l.replace(/^\s*[-*+]\s*/, "") + "</li>";
      }
      if (l.indexOf("<li>") === 0) {
        if (!emLista) { saida += "<ul>"; emLista = true; }
        saida += l;
        continue;
      }
      if (emLista) { saida += "</ul>"; emLista = false; }
      saida += l + "<br>";
    }
    if (emLista) saida += "</ul>";
    return saida;
  }

  function criarEditor(cont) {
    var ja = cont.querySelector(".__spj_editor__");
    if (ja) return ja;
    var ta = cont.querySelector("textarea");
    if (!ta) return null;
    var raiz = ta.closest('[data-testid="stTextAreaRootElement"]') || ta.parentNode;
    if (!raiz) return null;
    var servidor = ta.value || "";
    var local = (P.__spjHtml !== undefined && P.__spjHtml !== null) ? P.__spjHtml : "";
    var ed = doc.createElement("div");
    ed.className = "__spj_editor__";
    ed.setAttribute("contenteditable", "true");
    ed.setAttribute("spellcheck", "true");
    ed.setAttribute("lang", "pt-BR");
    ed.setAttribute("role", "textbox");
    ed.setAttribute("aria-multiline", "true");
    ed.setAttribute("aria-label", ALVO);
    ed.innerHTML = mdParaHtml(servidor.trim() ? servidor : local);
    ultimoHtml = ed.innerHTML;
    P.__spjHtml = ultimoHtml;
    raiz.insertBefore(ed, ta);
    cont.classList.add("__spj_com_editor__");
    ed.addEventListener("input", function () { digitar(ed); });
    ed.addEventListener("paste", function () { setTimeout(function () { digitar(ed); }, 30); });
    return ed;
  }

  function digitar(ed) {
    if (!ed) return;
    var html = ed.innerHTML;
    P.__spjHtml = html;
    ultimoHtml = html;
    var ta = caixa();
    if (ta) { setValor(ta, html); }
    salvarLocal(html);
    agendarCommit();
  }

  // se o cursor esta no meio de uma palavra, pega a palavra inteira
  function ampliarPalavra() {
    try {
      var sel = doc.getSelection();
      if (!sel || sel.rangeCount === 0) return;
      var r = sel.getRangeAt(0);
      if (!r.collapsed) return;
      var node = r.startContainer;
      if (node.nodeType !== 3) return;
      var txt = node.textContent || "";
      var ini = r.startOffset, fim = ini;
      while (ini > 0 && !/\s/.test(txt.charAt(ini - 1))) ini--;
      while (fim < txt.length && !/\s/.test(txt.charAt(fim))) fim++;
      if (fim > ini) {
        r.setStart(node, ini);
        r.setEnd(node, fim);
        sel.removeAllRanges();
        sel.addRange(r);
      }
    } catch (e) {}
  }

  function envolverTag(tag) {
    try {
      var sel = doc.getSelection();
      if (!sel || sel.rangeCount === 0) return;
      var r = sel.getRangeAt(0);
      if (r.collapsed) return;
      var el = doc.createElement(tag);
      try { r.surroundContents(el); }
      catch (e) { el.appendChild(r.extractContents()); r.insertNode(el); }
    } catch (e) {}
  }

  function limparFormatacao(ed) {
    try { doc.execCommand("removeFormat"); } catch (e) {}
    try {
      var listas = ed.querySelectorAll("ul,ol");
      for (var i = 0; i < listas.length; i++) {
        var itens = listas[i].querySelectorAll("li");
        var linhas = [];
        for (var j = 0; j < itens.length; j++) {
          linhas.push((listas[i].tagName === "OL" ? (j + 1) + ". " : "- ") + itens[j].textContent);
        }
        var bloco = doc.createElement("div");
        bloco.innerHTML = linhas.join("<br>");
        listas[i].parentNode.replaceChild(bloco, listas[i]);
      }
      var resto = ed.querySelectorAll("b,strong,i,em,u,s,strike,mark,span[style],font");
      for (var k = resto.length - 1; k >= 0; k--) {
        var el = resto[k];
        if (!el.parentNode) continue;
        while (el.firstChild) el.parentNode.insertBefore(el.firstChild, el);
        el.parentNode.removeChild(el);
      }
      var divs = ed.querySelectorAll("div");
      for (var d = divs.length - 1; d >= 0; d--) {
        var dv = divs[d];
        if (dv.parentNode === ed) continue;
        while (dv.firstChild) dv.parentNode.insertBefore(dv.firstChild, dv);
        dv.parentNode.removeChild(dv);
      }
    } catch (e) {}
  }

  function aplicar(b) {
    var ed = editor();
    if (ed) {
      try { ed.focus(); } catch (e) {}
      try {
        if (b.cmd === "undo" || b.cmd === "redo") {
          doc.execCommand(b.cmd);
        } else if (b.limpar) {
          limparFormatacao(ed);
        } else if (b.tag) {
          ampliarPalavra();
          envolverTag(b.tag);
        } else if (b.bloco) {
          doc.execCommand("formatBlock", false, b.bloco);
        } else if (b.cmd) {
          ampliarPalavra();
          doc.execCommand(b.cmd);
        }
      } catch (e) {}
      digitar(ed);
      return;
    }
    // sem editor: usa o modo antigo (marcadores **)
    var cx = caixa();
    if (!cx) return;
    try { cx.focus(); } catch (e) {}
    if (b.cmd === "undo") { try { doc.execCommand("undo"); } catch (e) {} return; }
    if (b.cmd === "redo") { try { doc.execCommand("redo"); } catch (e) {} return; }
    if (b.limpar) { limpar(cx); return; }
    if (b.bloco) { blocoAntigo(cx, b.bloco === "h2" ? "## " : "> "); return; }
    if (b.tag) { envolverAntigo(cx, "==", "=="); return; }
    if (b.cmd === "bold") { envolver(cx, "**", "**"); return; }
    if (b.cmd === "italic") { envolver(cx, "*", "*"); return; }
    if (b.cmd === "underline") { envolver(cx, "__", "__"); return; }
    if (b.cmd === "strikeThrough") { envolver(cx, "~~", "~~"); return; }
    if (b.cmd === "insertUnorderedList") { blocoAntigo(cx, "- "); return; }
    if (b.cmd === "insertOrderedList") { blocoAntigo(cx, "1. "); return; }
  }

  // ---- modo antigo (sem o editor) ----
  function gravar(ta, novo, i, f) {
    setValor(ta, novo);
    try { ta.focus(); ta.setSelectionRange(i, f); } catch (e) {}
    salvarLocal(novo);
  }

  function envolver(ta, a, b) {
    var s = sel(ta);
    var t = s.v.slice(s.i, s.f) || "texto";
    var novo = s.v.slice(0, s.i) + a + t + b + s.v.slice(s.f);
    var p = s.i + a.length + t.length;
    gravar(ta, novo, p, p);
  }

  function envolverAntigo(ta, a, b) { envolver(ta, a, b); }

  function bloco(ta, pref) {
    var s = sel(ta);
    var ini = s.v.lastIndexOf("\n", Math.max(0, s.i - 1)) + 1;
    var fim = s.v.indexOf("\n", s.f);
    if (fim < 0) fim = s.v.length;
    var linhas = s.v.slice(ini, fim).split("\n");
    var novo = linhas.map(function (l) {
      return pref + l.replace(/^\s*(#{1,6}\s+|[-*+]\s+|\d+\.\s+|>\s+)/, "");
    }).join("\n");
    var todo = s.v.slice(0, ini) + novo + s.v.slice(fim);
    gravar(ta, todo, ini, ini + novo.length);
  }

  function blocoAntigo(ta, pref) { bloco(ta, pref); }

  function limpar(ta) {
    var s = sel(ta);
    var t = s.v.slice(s.i, s.f) || s.v;
    var limpo = t.replace(/\*\*|__|~~|==/g, "")
                 .replace(/^\s*(#{1,6}\s+|[-*+]\s+|\d+\.\s+|>\s+)/gm, "");
    var novo = s.v.slice(0, s.i) + limpo + s.v.slice(s.f);
    gravar(ta, novo, s.i, s.i + limpo.length);
  }

  function ligar(btn, b) {
    if (btn.getAttribute("data-spj-ligado") === MEU) return;
    btn.setAttribute("data-spj-ligado", MEU);
    btn.addEventListener("mousedown", function (ev) { ev.preventDefault(); });
    btn.addEventListener("click", function () {
      var agora = new Date().getTime();
      if (doc.__spjAgora && (agora - doc.__spjAgora) < 80) return;
      doc.__spjAgora = agora;
      aplicar(b);
      var cx = caixa();
      if (cx) { ultimo = cx.value; comitar(cx); }
    });
  }

  function montar(cont) {
    if (!cont || cont.querySelector(".__spj_barra__")) return;
    var ta = cont.querySelector("textarea");
    if (!ta) return;
    var barra = doc.createElement("div");
    barra.className = "__spj_barra__";
    BTNS.forEach(function (b) {
      var btn = doc.createElement("button");
      btn.type = "button";
      btn.title = b.t;
      btn.setAttribute("aria-label", b.t);
      btn.innerHTML = b.i;
      ligar(btn, b);
      barra.appendChild(btn);
    });
    var lbl = cont.querySelector("label");
    if (lbl && lbl.parentNode) {
      lbl.parentNode.insertBefore(barra, lbl.nextSibling);
    } else {
      cont.insertBefore(barra, cont.firstChild);
    }
  }

  // ---------------- backup no navegador (o texto nunca se perde) --------
  function salvarLocal(txt) {
    try {
      if (!txt || !txt.trim()) { P.localStorage.removeItem(CHAVE); return; }
      P.localStorage.setItem(CHAVE, JSON.stringify({t: txt, ts: new Date().getTime()}));
    } catch (e) {}
  }

  function lerLocal() {
    try {
      var bruto = P.localStorage.getItem(CHAVE);
      if (!bruto) return null;
      var o = JSON.parse(bruto);
      return (o && o.t) ? o.t : null;
    } catch (e) { return null; }
  }

  P.__spjSalvar = salvarLocal;
  P.__spjLer = lerLocal;
  P.__spjApagar = function () {
    try { P.localStorage.removeItem(CHAVE); } catch (e) {}
  };
  P.__spjAplicar = function (antigo, novo) {
    try {
      var ed = editor();
      if (!ed) return false;
      var partes = ed.innerHTML.split(/(<[^>]+>)/);
      for (var i = 0; i < partes.length; i++) {
        if (partes[i].charAt(0) === "<") continue;
        if (partes[i].indexOf(antigo) >= 0) {
          partes[i] = partes[i].replace(antigo, novo);
          ed.innerHTML = partes.join("");
          digitar(ed);
          return true;
        }
      }
    } catch (e) {}
    return false;
  };

  function aviso(cont, texto) {
    try {
      if (cont.querySelector(".__spj_aviso__")) return;
      var av = doc.createElement("div");
      av.className = "__spj_aviso__";
      av.textContent = texto;
      cont.insertBefore(av, cont.firstChild);
    } catch (e) {}
  }

  function recuperar() {
    if (restaurado) return;
    var cont = achar();
    if (!cont) return;
    var ta = cont.querySelector("textarea");
    if (!ta) return;
    var ed = cont.querySelector(".__spj_editor__");
    var atual = ed ? (ed.innerText || "") : (ta.value || "");
    if (atual && atual.trim()) { restaurado = true; return; }
    var salvo = lerLocal();
    if (!salvo || !salvo.trim()) return;
    restaurado = true;
    if (ed) { ed.innerHTML = salvo; digitar(ed); }
    else { setValor(ta, salvo); }
    ultimo = salvo;
    aviso(cont, "💾 Recuperei o texto que você tinha digitado (ficou salvo no seu navegador).");
    setTimeout(function () { comitar(ta); }, 400);
  }

  function vigiar() {
    var cont = achar();
    if (!cont) return;
    var ta = cont.querySelector("textarea");
    if (!ta) return;
    if (ta.getAttribute("data-spj-vigia") !== MEU) {
      ta.setAttribute("data-spj-vigia", MEU);
      ta.addEventListener("input", function () {
        if (!cont.querySelector(".__spj_editor__")) { salvarLocal(ta.value); }
        agendarCommit();
      });
    }
  }

  // deixa a correcao ortografica do navegador ligada (palavra errada fica
  // sublinhada em vermelho e o botao direito mostra a correcao sugerida)
  function ativarOrtografia() {
    try {
      var todos = doc.querySelectorAll(".stTextArea textarea");
      for (var i = 0; i < todos.length; i++) {
        var ta = todos[i];
        if (ta.getAttribute("data-spj-spell") !== MEU) {
          ta.setAttribute("data-spj-spell", MEU);
          ta.setAttribute("spellcheck", "true");
          ta.setAttribute("lang", "pt-BR");
        }
      }
    } catch (e) {}
  }

  function garantir() {
    try {
      var cont = achar();
      if (!cont) return;
      var barra = cont.querySelector(".__spj_barra__");
      if (!barra) { montar(cont); } else {
        var bts = barra.querySelectorAll("button");
        for (var i = 0; i < bts.length; i++) ligar(bts[i], BTNS[i]);
      }
      var ed = criarEditor(cont);
      vigiar();
      recuperar();
      ativarOrtografia();
      // o servidor mudou o texto? (ex.: transcricao) -> atualiza o editor
      var ta = cont.querySelector("textarea");
      if (ed && ta && ultimoHtml !== null && ta.value !== ultimoHtml) {
        ed.innerHTML = mdParaHtml(ta.value);
        P.__spjHtml = ed.innerHTML;
        ultimoHtml = ed.innerHTML;
        digitar(ed);
      }
    } catch (e) {
      if (window.console) console.error("Barra de formatacao: " + e);
    }
  }

  // manda o texto ao servidor sem tirar o foco: quando o usuario PARA de digitar
  // (2,5 s) ou, no maximo, a cada 15 s. Assim o sistema nao fica "atualizando" sozinho.
  var timerCommit = null;

  function autoComitar(agora) {
    try {
      var ta = caixa();
      if (!ta) return;
      if (ultimo === null) { ultimo = ta.value; return; }
      if (ta.value === ultimo) return;
      if (!agora) return;
      ultimo = ta.value;
      comitar(ta);
    } catch (e) {}
  }

  function agendarCommit() {
    try { if (timerCommit) window.clearTimeout(timerCommit); } catch (e) {}
    timerCommit = window.setTimeout(function () { autoComitar(true); }, 2500);
  }

  garantir();
  setInterval(garantir, 1000);
  setInterval(function () { autoComitar(true); }, 15000);
  try {
    if (window.frameElement) {
      window.frameElement.style.display = "none";
      window.frameElement.style.height = "0px";
    }
  } catch (e) {}
})();
</script>"""


def barra_texto(alvo, chave="spj_relato"):
    """Coloca a barra de formatação (tipo Word) em cima de uma caixa de texto."""
    try:
        html_js = _JS_BARRA.replace("__ALVO__", alvo).replace("__CHAVE__", chave)
        components.html(html_js, height=0)
    except Exception:
        pass


def previa_texto(texto):
    """Mostra o texto com as marcações aplicadas (negrito, itálico, listas...)."""
    bruto = texto or ""
    if "<" in bruto and re.search(r"<\s*[a-zA-Z][^>]*>", bruto):
        # texto veio do editor formatado: mostra do jeito que o usuário digitou
        return motor.html_seguro(bruto)
    t = html.escape(bruto)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t, flags=re.S)
    t = re.sub(r"__(.+?)__", r"<u>\1</u>", t, flags=re.S)
    t = re.sub(r"==(.+?)==", r'<span style="background-color:#FFF59D">\1</span>', t, flags=re.S)
    t = re.sub(r"~~(.+?)~~", r"<s>\1</s>", t, flags=re.S)
    t = re.sub(r"(?<![*\w])\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", t)
    return t


ROTULOS_PARTES = {
    "Requerente / Requerido": ("Requerente", "Requerido"),
    "Autor / Réu (ação criminal)": ("Autor", "Réu"),
    "Recorrente / Recorrido (recurso)": ("Recorrente", "Recorrido"),
    "Embargante / Embargado": ("Embargante", "Embargado"),
}


def _g(chave):
    return str(st.session_state.get(chave, "") or "").strip()


def _dono():
    """Dono dos casos: admin usa a raiz (pega os casos antigos); os demais, a sua pasta."""
    if st.session_state.get("admin"):
        return ""
    return str(st.session_state.get("usuario", "") or "").strip()


def _dados_rascunho():
    """O que fica guardado automaticamente para não perder o trabalho."""
    return {
        "narrativa": st.session_state.get("narrativa", ""),
        "fatos": st.session_state.get("fatos_edit", ""),
        "peca": st.session_state.get("peca_edit", ""),
        "pend": st.session_state.get("pend", ""),
        "dados": st.session_state.get("dados", ""),
        "nome_caso": st.session_state.get("nome_caso", ""),
    }


def _salvar_rascunho(forcar=False):
    """Grava o rascunho agora (usado antes de operações pesadas e a cada execução)."""
    try:
        dados = _dados_rascunho()
        if not forcar and dados == st.session_state.get("_rascunho_ultimo"):
            return
        motor.salvar_rascunho(dados, _dono())
        st.session_state["_rascunho_ultimo"] = dados
    except Exception:
        motor._LOG.warning("Não consegui salvar o rascunho", exc_info=True)


def _recuperar_rascunho():
    """Recupera o rascunho salvo (quando o app fechou ou a sessão caiu)."""
    if st.session_state.get("_rascunho_recuperado"):
        return
    st.session_state["_rascunho_recuperado"] = True
    try:
        r = motor.carregar_rascunho(_dono())
    except Exception:
        return
    if not r:
        return
    achou = False
    for campo, chave in (("narrativa", "narrativa"), ("fatos", "fatos_edit"),
                          ("peca", "peca_edit"), ("pend", "pend")):
        valor = str(r.get(campo) or "")
        if valor.strip() and not st.session_state.get(chave):
            st.session_state[chave] = valor
            achou = True
    if not achou:
        return
    st.session_state["_rascunho_msg"] = (
        f"✅ Recuperei seu rascunho (salvo em {r.get('_salvo_em', 'ontem')}). "
        "Se for de outro trabalho, clique em ➕ **Nova peça** para começar limpo."
    )


_recuperar_rascunho()


def _sync_backup_navegador(texto):
    """Mantem o backup do navegador em dia depois de mexer no texto pelo servidor."""
    try:
        js = ("<script>var t=" + json.dumps(texto or "") + ";"
              "function f(){try{if(window.parent.__spjSalvar){window.parent.__spjSalvar(t);}}catch(e){}}"
              "f();setTimeout(f,700);setTimeout(f,1800);</script>")
        components.html(js, height=0)
    except Exception:
        pass


def _aplicar_correcao_pendente():
    """Aplica a correcao de escrita escolhida pelo usuario (antes de desenhar o campo)."""
    pend = st.session_state.pop("_corr_pendente", None)
    if not pend:
        return
    errado, certo = pend
    texto = st.session_state.get("narrativa", "") or ""
    novo = motor.substituir_em_html(texto, errado, certo)
    if novo is None:
        novo = motor.aplicar_correcao(texto, errado, certo)
    if novo is None:
        return
    st.session_state["narrativa"] = novo
    _salvar_rascunho(forcar=True)
    st.session_state["_corr_msg"] = f"✅ Corrigido: “{errado}” → “{certo}”"
    _sync_backup_navegador(novo)


def _memorizar(mem_key, valor):
    valor = str(valor or "").strip()
    if not valor:
        return
    lista = st.session_state.setdefault(mem_key, [])
    if valor not in lista:
        lista.append(valor)
        st.session_state[mem_key] = lista[-50:]


def _memoria_select(label, mem_key, alvo_key):
    alvo = _g(alvo_key)
    opcoes = [m for m in st.session_state.get(mem_key, []) if m != alvo]
    if not opcoes:
        return
    sel = st.selectbox(f"↩ {label}", ["—"] + opcoes, key=f"sel_{alvo_key}")
    if sel and sel != "—":
        st.session_state[alvo_key] = sel
        st.rerun()


def complementos_cidade(prefixo):
    """Cidade (pesquisável por iniciais) e UF (pesquisável), com opção de digitar outra cidade."""
    c5, c6 = st.columns([3, 1])
    uf = st.session_state.get(f"{prefixo}_uf", "—")
    lista = MUNICIPIOS.get(SIGLA_UF.get(uf, ""), []) if uf != "—" else []
    opcoes = ["—"] + lista + (["✏️ outra (digitar)"] if uf != "—" else [])
    c5.selectbox("Cidade", opcoes, key=f"{prefixo}_cidade")
    c6.selectbox("UF", OPCOES_UF, key=f"{prefixo}_uf")
    if st.session_state.get(f"{prefixo}_cidade", "") == "✏️ outra (digitar)":
        st.text_input("Digite a cidade", key=f"{prefixo}_cidade_livre", placeholder="Nome da cidade")


def _endereco_resumo(prefixo):
    partes = []
    rua = _g(f"{prefixo}_rua")
    num = _g(f"{prefixo}_num")
    if rua:
        partes.append(rua + (f", {num}" if num else ""))
    bairro = _g(f"{prefixo}_bairro")
    if bairro:
        partes.append(f"bairro {bairro}")
    cidade = _g(f"{prefixo}_cidade")
    if cidade == "✏️ outra (digitar)":
        cidade = _g(f"{prefixo}_cidade_livre") or cidade
    if cidade and cidade != "✏️ outra (digitar)":
        uf = SIGLA_UF.get(_g(f"{prefixo}_uf"), _g(f"{prefixo}_uf"))
        partes.append(cidade + (f" – {uf}" if uf else ""))
    cep = _g(f"{prefixo}_cep")
    if cep:
        partes.append(f"CEP {cep}")
    if _g(f"{prefixo}_compl"):
        partes.append(_g(f"{prefixo}_compl"))
    return ", ".join(partes)


def _qualificacao(nome, civil, prof, docs, endr):
    itens = []
    if nome:
        itens.append(f"nome: {nome}")
    if civil:
        itens.append(f"estado civil: {civil}")
    if prof:
        itens.append(f"profissão: {prof}")
    for d in (docs or []):
        itens.append(d)
    if endr:
        itens.append(f"endereço: {endr}")
    return "; ".join(itens)


def _documentos(prefixo):
    """Documentos separados (CPF, CNPJ, RG) de uma parte."""
    docs = []
    cpf = _g(f"{prefixo}_cpf")
    if cpf:
        docs.append(f"CPF: {cpf}")
    cnpj = _g(f"{prefixo}_cnpj")
    if cnpj:
        docs.append(f"CNPJ: {cnpj}")
    rg = _g(f"{prefixo}_rg")
    if rg:
        docs.append(f"RG: {rg}")
    return docs


def _doc_do_caso(caso, prefixo):
    """Lê os documentos do caso salvo, migrando o antigo campo único (doc)."""
    cpf = caso.get(f"{prefixo}_cpf", "")
    cnpj = caso.get(f"{prefixo}_cnpj", "")
    rg = caso.get(f"{prefixo}_rg", "")
    antigo = str(caso.get(f"{prefixo}_doc", "") or "").strip()
    if not (cpf or cnpj or rg) and antigo:
        if "/" in antigo:
            cnpj = antigo
        else:
            cpf = antigo
    return cpf, cnpj, rg


def _cadastro_parte(prefixo, rotulo):
    """Painel 'cadastro' de uma parte, com endereço em campos com memória."""
    with st.expander(f"📋 {rotulo} (cadastro)"):
        st.text_input("Nome completo", key=f"{prefixo}_nome", placeholder="Nome e sobrenome")
        c1, c2 = st.columns(2)
        c1.text_input("Estado civil", key=f"{prefixo}_civil", placeholder="ex.: casado(a)")
        c2.text_input("Profissão", key=f"{prefixo}_prof", placeholder="ex.: vendedor(a)")
        d1, d2, d3 = st.columns(3)
        d1.text_input("CPF", key=f"{prefixo}_cpf", placeholder="000.000.000-00")
        d2.text_input("CNPJ", key=f"{prefixo}_cnpj", placeholder="00.000.000/0001-00")
        d3.text_input("RG", key=f"{prefixo}_rg", placeholder="nº ...")
        st.markdown("**Endereço**")
        l1, l2 = st.columns([3, 1])
        l1.text_input("Rua", key=f"{prefixo}_rua", placeholder="Av. ...")
        l2.text_input("Número", key=f"{prefixo}_num", placeholder="123")
        _memorizar("mem_ruas", st.session_state.get(f"{prefixo}_rua", ""))
        _memoria_select("rua já usada", "mem_ruas", f"{prefixo}_rua")
        l3, l4 = st.columns([3, 1])
        l3.text_input("Bairro", key=f"{prefixo}_bairro", placeholder="Centro")
        l4.text_input("CEP", key=f"{prefixo}_cep", placeholder="00000-000")
        _memorizar("mem_bairros", st.session_state.get(f"{prefixo}_bairro", ""))
        _memoria_select("bairro já usado", "mem_bairros", f"{prefixo}_bairro")
        _memorizar("mem_ceps", st.session_state.get(f"{prefixo}_cep", ""))
        _memoria_select("CEP já usado", "mem_ceps", f"{prefixo}_cep")
        complementos_cidade(prefixo)
        st.text_input("Complemento (apto/bloco, e-mail...)", key=f"{prefixo}_compl")


def compor_dados():
    """Junta os campos do cabeçalho da peça num único bloco enviado à IA."""
    r1, r2 = ROTULOS_PARTES.get(st.session_state.get("f_rotulo", "Requerente / Requerido"),
                                ("Requerente", "Requerido"))
    partes = []
    if _g("f_juizo"):
        partes.append(f"Juízo/Vara: {_g('f_juizo')}")
    endr1 = _endereco_resumo("req")
    q1 = _qualificacao(_g("req_nome"), _g("req_civil"), _g("req_prof"), _documentos("req"), endr1)
    if q1:
        partes.append(f"{r1}: {q1}")
    endr2 = _endereco_resumo("rdo")
    q2 = _qualificacao(_g("rdo_nome"), _g("rdo_civil"), _g("rdo_prof"), _documentos("rdo"), endr2)
    if q2:
        partes.append(f"{r2}: {q2}")
    if _g("f_outros"):
        partes.append(f"Demais dados: {_g('f_outros')}")
    return "\n".join(partes)


def tentar(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        motor._LOG.exception("Erro na operação")
        st.error(motor.mensagem_amigavel(e))
        return None


def _reseta_formulario():
    """Limpa o caso em edição, mantendo as memórias de endereço."""
    for chave, inicial in DEFAULTS.items():
        if str(chave).startswith("mem_"):
            continue
        st.session_state[chave] = inicial.copy() if isinstance(inicial, list) else inicial
    for k in [k for k in st.session_state if str(k).startswith(("resp_", "sel_"))]:
        del st.session_state[k]
    for k in ("export_docx", "export_pdf"):
        st.session_state.pop(k, None)


def iniciar_limpo(nome):
    """Começa uma peça nova, zerando o formulário e fixando o nome do caso."""
    _reseta_formulario()
    st.session_state["nome_caso"] = nome
    st.session_state["dados"] = compor_dados()
    # o rascunho é do trabalho anterior: some para não voltar na próxima abertura
    try:
        motor.apagar_rascunho(_dono())
    except Exception:
        pass
    st.session_state["_rascunho_ultimo"] = None
    st.session_state.pop("_rascunho_msg", None)


def _dados_caso():
    """Monta o dicionário completo do caso para salvar."""
    return {
        "dados": compor_dados(),
        "f_juizo": st.session_state.get("f_juizo", ""),
        "f_outros": st.session_state.get("f_outros", ""),
        "f_rotulo": st.session_state.get("f_rotulo", "Requerente / Requerido"),
        "req_nome": st.session_state.get("req_nome", ""), "req_civil": st.session_state.get("req_civil", ""),
        "req_prof": st.session_state.get("req_prof", ""),
        "req_cpf": st.session_state.get("req_cpf", ""), "req_cnpj": st.session_state.get("req_cnpj", ""),
        "req_rg": st.session_state.get("req_rg", ""),
        **{f"req_{c}": st.session_state.get(f"req_{c}", "") for c in CAMPOS_ENDERECO},
        "rdo_nome": st.session_state.get("rdo_nome", ""), "rdo_civil": st.session_state.get("rdo_civil", ""),
        "rdo_prof": st.session_state.get("rdo_prof", ""),
        "rdo_cpf": st.session_state.get("rdo_cpf", ""), "rdo_cnpj": st.session_state.get("rdo_cnpj", ""),
        "rdo_rg": st.session_state.get("rdo_rg", ""),
        **{f"rdo_{c}": st.session_state.get(f"rdo_{c}", "") for c in CAMPOS_ENDERECO},
        "narrativa": st.session_state["narrativa"],
        "fatos": st.session_state["fatos_edit"], "peca": st.session_state["peca_edit"],
        "pend": st.session_state["pend"], "alertas": st.session_state["alertas"],
        "usadas": st.session_state["usadas"],
        "base_nome": st.session_state.get("base_nome", ""),
    }


def _salvar_automatico():
    nome = st.session_state.get("nome_caso", "").strip()
    if not nome:
        st.info("Para salvar sozinho(a), dê um nome à peça em ➕ **Nova peça** (lateral).")
        return
    try:
        caminho = motor.salvar_caso(nome, _dados_caso(), _dono())
        st.success(f"✅ Peça salva automaticamente em: **{caminho.stem}**")
    except Exception as e:
        st.error(f"Não consegui salvar automaticamente: {e}")


def _backup_status():
    try:
        import nuvem
        return nuvem.status()
    except Exception:
        return {"ativo": False}


def _backup_testar():
    try:
        import nuvem
        return nuvem.testar()
    except Exception as e:
        return False, f"Backup indisponível: {e}"


st.title("⚖️ Sistema de Peças Judiciais")
st.caption("A IA só cita o que está na BASE LEGAL. Confira sempre os alertas antes de protocolar.")

if motor.modo_uso()["uso_pago"]:
    st.success("🔒 Conta declarada como **paga/Vertex**: o provedor não usa seus dados para treinar modelos.", icon="🔒")
else:
    st.warning(
        "⚠️ **Modo gratuito**: a cota grátis do Gemini PODE usar seus dados para treinamento e ser lida por "
        "revisores humanos. Para dados reais de cliente, mantenha o **Modo seguro** ligado (lateral) e/ou "
        "ative faturamento ou use Vertex AI nas **Configurações**."
    )

# ------------------------------------------------------------------ barra lateral
with st.sidebar:
    st.markdown(
        "<div style='text-align:center; font-size:34px; line-height:1; margin-bottom:4px;'>⚖️</div>",
        unsafe_allow_html=True,
    )
    st.caption(f"Sessão: {st.session_state.get('usuario', 'advogado(a)')}")
    if st.button("🚪 Sair do sistema", width="stretch"):
        st.session_state["autenticado"] = False
        st.session_state["chat_hist"] = []
        st.session_state["_cookie_apagar"] = True
        st.rerun()
    st.divider()

    if st.session_state.get("admin"):
        try:
            pendentes = usuarios.listar_pendentes()
            ativos = usuarios.listar_ativos()
        except Exception:
            pendentes, ativos = [], []
        titulo = f"Contas — {len(pendentes)} pendente(s)" if pendentes else "Contas"
        with st.expander(titulo, icon=":material/group:"):
            if pendentes:
                for u in pendentes:
                    st.markdown(f"**{u.get('usuario', '')}**  \n{u.get('nome', '') or '—'}")
                    b1, b2 = st.columns(2)
                    if b1.button("✅ Aprovar", key=f"aprov_{u.get('usuario')}", width="stretch"):
                        usuarios.aprovar(u.get("usuario"))
                        st.rerun()
                    if b2.button("🗑️ Recusar", key=f"recus_{u.get('usuario')}", width="stretch"):
                        usuarios.remover(u.get("usuario"))
                        st.rerun()
            else:
                st.caption("Nenhuma conta aguardando aprovação.")
            if ativos:
                st.divider()
                st.caption("Contas ativas:")
                for u in ativos:
                    st.write(f"• {u.get('usuario', '')}")
                st.divider()
                st.caption("🔑 Redefinir a senha de um usuário:")
                alvo = st.selectbox("Usuário", ["—"] + [u.get("usuario", "") for u in ativos],
                                    key="reset_usuario")
                with st.form("form_reset_senha"):
                    nova = st.text_input("Nova senha (mínimo 6 caracteres)", type="password",
                                         key="reset_nova")
                    if st.form_submit_button("Redefinir senha"):
                        if alvo == "—":
                            st.warning("Escolha o usuário.")
                        else:
                            try:
                                usuarios.redefinir_senha(alvo, nova)
                                st.success(f"Senha de **{alvo}** redefinida.")
                            except ValueError as e:
                                st.error(str(e))
                            except Exception as e:
                                st.error(f"Não foi possível redefinir: {e}")
        st.divider()

    st.header("📁 Casos salvos")
    casos = motor.listar_casos(_dono())
    if casos:
        escolhido = st.selectbox("Abrir caso", ["—"] + casos, key="caso_escolhido")
        c1, c2 = st.columns(2)
        if c1.button("Abrir", width="stretch") and escolhido != "—":
            caso = motor.carregar_caso(escolhido, _dono())
            _cpf1, _cnpj1, _rg1 = _doc_do_caso(caso, "req")
            _cpf2, _cnpj2, _rg2 = _doc_do_caso(caso, "rdo")
            st.session_state.update(
                f_rotulo=caso.get("f_rotulo", "Requerente / Requerido"),
                f_juizo=caso.get("f_juizo", ""),
                f_outros=caso.get("f_outros", caso.get("dados", "")),
                req_nome=caso.get("req_nome") or caso.get("f_autor", ""),
                req_civil=caso.get("req_civil", ""), req_prof=caso.get("req_prof", ""),
                req_cpf=_cpf1, req_cnpj=_cnpj1, req_rg=_rg1,
                **{f"req_{c}": caso.get(f"req_{c}", "") for c in CAMPOS_ENDERECO},
                req_compl=caso.get("req_compl") or caso.get("req_endr", ""),
                rdo_nome=caso.get("rdo_nome") or caso.get("f_reu", ""),
                rdo_civil=caso.get("rdo_civil", ""), rdo_prof=caso.get("rdo_prof", ""),
                rdo_cpf=_cpf2, rdo_cnpj=_cnpj2, rdo_rg=_rg2,
                **{f"rdo_{c}": caso.get(f"rdo_{c}", "") for c in CAMPOS_ENDERECO},
                rdo_compl=caso.get("rdo_compl") or caso.get("rdo_endr", ""),
                narrativa=caso.get("narrativa", ""),
                fatos_edit=caso.get("fatos", ""), peca_edit=caso.get("peca") or "",
                pend=caso.get("pend", ""), alertas=caso.get("alertas", []), usadas=caso.get("usadas", []),
            )
            st.session_state["dados"] = compor_dados()
            base_salva = caso.get("base_nome", "")
            if base_salva and base_salva in motor.listar_bases():
                st.session_state["base_nome"] = base_salva
                st.session_state["base_editor_nome"] = base_salva
            st.rerun()
        if c2.button("Apagar", width="stretch") and escolhido != "—":
            motor.apagar_caso(escolhido, _dono())
            st.rerun()
    else:
        st.caption("Nenhum caso salvo ainda.")

    st.divider()
    st.subheader("➕ Nova peça")
    nova_peca_nome = st.text_input("Nome da nova peça", key="nova_peca_nome",
                                   placeholder="ex.: Voo FTL→SP – M. Souza")
    if st.button("Começar nova peça", width="stretch"):
        nome = (nova_peca_nome or "").strip()
        if not nome:
            st.warning("Dê um nome para a nova peça.")
        else:
            caminho = motor.salvar_caso(nome, {}, _dono())
            iniciar_limpo(caminho.stem)
            base_novo = caminho.stem
            if base_novo not in motor.listar_bases():
                motor.salvar_base(base_novo, [])
            st.session_state["base_nome"] = base_novo
            st.session_state["base_editor_nome"] = base_novo
            st.rerun()

    st.divider()
    st.subheader("📝 Gerar peça")
    modelo_nome = st.selectbox("Modelo da peça", motor.listar_modelos(), key="modelo_nome",
                               placeholder="Escolha o modelo da peça")
    st.caption("Sugerido conforme os fatos; você pode trocar.")
    base_nome = st.selectbox("Base legal", motor.listar_bases(), key="base_nome",
                              placeholder="Escolha a base legal")
    with st.expander("Ver a base legal carregada"):
        for item in motor.carregar_base(base_nome):
            st.markdown(f"**{item['referencia']}** — status: `{item['status']}`")
            st.write(item["texto"])
    if st.button("📝 Gerar a peça", type="primary", width="stretch"):
        fatos = st.session_state["fatos_edit"]
        if not fatos.strip():
            st.warning("Não há fatos ainda. Preencha o relato e use 'Limpar fatos' na aba 2️⃣.")
        else:
            st.session_state.update(peca_edit="", alertas=[], usadas=[])
            st.session_state.pop("export_docx", None)
            st.session_state.pop("export_pdf", None)
            base = motor.carregar_base(base_nome)
            with st.status("Redigindo a peça...", expanded=False) as s:
                bruto = tentar(motor.gerar_peca, motor.carregar_modelo(modelo_nome),
                               st.session_state["dados"], fatos, base, anonimizador)
                if bruto:
                    conf = motor.conferir_citacoes(bruto, base, f"{st.session_state['dados']}\n{fatos}")
                    st.session_state.update(peca_edit=conf["texto"], alertas=conf["alertas"], usadas=conf["usadas"])
                    s.update(label="Peça gerada e conferida", state="complete")
                else:
                    s.update(label="Falha ao gerar", state="error")

    st.divider()
    nome_caso = st.text_input("Nome do caso (para salvar)", key="nome_caso")
    if st.button("💾 Salvar caso atual", width="stretch"):
        if not nome_caso.strip():
            st.warning("Dê um nome antes de salvar.")
        else:
            caminho = motor.salvar_caso(nome_caso, _dados_caso(), _dono())
            st.success(f"Salvo: {caminho.stem}")

    st.divider()
    st.subheader("🛡️ Segurança (LGPD)")
    st.checkbox("Modo seguro: anonimizar antes de enviar", value=True, key="modo_seguro",
                help="Troca nomes, CPF, e-mails etc. por marcadores antes de enviar à IA e restaura na peça final.")

    st.divider()
    with st.expander("⚙️ Configurações do provedor"):
        _m = motor.modo_uso()
        pago = st.selectbox("A conta Google tem faturamento (pago)?", ["não", "sim"],
                            index=1 if _m["uso_pago"] else 0, key="cfg_pago",
                            placeholder="Escolha uma opção")
        chave_modo = st.selectbox("Modo da chave", ["gemini", "vertex"],
                                  index=0 if _m["modo_chave"] == "gemini" else 1, key="cfg_modo",
                                  placeholder="Escolha uma opção")
        regiao = st.text_input("Região (Vertex AI)", value=_m["regiao"],
                               placeholder="ex.: southamerica-east1", key="cfg_regiao")
        modelo_edit = st.text_input("Modelo", value=_m["modelo"], key="cfg_modelo")
        if st.button("💾 Salvar configurações"):
            motor.atualizar_env({
                "USO_PAGO": "sim" if pago == "sim" else "nao",
                "MODO_CHAVE": chave_modo,
                "REGIAO": regiao.strip(),
                "MODELO": modelo_edit.strip(),
            })
            st.success("Configurações salvas no .env.")
            st.rerun()

    with st.expander("☁️ Backup na nuvem (nuvem → seu PC)"):
        _bk = _backup_status()
        if _bk.get("ativo"):
            _prov = _bk.get("provedor") or "nuvem"
            _extra = f" Repositório: **{_bk['repo']}**." if _bk.get("repo") else ""
            st.success(f"Backup ATIVADO via **{_prov}**. Cada caso/peça/base salvo(a) vai para a nuvem "
                       "e chega automaticamente ao seu PC (no GitHub, a cada ~5 min)."
                       + _extra)
            if st.button("🔌 Testar backup agora"):
                ok, msg = _backup_testar()
                (st.success if ok else st.error)(msg)
        else:
            st.info("Backup DESATIVADO. Recomendado: **GITHUB_BACKUP_TOKEN** + **GITHUB_BACKUP_REPO** "
                    "(token que não expira). Alternativa: **GOOGLE_CLIENT_ID**, **GOOGLE_CLIENT_SECRET** e "
                    "**GOOGLE_REFRESH_TOKEN**. Configure nos *Secrets* (nuvem) ou no `.env` (PC). "
                    "O passo a passo está no arquivo LEIA-ME.")

    with st.expander("🗝️ Trocar usuário / senha"):
        st.caption("O acesso fica gravado no .env (senha com hash; vale também para a nuvem).")
        novo_usuario = st.text_input("Usuário", value=st.session_state.get("usuario", ""),
                                     key="acesso_usuario")
        nova1 = st.text_input("Nova senha", type="password", key="senha_nova1")
        nova2 = st.text_input("Repita a nova senha", type="password", key="senha_nova2")
        if st.button("Salvar acesso"):
            if not novo_usuario.strip():
                st.error("Informe o usuário.")
            elif not nova1 or nova1 != nova2:
                st.error("As senhas não conferem.")
            else:
                try:
                    motor.definir_acesso(novo_usuario, nova1)
                    st.session_state["usuario"] = novo_usuario.strip()
                    st.success("Acesso atualizado no .env.")
                except Exception as e:
                    st.error(str(e))

    st.divider()
    _m = motor.modo_uso()
    _extra = f" · Região: **{_m['regiao']}**" if _m["regiao"] else ""
    st.caption(f"Provedor: **{_m['provedor']}** · Modelo: **{_m['modelo'] or '(definir no .env)'}**{_extra}")


anonimizador = None
if st.session_state.get("modo_seguro", True):
    anonimizador = motor.Anonimizador([])


# ------------------------------------------------------------------ componentes
def aba_base():
    st.subheader("🗂️ Curadoria da base legal")
    st.caption("Só o que estiver aqui pode ser citado. Mantenha o status em 'verificado' após conferir o texto oficial.")
    bases = motor.listar_bases()
    if not bases:
        st.info("Nenhuma base encontrada.")
        return
    base_nome = st.selectbox("Base", bases, key="base_editor_nome")
    itens = motor.carregar_base(base_nome)
    df = pd.DataFrame(itens or [{"id": "", "referencia": "", "status": "conferir", "texto": "", "fonte": ""}])
    df.insert(0, "apagar", False)
    st.caption("Para tirar um item que você não quer mais: marque a caixa **🗑️ apagar** e clique em "
               "**🗑️ Apagar marcados**. Você também pode adicionar novas linhas ao fim da tabela.")
    editado = st.data_editor(
        df, num_rows="dynamic", width="stretch", hide_index=True,
        column_config={
            "apagar": st.column_config.CheckboxColumn("🗑️ apagar", default=False, width="small"),
            "status": st.column_config.SelectboxColumn("status", options=list(motor.STATUS_VALIDOS), required=True),
            "texto": st.column_config.TextColumn("texto", width="large"),
            "fonte": st.column_config.LinkColumn("fonte"),
        },
    )
    conteudo = editado.fillna("").to_dict("records")
    marcados = [bool(r.get("apagar")) for r in conteudo]
    for r in conteudo:
        r.pop("apagar", None)
    restantes = [r for r, ap in zip(conteudo, marcados) if not ap]

    def _ids_ok(recs):
        ids = [str(r.get("id", "")).strip() for r in recs if str(r.get("id", "")).strip()]
        if len(ids) != len(set(ids)):
            st.error("Há IDs repetidos na base. Cada item precisa de um ID único.")
            return False
        if not ids:
            st.error("A base precisa de pelo menos um item com ID.")
            return False
        return True

    c1, c2, c3 = st.columns([1, 1, 2])
    if c1.button("💾 Salvar base", type="primary"):
        if _ids_ok(restantes) and tentar(motor.salvar_base, base_nome, restantes) is not None:
            st.success("Base salva.")
    if c2.button("🗑️ Apagar marcados"):
        if not any(marcados):
            st.info("Marque ao menos um item na coluna **🗑️ apagar** para apagar.")
        elif tentar(motor.salvar_base, base_nome, restantes) is not None:
            st.success(f"{sum(marcados)} item(ns) apagado(s).")
            st.rerun()
    with c3.expander("Mais opções"):
        nova = st.text_input("Criar nova base (nome sem espaços)", key="nova_base")
        if st.button("Criar base vazia"):
            if tentar(motor.salvar_base, nova, []) is not None:
                st.success(f"Base '{nova}' criada.")
                st.rerun()
        st.divider()
        st.caption(f"Apagar a base **{base_nome}** inteira. Esta ação não volta.")
        conf_base = st.checkbox(f"Confirmo apagar '{base_nome}'", key="conf_apagar_base")
        if st.button("🗑️ Apagar base inteira", disabled=not conf_base):
            if tentar(motor.apagar_base, base_nome) is not None:
                st.success(f"Base '{base_nome}' apagada.")
                st.rerun()


def aba_conferencia():
    st.subheader("🔎 Conferência automática (anti-invenção)")
    if not st.session_state["alertas"]:
        st.info("Gere uma peça para rodar a conferência.")
        return
    erros = sum(1 for n, _ in st.session_state["alertas"] if n == "erro")
    c1, c2 = st.columns(2)
    c1.metric("Erros graves", erros)
    c2.metric("Alertas a revisar", sum(1 for n, _ in st.session_state["alertas"] if n == "aviso"))
    for n, m in st.session_state["alertas"]:
        alerta(n, m)
    if erros:
        st.error("Corrija os erros graves antes de protocolar: a IA citou algo que não existe na base.")
    elif any(n == "aviso" for n, _ in st.session_state["alertas"]):
        st.warning("Há pontos a revisar manualmente.")
    else:
        st.success("Passou na conferência automática. Ainda assim, revise.")

    st.write("**Fontes usadas:**")
    for i in st.session_state["usadas"]:
        st.write(f"- {i['referencia']} — `{i['status']}` — {i.get('fonte', '')}")


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def _stj_acordaos(datasets, limite):
    return decisoes.acordaos_recentes(list(datasets), limite)


@st.cache_data(ttl=1 * 3600, show_spinner=False)
def _datajud_consultar(alias, numero):
    return decisoes.consultar_processo(alias, numero)


@st.cache_data(ttl=1 * 3600, show_spinner=False)
def _comunicacoes_processo(alias, numero):
    """Comunicações (Diário/intimações) do processo; tolera `decisoes` antigo."""
    fn = getattr(decisoes, "comunicacoes_processo", None)
    return fn(alias, numero) if fn else None


def aba_decisoes():
    st.subheader("📰 Decisões & Processos")
    st.caption(
        "Pesquisa de jurisprudência nas **fontes oficiais** (STJ, STF, TST, TJs...) e atalhos. "
        "O sistema só reúne e organiza — confira sempre no site oficial antes de citar."
    )
    t_stj, t_links = st.tabs(
        ["🔎 Pesquisar jurisprudência", "🔗 Atalhos oficiais"]
    )

    with t_stj:
        st.caption("Escolha **onde pesquisar** e, se quiser, os **termos** do caso. O botão abre a "
                   "pesquisa **oficial** de jurisprudência no site do órgão escolhido.")
        fonte = st.selectbox("Onde pesquisar", decisoes.FONTES_JURIS, key="jur_fonte")
        termo_jur = st.text_input("Termos da pesquisa (opcional)", key="jur_termo",
                                  placeholder="ex.: responsabilidade civil, dano moral, nexo causal")
        colegiado = ""
        if fonte.upper().startswith("STJ"):
            sel_col = st.selectbox("Colegiado (STJ)", ["Todos os órgãos"] + list(decisoes.STJ_COLEGIADOS),
                                   key="jur_colegiado")
            colegiado = "" if sel_col == "Todos os órgãos" else sel_col
        st.link_button("🔎 Abrir busca de jurisprudência",
                       decisoes.link_juris(fonte, termo_jur, colegiado))
        st.caption("A busca abre no site oficial do órgão. Confira sempre o inteiro teor antes de citar.")

        with st.expander("Ver também: acórdãos recentes (Portal de Dados Abertos do STJ)"):
            st.caption("Baixa o arquivo mais recente de cada órgão e mostra as decisões mais novas. "
                       "Mais órgãos = mais demorado (na primeira vez).")
            rotulos = [r for r, _ in decisoes.ORGAOS_STJ]
            sel = st.multiselect("Órgãos do STJ", rotulos,
                                 default=["Corte Especial", "1ª Seção", "2ª Seção", "3ª Seção"],
                                 key="stj_orgaos")
            c1, c2 = st.columns([1, 2])
            limite = c1.selectbox("Quantas decisões", [30, 60, 100, 200], index=1, key="stj_limite")
            filtro = c2.text_input("Filtrar (palavra na ementa, nº do processo, relator)", key="stj_filtro")
            if st.button("🔄 Buscar acórdãos recentes", type="primary"):
                mapa = dict(decisoes.ORGAOS_STJ)
                datasets = tuple(mapa[r] for r in sel)
                if not datasets:
                    st.warning("Escolha ao menos um órgão.")
                else:
                    with st.status("Baixando acórdãos do STJ...", expanded=False) as s:
                        lista, erros = _stj_acordaos(datasets, limite)
                        s.update(label=f"{len(lista)} acórdão(ões) carregado(s)",
                                 state="complete" if lista else "error")
                    st.session_state["stj_lista"] = lista
                    st.session_state["stj_erros"] = erros
            for e in st.session_state.get("stj_erros", []):
                st.warning(f"Não consegui ler um conjunto: {e}")
            lista = st.session_state.get("stj_lista") or []
            if not lista:
                st.info("Clique em **🔄 Buscar acórdãos recentes** para carregar as decisões.")
            else:
                termo = (filtro or "").strip().lower()
                mostrados = 0
                for a in lista:
                    alvo = (f"{a['processo']} {a['relator']} {a['orgao']} {a['classe']} "
                            f"{a['ementa']} {a['tese']} {a['tema']}").lower()
                    if termo and termo not in alvo:
                        continue
                    mostrados += 1
                    titulo = f"{a['data'] or '—'} · {a['orgao']} · {a['processo']} — {a['classe']}"
                    with st.expander(titulo):
                        st.markdown(f"**Relator(a):** {a['relator'] or '—'}")
                        if a["tema"]:
                            st.markdown(f"**Tema / repetitivo:** {a['tema']}")
                        if a["tese"]:
                            st.markdown(f"**Tese firmada:** {a['tese']}")
                        st.markdown("**Ementa:**")
                        st.write(a["ementa"] or "(sem ementa)")
                        if a["processo"]:
                            st.link_button(
                                "Ver o processo no STJ",
                                f"https://processo.stj.jus.br/processo/pesquisa/?termo={a['processo']}",
                            )
                if mostrados == 0:
                    st.info("Nenhuma decisão casou com o filtro.")

    with t_links:
        st.markdown("### 📚 Buscar legislação")
        st.caption("Digite o assunto, o nome do código ou a lei (ex.: civil, penal, trabalho, "
                   "consumidor, licitação, improbidade...). O botão abre o **texto oficial** no Planalto.")
        termo_lei = st.text_input("Pesquisar lei, código ou assunto", key="lei_busca",
                                  placeholder="ex.: código civil · penal · CLT · consumidor · tributário")
        achados = decisoes.buscar_legislacao(termo_lei)
        if not achados:
            st.info("Nada encontrado. Tente outra palavra (ex.: 'civil', 'penal', 'trabalho', 'tributário').")
        else:
            st.markdown(_CSS_LEIS, unsafe_allow_html=True)
            itens = "".join(
                f'<a href="{item["url"]}" target="_blank" rel="noopener">'
                f'{html.escape(item["nome"])}</a>'
                for item in achados
            )
            st.markdown(f'<div class="lei-grid">{itens}</div>', unsafe_allow_html=True)

        st.divider()
        st.markdown("### 🔗 Atalhos oficiais dos tribunais")
        st.caption("Não existe um feed automático oficial para todos os tribunais. Estes atalhos abrem "
                   "a busca no site do próprio órgão, que é o repositório oficial da jurisprudência.")
        for grupo, itens in decisoes.ATALHOS:
            st.markdown(f"**{grupo}**")
            colunas = st.columns(2)
            for j, (titulo, url) in enumerate(itens):
                colunas[j % 2].link_button(titulo, url, width="stretch")


def aba_processos():
    st.subheader("📌 Acompanhar processo")
    st.caption("Consulta, pelo número único, os dados e as **movimentações** de um processo. "
               "São metadados oficiais do DataJud — o texto da decisão você lê no site do tribunal.")
    c1, c2 = st.columns(2)
    ramos = list(decisoes.DATAJUD_RAMOS)
    ramo = c1.selectbox("Ramo", ramos, index=ramos.index("Justiça Estadual"), key="dj_ramo")
    opcoes = decisoes.DATAJUD_RAMOS[ramo]
    preferido = {"Justiça Federal": "api_publica_trf5",
                 "Justiça do Trabalho": "api_publica_trt7",
                 "Justiça Eleitoral": "api_publica_tre-ce",
                 "Justiça Estadual": "api_publica_tjce"}.get(ramo)
    idx = next((j for j, (_, a) in enumerate(opcoes) if a == preferido), 0)
    tribunal_rot = c2.selectbox("Tribunal", [r for r, _ in opcoes], index=idx, key="dj_tribunal")
    alias = dict(opcoes)[tribunal_rot]
    modo = st.radio("Buscar por",
                    ["Número do processo", "Nome da parte (no site do tribunal)"],
                    horizontal=True, key="dj_modo")
    if modo.startswith("Número"):
        numero = st.text_input("Número do processo",
                               key=f"dj_numero_{st.session_state.get('dj_versao', 0)}",
                               placeholder="ex.: 3000867-89.2026.8.06.0000")
        b1, b2 = st.columns([2, 1])
        consultar = b1.button("🔍 Consultar processo", type="primary")
        if b2.button("🧹 Limpar / nova consulta"):
            st.session_state["dj_versao"] = st.session_state.get("dj_versao", 0) + 1
            st.session_state.pop("dj_procs", None)
            st.session_state.pop("dj_erro", None)
            st.session_state.pop("dj_nome_busca", None)
            st.rerun()
            st.rerun()
        if consultar:
            if not numero.strip():
                st.warning("Digite o número do processo.")
            else:
                try:
                    with st.status("Consultando o DataJud...", expanded=False) as s:
                        procs = _datajud_consultar(alias, numero)
                        s.update(label=f"{len(procs)} processo(s) encontrado(s)",
                                 state="complete" if procs else "error")
                    st.session_state["dj_procs"] = procs
                    st.session_state["dj_erro"] = ""
                except Exception as e:
                    st.session_state["dj_procs"] = []
                    st.session_state["dj_erro"] = str(e)
        if st.session_state.get("dj_erro"):
            st.error(st.session_state["dj_erro"])
        procs = st.session_state.get("dj_procs") or []
        if not procs and not st.session_state.get("dj_erro"):
            st.info("Digite o número e clique em **🔍 Consultar processo**.")
        for p in procs:
            st.markdown(f"### {p['numero']} — {p['tribunal']} ({p['grau']})")
            st.caption("Abrir o processo direto no site oficial:")
            for rotulo_link, url_link in _links_processo(alias, p["numero"], p.get("grau")):
                st.link_button(rotulo_link, url_link)
            if p["classe"]:
                st.markdown(f"**Classe:** {p['classe']}")
            if p["orgao"]:
                st.markdown(f"**Órgão julgador:** {p['orgao']}")
            if p["ajuizamento"]:
                st.markdown(f"**Ajuizamento:** {p['ajuizamento']}")
            if p["assuntos"]:
                st.markdown("**Assuntos:** " + "; ".join(p["assuntos"]))
            st.markdown(f"**Movimentações ({len(p['movimentos'])})** — mais recentes primeiro:")
            for m in p["movimentos"][:20]:
                st.markdown(f"- `{m['data']}` — {m['nome']}")
            if len(p["movimentos"]) > 20:
                with st.expander(f"Ver as demais {len(p['movimentos']) - 20} movimentações"):
                    for m in p["movimentos"][20:]:
                        st.markdown(f"- `{m['data']}` — {m['nome']}")
            comunica = _comunicacoes_processo(alias, p["numero"])
            if comunica:
                st.markdown(f"**📬 Comunicações no Diário / PJe ({len(comunica)})** — mais recentes primeiro:")
                for c in comunica[:20]:
                    linha = f"- `{c['data']}` — **{c['tipo']}** — {c['orgao']}"
                    if c["meio"]:
                        linha += f"  _( {c['meio']} )_"
                    st.markdown(linha)
                    if c["texto"]:
                        with st.expander("📄 ler o teor da comunicação"):
                            st.write(c["texto"])
                            if c["link"]:
                                st.link_button("🔗 Abrir o documento no PJe", c["link"])
                    elif c["link"]:
                        st.link_button("🔗 Abrir o documento no PJe", c["link"])
                if len(comunica) > 20:
                    st.caption(f"Mostrando 20 de {len(comunica)} comunicações.")
            st.caption("Processos em segredo de justiça não aparecem. Confirme no site do tribunal.")
    else:
        st.caption("O **DataJud** não divulga nomes de partes. A busca por nome é feita no "
                   "**site oficial do tribunal** escolhido acima (com o nome completo ou parte dele).")
        nome_parte = st.text_input("Nome da parte (requerente/autor ou requerido/réu)",
                                   key=f"dj_nome_{st.session_state.get('dj_versao', 0)}",
                                   placeholder="ex.: Maria da Silva")
        n1, n2 = st.columns([2, 1])
        if n1.button("🔍 Buscar por nome", type="primary"):
            st.session_state["dj_nome_busca"] = nome_parte.strip()
        if n2.button("🧹 Limpar / nova busca"):
            st.session_state["dj_versao"] = st.session_state.get("dj_versao", 0) + 1
            st.session_state.pop("dj_nome_busca", None)
            st.rerun()
        alvo = st.session_state.get("dj_nome_busca", "")
        if alvo:
            with st.spinner("Procurando o nome nos sites oficiais..."):
                achados = _buscar_nome_esaj(alias, alvo)
            if achados:
                st.success(f"✅ Encontrei {len(achados)} processo(s) em nome de “{alvo}” "
                           f"no e-SAJ:")
                for numero in achados[:10]:
                    st.markdown(f"**{numero}**")
                    opcoes = _links_processo(alias, numero, com_detalhe=False)
                    for coluna, (rotulo_link, url_link) in zip(st.columns(len(opcoes)), opcoes):
                        coluna.link_button(rotulo_link, url_link)
                if len(achados) > 10:
                    st.caption(f"Mostrando 10 de {len(achados)}. Refine o nome para ver menos.")
            else:
                if achados is not None:
                    st.warning(f"Não encontrei “{alvo}” no e-SAJ. Procure no PJe:")
                links = _links_processo_nome(alias, alvo)
                colunas = st.columns(len(links))
                for coluna, (rotulo_link, url_link) in zip(colunas, links):
                    coluna.link_button(rotulo_link, url_link)
        else:
            st.info("Digite o nome da parte e clique em **🔍 Buscar por nome**.")


def exportar(texto):
    stamp = f"{datetime.now():%Y%m%d_%H%M%S}"
    c1, c2 = st.columns(2)
    if c1.button("💾 Exportar Word (.docx)"):
        if tentar(motor.salvar_docx, texto, motor.PASTA_SAIDA / f"peca_{stamp}.docx"):
            st.session_state["export_docx"] = str(motor.PASTA_SAIDA / f"peca_{stamp}.docx")
            _salvar_automatico()
    if c2.button("💾 Exportar PDF"):
        if tentar(motor.salvar_pdf, texto, motor.PASTA_SAIDA / f"peca_{stamp}.pdf"):
            st.session_state["export_pdf"] = str(motor.PASTA_SAIDA / f"peca_{stamp}.pdf")
            _salvar_automatico()
    d1, d2 = st.columns(2)
    for coluna, chave in ((d1, "export_docx"), (d2, "export_pdf")):
        caminho = st.session_state.get(chave)
        if caminho and Path(caminho).exists():
            p = Path(caminho)
            coluna.download_button(f"⬇️ Baixar {p.suffix}", p.read_bytes(),
                                   file_name=p.name, key=f"dl_{chave}")


# ------------------------------------------------------------------ abas principais
aba_caso, aba_fatos, aba_peca, aba_conf, aba_base_ui, aba_anexo, aba_decisoes_ui, aba_processos_ui, aba_chat = st.tabs(
    ["1️⃣ Caso", "2️⃣ Fatos", "3️⃣ Peça", "4️⃣ Conferência", "🗂️ Base legal", "📎 Anexo/Análise",
     "📰 Decisões & Processos", "📌 Acompanhar processo", "💬 Chat IA"]
)

with aba_caso:
    st.subheader("Dados da peça")
    st.caption("Preencha como no cabeçalho da peça. O que ficar em branco, a IA identifica nos fatos na hora "
               "de redigir; no final tudo sai junto no cabeçalho.")
    st.text_input("Juízo / Vara / Tribunal", key="f_juizo",
                  placeholder="ex.: Juizado Especial Cível da Comarca de Fortaleza/CE")

    st.selectbox("Como chamar as partes", list(ROTULOS_PARTES), key="f_rotulo",
                 help="Requerente/Requerido no geral; Autor/Réu em ação criminal; Recorrente/Recorrido em recurso; etc.")
    r1, r2 = ROTULOS_PARTES[st.session_state.get("f_rotulo", "Requerente / Requerido")]
    c1, c2 = st.columns(2)
    with c1:
        _cadastro_parte("req", r1)
    with c2:
        _cadastro_parte("rdo", r2)
    st.text_area("Demais dados (datas, valores, números, o que mais importar)", key="f_outros",
                 height=100, placeholder="Digite aqui as datas, valores e outros dados importantes")
    st.session_state["dados"] = compor_dados()
    with st.expander("Ver bloco de dados que vai para a IA"):
        st.code(st.session_state["dados"] or "(vazio)")

with aba_anexo:
    st.subheader("📎 Anexar documento e analisar (triagem)")
    st.caption("A IA lê o documento (PDF/DOCX/TXT digital), identifica o tipo de peça cabível e aponta "
               "possíveis erros, indicando a fundamentação A CONFERIR. É um apoio; não substitui sua análise.")
    up = st.file_uploader("Anexe o documento", type=["pdf", "docx", "txt", "md"])
    if up is not None:
        st.caption(f"📄 {up.name} — {max(1, len(up.getvalue()) // 1024)} KB")
        if st.button("🔎 Ler e analisar documento", type="primary"):
            texto_doc = tentar(motor.extrair_texto_anexo, up.name, up.getvalue())
            if texto_doc is not None and not texto_doc.strip():
                st.error("Não consegui extrair texto (PDF pode ser escaneado/imagem — não suportado nesta versão).")
            elif texto_doc:
                bases = motor.listar_bases()
                base_nome = st.session_state.get("base_nome") or (bases[0] if bases else None)
                base = motor.carregar_base(base_nome) if base_nome else []
                with st.status("Analisando o documento...", expanded=False) as s:
                    rel = tentar(motor.analisar_documento, texto_doc, st.session_state["dados"], base, anonimizador)
                    s.update(label="Relatório pronto" if rel else "Falha",
                             state="complete" if rel else "error")
                if rel:
                    conf = motor.conferir_citacoes(rel, base, "")
                    st.session_state["analise_doc"] = conf["texto"]
                    st.session_state["analise_alertas"] = conf["alertas"]
    if st.session_state["analise_doc"]:
        c1, c2 = st.columns([1, 4])
        if c1.button("🗑️ Apagar relatório", width="stretch"):
            st.session_state["analise_doc"] = ""
            st.session_state["analise_alertas"] = []
            st.rerun()
        c2.caption("Dá para editar ou remover trechos direto no quadro abaixo, e também trocar/remover o anexo no 'x'.")
        st.text_area("Relatório (editável)", key="analise_doc", height=420,
                 placeholder="O relatório aparece aqui para você conferir e corrigir")
        with st.expander("Ver relatório formatado"):
            st.markdown(st.session_state["analise_doc"])
        if st.session_state.get("analise_alertas"):
            with st.expander("Alertas da conferência"):
                for n, m in st.session_state["analise_alertas"]:
                    alerta(n, m)
        st.caption("Para a IA poder citar uma norma na peça, cadastre-a na aba 🗂️ Base legal (status 'verificado').")

with aba_fatos:
    st.subheader("Relato do cliente")
    if st.session_state.get("_rascunho_msg"):
        st.info(st.session_state.pop("_rascunho_msg"), icon="💾")
    audio = st.audio_input("🎙️ Grave o relato (opcional)")
    if audio is not None and st.button("Transcrever"):
        with st.status("Transcrevendo...", expanded=False) as s:
            texto = tentar(motor.transcrever_audio, audio.getvalue(), audio.type or "audio/wav")
            s.update(label="Transcrição concluída" if texto else "Falha",
                     state="complete" if texto else "error")
        if texto:
            atual = (st.session_state["narrativa"] or "").strip()
            st.session_state["narrativa"] = (
                (atual + "<br>" if atual else "") + html.escape(texto))
            _salvar_rascunho()
            st.rerun()
    barra_texto("Relato (dite ou escreva o que o cliente contou)",
                "spj_relato_" + (_dono() or "admin"))
    _aplicar_correcao_pendente()
    if st.session_state.get("_corr_msg"):
        st.success(st.session_state.pop("_corr_msg"), icon="✍️")
    st.text_area("Relato (dite ou escreva o que o cliente contou)", key="narrativa", height=150,
                 placeholder="Digite seu texto aqui")
    c_prev, c_aviso = st.columns([1, 3])
    if c_prev.checkbox("👁 Ver com formatação", key="relato_preview"):
        with st.container(border=True):
            st.markdown(previa_texto(st.session_state.get("narrativa", "")),
                        unsafe_allow_html=True)
    c_aviso.caption("💾 Salvo sozinho enquanto você digita (no seu navegador e no sistema). "
                    "Pode deixar o sistema aberto sem medo de perder o que escreveu.")
    st.caption("✍️ **Palavra errada?** Ela fica **sublinhada em vermelho** no campo acima: "
               "clique com o botão direito na palavra e escolha a correção sugerida. "
               "Exemplo: “A cliente comprou passagem de Fortaleza para São Paulo no dia 10/03/2026…”")

    if st.button("🔤 Revisar minha escrita com a IA", key="btn_revisar_escrita"):
        st.session_state["_correcoes"] = []
        st.session_state["_revisou"] = False
        if not st.session_state["narrativa"].strip():
            st.warning("Escreva o relato primeiro.")
        else:
            with st.status("Revisando a escrita...", expanded=False) as s:
                achados = tentar(motor.revisar_escrita,
                                 motor.texto_simples(st.session_state["narrativa"]),
                                 anonimizador)
                s.update(label="Revisão concluída" if achados is not None else "Falha",
                         state="complete" if achados is not None else "error")
            if achados is not None:
                st.session_state["_correcoes"] = achados
                st.session_state["_revisou"] = True

    achados = st.session_state.get("_correcoes") or []
    if achados:
        st.info(f"🔎 Encontrei {len(achados)} possível(is) erro(s) de escrita. "
                "Clique no que quer corrigir:")
        for i, achado in enumerate(achados[:12]):
            col1, col2 = st.columns([3, 4])
            if col1.button(f"❌ {achado['errado']}  →  ✅ {achado['certo']}", key=f"corr_{i}"):
                st.session_state["_corr_pendente"] = (achado["errado"], achado["certo"])
                st.rerun()
            col2.caption(achado.get("motivo", ""))
    elif st.session_state.get("_revisou"):
        st.success("✅ Não encontrei erros de escrita no relato.")

    if st.button("🧹 Limpar fatos e listar pendências", type="primary"):
        if not st.session_state["narrativa"].strip():
            st.warning("Escreva ou dite o relato primeiro.")
        else:
            _salvar_rascunho()  # guarda o texto ANTES de chamar a IA
            with st.status("Organizando os fatos...", expanded=False) as s:
                resultado = tentar(motor.limpar_fatos, st.session_state["dados"],
                                   motor.texto_simples(st.session_state["narrativa"]),
                                   anonimizador)
                s.update(label="Fatos organizados" if resultado else "Falha",
                         state="complete" if resultado else "error")
            if resultado:
                st.session_state["fatos_edit"] = resultado[0]
                st.session_state["pend"] = resultado[1]
                sugerido = motor.identificar_modelo(resultado[0], motor.listar_modelos())
                if sugerido and sugerido != st.session_state.get("modelo_nome"):
                    st.session_state["modelo_nome"] = sugerido
                st.success(f"Fatos organizados abaixo. Modelo sugerido: **{sugerido or '—'}** (confira na barra lateral).")

    st.divider()
    st.subheader("Fatos organizados (edite à vontade)")
    if not st.session_state["fatos_edit"]:
        st.info("Escreva o relato acima, clique em 'Limpar fatos' e os fatos aparecerão aqui.")
    else:
        st.text_area("Fatos", key="fatos_edit", height=280,
                     placeholder="Os fatos organizados aparecem aqui — pode editar à vontade")
    st.caption("Quando estiver pronto, gere a peça pelo botão **📝 Gerar peça** na barra lateral.")

    perguntas = [p.strip().lstrip("-").strip()
                 for p in st.session_state["pend"].splitlines() if p.strip()]
    if perguntas:
        st.divider()
        st.warning("Perguntas pendentes — responda logo abaixo de cada uma:")
        blocos = []
        for i, pergunta in enumerate(perguntas):
            st.markdown(f"**{i + 1}. {pergunta}**")
            resp = st.text_area("Resposta", key=f"resp_{i}", height=80,
                                label_visibility="collapsed",
                                placeholder="Escreva a resposta aqui...")
            if resp.strip():
                blocos.append(f"PERGUNTA: {pergunta}\nRESPOSTA: {resp.strip()}")
        if st.button("🔄 Incorporar respostas aos fatos"):
            if not blocos:
                st.warning("Escreva ao menos uma resposta.")
            else:
                respostas = "\n\n".join(blocos)
                with st.status("Atualizando os fatos...", expanded=False) as s:
                    r = tentar(motor.incorporar_respostas, st.session_state["dados"],
                               st.session_state["fatos_edit"], st.session_state["pend"],
                               respostas, anonimizador)
                    s.update(label="Fatos atualizados" if r else "Falha",
                             state="complete" if r else "error")
                if r:
                    st.session_state["_p_fatos"] = r[0]
                    st.session_state["_p_pend"] = r[1]
                    st.session_state["_limpar_respostas"] = True
                    st.rerun()

with aba_peca:
    st.subheader("Peça gerada (edite à vontade)")
    if not st.session_state["peca_edit"]:
        st.info("Gere a peça na aba 2️⃣.")
    else:
        texto = st.text_area("Texto da peça", key="peca_edit", height=520,
                         placeholder="A peça aparece aqui — pode corrigir antes de exportar")
        exportar(texto)

with aba_conf:
    st.subheader("🔍 Sugestões de jurisprudência (conferir)")
    st.warning(
        "A IA sugere **fontes para você CONFERIR** na origem. Nada entra na peça automaticamente. "
        "Confirme tribunal, número e tese no site oficial antes de citar."
    )
    if st.button("🔍 Buscar sugestões conforme os fatos", type="primary"):
        fatos = st.session_state["fatos_edit"]
        if not fatos.strip():
            st.warning("Organize os fatos primeiro (aba 2️⃣).")
        else:
            bases = motor.listar_bases()
            base_nome = st.session_state.get("base_nome") or (bases[0] if bases else None)
            base = motor.carregar_base(base_nome) if base_nome else []
            with st.status("Procurando fontes...", expanded=False) as s:
                texto = tentar(motor.sugerir_jurisprudencia, st.session_state["dados"], fatos, base, anonimizador)
                s.update(label="Sugestões geradas" if texto else "Falha",
                         state="complete" if texto else "error")
            if texto:
                st.session_state["juris_sugerida"] = texto
    if st.session_state["juris_sugerida"]:
        c1, c2 = st.columns([1, 4])
        if c1.button("🗑️ Apagar sugestões", width="stretch"):
            st.session_state["juris_sugerida"] = ""
            st.rerun()
        c2.caption("Você pode editar ou remover sugestões direto no quadro abaixo.")
        st.text_area("Sugestões (editável)", key="juris_sugerida", height=360,
                 placeholder="As sugestões de jurisprudência e de legislação aparecem aqui")
        st.markdown("**🔗 Abrir cada sugestão na fonte oficial** (clique para pesquisar no site do tribunal):")
        itens = decisoes.parse_sugestoes_juris(st.session_state["juris_sugerida"])
        if not itens:
            st.caption("Não consegui separar as sugestões automaticamente — use o quadro editável acima.")
        for it in itens:
            with st.expander(it["cabecalho"] or "Sugestão"):
                if it["tese"]:
                    st.markdown(f"**Tese:** {it['tese']}")
                if it["identificacao"]:
                    st.markdown(f"**Identificação:** {it['identificacao']}")
                if it["busca"]:
                    st.markdown(f"**Busca:** {it['busca']}")
                st.link_button("🔎 Abrir busca na fonte oficial", it["url"])
        st.caption("Depois de conferir no site oficial, cadastre na aba 🗂️ Base legal com status "
                   "'verificado' para a IA poder citar na peça.")
    st.divider()
    aba_conferencia()

with aba_base_ui:
    aba_base()

with aba_decisoes_ui:
    aba_decisoes()

with aba_processos_ui:
    aba_processos()

with aba_chat:
    st.subheader("💬 Conversar com a IA")
    st.caption("Tire dúvidas e pesquise sobre o processo. A IA é apoio — confira sempre as fontes oficiais.")
    c1, c2 = st.columns([1, 4])
    if c1.button("🗑️ Limpar conversa", width="stretch"):
        st.session_state["chat_hist"] = []
        st.rerun()
    c2.checkbox("Incluir os dados e os fatos deste caso no contexto", value=True,
                key="chat_usar_caso")
    for _m in st.session_state["chat_hist"]:
        with st.chat_message("user" if _m.get("role") == "user" else "assistant"):
            st.markdown(_m.get("content", ""))
    _pergunta = st.chat_input("Escreva sua pergunta...", key="chat_pergunta")
    if _pergunta and _pergunta.strip():
        _pergunta = _pergunta.strip()
        st.session_state["chat_hist"].append({"role": "user", "content": _pergunta})
        with st.chat_message("user"):
            st.markdown(_pergunta)
        _contexto = ""
        if st.session_state.get("chat_usar_caso", True):
            _partes = []
            if st.session_state.get("dados", "").strip():
                _partes.append(st.session_state["dados"])
            if st.session_state.get("fatos_edit", "").strip():
                _partes.append("FATOS:\n" + st.session_state["fatos_edit"])
            _contexto = "\n\n".join(_partes)
        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                _resposta = tentar(motor.responder_chat, st.session_state["chat_hist"],
                                   _contexto, anonimizador)
            if _resposta:
                st.markdown(_resposta)
        if _resposta:
            st.session_state["chat_hist"].append({"role": "assistant", "content": _resposta})

# salva o que está sendo escrito (roda a cada execução, sem recarregar a tela)
_salvar_rascunho()

# guarda a aba em que você estava, para voltar para a mesma tela após atualizar
_JS_ABAS = """
<script>
(function () {
  var P = window.parent;
  var doc = P.document;
  var CHAVE = "spj_aba";
  var MEU = "spj-aba-" + Math.random().toString(36).slice(2);

  function lista() {
    var listas = doc.querySelectorAll('div[data-testid="stAppViewContainer"] [role="tablist"]');
    for (var i = 0; i < listas.length; i++) {
      var ts = listas[i].querySelectorAll('[role="tab"]');
      if (ts.length >= 5) return ts;
    }
    return null;
  }

  function indiceAtual(ts) {
    for (var i = 0; i < ts.length; i++) {
      if (ts[i].getAttribute("aria-selected") === "true") return i;
    }
    return -1;
  }

  function salvar(i) {
    try { P.localStorage.setItem(CHAVE, String(i)); } catch (e) {}
  }

  function restaurar(ts) {
    var guardado = null;
    try { guardado = P.localStorage.getItem(CHAVE); } catch (e) {}
    if (guardado === null) return;
    var alvo = parseInt(guardado, 10);
    if (isNaN(alvo) || alvo < 0 || alvo >= ts.length) return;
    if (indiceAtual(ts) === alvo) return;
    try { ts[alvo].click(); } catch (e) {}
  }

  function marcarAoClicar(ts) {
    var caixa = ts[0] ? ts[0].parentNode : null;
    if (!caixa || caixa.getAttribute("data-spj-aba") === MEU) return;
    caixa.setAttribute("data-spj-aba", MEU);
    caixa.addEventListener("click", function (ev) {
      var alvo = ev.target && ev.target.closest ? ev.target.closest('[role="tab"]') : null;
      if (!alvo) return;
      var ts2 = lista();
      if (!ts2) return;
      for (var i = 0; i < ts2.length; i++) {
        if (ts2[i] === alvo) { salvar(i); return; }
      }
    }, true);
  }

  function rodar() {
    try {
      var ts = lista();
      if (!ts) return;
      marcarAoClicar(ts);
      restaurar(ts);
    } catch (e) {}
  }

  rodar();
  setInterval(rodar, 700);
})();
</script>
"""
try:
    components.html(_JS_ABAS, height=0)
except Exception:
    pass
