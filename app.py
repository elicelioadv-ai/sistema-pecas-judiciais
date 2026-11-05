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


def _nome_tribunal(alias):
    """Nome curto do tribunal (ex.: ``api_publica_trt2`` -> ``TRT 2ª Região``)."""
    for _ramo, _opcoes in getattr(decisoes, "DATAJUD_RAMOS", {}).items():
        for _rot, _alias in _opcoes:
            if _alias == alias:
                return _rot
    return alias or ""


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
/* centraliza o cartao de login no meio da tela. O "safe" evita que o topo
   do cartao fique cortado quando a tela e baixa (o cartao passa a comecar
   no topo e a pagina rola normalmente). */
[data-testid="stAppViewContainer"] .block-container,
.block-container {
    min-height: 100vh !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    justify-content: safe center !important;
    align-items: center !important;
    padding-top: 1.5rem !important;
    padding-bottom: 1.5rem !important;
    max-width: 100% !important;
}
[data-testid="stAppViewContainer"] .block-container > div,
.block-container > div { width: 100%; }
html, body { scroll-behavior: auto !important; }
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
    max-width: 470px; margin: 0 auto;
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
/* Esconde só os icones que o proprio navegador desenha dentro do campo
   (o "revelar senha" do Edge/Chrome). O olhinho do Streamlit fica visivel. */
