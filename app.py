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


def _links_processo(alias, numero, grau=None):
    """Links oficiais do processo; tolera um `decisoes` antigo em cache."""
    fn = getattr(decisoes, "links_processo", None)
    if fn:
        return fn(alias, numero, grau)
    return [("🔗 Abrir no site do tribunal", decisoes.link_processo(alias, numero))]


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
.stApp, [data-testid="stAppViewContainer"] { background: #e8ecf1 !important; }
[data-testid="stHeader"] { background: transparent !important; }
.login-head { max-width: 470px; margin: 6vh auto 0 auto; text-align: center; }
.login-logo { font-size: clamp(60px, 14vw, 88px); line-height: 1; margin-bottom: 2px; }
.login-head .login-title, .login-title {
    margin: 0; font-size: 1.7rem; font-weight: 800; letter-spacing: .2px;
    color: #1F4E78 !important;
}
.login-saudacao { font-size: 2.1rem; font-weight: 700; color: #1F4E78; margin: 18px 0 6px 0; font-family: 'Playfair Display', Georgia, 'Times New Roman', serif; }
.login-sub { color: #000000; font-size: 0.95rem; margin: 2px 0 0 0; }
.login-msg { color: #000000; font-size: 0.88rem; font-style: italic; margin: 12px 0 2px 0; }
div[data-testid="stForm"] {
    max-width: 470px; margin: 16px auto 0 auto; background: #ffffff;
    border: 1px solid #d5d9de; border-top: 5px solid #1F4E78; border-radius: 14px;
    padding: 24px 26px 20px 26px;
    box-shadow: 0 14px 34px rgba(15, 23, 42, 0.10);
}
div[data-testid="stForm"] label { color: #000000 !important; font-weight: 600; }
div[data-testid="stForm"] [data-testid="stTextInputRootElement"],
div[data-testid="stForm"] div[data-baseweb="input"] {
    background: #ffffff !important; border: 1px solid #cbd2d9 !important;
    border-radius: 10px !important;
}
div[data-testid="stForm"] [data-testid="stTextInputRootElement"]:focus-within,
div[data-testid="stForm"] div[data-baseweb="input"]:focus-within {
    background: #ffffff !important; border-color: #cbd2d9 !important;
}
div[data-testid="stForm"] input,
div[data-testid="stForm"] [data-testid="stTextInputRootElement"] input,
div[data-testid="stForm"] div[data-baseweb="input"] input {
    background: #ffffff !important; color: #000000 !important;
    -webkit-text-fill-color: #000000 !important; caret-color: #000000 !important;
}
div[data-testid="stForm"] input:focus,
div[data-testid="stForm"] input:active,
div[data-testid="stForm"] input:hover {
    background: #ffffff !important; color: #000000 !important;
    -webkit-text-fill-color: #000000 !important;
}
div[data-testid="stForm"] input:-webkit-autofill,
div[data-testid="stForm"] input:-webkit-autofill:hover,
div[data-testid="stForm"] input:-webkit-autofill:focus,
div[data-testid="stForm"] input:-webkit-autofill:active {
    -webkit-text-fill-color: #000000 !important;
    -webkit-box-shadow: 0 0 0 1000px #ffffff inset !important;
    box-shadow: 0 0 0 1000px #ffffff inset !important;
}
div[data-testid="stForm"] ::selection { background: #cfe2ff; color: #000000; }
div[data-testid="stForm"] button {
    border-radius: 10px; font-weight: 700; background: #1F4E78; color: #ffffff; border: none;
}
div[data-testid="stForm"] button:hover { background: #2d6aa3; color: #ffffff; }
div[data-testid="stForm"] [data-testid="stTextInputRootElement"] button,
div[data-testid="stForm"] [data-testid="stTextInputRootElement"] button *,
div[data-testid="stForm"] [data-testid="stTextInputRootElement"] [data-baseweb="button"],
div[data-testid="stForm"] [data-testid="stTextInputRootElement"] [role="button"],
div[data-testid="stForm"] [data-baseweb="input"] button,
div[data-testid="stForm"] [data-baseweb="input"] [role="button"] {
    background: transparent !important; background-color: transparent !important;
    border: 0 !important; border-radius: 0 !important; box-shadow: none !important;
    outline: none !important; min-height: 0 !important; height: auto !important;
    min-width: 0 !important; padding: 0 4px !important; color: #000000 !important;
}
/* Esconde o "olhinho"/opções de senha (Streamlit e navegador) */
div[data-testid="stForm"] [data-testid="stTextInputRootElement"] button,
div[data-testid="stForm"] [data-testid="stTextInputRootElement"] [role="button"],
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
div[data-testid="stForm"] input[aria-label="Senha de acesso"] {
    -webkit-text-security: disc !important; letter-spacing: 2px !important;
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
[data-testid="stSidebar"] div[data-baseweb="select"] > div,
[data-testid="stSidebar"] div[data-baseweb="input"] {
    background: #F7F9FA !important; border: 1px solid rgba(255,255,255,0.35) !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.08);
}
[data-testid="stSidebar"] div[data-baseweb="select"] *,
[data-testid="stSidebar"] div[data-baseweb="input"] * {
    color: #1F2933 !important;
}
[data-testid="stSidebar"] .stButton > button, [data-testid="stSidebar"] .stDownloadButton > button,
[data-testid="stSidebar"] button:not([kind]), [data-testid="stSidebar"] a[role="button"] {
    background: rgba(255,255,255,0.16) !important; color: #FFFFFF !important;
    border: 1px solid rgba(255,255,255,0.35) !important;
}
[data-testid="stSidebar"] .stButton > button:hover,
[data-testid="stSidebar"] button:not([kind]):hover, [data-testid="stSidebar"] a[role="button"]:hover {
    background: rgba(255,255,255,0.22) !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"],
[data-testid="stSidebar"] .stFormSubmitButton > button,
[data-testid="stSidebar"] button[kind="primary"], [data-testid="stSidebar"] a[role="button"][class*="primary"] {
    background: var(--azul-escuro) !important; color: #FFFFFF !important;
    border: 1px solid rgba(255,255,255,0.25) !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover,
[data-testid="stSidebar"] .stFormSubmitButton > button:hover,
[data-testid="stSidebar"] button[kind="primary"]:hover, [data-testid="stSidebar"] a[role="button"][class*="primary"]:hover {
    background: var(--azul-petroleo) !important;
}
/* campos brancos */
div[data-baseweb="input"], div[data-baseweb="select"] > div,
div[data-baseweb="base-input"], div[data-baseweb="textarea"] textarea,
[data-testid="stNumberInputContainer"] {
    background: #FFFFFF !important; border-color: var(--botao-busca) !important;
}
input::placeholder, textarea::placeholder { color: var(--placeholder) !important; }
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
/* botões */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
    border-radius: 8px !important; font-weight: 600 !important;
}
.stButton > button[kind="primary"], .stFormSubmitButton > button,
[data-testid="stDownloadButton"] > button {
    background: var(--azul-escuro) !important; color: #ffffff !important;
    border: 1px solid var(--azul-aviso) !important;
}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button:hover {
    background: var(--azul-petroleo) !important; border-color: var(--azul-petroleo) !important;
}
.stButton > button[kind="secondary"] {
    background: var(--botao) !important; color: var(--texto-menu) !important;
    border: 1px solid var(--botao-busca) !important;
}
.stButton > button[kind="secondary"]:hover {
    background: var(--botao-busca) !important; color: var(--texto-menu) !important;
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

# aplica valores definidos por botões (antes de criar os campos, para não dar erro)
for _campo, _pendente in (("fatos_edit", "_p_fatos"), ("peca_edit", "_p_peca"),
                          ("pend", "_p_pend"), ("respostas", "_p_respostas")):
    if _pendente in st.session_state:
        st.session_state[_campo] = st.session_state.pop(_pendente)

if st.session_state.pop("_limpar_respostas", False):
    for _k in [k for k in st.session_state if str(k).startswith("resp_")]:
        del st.session_state[_k]


# ---------------------------------------------------------------- portão de acesso (senha)
if not st.session_state.setdefault("autenticado", False):
    if "msg_abertura" not in st.session_state:
        st.session_state["msg_abertura"] = random.choice(MENSAGENS_ABERTURA)
    st.markdown(_CSS_LOGIN, unsafe_allow_html=True)
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

    modo_login = st.radio("Acesso", ["Entrar", "Criar conta"], horizontal=True,
                          key="login_modo", label_visibility="collapsed")

    if modo_login == "Entrar":
        with st.form("login_form"):
            usuario_entrada = st.text_input("Usuário (ou e-mail)", key="login_usuario")
            senha_entrada = st.text_input("Senha de acesso", key="login_senha")
            entrar = st.form_submit_button("Entrar", type="primary", width="stretch")

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
                      el.style.webkitTextSecurity = 'disc';
                      el.style.letterSpacing = '2px';
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
                  b.onclick = function () {
                    var mostrando = campo.style.webkitTextSecurity === 'none';
                    campo.style.webkitTextSecurity = mostrando ? 'disc' : 'none';
                    campo.style.letterSpacing = mostrando ? '2px' : 'normal';
                    b.innerHTML = mostrando ? ABERTO : FECHADO;
                    b.title = mostrando ? 'Mostrar senha' : 'Ocultar senha';
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
                            st.rerun()
                        except Exception as e:
                            st.error(f"Não deu para definir o acesso: {e}")

        if entrar:
            if motor.verificar_acesso(usuario_entrada, senha_entrada):
                st.session_state.update(autenticado=True, admin=True,
                                        usuario=motor.usuario_acesso() or usuario_entrada.strip())
                st.rerun()
            else:
                resultado = usuarios.autenticar(usuario_entrada, senha_entrada)
                if resultado == usuarios.OK:
                    st.session_state.update(autenticado=True, admin=False, usuario=usuario_entrada.strip())
                    st.rerun()
                elif resultado == usuarios.PENDENTE:
                    st.warning("Sua conta foi criada, mas ainda aguarda a **aprovação** do administrador.")
                else:
                    st.error("Usuário ou senha incorretos.")
    else:
        st.caption("Crie sua conta. Ela será liberada depois que o administrador aprovar.")
        with st.form("cadastro_form"):
            cad_nome = st.text_input("Nome completo", key="cad_nome")
            cad_usuario = st.text_input("E-mail (será seu usuário)", key="cad_usuario")
            cad_s1 = st.text_input("Senha (mínimo 6 caracteres)", type="password", key="cad_s1")
            cad_s2 = st.text_input("Repita a senha", type="password", key="cad_s2")
            criar = st.form_submit_button("Criar conta", type="primary", width="stretch")
        if criar:
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

    st.stop()

# tema visual do interior (aplicado só depois do login)
st.markdown(_CSS_TEMA, unsafe_allow_html=True)


def alerta(nivel, msg):
    icone = {"erro": "❌", "aviso": "⚠️", "ok": "✅"}.get(nivel, "•")
    st.markdown(f"{icone} {msg}")


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
        st.error(str(e))
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
        st.rerun()
    st.divider()

    if st.session_state.get("admin"):
        try:
            pendentes = usuarios.listar_pendentes()
            ativos = usuarios.listar_ativos()
        except Exception:
            pendentes, ativos = [], []
        titulo = f"👥 Contas — {len(pendentes)} pendente(s)" if pendentes else "👥 Contas"
        with st.expander(titulo):
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
    modelo_nome = st.selectbox("Modelo da peça", motor.listar_modelos(), key="modelo_nome")
    st.caption("Sugerido conforme os fatos; você pode trocar.")
    base_nome = st.selectbox("Base legal", motor.listar_bases(), key="base_nome")
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
                            index=1 if _m["uso_pago"] else 0, key="cfg_pago")
        chave_modo = st.selectbox("Modo da chave", ["gemini", "vertex"],
                                  index=0 if _m["modo_chave"] == "gemini" else 1, key="cfg_modo")
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
    editado = st.data_editor(
        df, num_rows="dynamic", width="stretch", hide_index=True,
        column_config={
            "status": st.column_config.SelectboxColumn("status", options=list(motor.STATUS_VALIDOS), required=True),
            "texto": st.column_config.TextColumn("texto", width="large"),
            "fonte": st.column_config.LinkColumn("fonte"),
        },
    )
    c1, c2 = st.columns([1, 3])
    if c1.button("💾 Salvar base"):
        registros = editado.fillna("").to_dict("records")
        ids = [r["id"].strip() for r in registros if r["id"].strip()]
        if len(ids) != len(set(ids)):
            st.error("Há IDs repetidos na base. Cada item precisa de um ID único.")
        elif not ids:
            st.error("A base precisa de pelo menos um item com ID.")
        elif tentar(motor.salvar_base, base_nome, registros) is not None:
            st.success("Base salva.")
    with c2.expander("Criar nova base"):
        nova = st.text_input("Nome da nova base (sem espaços)", key="nova_base")
        if st.button("Criar base vazia"):
            if tentar(motor.salvar_base, nova, []) is not None:
                st.success(f"Base '{nova}' criada.")
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
                    opcoes = _links_processo(alias, numero)
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
aba_caso, aba_fatos, aba_peca, aba_conf, aba_base_ui, aba_anexo, aba_decisoes_ui, aba_processos_ui = st.tabs(
    ["1️⃣ Caso", "2️⃣ Fatos", "3️⃣ Peça", "4️⃣ Conferência", "🗂️ Base legal", "📎 Anexo/Análise",
     "📰 Decisões & Processos", "📌 Acompanhar processo"]
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
    st.text_area("Demais dados (datas, valores, números, o que mais importar)", key="f_outros", height=100)
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
        st.text_area("Relatório (editável)", key="analise_doc", height=420)
        with st.expander("Ver relatório formatado"):
            st.markdown(st.session_state["analise_doc"])
        if st.session_state.get("analise_alertas"):
            with st.expander("Alertas da conferência"):
                for n, m in st.session_state["analise_alertas"]:
                    alerta(n, m)
        st.caption("Para a IA poder citar uma norma na peça, cadastre-a na aba 🗂️ Base legal (status 'verificado').")

with aba_fatos:
    st.subheader("Relato do cliente")
    audio = st.audio_input("🎙️ Grave o relato (opcional)")
    if audio is not None and st.button("Transcrever"):
        with st.status("Transcrevendo...", expanded=False) as s:
            texto = tentar(motor.transcrever_audio, audio.getvalue(), audio.type or "audio/wav")
            s.update(label="Transcrição concluída" if texto else "Falha",
                     state="complete" if texto else "error")
        if texto:
            atual = st.session_state["narrativa"].strip()
            st.session_state["narrativa"] = f"{atual}\n{texto}".strip() if atual else texto
            st.rerun()
    st.text_area("Relato (dite ou escreva o que o cliente contou)", key="narrativa", height=150,
                 placeholder="ex.: 'A cliente comprou passagem de Fortaleza para São Paulo no dia 10/03/2026...'")
    if st.button("🧹 Limpar fatos e listar pendências", type="primary"):
        if not st.session_state["narrativa"].strip():
            st.warning("Escreva ou dite o relato primeiro.")
        else:
            with st.status("Organizando os fatos...", expanded=False) as s:
                resultado = tentar(motor.limpar_fatos, st.session_state["dados"],
                                   st.session_state["narrativa"], anonimizador)
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
        st.text_area("Fatos", key="fatos_edit", height=280)
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
        texto = st.text_area("Texto da peça", key="peca_edit", height=520)
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
        st.text_area("Sugestões (editável)", key="juris_sugerida", height=360)
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