input[type="password"]::-ms-reveal,
input[type="password"]::-ms-clear,
input[type="password"]::-webkit-credentials-auto-fill-button,
input[type="password"]::-webkit-strong-password-auto-fill-button,
input[type="password"]::-webkit-textfield-decoration-container {
    display: none !important; visibility: hidden !important;
}
/* Campo de senha do login: o mascaramento vem do proprio type="password". */
.st-key-login_senha input,
.st-key-login_campos input[aria-label="Senha de acesso"],
div[data-testid="stForm"] input[aria-label="Senha de acesso"] {
    letter-spacing: 1px;
}
/* O olhinho de mostrar/ocultar a senha e o nativo do Streamlit
   (type="password"). Nao criamos mais um botao por JavaScript. */
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
/* "Não sou um robô" moderno */
.st-key-captcha_humano_btn { width: 100%; }
.st-key-captcha_humano_btn button {
    justify-content: flex-start !important; width: 100% !important; min-height: 74px !important;
    background: #ffffff !important; color: #202124 !important;
    border: 1px solid #dadce0 !important; border-radius: 6px !important;
    font-weight: 400 !important; padding: 12px 18px !important;
    box-shadow: 0 1px 2px rgba(60,64,67,0.08) !important;
    gap: 14px !important;
}
.st-key-captcha_humano_btn button::before {
    content: ''; width: 26px; height: 26px; border: 2px solid #5f6368; border-radius: 4px;
    background: #ffffff; margin-right: 0; display: inline-block; flex-shrink: 0;
    box-sizing: border-box;
}
.st-key-captcha_humano_btn button:hover {
    background: #f8f9fa !important;
    box-shadow: 0 1px 3px rgba(60,64,67,0.15) !important;
}
.st-key-captcha_humano_btn button p { color: #3c4043 !important; font-size: 0.9rem !important; }
/* grade de figuras */
.st-key-captcha_nativo [data-testid="stHorizontalBlock"] { gap: 8px !important; }
.st-key-captcha_nativo [data-testid="stButton"] { margin: 0 !important; }
.st-key-captcha_nativo button {
    width: 100% !important; height: 92px !important; padding: 0 !important;
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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
    --azul-escuro:#1F4E78; --azul-aviso:#1F4E78; --azul-petroleo:#2d6aa3;
    --vermelho:#B2101D; --roxo:#694467; --amarelo:#F5AF00;
    --fundo:#f7f9fc; --header:#1F4E78; --botao:#E4E9EC; --botao-busca:#C3D1D9;
    --aba-ativa:#1F4E78; --aba:#f1f3f6;
    --texto-menu:#FFFFFF; --texto-menu-sec:#EEF3F6; --texto-aba:#3c4043; --link:#1F4E78; --placeholder:#6C757D;
    --botao-menu:rgba(255,255,255,0.08); --botao-menu-ativo:rgba(255,255,255,0.15);
    --card-bg:#FFFFFF; --border:#e0e7ef; --shadow:0 1px 3px rgba(16,24,40,0.05), 0 1px 2px rgba(16,24,40,0.03);
}
* { font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, sans-serif !important; }
.stApp, [data-testid="stAppViewContainer"] { background: var(--fundo) !important; }
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1F4E78 0%, #153a5c 100%) !important;
    border-right: none !important;
    box-shadow: 2px 0 8px rgba(0,0,0,0.08);
}
[data-testid="stSidebar"] [role="radiogroup"] label {
    padding: 8px 12px !important;
    border-radius: 8px !important;
    margin-bottom: 2px !important;
    transition: all 0.15s ease !important;
    color: #FFFFFF !important;
}
[data-testid="stSidebar"] [role="radiogroup"] label:hover { background: rgba(255,255,255,0.1) !important; }
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) { background: rgba(255,255,255,0.15) !important; font-weight: 600 !important; }
[data-testid="stSidebar"] * { color: var(--texto-menu); }
[data-testid="stSidebar"] a { color: #FFFFFF !important; }
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.12) !important; }
h1, h2, h3 { color: #101828 !important; font-weight: 600 !important; letter-spacing: -0.01em; }
h1 { font-size: 1.875rem !important; margin-bottom: 1.5rem !important; }
[data-baseweb="tab-list"] {
    background: #f1f3f6 !important; border-radius: 10px !important; padding: 4px !important; gap: 4px;
    border: 1px solid var(--border) !important;
}
[data-baseweb="tab"] { color: var(--texto-aba) !important; border-radius: 8px !important; padding: 8px 16px !important; font-weight: 500 !important; }
[data-baseweb="tab"][aria-selected="true"] {
    color: #FFFFFF !important; background: var(--azul-escuro) !important; font-weight: 600 !important;
}
button[data-testid^="stBaseButton-"], a[data-testid^="stBaseLinkButton-"] {
    background: var(--azul-escuro) !important; color: #FFFFFF !important;
    border: none !important; border-radius: 8px !important; font-weight: 600 !important;
}
[data-testid="stDataFrame"], [data-testid="stTable"] {
    border: 1px solid var(--border); border-radius: 10px; overflow: hidden; box-shadow: var(--shadow);
}
</style>
"""
st.markdown(_CSS_TEMA, unsafe_allow_html=True)


def alerta(nivel, msg):
    icone = {"erro": "�", "aviso": "⚠️", "ok": "✅"}.get(nivel, "•")
    st.markdown(f"{icone} {msg}")


# ------------------------------------------------- barra de formatação (tipo Word)
# A caixa de texto do Streamlit é "crua". Esta barra injeta botões (negrito,
# itálico, lista...) que marcam o texto selecionado, como no Word. As marcas
# (**negrito**, _itálico_...) vão junto para a IA e aparecem formatadas na
# pré-visualização.
#
# Esta folha de estilo vai para a P�GINA DE FORA (a barra e a paletinha de cores
# são criadas no documento principal, não dentro do app): por isso o CSS usa
# cores fixas, e não as variáveis do tema.
_CSS_BARRA = """
.__spj_barra__ {
    display: flex; flex-wrap: wrap; gap: 4px; align-items: center;
    background: #ECEFF1; border: 1px solid #C3D1D9; border-radius: 6px;
    padding: 4px 6px; margin: 0 0 6px 0;
}
.__spj_barra__ button {
    min-width: 30px; height: 28px; padding: 0 6px; line-height: 1;
    border: 1px solid #C3D1D9; border-radius: 4px;
    background: #FFFFFF; color: #003F65; font-size: 14px;
    cursor: pointer; font-family: inherit;
}
.__spj_barra__ button:hover { background: #D2D4D5; border-color: #003F65; }
.__spj_barra__ button:active { background: #C3D1D9; }
.__spj_barra__ button[aria-label="Destaque"] {
    position: relative; padding-bottom: 6px;
    background-image: linear-gradient(90deg, #FFF59D 0%, #C8E6C9 25%, #BBDEFB 50%,
                                     #F8BBD0 75%, #FFE0B2 100%);
}
.__spj_barra__ button[aria-label="Destaque"] mark { background: transparent; color: #1F2933; }
.__spj_paleta__ {
    position: absolute; z-index: 999999; display: flex; gap: 4px; padding: 6px;
    background: #ffffff; border: 1px solid #C3D1D9;
    border-radius: 8px; box-shadow: 0 6px 18px rgba(0, 0, 0, 0.22);
}
.__spj_paleta__ button {
    width: 24px; height: 24px; border-radius: 5px; border: 1px solid #b0bec5;
    cursor: pointer; padding: 0; margin: 0; background: #ffffff;
}
.__spj_paleta__ button:hover { outline: 2px solid #2d6aa3; outline-offset: 1px; }
.__spj_paleta__ .sem_cor {
    background: #ffffff !important;
    background-image: linear-gradient(45deg, #e53935 44%, transparent 44%, transparent 56%, #e53935 56%) !important;
}
.__spj_paleta__ .hl_d1 { background: #FFF59D !important; }
.__spj_paleta__ .hl_d2 { background: #C8E6C9 !important; }
.__spj_paleta__ .hl_d3 { background: #BBDEFB !important; }
.__spj_paleta__ .hl_d4 { background: #F8BBD0 !important; }
.__spj_paleta__ .hl_d5 { background: #FFE0B2 !important; }
.__spj_paleta__ .hl_d6 { background: #E0E0E0 !important; }
"""

_JS_BARRA = r"""<script>
(function () {
  var ALVO = "__ALVO__";
  var CHAVE = "__CHAVE__";
  var CSS = __CSS_BARRA__;
  var P = window.parent;
  var doc = P.document;
  var MEU = "spj" + Math.random().toString(36).slice(2, 9);
  var ultimo = null;        // texto que ja foi enviado ao servidor
  var ultimoIniciado = false;
  var ultimoHtml = null;
  var restaurado = false;

  // leva o estilo da barra e da paletinha para a pagina de fora
  function injetarEstilo() {
    try {
      if (doc.getElementById("__spj_estilo__")) return;
      var s = doc.createElement("style");
      s.id = "__spj_estilo__";
      s.textContent = CSS;
      (doc.head || doc.documentElement).appendChild(s);
    } catch (e) {}
  }
  injetarEstilo();
  var BTNS = [
    {t:"Negrito",           i:"<b>N</b>",  cmd:"bold"},
    {t:"Itálico",           i:"<i>I</i>",  cmd:"italic"},
    {t:"Sublinhado",        i:"<u>S</u>",  cmd:"underline"},
    {t:"Tachado",           i:"<s>T</s>",  cmd:"strikeThrough"},
    {t:"Destaque",          i:"<mark>A</mark>", destaque:true},
    {t:"Título",            i:"H",        bloco:"h2"},
    {t:"Lista",             i:"&#8226;",  cmd:"insertUnorderedList"},
    {t:"Lista numerada",    i:"1.",       cmd:"insertOrderedList"},
    {t:"Citação",           i:"&#10077;", bloco:"blockquote"},
    {t:"Desfazer",          i:"&#8630;",  cmd:"undo"},
    {t:"Refazer",           i:"&#8631;",  cmd:"redo"},
    {t:"Limpar formatação", i:"&#129534;", limpar:true}
  ];
  // cores do destaque (igual ao Word): a primeira e "sem destaque"
  var CORES = [
    {classe:"",           nome:"Sem destaque", estilo:"#ffffff"},
    {classe:"hl_d1",      nome:"Amarelo",      estilo:"#FFF59D"},
    {classe:"hl_d2",      nome:"Verde",        estilo:"#C8E6C9"},
    {classe:"hl_d3",      nome:"Azul",         estilo:"#BBDEFB"},
    {classe:"hl_d4",      nome:"Rosa",         estilo:"#F8BBD0"},
    {classe:"hl_d5",      nome:"Laranja",      estilo:"#FFE0B2"},
    {classe:"hl_d6",      nome:"Cinza",        estilo:"#E0E0E0"}
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

  // o editor que esta VALENDO agora: o que esta na mesma caixa de texto
  // (quando a tela atualiza, podem sobrar editores antigos por perto)
  function editor() {
    var c = achar();
    if (!c) return null;
    var ta = c.querySelector("textarea");
    if (!ta) return null;
    var raiz = ta.closest('[data-testid="stTextAreaRootElement"]') || ta.parentNode;
    if (!raiz) return null;
    var e = null;
    var todos = raiz.querySelectorAll(".__spj_editor__");
    for (var i = todos.length - 1; i >= 0; i--) {
      if (todos[i].isConnected) { e = todos[i]; break; }
    }
    if (!e) {
      // a tela acabou de atualizar e o editor ainda nao foi refeito: cria agora
      try { e = criarEditor(c); } catch (e2) {}
    }
    return e;
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
    var ta0 = cont.querySelector("textarea");
    if (!ta0) return null;
    var raiz0 = ta0.closest('[data-testid="stTextAreaRootElement"]') || ta0.parentNode;
    if (raiz0) {
      // o editor da tela anterior: se ainda da para usar, ele volta no lugar
      // (assim o texto e a selecao do usuario nao se perdem na atualizacao)
      var anterior = P.__spjEditor;
      if (anterior && !anterior.isConnected) {
        try {
          raiz0.insertBefore(anterior, ta0);
          var c2 = raiz0.closest(".stTextArea");
          if (c2) c2.classList.add("__spj_com_editor__");
          P.__spjEditor = anterior;
          return anterior;
        } catch (e) {}
      }
      var ja = null;
      var velhos = raiz0.querySelectorAll(".__spj_editor__");
      for (var i = 0; i < velhos.length; i++) {
        if (velhos[i].isConnected && !ja) ja = velhos[i];
      }
      if (ja) { P.__spjEditor = ja; return ja; }
      // sobrou editor de uma tela anterior? tira, para nao mexer no errado
      for (var j = 0; j < velhos.length; j++) {
        try { velhos[j].parentNode.removeChild(velhos[j]); } catch (e) {}
      }
    }
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
    // se o usuario ainda tem mudanca nao enviada, o texto dele manda
    // (senao a atualizacao da tela apagaria a formatacao recem aplicada)
    var usarLocal = (local && local.trim() && (P.__spjPendente || !servidor.trim()));
    ed.innerHTML = mdParaHtml(usarLocal ? local : servidor);
    if (!usarLocal) { try { P.__spjPendente = false; } catch (e) {} }
    ultimoHtml = ed.innerHTML;
    P.__spjHtml = ultimoHtml;
    raiz.insertBefore(ed, ta);
    P.__spjEditor = ed;
    cont.classList.add("__spj_com_editor__");
    ed.addEventListener("input", function () { digitar(ed); });
    ed.addEventListener("paste", function () { setTimeout(function () { digitar(ed); }, 30); });
    return ed;
  }

  function digitar(ed) {
    if (!ed) return;
    P.__spjPendente = true;
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
      var off = r.startOffset;
      if (node.nodeType !== 3) {
        // cursor num elemento (ex.: o proprio editor): acha o texto la dentro
        var txtNode = null;
        var filhos = node.childNodes;
        if (filhos && filhos.length) {
          var f = filhos[Math.min(off, filhos.length - 1)];
          while (f && f.nodeType !== 3) f = f.firstChild;
          if (f) { txtNode = f; off = 0; }
        }
        if (!txtNode) return;
        node = txtNode;
      }
      var txt = node.textContent || "";
      var ini = off, fim = off;
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

  // ------------------- destaque (marca-texto com cor) --------------------
  // A selecao e guardada por POSICAO no texto (e nao por no do DOM), porque o
  // Streamlit recria o editor a cada atualizacao da tela: assim o trecho
  // escolhido continua valendo mesmo depois do recarregamento.
  var selSalva = null;   // {ini: posicao, fim: posicao}

  function nosDeTexto(ed) {
    var lista = [];
    try {
      var w = doc.createTreeWalker(ed, NodeFilter.SHOW_TEXT, null);
      var n, pos = 0;
      while ((n = w.nextNode())) {
        var tam = (n.textContent || "").length;
        lista.push({no: n, ini: pos, tam: tam});
        pos += tam;
      }
    } catch (e) {}
    return lista;
  }

  function posicaoDe(ed, no, off) {
    var lista = nosDeTexto(ed);
    var total = 0;
    for (var i = 0; i < lista.length; i++) {
      if (lista[i].no === no) return lista[i].ini + off;
      total += lista[i].tam;
    }
    return total;
  }

  function noEPosicaoDe(ed, pos) {
    var lista = nosDeTexto(ed);
    if (!lista.length) return null;
    for (var i = 0; i < lista.length; i++) {
      if (pos >= lista[i].ini && pos <= lista[i].ini + lista[i].tam) {
        return {no: lista[i].no, off: pos - lista[i].ini};
      }
    }
    var u = lista[lista.length - 1];
    return {no: u.no, off: u.tam};
  }

  function guardarSelecao() {
    try {
      var ed = editor();
      if (!ed) return;
      var sel = doc.getSelection();
      if (!sel || sel.rangeCount === 0) return;
      var r = sel.getRangeAt(0);
      var ini = posicaoDe(ed, r.startContainer, r.startOffset);
      var fim = posicaoDe(ed, r.endContainer, r.endOffset);
      if (fim < ini) { var t = ini; ini = fim; fim = t; }
      selSalva = {ini: ini, fim: fim};
      // guarda tambem no documento pai: se a tela se atualizar e o editor for
      // recriado, o trecho escolhido continua valendo
      P.__spjSel = {ini: ini, fim: fim};
    } catch (e) {}
  }

  function restaurarSelecao() {
    try {
      var ed = editor();
      var ss = selSalva || P.__spjSel;
      if (!ed || !ss) return false;
      var a = noEPosicaoDe(ed, ss.ini);
      var b = noEPosicaoDe(ed, ss.fim);
      if (!a || !b) return false;
      var r = doc.createRange();
      r.setStart(a.no, a.off);
      r.setEnd(b.no, b.off);
      if (r.collapsed) return false;
      var sel = doc.getSelection();
      sel.removeAllRanges();
      sel.addRange(r);
      return true;
    } catch (e) { return false; }
  }

  function envolverClasse(tag, classe) {
    try {
      var sel = doc.getSelection();
      if (!sel || sel.rangeCount === 0) return;
      var r = sel.getRangeAt(0);
      if (r.collapsed) return;
      var el = doc.createElement(tag);
      if (classe) el.className = classe;
      try { r.surroundContents(el); }
      catch (e) { el.appendChild(r.extractContents()); r.insertNode(el); }
    } catch (e) {}
  }

  function tirarMarca(m) {
    try {
      var pai = m.parentNode;
      if (!pai) return;
      while (m.firstChild) pai.insertBefore(m.firstChild, m);
      pai.removeChild(m);
    } catch (e) {}
  }

  function marcasDoTrecho(ed, r) {
    var res = [];
    try {
      var marcas = ed.querySelectorAll("mark");
      for (var i = 0; i < marcas.length; i++) {
        var m = marcas[i];
        if (!r.intersectsNode || r.intersectsNode(m)) res.push(m);
      }
    } catch (e) {}
    return res;
  }

  // o trecho onde a marca deve ficar (em posicoes do texto do editor)
  function trechoEscolhido(ed) {
    var sel = doc.getSelection();
    var r = (sel && sel.rangeCount) ? sel.getRangeAt(0) : null;
    if (r && !r.collapsed) {
      // a selecao vale so se ainda estiver dentro do editor (a tela pode ter
      // recriado o editor no meantime)
      var dentro = false;
      try { dentro = ed.contains(r.startContainer) && ed.contains(r.endContainer); } catch (e) {}
      if (dentro) {
        var a = posicaoDe(ed, r.startContainer, r.startOffset);
        var b = posicaoDe(ed, r.endContainer, r.endOffset);
        if (b < a) { var t = a; a = b; b = t; }
        if (b > a) return {ini: a, fim: b};
      }
    }
    var ss = selSalva || P.__spjSel;
    if (ss && ss.fim > ss.ini) return {ini: ss.ini, fim: ss.fim};
    return null;
  }

  // intervalo de texto coberto por uma marca
  function intervaloDaMarca(lista, m) {
    var ini = -1, fim = -1;
    for (var i = 0; i < lista.length; i++) {
      var dentro = false;
      try { dentro = m.contains(lista[i].no); } catch (e) {}
      if (dentro) {
        if (ini < 0) ini = lista[i].ini;
        fim = lista[i].ini + lista[i].tam;
      }
    }
    return {ini: ini, fim: fim};
  }

  // marca o trecho (por posicao) com a cor escolhida
  function envolverPorPosicao(ed, ini, fim, classe) {
    var lista = nosDeTexto(ed);
    var a = null, b = null;
    for (var i = 0; i < lista.length; i++) {
      if (!a && ini >= lista[i].ini && ini <= lista[i].ini + lista[i].tam) {
        a = {no: lista[i].no, off: ini - lista[i].ini};
      }
      if (fim >= lista[i].ini && fim <= lista[i].ini + lista[i].tam) {
        b = {no: lista[i].no, off: fim - lista[i].ini};
      }
    }
    if (!a || !b) return false;
    if (a.no === b.no && a.off === b.off) return false;
    var r = doc.createRange();
    try {
      r.setStart(a.no, a.off);
      r.setEnd(b.no, b.off);
    } catch (e) { return false; }
    var el = doc.createElement("mark");
    el.className = classe;
    try { r.surroundContents(el); }
    catch (e) { el.appendChild(r.extractContents()); r.insertNode(el); }
    return true;
  }

  // aplica a cor escolhida; se o trecho ja estiver com a mesma cor, desmarca
  function aplicarDestaque(classe) {
    var ed = editor();
    if (!ed) {
      // a tela esta se atualizando e o editor sumiu: tenta de novo em instantes
      var tentativas = 0;
      var timer = setInterval(function () {
        tentativas++;
        if (editor()) {
          clearInterval(timer);
          aplicarDestaque(classe);
        } else if (tentativas > 25) {
          clearInterval(timer);
        }
      }, 120);
      return;
    }
    var trecho = trechoEscolhido(ed);
    if (!trecho) return;
    selSalva = {ini: trecho.ini, fim: trecho.fim};

    // tira as marcas que ja existem no trecho
    var lista = nosDeTexto(ed);
    var marcas = ed.querySelectorAll("mark");
    var alvo = [];
    var mesmaCor = false;
    for (var i = 0; i < marcas.length; i++) {
      var iv = intervaloDaMarca(lista, marcas[i]);
      if (iv.ini < 0) continue;
      if (iv.ini < trecho.fim && iv.fim > trecho.ini) {
        alvo.push(marcas[i]);
        if ((marcas[i].className || "") === (classe || "")) mesmaCor = true;
      }
    }
    for (var j = 0; j < alvo.length; j++) { tirarMarca(alvo[j]); }

    // se o trecho ja estava com essa cor, e so desmarcar (nao pinta de novo).
    // (so conta a marca do proprio trecho: marca em outro lugar nao impede)
    if (classe && !(alvo.length > 0 && mesmaCor)) {
      envolverPorPosicao(ed, trecho.ini, trecho.fim, classe);
    }
    digitar(ed);
  }

  function fecharPaleta() {
    try {
      var pal = doc.querySelector(".__spj_paleta__");
      if (pal) pal.parentNode.removeChild(pal);
    } catch (e) {}
  }

  function abrirPaleta(btn) {
    try { fecharPaleta(); } catch (e) {}
    var pal = doc.createElement("div");
    pal.className = "__spj_paleta__";
    CORES.forEach(function (c) {
      var sw = doc.createElement("button");
      sw.type = "button";
      sw.title = c.nome;
      sw.setAttribute("aria-label", "Destaque " + c.nome);
      if (c.classe) { sw.className = c.classe; } else { sw.className = "sem_cor"; }
      sw.addEventListener("mousedown", function (ev) { ev.preventDefault(); });
      sw.addEventListener("click", function () {
        aplicarDestaque(c.classe);
        fecharPaleta();
      });
      pal.appendChild(sw);
    });
    doc.body.appendChild(pal);
    var r = btn.getBoundingClientRect();
    var sx = (doc.defaultView && doc.defaultView.scrollX) || 0;
    var sy = (doc.defaultView && doc.defaultView.scrollY) || 0;
    pal.style.left = Math.max(6, r.left + sx) + "px";
    pal.style.top = (r.bottom + sy + 6) + "px";
    // clicking anywhere else closes the palette
    setTimeout(function () {
      try {
        doc.addEventListener("click", function (ev) {
          if (pal.parentNode && !pal.contains(ev.target)) { fecharPaleta(); }
        }, true);
      } catch (e) {}
    }, 30);
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

  // foca o editor sem apagar o que o usuario ja selecionou
  function focar(el) {
    try {
      if (!el) return;
      if (doc.activeElement === el) return;
      el.focus();
    } catch (e) {}
  }

  function aplicar(b, btn) {
    var ed = editor();
    if (ed) {
      if (b.destaque) {
        // guarda o trecho escolhido ANTES de mexer no foco (a paletinha
        // precisa saber o que o usuario queria marcar)
        guardarSelecao();
        focar(ed);
        try { abrirPaleta(btn); } catch (e) {}
        return;
      }
      focar(ed);
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
      aplicar(b, btn);
      // nao manda para o servidor agora: isso atualizaria a tela e apagaria
      // a selecao do usuario. O envio fica para o "autoComitar" (2,5 s depois).
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
      // o editor foi recriado (a tela atualizou): devolve a selecao do usuario
      if (ed && (selSalva || P.__spjSel)) {
        try { restaurarSelecao(); } catch (e) {}
      }
      vigiar();
      recuperar();
      ativarOrtografia();
      // o servidor mudou o texto? (ex.: transcricao) -> atualiza o editor
      var ta = cont.querySelector("textarea");
      // na primeira vez, guarda o texto que ja estava no servidor: assim
      // qualquer mudanca do usuario e enviada (e nao se perde no caminho)
      if (ta && !ultimoIniciado) { ultimo = ta.value; ultimoIniciado = true; }
      // o servidor mandou um texto novo? (ex.: transcricao) -> atualiza o editor.
      // So quando o usuario nao tem nada pendente: se ele acabou de formatar,
      // o texto dele manda (senao a atualizacao da tela apagaria a formatacao).
      if (ed && ta && ultimoHtml !== null && ta.value !== ultimoHtml && ultimoHtml === ultimo) {
        ed.innerHTML = mdParaHtml(ta.value);
        P.__spjHtml = ed.innerHTML;
        ultimoHtml = ed.innerHTML;
        try { P.__spjPendente = false; } catch (e) {}
        digitar(ed);
      }
    } catch (e) {
      if (window.console) console.error("Barra de formatacao: " + e);
    }
  }

  // a tela do Streamlit recria os elementos a cada atualizacao: se o editor
  // for removido, ele volta no mesmo lugar (com o texto e a selecao do usuario)
  function vigiarEdicao() {
    try {
      if (!P.MutationObserver) return;
      if (P.__spjObs) { try { P.__spjObs.disconnect(); } catch (e) {} }
      var obs = new P.MutationObserver(function () {
        var ed = P.__spjEditor;
        if (!ed || ed.isConnected) return;
        try {
          var c = achar();
          if (!c) return;
          var ta = c.querySelector("textarea");
          if (!ta) return;
          var raiz = ta.closest('[data-testid="stTextAreaRootElement"]') || ta.parentNode;
          if (!raiz) return;
          raiz.insertBefore(ed, ta);
          var c2 = raiz.closest(".stTextArea");
          if (c2) c2.classList.add("__spj_com_editor__");
          try { restaurarSelecao(); } catch (e) {}
        } catch (e) {}
      });
      obs.observe(P.document.body, {childList: true, subtree: true});
      P.__spjObs = obs;
    } catch (e) {}
  }

  // manda o texto ao servidor sem tirar o foco: quando o usuario PARA de digitar
  // (2,5 s) ou, no maximo, a cada 15 s. Assim o sistema nao fica "atualizando" sozinho.
  var timerCommit = null;

  function autoComitar(agora) {
    try {
      var ta = caixa();
      if (!ta) return;
      // no primeiro uso so guardamos o valor atual (para saber o que mudou)
      if (ultimo === null) { ultimo = ta.value; ultimoIniciado = true; }
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
  vigiarEdicao();
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
        html_js = (_JS_BARRA.replace("__ALVO__", alvo)
                          .replace("__CHAVE__", chave)
                          .replace("__CSS_BARRA__", json.dumps(_CSS_BARRA)))
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


def _caso_id():
    """Identificador do caso em edição (separa o backup do navegador por caso)."""
    return str(st.session_state.get("_caso_id") or "").strip() or "padrao"


def _chave_backup_relato():
    """Chave do backup do navegador: uma por caso, para nao voltar texto de outro."""
    return "spj_relato_" + (_dono() or "admin") + "_" + _caso_id()


def _dados_rascunho():
    """O que fica guardado automaticamente para não perder o trabalho."""
    return {
        "narrativa": st.session_state.get("narrativa", ""),
        "fatos": st.session_state.get("fatos_edit", ""),
        "peca": st.session_state.get("peca_edit", ""),
        "pend": st.session_state.get("pend", ""),
        "dados": st.session_state.get("dados", ""),
        "nome_caso": st.session_state.get("nome_caso", ""),
        "caso_id": _caso_id(),
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
    if st.session_state.get("_iniciando_limpo"):
        st.session_state["_rascunho_recuperado"] = True
        return
    st.session_state["_rascunho_recuperado"] = True
    try:
        r = motor.carregar_rascunho(_dono())
    except Exception:
        return
    if not r:
        return
    # se acabamos de iniciar um caso novo limpo nesta sessao, nao traga rascunho antigo
    if str(st.session_state.get("_caso_id") or "").startswith("novo_"):
        return
    achou = False
    for campo, chave in (("narrativa", "narrativa"), ("fatos", "fatos_edit"),
                          ("peca", "peca_edit"), ("pend", "pend")):
        valor = str(r.get(campo) or "")
        if valor.strip() and not st.session_state.get(chave):
            st.session_state[chave] = valor
            achou = True
    # devolve tambem o nome do caso e o "id" do caso: assim o salvamento cai no
    # nome certo e o backup do navegador continua sendo o mesmo
    if str(r.get("nome_caso") or "").strip() and not st.session_state.get("nome_caso"):
        st.session_state["nome_caso"] = str(r["nome_caso"]).strip()
    if str(r.get("caso_id") or "").strip() and not st.session_state.get("_caso_id"):
        st.session_state["_caso_id"] = str(r["caso_id"]).strip()
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
    st.session_state["_corr_msg"] = f"✅ Corrigido: “{errado}� → “{certo}�"
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
    # Oculta sugestões "usado pela última vez" conforme solicitação
    return


def complementos_cidade(prefixo):
    """Cidade (pesquisável por iniciais) e UF (pesquisável), com opção de digitar outra cidade."""
    c5, c6 = st.columns([3, 1])
    uf = st.session_state.get(f"{prefixo}_uf", "—")
    lista = MUNICIPIOS.get(SIGLA_UF.get(uf, ""), []) if uf != "—" else []
    opcoes = ["—"] + lista + (["�� outra (digitar)"] if uf != "—" else [])
    c5.selectbox("Cidade", opcoes, key=f"{prefixo}_cidade")
    c6.selectbox("UF", OPCOES_UF, key=f"{prefixo}_uf")
    if st.session_state.get(f"{prefixo}_cidade", "") == "�� outra (digitar)":
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
    if cidade == "�� outra (digitar)":
        cidade = _g(f"{prefixo}_cidade_livre") or cidade
    if cidade and cidade != "�� outra (digitar)":
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


def _documentos_parte(prefixo, indice):
    docs = []
    cpf = str(st.session_state.get(f"{prefixo}_cpf_{indice}", "") or "").strip()
    if cpf:
        docs.append(f"CPF: {cpf}")
    cnpj = str(st.session_state.get(f"{prefixo}_cnpj_{indice}", "") or "").strip()
    if cnpj:
        docs.append(f"CNPJ: {cnpj}")
    rg = str(st.session_state.get(f"{prefixo}_rg_{indice}", "") or "").strip()
    if rg:
        docs.append(f"RG: {rg}")
    return docs


def _endereco_resumo_parte(prefixo, indice):
    partes = []
    rua = str(st.session_state.get(f"{prefixo}_rua_{indice}", "") or "").strip()
    num = str(st.session_state.get(f"{prefixo}_num_{indice}", "") or "").strip()
    if rua:
        partes.append(rua + (f", {num}" if num else ""))
    bairro = str(st.session_state.get(f"{prefixo}_bairro_{indice}", "") or "").strip()
    if bairro:
        partes.append(f"bairro {bairro}")
    cidade = str(st.session_state.get(f"{prefixo}_cidade_{indice}", "") or "").strip()
    if cidade == "�� outra (digitar)":
        cidade = str(st.session_state.get(f"{prefixo}_cidade_livre_{indice}", "") or "").strip() or cidade
    if cidade and cidade != "�� outra (digitar)":
        ufv = str(st.session_state.get(f"{prefixo}_uf_{indice}", "") or "").strip()
        uf = SIGLA_UF.get(ufv, ufv)
        partes.append(cidade + (f" – {uf}" if uf and uf != "—" else ""))
    cep = str(st.session_state.get(f"{prefixo}_cep_{indice}", "") or "").strip()
    if cep:
        partes.append(f"CEP {cep}")
    compl = str(st.session_state.get(f"{prefixo}_compl_{indice}", "") or "").strip()
    if compl:
        partes.append(compl)
    return ", ".join(partes)


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


def _cadastro_parte(prefixo, rotulo, indice=0):
    """Painel 'cadastro' de uma parte, com endereço em campos com memória."""
    chave_exp = f"exp_{prefixo}_{indice}"
    with st.expander(f"📋 {rotulo} (cadastro)", expanded=True):
        st.text_input("Nome completo", key=f"{prefixo}_nome_{indice}", placeholder="Nome e sobrenome")
        c1, c2 = st.columns(2)
        c1.text_input("Estado civil", key=f"{prefixo}_civil_{indice}", placeholder="ex.: casado(a)")
        c2.text_input("Profissão", key=f"{prefixo}_prof_{indice}", placeholder="ex.: vendedor(a)")
        d1, d2, d3 = st.columns(3)
        d1.text_input("CPF", key=f"{prefixo}_cpf_{indice}", placeholder="000.000.000-00")
        d2.text_input("CNPJ", key=f"{prefixo}_cnpj_{indice}", placeholder="00.000.000/0001-00")
        d3.text_input("RG", key=f"{prefixo}_rg_{indice}", placeholder="nº ...")
        st.markdown("**Endereço**")
        l1, l2 = st.columns([3, 1])
        l1.text_input("Rua", key=f"{prefixo}_rua_{indice}", placeholder="Av. ...")
        l2.text_input("Número", key=f"{prefixo}_num_{indice}", placeholder="123")
        _memorizar("mem_ruas", st.session_state.get(f"{prefixo}_rua_{indice}", ""))
        l3, l4 = st.columns([3, 1])
        l3.text_input("Bairro", key=f"{prefixo}_bairro_{indice}", placeholder="Centro")
        l4.text_input("CEP", key=f"{prefixo}_cep_{indice}", placeholder="00000-000")
        _memorizar("mem_bairros", st.session_state.get(f"{prefixo}_bairro_{indice}", ""))
        _memorizar("mem_ceps", st.session_state.get(f"{prefixo}_cep_{indice}", ""))
        # cidade/UF por índice
        c5, c6 = st.columns([3, 1])
        uf = st.session_state.get(f"{prefixo}_uf_{indice}", "—")
        lista = MUNICIPIOS.get(SIGLA_UF.get(uf, ""), []) if uf != "—" else []
        opcoes = ["—"] + lista + (["�� outra (digitar)"] if uf != "—" else [])
        c5.selectbox("Cidade", opcoes, key=f"{prefixo}_cidade_{indice}")
        c6.selectbox("UF", OPCOES_UF, key=f"{prefixo}_uf_{indice}")
        if st.session_state.get(f"{prefixo}_cidade_{indice}", "") == "�� outra (digitar)":
            st.text_input("Digite a cidade", key=f"{prefixo}_cidade_livre_{indice}", placeholder="Nome da cidade")
        st.text_input("Complemento (apto/bloco, e-mail...)", key=f"{prefixo}_compl_{indice}")


def compor_dados():
    """Junta os campos do cabeçalho da peça num único bloco enviado à IA."""
    r1, r2 = ROTULOS_PARTES.get(st.session_state.get("f_rotulo", "Requerente / Requerido"),
                                ("Requerente", "Requerido"))
    partes = []
    if _g("f_juizo"):
        partes.append(f"Juízo/Vara: {_g('f_juizo')}")
    req_count = int(st.session_state.get("req_count", 1) or 1)
    for i in range(req_count):
        endr1 = _endereco_resumo_parte("req", i)
        q1 = _qualificacao(st.session_state.get(f"req_nome_{i}", ""), st.session_state.get(f"req_civil_{i}", ""),
                           st.session_state.get(f"req_prof_{i}", ""), _documentos_parte("req", i), endr1)
        if q1:
            rot = r1 if req_count == 1 else f"{r1} {i+1}"
            partes.append(f"{rot}: {q1}")
    rdo_count = int(st.session_state.get("rdo_count", 1) or 1)
    for i in range(rdo_count):
        endr2 = _endereco_resumo_parte("rdo", i)
        q2 = _qualificacao(st.session_state.get(f"rdo_nome_{i}", ""), st.session_state.get(f"rdo_civil_{i}", ""),
                           st.session_state.get(f"rdo_prof_{i}", ""), _documentos_parte("rdo", i), endr2)
        if q2:
            rot = r2 if rdo_count == 1 else f"{r2} {i+1}"
            partes.append(f"{rot}: {q2}")
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
    """Limpa o caso em edição, mantendo apenas as memórias de endereço."""
    for chave, inicial in DEFAULTS.items():
        if str(chave).startswith("mem_"):
            continue
        st.session_state[chave] = inicial.copy() if isinstance(inicial, list) else inicial
    # partes (várias por caso), respostas, seleções e restos do trabalho anterior
    for k in list(st.session_state.keys()):
        sk = str(k)
        if _RE_CHAVE_PARTE.match(sk):
            st.session_state.pop(k, None)
            continue
        if sk.startswith(("resp_", "sel_", "corr_", "dj_", "exp_req_", "exp_rdo_")):
            st.session_state.pop(k, None)
            continue
        if re.match(r"^(req|rdo)_(nome|civil|prof|cpf|cnpj|rg|rua|num|bairro|cep|uf|cidade|cidade_livre|compl|endr)_\d+$", sk):
            st.session_state.pop(k, None)
            continue
        if re.match(r"^(req|rdo)_(nome|civil|prof|cpf|cnpj|rg|rua|num|bairro|cep|uf|cidade|cidade_livre|compl|endr)$", sk):
            st.session_state.pop(k, None)
            continue
    st.session_state["req_count"] = 1
    st.session_state["rdo_count"] = 1
    st.session_state["chat_hist"] = []
    st.session_state["chat_pergunta"] = ""
    st.session_state["relato_preview"] = False
    for k in ("export_docx", "export_pdf", "_correcoes", "_revisou", "_corr_msg",
              "_corr_pendente", "_rascunho_msg", "_rascunho_ultimo", "analise_doc", "analise_alertas"):
        st.session_state.pop(k, None)
    # garantir chaves indexadas zeradas
    for prefixo in ("req", "rdo"):
        for i in range(5):  # limpar até 5 possíveis
            for campo in CAMPOS_PARTE:
                st.session_state[f"{prefixo}_{campo}_{i}"] = ""


def iniciar_limpo(nome):
    """Começa uma peça nova, zerando o formulário e fixando o nome do caso."""
    st.session_state["_iniciando_limpo"] = True
    st.session_state["_rascunho_recuperado"] = True  # impede que o rascunho antigo seja trazido de volta
    _reseta_formulario()
    st.session_state["nome_caso"] = nome
    # id novo = backup do navegador novo (o texto do caso anterior não volta)
    st.session_state["_caso_id"] = "novo_" + datetime.now().strftime("%Y%m%d%H%M%S%f")
    st.session_state["dados"] = compor_dados()
    # o rascunho é do trabalho anterior: some para não voltar na próxima abertura
    try:
        motor.apagar_rascunho(_dono())
    except Exception:
        pass
    st.session_state["_rascunho_ultimo"] = None
    st.session_state.pop("_rascunho_msg", None)
    # grava ja o rascunho novo (vazio): se a pagina for recarregada, o sistema
    # volta para ESTE caso (nome e id certos), e nao para o trabalho anterior
    try:
        _salvar_rascunho(forcar=True)
    except Exception:
        pass


def _dados_caso():
    """Monta o dicionário completo do caso para salvar."""
    dados = {
        "f_juizo": st.session_state.get("f_juizo", ""),
        "f_outros": st.session_state.get("f_outros", ""),
        "f_rotulo": st.session_state.get("f_rotulo", "Requerente / Requerido"),
        "req_count": int(st.session_state.get("req_count", 1) or 1),
        "rdo_count": int(st.session_state.get("rdo_count", 1) or 1),
        "narrativa": st.session_state.get("narrativa", ""),
        "fatos": st.session_state.get("fatos_edit", ""),
        "peca": st.session_state.get("peca_edit", ""),
        "pend": st.session_state.get("pend", ""),
        "alertas": st.session_state.get("alertas", []),
        "usadas": st.session_state.get("usadas", []),
        "base_nome": st.session_state.get("base_nome", ""),
        "dados": compor_dados(),
    }
    dados.update(_partes_salvas())
    return dados


def _partes_salvas():
    """Todas as partes do caso (com os indices, para salvar mais de uma)."""
    dados = {}
    for prefixo in ("req", "rdo"):
        qtd = int(st.session_state.get(f"{prefixo}_count", 1) or 1)
        for i in range(qtd):
            for campo in CAMPOS_PARTE:
                chave = f"{prefixo}_{campo}_{i}"
                dados[chave] = st.session_state.get(chave, "")
    return dados


def _aplicar_caso_salvo(nome, caso):
    """Traz para a tela um caso salvo (formato novo ou antigo)."""
    _reseta_formulario()
    st.session_state["nome_caso"] = nome
    st.session_state["_caso_id"] = "caso_" + str(nome)
    st.session_state.update(
        f_rotulo=caso.get("f_rotulo", "Requerente / Requerido"),
        f_juizo=caso.get("f_juizo", ""),
        f_outros=caso.get("f_outros", caso.get("dados", "")),
        narrativa=caso.get("narrativa", ""),
        fatos_edit=caso.get("fatos", ""), peca_edit=caso.get("peca") or "",
        pend=caso.get("pend", ""), alertas=caso.get("alertas") or [],
        usadas=caso.get("usadas") or [],
    )
    for prefixo in ("req", "rdo"):
        qtd = int(caso.get(f"{prefixo}_count") or 0) or 1
        antigo = {c: caso.get(f"{prefixo}_{c}", "") for c in CAMPOS_ENDERECO}
        antigo.update(
            nome=caso.get(f"{prefixo}_nome")
                 or caso.get("f_autor" if prefixo == "req" else "f_reu", ""),
            civil=caso.get(f"{prefixo}_civil", ""),
            prof=caso.get(f"{prefixo}_prof", ""),
            compl=caso.get(f"{prefixo}_compl") or caso.get(f"{prefixo}_endr", ""),
        )
        cpf, cnpj, rg = _doc_do_caso(caso, prefixo)
        antigo.update(cpf=cpf, cnpj=cnpj, rg=rg)
        st.session_state[f"{prefixo}_count"] = qtd
        for i in range(qtd):
            novo_formato = any(f"{prefixo}_{c}_{i}" in caso for c in CAMPOS_PARTE)
            for campo in CAMPOS_PARTE:
                chave = f"{prefixo}_{campo}_{i}"
                if novo_formato:
                    st.session_state[chave] = caso.get(chave, "")
                else:
                    st.session_state[chave] = antigo.get(campo, "") if i == 0 else ""
    st.session_state["dados"] = compor_dados()
    base_salva = caso.get("base_nome", "")
    if base_salva and base_salva in motor.listar_bases():
        st.session_state["base_nome"] = base_salva
        st.session_state["base_editor_nome"] = base_salva


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


st.title("⚖� Sistema de Peças Judiciais")
st.caption("A IA só cita o que está na BASE LEGAL. Confira sempre os alertas antes de protocolar.")

if motor.modo_uso()["uso_pago"]:
    st.success("🔒 Conta declarada como **paga/Vertex**: o provedor não usa seus dados para treinar modelos.", icon="🔒")
else:
    st.warning(
        "⚠� **Modo gratuito**: a cota grátis do Gemini PODE usar seus dados para treinamento e ser lida por "
        "revisores humanos. Para dados reais de cliente, mantenha o **Modo seguro** ligado (lateral) e/ou "
        "ative faturamento ou use Vertex AI nas **Configurações**."
    )

# ------------------------------------------------------------------ barra lateral
with st.sidebar:
    st.markdown(
        "<div style='text-align:center; font-size:34px; line-height:1; margin-bottom:4px;'>⚖�</div>",
        unsafe_allow_html=True,
    )
    st.caption(f"Sessão: {st.session_state.get('usuario', 'advogado(a)')}")
    if st.button("🚪 Sair do sistema", width="stretch"):
        st.session_state["autenticado"] = False
        st.session_state["chat_hist"] = []
        st.session_state["_cookie_apagar"] = True
        # ao sair, a verificacao de seguranca e pedida de novo no proximo acesso
        st.session_state["captcha_humano"] = False
        st.session_state["captcha_ok"] = False
        st.session_state["captcha_sel"] = []
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
                    if b2.button("🗑� Recusar", key=f"recus_{u.get('usuario')}", width="stretch"):
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

    st.header("� Casos salvos")
    casos = motor.listar_casos(_dono())
    if casos:
        escolhido = st.selectbox("Abrir caso", ["—"] + casos, key="caso_escolhido")
        c1, c2 = st.columns(2)
        if c1.button("Abrir", width="stretch") and escolhido != "—":
            caso = motor.carregar_caso(escolhido, _dono())
            _aplicar_caso_salvo(escolhido, caso)
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
        elif nome in motor.listar_casos(_dono()):
            st.warning("Já existe um caso com esse nome. Escolha outro nome (ou abra o caso existente).")
        else:
            caminho = motor.salvar_caso(nome, {}, _dono())
            iniciar_limpo(caminho.stem)
            # a base legal tem regra propria de nome (sem espacos/acentos)
            base_novo = re.sub(r"[^A-Za-z0-9_\-]", "_", caminho.stem).strip("_") or "base_do_caso"
            try:
                if base_novo not in motor.listar_bases():
                    motor.salvar_base(base_novo, [])
            except Exception:
                pass
            st.session_state["base_nome"] = base_novo
            st.session_state["base_editor_nome"] = base_novo
            # limpa o campo do nome na proxima execucao (nao pode mudar agora)
            st.session_state["_p_nova_peca"] = ""
            st.rerun()

    st.divider()
    st.subheader("� Gerar peça")
    modelo_nome = st.selectbox("Modelo da peça", motor.listar_modelos(), key="modelo_nome",
                               placeholder="Escolha o modelo da peça")
    st.caption("Sugerido conforme os fatos; você pode trocar.")
    base_nome = st.selectbox("Base legal", motor.listar_bases(), key="base_nome",
                              placeholder="Escolha a base legal")
    with st.expander("Ver a base legal carregada"):
        for item in motor.carregar_base(base_nome):
            st.markdown(f"**{item['referencia']}** — status: `{item['status']}`")
            st.write(item["texto"])
    if st.button("� Gerar a peça", type="primary", width="stretch"):
        fatos = st.session_state["fatos_edit"]
        if not fatos.strip():
            st.warning("Não há fatos ainda. Preencha o relato e use 'Limpar fatos' na aba 2�⃣.")
        else:
            st.session_state.update(peca_edit="", alertas=[], usadas=[])
            st.session_state.pop("export_docx", None)
            st.session_state.pop("export_pdf", None)
            base = motor.carregar_base(base_nome)
            _anon = None
            if st.session_state.get("modo_seguro", True):
                try:
                    _anon = motor.Anonimizador([])
                except Exception:
                    _anon = None
            with st.status("Redigindo a peça...", expanded=False) as s:
                bruto = tentar(motor.gerar_peca, motor.carregar_modelo(modelo_nome),
                               st.session_state["dados"], fatos, base, _anon)
                if bruto:
                    conf = motor.conferir_citacoes(bruto, base, f"{st.session_state['dados']}\n{fatos}")
                    st.session_state.update(peca_edit=conf["texto"], alertas=conf["alertas"], usadas=conf["usadas"])
                    s.update(label="Peça gerada e conferida", state="complete")
                else:
                    s.update(label="Falha ao gerar", state="error")

    st.divider()
    nome_caso = st.text_input("Nome do caso (para salvar)", key="nome_caso")
    if st.button("💾 Salvar caso atual", width="stretch"):
        nome_limpo = (nome_caso or "").strip()
        if not nome_limpo:
            st.warning("Dê um nome antes de salvar.")
        else:
            caminho = motor.salvar_caso(nome_limpo, _dados_caso(), _dono())
            st.session_state["_caso_id"] = "caso_" + caminho.stem
            st.success(f"Salvo como **{caminho.stem}** — está em � Casos salvos.")

    st.divider()
    st.subheader("🛡� Segurança (LGPD)")
    st.checkbox("Modo seguro: anonimizar antes de enviar", value=True, key="modo_seguro",
                help="Troca nomes, CPF, e-mails etc. por marcadores antes de enviar à IA e restaura na peça final.")

    st.divider()
    with st.expander("⚙� Configurações do provedor"):
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

    with st.expander("�� Backup na nuvem (nuvem → seu PC)"):
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

    with st.expander("�� Trocar usuário / senha"):
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
    st.subheader("🗂� Curadoria da base legal")
    st.caption("Só o que estiver aqui pode ser citado. Mantenha o status em 'verificado' após conferir o texto oficial.")
    bases = motor.listar_bases()
    if not bases:
        st.info("Nenhuma base encontrada.")
        return
    base_nome = st.selectbox("Base", bases, key="base_editor_nome")
    itens = motor.carregar_base(base_nome)
    df = pd.DataFrame(itens or [{"id": "", "referencia": "", "status": "conferir", "texto": "", "fonte": ""}])
    df.insert(0, "apagar", False)
    st.caption("Para tirar um item que você não quer mais: marque a caixa **🗑� apagar** e clique em "
               "**🗑� Apagar marcados**. Você também pode adicionar novas linhas ao fim da tabela.")
    editado = st.data_editor(
        df, num_rows="dynamic", width="stretch", hide_index=True,
        column_config={
            "apagar": st.column_config.CheckboxColumn("🗑� apagar", default=False, width="small"),
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
    if c2.button("🗑� Apagar marcados"):
        if not any(marcados):
            st.info("Marque ao menos um item na coluna **🗑� apagar** para apagar.")
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
        if st.button("🗑� Apagar base inteira", disabled=not conf_base):
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
def _datajud_consultar_numero(numero, alias_preferido=None, busca_ampla=False):
    """Consulta o processo deduzindo o tribunal pelo número (com cache)."""
    fn = getattr(decisoes, "consultar_processo_numero", None)
    if not fn:
        return decisoes.consultar_processo(alias_preferido, numero), alias_preferido
    return fn(numero, alias_preferido, busca_ampla)


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
    with st.sidebar:
        st.markdown("#### Decisoes")
        subaba = st.radio("Secao", ["Pesquisar jurisprudencia", "Atalhos oficiais"], key="sub_decisoes", label_visibility="collapsed")
    if subaba == "Pesquisar jurisprudencia":
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

    elif subaba == "Atalhos oficiais":
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
        consultar = b1.button("� Consultar processo", type="primary")
        if b2.button("🧹 Limpar / nova consulta"):
            st.session_state["dj_versao"] = st.session_state.get("dj_versao", 0) + 1
            st.session_state.pop("dj_procs", None)
            st.session_state.pop("dj_erro", None)
            st.session_state.pop("dj_nome_busca", None)
            st.session_state.pop("dj_alias", None)
            st.session_state.pop("dj_consultou", None)
            st.rerun()
        busca_ampla = st.checkbox(
            "🔎 Se não encontrar, procurar em todos os tribunais do ramo",
            key="dj_busca_ampla",
            help="Útil quando o número do processo foi digitado com a vara errada "
                 "ou quando o processo não está no tribunal escolhido acima.")
        if consultar:
            if not numero.strip():
                st.warning("Digite o número do processo.")
            else:
                try:
                    with st.status("Consultando o DataJud...", expanded=False) as s:
                        procs, achado_em = _datajud_consultar_numero(
                            numero, alias, busca_ampla)
                        s.update(label=f"{len(procs)} processo(s) encontrado(s)",
                                 state="complete" if procs else "error")
                    st.session_state["dj_procs"] = procs
                    st.session_state["dj_alias"] = achado_em or alias
                    st.session_state["dj_erro"] = ""
                    st.session_state["dj_consultou"] = True
                except Exception as e:
                    st.session_state["dj_procs"] = []
                    st.session_state["dj_alias"] = alias
                    st.session_state["dj_erro"] = str(e)
                    st.session_state["dj_consultou"] = True
        if st.session_state.get("dj_erro"):
            st.error(st.session_state["dj_erro"])
        procs = st.session_state.get("dj_procs") or []
        consultou = bool(st.session_state.get("dj_consultou"))
        if not procs and not st.session_state.get("dj_erro") and not consultou:
            st.info("Digite o número e clique em **� Consultar processo**.")
        alias_uso = st.session_state.get("dj_alias") or alias
        if procs and alias_uso != alias:
            st.info("✅ O processo foi encontrado no **%s**. (O número do processo "
                    "indica esse tribunal; o da tela era %s.)"
                    % (_nome_tribunal(alias_uso), _nome_tribunal(alias)))
        if not procs and consultou and not st.session_state.get("dj_erro"):
            st.warning("Não encontrei esse processo no **%s**.\n\n"
                       "Confira o número (20 dígitos) ou marque a opção de procurar "
                       "em todos os tribunais do ramo. Processos em **segredo de "
                       "justiça** não aparecem no DataJud."
                       % _nome_tribunal(alias))
        for p in procs:
            st.markdown(f"### {p['numero']} — {p['tribunal']} ({p['grau']})")
            st.caption("Abrir o processo direto no site oficial:")
            for rotulo_link, url_link in _links_processo(alias_uso, p["numero"], p.get("grau")):
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
            comunica = _comunicacoes_processo(alias_uso, p["numero"])
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
        if n1.button("� Buscar por nome", type="primary"):
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
                st.success(f"✅ Encontrei {len(achados)} processo(s) em nome de “{alvo}� "
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
                    st.warning(f"Não encontrei “{alvo}� no e-SAJ. Procure no PJe:")
                links = _links_processo_nome(alias, alvo)
                colunas = st.columns(len(links))
                for coluna, (rotulo_link, url_link) in zip(colunas, links):
                    coluna.link_button(rotulo_link, url_link)
        else:
            st.info("Digite o nome da parte e clique em **� Buscar por nome**.")


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
            coluna.download_button(f"⬇� Baixar {p.suffix}", p.read_bytes(),
                                   file_name=p.name, key=f"dl_{chave}")


# ------------------------------------------------------------------ navegacao principal
st.sidebar.markdown("### Navegacao")
menu_opcoes = ["1) Caso", "2) Fatos", "3) Peca", "4) Conferencia", "Base legal", "Anexo/Analise", "Decisoes & Processos", "Acompanhar processo", "Chat IA"]
aba_selecionada = st.sidebar.radio("Ir para", menu_opcoes, label_visibility="collapsed", key="menu_navegacao")
aba_caso = st.container() if aba_selecionada == "1) Caso" else None
aba_fatos = st.container() if aba_selecionada == "2) Fatos" else None
aba_peca = st.container() if aba_selecionada == "3) Peca" else None
aba_conf = st.container() if aba_selecionada == "4) Conferencia" else None
aba_base_ui = st.container() if aba_selecionada == "Base legal" else None
aba_anexo = st.container() if aba_selecionada == "Anexo/Analise" else None
aba_decisoes_ui = st.container() if aba_selecionada == "Decisoes & Processos" else None
aba_processos_ui = st.container() if aba_selecionada == "Acompanhar processo" else None
aba_chat = st.container() if aba_selecionada == "Chat IA" else None

with aba_caso:
    st.subheader("Dados da peça")
    st.caption("Preencha como no cabeçalho da peça. O que ficar em branco, a IA identifica nos fatos na hora "
               "de redigir; no final tudo sai junto no cabeçalho.")
    st.text_input("Juízo / Vara / Tribunal", key="f_juizo",
                  placeholder="ex.: Juizado Especial Cível da Comarca de Fortaleza/CE")

    st.selectbox("Como chamar as partes", list(ROTULOS_PARTES), key="f_rotulo",
                 help="Requerente/Requerido no geral; Autor/Réu em ação criminal; Recorrente/Recorrido em recurso; etc.")
    r1, r2 = ROTULOS_PARTES[st.session_state.get("f_rotulo", "Requerente / Requerido")]
    st.markdown(f"### {r1}(s)")
    if "req_count" not in st.session_state:
        st.session_state["req_count"] = 1
    for i in range(st.session_state["req_count"]):
        _cadastro_parte("req", r1 if i == 0 else f"{r1} {i+1}", indice=i)
    if st.button(f"➕ Adicionar outro(a) {r1}", key="add_req"):
        st.session_state["req_count"] += 1
        st.rerun()
    st.divider()
    st.markdown(f"### {r2}(s)")
    if "rdo_count" not in st.session_state:
        st.session_state["rdo_count"] = 1
    for i in range(st.session_state["rdo_count"]):
        _cadastro_parte("rdo", r2 if i == 0 else f"{r2} {i+1}", indice=i)
    if st.button(f"➕ Adicionar outro(a) {r2}", key="add_rdo"):
        st.session_state["rdo_count"] += 1
        st.rerun()
    st.text_area("Demais dados (datas, valores, números, o que mais importar)", key="f_outros",
                 height=100, placeholder="Digite aqui as datas, valores e outros dados importantes")
    cbl1, cbl2 = st.columns([9, 1])
    with cbl2:
        if st.button("💾", help="Salvar dados das partes", key="salvar_dados_partes", use_container_width=True):
            st.session_state["dados"] = compor_dados()
            try:
                _salvar_rascunho(forcar=True)
            except Exception:
                pass
            st.toast("Dados dos requerente/requerido salvos", icon="💾")
    with cbl1:
        if st.button("🔄 Atualizar bloco para a IA", key="atualizar_bloco_ia", use_container_width=True):
            st.session_state["dados"] = compor_dados()
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
        if c1.button("🗑� Apagar relatório", width="stretch"):
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
        st.caption("Para a IA poder citar uma norma na peça, cadastre-a na aba 🗂� Base legal (status 'verificado').")

with aba_fatos:
    st.subheader("Relato do cliente")
    if st.session_state.get("_rascunho_msg"):
        st.info(st.session_state.pop("_rascunho_msg"), icon="💾")
    audio = st.audio_input("🎙� Grave o relato (opcional)")
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
                _chave_backup_relato())
    _aplicar_correcao_pendente()
    if st.session_state.get("_corr_msg"):
        st.success(st.session_state.pop("_corr_msg"), icon="��")
    st.text_area("Relato (dite ou escreva o que o cliente contou)", key="narrativa", height=150,
                 placeholder="Digite seu texto aqui")
    c_prev, c_aviso = st.columns([1, 3])
    if c_prev.checkbox("� Ver com formatação", key="relato_preview"):
        with st.container(border=True):
            st.markdown(previa_texto(st.session_state.get("narrativa", "")),
                        unsafe_allow_html=True)
    c_aviso.caption("💾 Salvo sozinho enquanto você digita (no seu navegador e no sistema). "
                    "Pode deixar o sistema aberto sem medo de perder o que escreveu.")
    st.caption("�� **Palavra errada?** Ela fica **sublinhada em vermelho** no campo acima: "
               "clique com o botão direito na palavra e escolha a correção sugerida. "
               "Exemplo: “A cliente comprou passagem de Fortaleza para São Paulo no dia 10/03/2026…�")

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
            if col1.button(f"� {achado['errado']}  →  ✅ {achado['certo']}", key=f"corr_{i}"):
                st.session_state["_corr_pendente"] = (achado["errado"], achado["certo"])
                st.rerun()
            col2.caption(achado.get("motivo", ""))
    elif st.session_state.get("_revisou"):
        st.success("✅ Não encontrei erros de escrita no relato.")

    if st.button("�� Corrigir e organizar fatos (gramática/ABNT)", type="primary"):
        if not st.session_state["narrativa"].strip():
            st.warning("Escreva ou dite o relato primeiro.")
        else:
            _salvar_rascunho()
            with st.status("Corrigindo e organizando...", expanded=False) as s:
                resultado = tentar(motor.limpar_fatos, st.session_state["dados"],
                                   motor.texto_simples(st.session_state["narrativa"]),
                                   anonimizador)
                s.update(label="Texto corrigido" if resultado else "Falha",
                         state="complete" if resultado else "error")
            if resultado:
                st.session_state["fatos_edit"] = resultado[0]
                st.session_state["pend"] = resultado[1]
                sugerido = motor.identificar_modelo(resultado[0], motor.listar_modelos())
                if sugerido and sugerido != st.session_state.get("modelo_nome"):
                    st.session_state["modelo_nome"] = sugerido
                st.success("Texto corrigido e organizado em parágrafos abaixo. Se houver perguntas, responda logo abaixo.")

    st.divider()
    st.subheader("Fatos corrigidos/organizados (edite à vontade)")
    if not st.session_state["fatos_edit"]:
        st.info("Escreva ou dite o relato acima e clique em 'Corrigir e organizar fatos' para ver o resultado aqui.")
    else:
        st.text_area("Fatos corrigidos", key="fatos_edit", height=320,
                     placeholder="O texto corrigido e organizado em parágrafos aparece aqui — pode editar à vontade")

    st.divider()
    st.subheader("� Gerar peça nesta aba")
    modelo_nome = st.session_state.get("modelo_nome") or (motor.listar_modelos()[0] if motor.listar_modelos() else "")
    base_nome = st.session_state.get("base_nome") or (motor.listar_bases()[0] if motor.listar_bases() else None)
    if st.button("� Gerar a peça", type="primary", use_container_width=True):
        fatos = st.session_state.get("fatos_edit") or ""
        if not fatos.strip():
            st.warning("Corrija/organize os fatos primeiro ou cole o relato corrigido acima.")
        else:
            st.session_state.update(peca_edit="", alertas=[], usadas=[])
            st.session_state.pop("export_docx", None)
            st.session_state.pop("export_pdf", None)
            base = motor.carregar_base(base_nome) if base_nome else []
            _anon = None
            if st.session_state.get("modo_seguro", True):
                try:
                    _anon = motor.Anonimizador([])
                except Exception:
                    _anon = None
            with st.status("Redigindo a peça...", expanded=False) as s:
                bruto = tentar(motor.gerar_peca, motor.carregar_modelo(modelo_nome),
                               st.session_state.get("dados", ""), fatos, base, _anon)
                if bruto:
                    conf = motor.conferir_citacoes(bruto, base, f"{st.session_state.get('dados','')}\n{fatos}")
                    st.session_state.update(peca_edit=conf["texto"], alertas=conf["alertas"], usadas=conf["usadas"])
                    s.update(label="Peça gerada e conferida", state="complete")
                else:
                    s.update(label="Falha ao gerar", state="error")
            st.rerun()

    if st.session_state.get("peca_edit"):
        st.divider()
        st.subheader("Peça gerada (edite à vontade)")
        texto = st.text_area("Texto da peça", key="peca_edit", height=520,
                             placeholder="A peça aparece aqui — pode corrigir antes de exportar")
        exportar(texto)

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
        st.info("Gere a peça na aba 2�⃣.")
    else:
        texto = st.text_area("Texto da peça", key="peca_edit", height=520,
                         placeholder="A peça aparece aqui — pode corrigir antes de exportar")
        exportar(texto)

with aba_conf:
    st.subheader("� Sugestões de jurisprudência (conferir)")
    st.warning(
        "A IA sugere **fontes para você CONFERIR** na origem. Nada entra na peça automaticamente. "
        "Confirme tribunal, número e tese no site oficial antes de citar."
    )
    if st.button("� Buscar sugestões conforme os fatos", type="primary"):
        fatos = st.session_state["fatos_edit"]
        if not fatos.strip():
            st.warning("Organize os fatos primeiro (aba 2�⃣).")
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
        if c1.button("🗑� Apagar sugestões", width="stretch"):
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
        st.caption("Depois de conferir no site oficial, cadastre na aba 🗂� Base legal com status "
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
    if c1.button("🗑� Limpar conversa", width="stretch"):
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
                try:
                    _resposta = motor.responder_chat(st.session_state["chat_hist"], _contexto, anonimizador)
                except Exception as e:
                    try:
                        motor._LOG.exception("Erro no chat")
                        st.error(motor.mensagem_amigavel(e))
                    except Exception:
                        st.error(str(e))
                    _resposta = None
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
