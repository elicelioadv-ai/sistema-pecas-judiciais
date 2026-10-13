"""
decisoes.py - feed de decisões do STJ e consulta de processos (CNJ/DataJud).

Usa apenas FONTES OFICIAIS e GRATUITAS:
  - STJ - Portal de Dados Abertos (dadosabertos.web.stj.jus.br): acórdãos em JSON,
    com ementa, tese jurídica, relator, órgão julgador, datas etc.
  - CNJ - API Pública do DataJud: metadados e movimentações dos processos públicos
    de todo o Judiciário brasileiro (não traz o texto das decisões).

Sem dependências novas: usa somente a biblioteca padrão do Python.
"""
from __future__ import annotations

import io
import json
import os
import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zipfile

_CABECALHO = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

CKAN_STJ = "https://dadosabertos.web.stj.jus.br/api/3/action"
DATAJUD_BASE = "https://api-publica.datajud.cnj.jus.br"
DATAJUD_KEY_PADRAO = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="

# "Espelhos de acórdãos" do STJ: (rótulo, nome do conjunto de dados no portal)
ORGAOS_STJ = [
    ("Corte Especial", "espelhos-de-acordaos-corte-especial"),
    ("1ª Seção", "espelhos-de-acordaos-primeira-secao"),
    ("2ª Seção", "espelhos-de-acordaos-segunda-secao"),
    ("3ª Seção", "espelhos-de-acordaos-terceira-secao"),
    ("1ª Turma", "espelhos-de-acordaos-primeira-turma"),
    ("2ª Turma", "espelhos-de-acordaos-segunda-turma"),
    ("3ª Turma", "espelhos-de-acordaos-terceira-turma"),
    ("4ª Turma", "espelhos-de-acordaos-quarta-turma"),
    ("5ª Turma", "espelhos-de-acordaos-quinta-turma"),
    ("6ª Turma", "espelhos-de-acordaos-sexta-turma"),
]

# Tribunais disponíveis na API Pública do DataJud, agrupados por ramo.
DATAJUD_RAMOS = {
    "Tribunais superiores": [
        ("STJ - Superior Tribunal de Justiça", "api_publica_stj"),
        ("TST - Tribunal Superior do Trabalho", "api_publica_tst"),
        ("TSE - Tribunal Superior Eleitoral", "api_publica_tse"),
        ("STM - Superior Tribunal Militar", "api_publica_stm"),
    ],
    "Justiça Federal": [
        ("TRF 1ª Região", "api_publica_trf1"),
        ("TRF 2ª Região", "api_publica_trf2"),
        ("TRF 3ª Região", "api_publica_trf3"),
        ("TRF 4ª Região", "api_publica_trf4"),
        ("TRF 5ª Região (CE, RN, PB, PE, AL, SE)", "api_publica_trf5"),
        ("TRF 6ª Região (MG)", "api_publica_trf6"),
    ],
    "Justiça Estadual": [
        ("TJ do Acre", "api_publica_tjac"), ("TJ de Alagoas", "api_publica_tjal"),
        ("TJ do Amapá", "api_publica_tjap"), ("TJ do Amazonas", "api_publica_tjam"),
        ("TJ da Bahia", "api_publica_tjba"), ("TJ do Ceará (TJCE)", "api_publica_tjce"),
        ("TJ do Distrito Federal e Territórios", "api_publica_tjdft"),
        ("TJ do Espírito Santo", "api_publica_tjes"), ("TJ de Goiás", "api_publica_tjgo"),
        ("TJ do Maranhão", "api_publica_tjma"), ("TJ de Minas Gerais", "api_publica_tjmg"),
        ("TJ de Mato Grosso do Sul", "api_publica_tjms"), ("TJ de Mato Grosso", "api_publica_tjmt"),
        ("TJ do Pará", "api_publica_tjpa"), ("TJ da Paraíba", "api_publica_tjpb"),
        ("TJ de Pernambuco", "api_publica_tjpe"), ("TJ do Piauí", "api_publica_tjpi"),
        ("TJ do Paraná", "api_publica_tjpr"), ("TJ do Rio de Janeiro", "api_publica_tjrj"),
        ("TJ do Rio Grande do Norte", "api_publica_tjrn"), ("TJ de Rondônia", "api_publica_tjro"),
        ("TJ de Roraima", "api_publica_tjrr"), ("TJ do Rio Grande do Sul", "api_publica_tjrs"),
        ("TJ de Santa Catarina", "api_publica_tjsc"), ("TJ de Sergipe", "api_publica_tjse"),
        ("TJ de São Paulo", "api_publica_tjsp"), ("TJ do Tocantins", "api_publica_tjto"),
    ],
    "Justiça do Trabalho": [
        ("TRT 1ª Região (RJ)", "api_publica_trt1"), ("TRT 2ª Região (SP)", "api_publica_trt2"),
        ("TRT 3ª Região (MG)", "api_publica_trt3"), ("TRT 4ª Região (RS)", "api_publica_trt4"),
        ("TRT 5ª Região (BA)", "api_publica_trt5"), ("TRT 6ª Região (PE)", "api_publica_trt6"),
        ("TRT 7ª Região (CE)", "api_publica_trt7"), ("TRT 8ª Região (PA/AP)", "api_publica_trt8"),
        ("TRT 9ª Região (PR)", "api_publica_trt9"), ("TRT 10ª Região (DF/TO)", "api_publica_trt10"),
        ("TRT 11ª Região (AM/RR)", "api_publica_trt11"), ("TRT 12ª Região (SC)", "api_publica_trt12"),
        ("TRT 13ª Região (PB)", "api_publica_trt13"), ("TRT 14ª Região (RO/AC)", "api_publica_trt14"),
        ("TRT 15ª Região (Campinas)", "api_publica_trt15"), ("TRT 16ª Região (MA)", "api_publica_trt16"),
        ("TRT 17ª Região (ES)", "api_publica_trt17"), ("TRT 18ª Região (GO)", "api_publica_trt18"),
        ("TRT 19ª Região (AL)", "api_publica_trt19"), ("TRT 20ª Região (SE)", "api_publica_trt20"),
        ("TRT 21ª Região (RN)", "api_publica_trt21"), ("TRT 22ª Região (PI)", "api_publica_trt22"),
        ("TRT 23ª Região (MT)", "api_publica_trt23"), ("TRT 24ª Região (MS)", "api_publica_trt24"),
    ],
    "Justiça Eleitoral": [
        ("TRE do Ceará (TRE-CE)", "api_publica_tre-ce"),
        ("TRE de São Paulo (TRE-SP)", "api_publica_tre-sp"),
        ("TRE do Rio de Janeiro (TRE-RJ)", "api_publica_tre-rj"),
        ("TRE da Bahia (TRE-BA)", "api_publica_tre-ba"),
        ("TRE de Pernambuco (TRE-PE)", "api_publica_tre-pe"),
        ("TRE do Piauí (TRE-PI)", "api_publica_tre-pi"),
    ],
    "Justiça Militar": [
        ("TJ Militar de Minas Gerais", "api_publica_tjmmg"),
        ("TJ Militar do Rio Grande do Sul", "api_publica_tjmrs"),
        ("TJ Militar de São Paulo", "api_publica_tjmsp"),
    ],
}

# Link direto para abrir o processo no site OFICIAL do tribunal (pelo número único CNJ).
# {dig} = número com 20 dígitos, sem pontos/traços.
DATAJUD_SITE = {
    "api_publica_tjac": "https://esaj.tjac.jus.br/cpopg/search.do?dadosConsulta.valorConsultaNuUnificado={dig}&dadosConsulta.tipoNuProcesso=UNIFICADO",
    "api_publica_tjce": "https://esaj.tjce.jus.br/cpopg/search.do?dadosConsulta.valorConsultaNuUnificado={dig}&dadosConsulta.tipoNuProcesso=UNIFICADO",
    "api_publica_tjms": "https://esaj.tjms.jus.br/cpopg/search.do?dadosConsulta.valorConsultaNuUnificado={dig}&dadosConsulta.tipoNuProcesso=UNIFICADO",
    "api_publica_tjsp": "https://esaj.tjsp.jus.br/cpopg/search.do?dadosConsulta.valorConsultaNuUnificado={dig}&dadosConsulta.tipoNuProcesso=UNIFICADO",
    "api_publica_stj": "https://processo.stj.jus.br/processo/pesquisa/?termo={dig}",
    "api_publica_tst": "https://consultaprocessual.tst.jus.br/consultaProcessual/consultaTstNumUnica.do?numeroTst={dig}",
}

# Link para BUSCAR POR NOME DA PARTE no site oficial (quando o tribunal permite).
# {nome} = nome já codificado para URL.
DATAJUD_SITE_NOME = {
    "api_publica_tjac": "https://esaj.tjac.jus.br/cpopg/search.do?cbPesquisa=NMPARTE&dadosConsulta.valorConsulta={nome}&dadosConsulta.tipoNuProcesso=UNIFICADO",
    "api_publica_tjce": "https://esaj.tjce.jus.br/cpopg/search.do?cbPesquisa=NMPARTE&dadosConsulta.valorConsulta={nome}&dadosConsulta.tipoNuProcesso=UNIFICADO",
    "api_publica_tjms": "https://esaj.tjms.jus.br/cpopg/search.do?cbPesquisa=NMPARTE&dadosConsulta.valorConsulta={nome}&dadosConsulta.tipoNuProcesso=UNIFICADO",
    "api_publica_tjsp": "https://esaj.tjsp.jus.br/cpopg/search.do?cbPesquisa=NMPARTE&dadosConsulta.valorConsulta={nome}&dadosConsulta.tipoNuProcesso=UNIFICADO",
}


# Atalhos oficiais (não é "feed": abre a busca no site do próprio órgão)
ATALHOS = [    ("⚖️ Tribunais superiores", [
        ("STF — jurisprudência e súmulas", "https://jurisprudencia.stf.jus.br/pages/search"),
        ("STF — Corte Aberta (dados abertos)", "https://portal.stf.jus.br/corteaberta/"),
        ("STJ — pesquisa de jurisprudência (SCON)", "https://scon.stj.jus.br/SCON/"),
        ("TST — jurisprudência", "https://www.tst.jus.br/jurisprudencia"),
        ("TSE — jurisprudência", "https://jurisprudencia.tse.jus.br/"),
        ("STM — jurisprudência", "https://jurisprudencia.stm.jus.br/"),
    ]),
    ("🧾 Tribunais de Contas", [
        ("TCU — pesquisa de acórdãos", "https://pesquisa.apps.tcu.gov.br/#/pesquisa/acordao-completo"),
        ("TCE-CE — consulta de jurisprudência", "https://www.tce.ce.gov.br/jurisdicionado/jurisprudencia/consulta"),
    ]),
    ("🏛️ Justiça no Ceará e Federal", [
        ("TJCE — jurisprudência (e-SAJ)", "https://esaj.tjce.jus.br/cjsg/consultaCompleta.do"),
        ("TJCE — informativo de jurisprudência", "https://www.tjce.jus.br/institucional/informativo-de-jurisprudencia"),
        ("TRF 5ª Região", "https://www.trf5.jus.br/"),
        ("TRT 7ª Região (CE)", "https://www.trt7.jus.br/"),
        ("TRE do Ceará", "https://www.tre-ce.jus.br/"),
    ]),
    ("🇧🇷 Portais e dados oficiais", [
        ("CNJ — Portal", "https://www.cnj.jus.br/"),
        ("CNJ — DataJud (processos)", "https://www.cnj.jus.br/sistemas/datajud/"),
        ("STJ — Portal de Dados Abertos", "https://dadosabertos.web.stj.jus.br/"),
        ("Planalto — legislação federal", "https://www.planalto.gov.br/ccivil_03/"),
    ]),
]

# Legislação federal (texto oficial no Planalto). "tags" são palavras extras de busca.
LEGISLACAO = [
    {"nome": "Constituição Federal de 1988", "tags": "cf constituicao emenda",
     "url": "https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm"},
    {"nome": "Código Civil (Lei 10.406/2002)", "tags": "cc civil",
     "url": "https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm"},
    {"nome": "Código de Processo Civil (Lei 13.105/2015)", "tags": "cpc processo civil",
     "url": "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/lei/l13105.htm"},
    {"nome": "Código Penal (Decreto-Lei 2.848/1940)", "tags": "cp penal crime",
     "url": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del2848compilado.htm"},
    {"nome": "Código de Processo Penal (Decreto-Lei 3.689/1941)", "tags": "cpp processo penal",
     "url": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del3689compilado.htm"},
    {"nome": "CLT — Consolidação das Leis do Trabalho", "tags": "clt trabalho",
     "url": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del5452.htm"},
    {"nome": "Código Tributário Nacional (Lei 5.172/1966)", "tags": "ctn tributario imposto",
     "url": "https://www.planalto.gov.br/ccivil_03/leis/l5172compilado.htm"},
    {"nome": "Código de Defesa do Consumidor (Lei 8.078/1990)", "tags": "cdc consumidor",
     "url": "https://www.planalto.gov.br/ccivil_03/leis/l8078compilado.htm"},
    {"nome": "ECA — Estatuto da Criança e do Adolescente (Lei 8.069/1990)", "tags": "eca crianca adolescente",
     "url": "https://www.planalto.gov.br/ccivil_03/leis/l8069.htm"},
    {"nome": "Estatuto da Pessoa Idosa (Lei 10.741/2003)", "tags": "idoso",
     "url": "https://www.planalto.gov.br/ccivil_03/leis/2003/l10.741.htm"},
    {"nome": "Estatuto da Pessoa com Deficiência (Lei 13.146/2015)", "tags": "pcd deficiencia",
     "url": "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/lei/l13146.htm"},
    {"nome": "Estatuto da Cidade (Lei 10.257/2001)", "tags": "urbanistico cidade",
     "url": "https://www.planalto.gov.br/ccivil_03/leis/leis_2001/l10257.htm"},
    {"nome": "Servidores Públicos Civis da União (Lei 8.112/1990)", "tags": "servidor administrativo",
     "url": "https://www.planalto.gov.br/ccivil_03/leis/l8112cons.htm"},
    {"nome": "Código de Trânsito Brasileiro (Lei 9.503/1997)", "tags": "ctb transito",
     "url": "https://www.planalto.gov.br/ccivil_03/leis/l9503compilado.htm"},
    {"nome": "Lei de Licitações e Contratos (Lei 14.133/2021)", "tags": "licitacao contrato administrativo",
     "url": "https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/l14133.htm"},
    {"nome": "Lei de Improbidade Administrativa (Lei 8.429/1992)", "tags": "improbidade administrativa",
     "url": "https://www.planalto.gov.br/ccivil_03/leis/l8429.htm"},
    {"nome": "Lei de Execução Penal (Lei 7.210/1984)", "tags": "lep execucao penal",
     "url": "https://www.planalto.gov.br/ccivil_03/leis/l7210.htm"},
    {"nome": "Lei Maria da Penha (Lei 11.340/2006)", "tags": "violencia domestica mulher",
     "url": "https://www.planalto.gov.br/ccivil_03/_ato2004-2006/2006/lei/l11340.htm"},
    {"nome": "Lei de Drogas (Lei 11.343/2006)", "tags": "drogas entorpecentes",
     "url": "https://www.planalto.gov.br/ccivil_03/_ato2004-2006/2006/lei/l11343.htm"},
    {"nome": "Lei do Mandado de Segurança (Lei 12.016/2009)", "tags": "mandado seguranca",
     "url": "https://www.planalto.gov.br/ccivil_03/_ato2007-2010/2009/lei/l12016.htm"},
    {"nome": "Lei da Ação Civil Pública (Lei 7.347/1985)", "tags": "acp coletivo",
     "url": "https://www.planalto.gov.br/ccivil_03/leis/l7347orig.htm"},
    {"nome": "Lei de Crimes Ambientais (Lei 9.605/1998)", "tags": "ambiental meio ambiente",
     "url": "https://www.planalto.gov.br/ccivil_03/leis/l9605.htm"},
    {"nome": "Código Florestal (Lei 12.651/2012)", "tags": "florestal ambiental",
     "url": "https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2012/lei/l12651.htm"},
    {"nome": "Lei de Arbitragem (Lei 9.307/1996)", "tags": "arbitragem",
     "url": "https://www.planalto.gov.br/ccivil_03/leis/l9307.htm"},
    {"nome": "Lei do Inquilinato (Lei 8.245/1991)", "tags": "locacao inquilino aluguel",
     "url": "https://www.planalto.gov.br/ccivil_03/leis/l8245.htm"},
    {"nome": "Lei de Alimentos (Lei 5.478/1968)", "tags": "alimentos pensao",
     "url": "https://www.planalto.gov.br/ccivil_03/leis/l5478.htm"},
    {"nome": "Lei do Divórcio (Lei 6.515/1977)", "tags": "divorcio familia",
     "url": "https://www.planalto.gov.br/ccivil_03/leis/l6515.htm"},
    {"nome": "Processo Administrativo Federal (Lei 9.784/1999)", "tags": "processo administrativo",
     "url": "https://www.planalto.gov.br/ccivil_03/leis/l9784.htm"},
    {"nome": "LINDB (Decreto-Lei 4.657/1942)", "tags": "lindb introducao normas",
     "url": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del4657compilado.htm"},
    {"nome": "Estatuto da Advocacia (Lei 8.906/1994)", "tags": "advocacia oab",
     "url": "https://www.planalto.gov.br/ccivil_03/leis/l8906.htm"},
    {"nome": "Lei das S.A. (Lei 6.404/1976)", "tags": "sociedades anonimas empresa",
     "url": "https://www.planalto.gov.br/ccivil_03/leis/l6404consol.htm"},
    {"nome": "Lei de Execução Fiscal (Lei 6.830/1980)", "tags": "execucao fiscal divida ativa",
     "url": "https://www.planalto.gov.br/ccivil_03/leis/l6830.htm"},
    {"nome": "Lei de Registros Públicos (Lei 6.015/1973)", "tags": "registros publicos",
     "url": "https://www.planalto.gov.br/ccivil_03/leis/l6015compilada.htm"},
    {"nome": "Marco Civil da Internet (Lei 12.965/2014)", "tags": "internet marco civil",
     "url": "https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2014/lei/l12965.htm"},
    {"nome": "LGPD (Lei 13.709/2018)", "tags": "lgpd dados privacidade",
     "url": "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm"},
    {"nome": "Lei Anticorrupção (Lei 12.846/2013)", "tags": "anticorrupcao",
     "url": "https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2013/lei/l12846.htm"},
    {"nome": "Lei de Acesso à Informação (Lei 12.527/2011)", "tags": "lai informacao",
     "url": "https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2011/lei/l12527.htm"},
]


# ------------------------------------------------------------------ utilidades
def so_digitos(texto):
    return re.sub(r"\D", "", texto or "")


def formatar_numero(numero):
    """Converte 20 dígitos no formato CNJ: NNNNNNN-DD.AAAA.J.TR.OOOO."""
    n = so_digitos(numero)
    if len(n) != 20:
        return numero
    return f"{n[0:7]}-{n[7:9]}.{n[9:13]}.{n[13]}.{n[14:16]}.{n[16:20]}"


def sem_acento(texto):
    """Minúsculas e sem acentos, para busca tolerante (ex.: 'licitacao' acha 'Licitação')."""
    normal = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in normal if not unicodedata.combining(c)).lower()


def buscar_legislacao(termo):
    """Filtra LEGISLACAO pelo termo (nome ou palavras-chave), ignorando acentos."""
    alvo = sem_acento(termo).strip()
    if not alvo:
        return list(LEGISLACAO)
    palavras = alvo.split()
    achados = []
    for item in LEGISLACAO:
        texto = sem_acento(f"{item['nome']} {item.get('tags', '')}")
        if all(p in texto for p in palavras):
            achados.append(item)
    return achados


def _data_br(valor):
    """Converte datas 'AAAAMMDD[HHMMSS]' ou ISO 'AAAA-MM-DD...' em 'DD/MM/AAAA'."""
    valor = (valor or "").strip()
    m = re.match(r"(\d{4})(\d{2})(\d{2})", valor)
    if m:
        return f"{m.group(3)}/{m.group(2)}/{m.group(1)}"
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", valor)
    if m:
        return f"{m.group(3)}/{m.group(2)}/{m.group(1)}"
    return valor


def _get_json(url, timeout=60):
    req = urllib.request.Request(url, headers=_CABECALHO)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _post_json(url, corpo, timeout=60, cabecalhos=None):
    headers = {**_CABECALHO, **(cabecalhos or {})}
    req = urllib.request.Request(url, data=json.dumps(corpo).encode("utf-8"),
                                 headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ------------------------------------------------------------------ STJ (acórdãos)
def _recursos_json(dataset):
    """Lista (em ordem cronológica) os arquivos JSON mensais de um conjunto do STJ."""
    info = _get_json(f"{CKAN_STJ}/package_show?id={dataset}")
    recursos = info["result"]["resources"]
    arquivos = [r for r in recursos
                if (r.get("format") or "").upper() == "JSON"
                and re.fullmatch(r"\d{8}\.json", r.get("name", "") or "")]
    arquivos.sort(key=lambda r: r.get("last_modified", "") or "")
    return arquivos


def _ler_acordaos(url):
    """Baixa um arquivo do STJ (JSON ou ZIP com JSONs) e devolve a lista de acórdãos."""
    req = urllib.request.Request(url, headers=_CABECALHO)
    with urllib.request.urlopen(req, timeout=180) as resp:
        dados = resp.read()
    if url.lower().endswith(".zip"):
        itens = []
        with zipfile.ZipFile(io.BytesIO(dados)) as z:
            for nome in z.namelist():
                if nome.lower().endswith(".json"):
                    itens.extend(json.loads(z.read(nome).decode("utf-8")))
        return itens
    return json.loads(dados.decode("utf-8"))


def _normalizar_acordao(item):
    texto = " ".join((item.get("ementa") or "").split())
    tese = " ".join((item.get("teseJuridica") or "").split())
    return {
        "id": str(item.get("id") or ""),
        "processo": (item.get("numeroProcesso") or "").strip(),
        "classe": (item.get("siglaClasse") or "").strip(),
        "orgao": (item.get("nomeOrgaoJulgador") or "").strip(),
        "relator": (item.get("ministroRelator") or "").strip(),
        "data": _data_br(item.get("dataDecisao")),
        "data_ordem": (item.get("dataDecisao") or ""),
        "ementa": texto,
        "tese": tese,
        "tema": (item.get("tema") or "").strip(),
    }


def acordaos_recentes(datasets=None, limite=60):
    """Busca os acórdãos mais recentes do STJ.

    Baixa o arquivo JSON mensal mais novo de cada conjunto escolhido, junta tudo e
    devolve (lista, erros). A lista vem ordenada da decisão mais recente para a mais
    antiga. 'erros' traz avisos de conjuntos que não puderam ser lidos.
    """
    datasets = list(datasets) if datasets else [d for _, d in ORGAOS_STJ]
    coletados, erros = [], []
    for ds in datasets:
        try:
            arquivos = _recursos_json(ds)
            if not arquivos:
                continue
            for item in _ler_acordaos(arquivos[-1]["url"]):
                coletados.append(_normalizar_acordao(item))
        except Exception as e:  # rede/portal fora do ar: segue os demais
            erros.append(f"{ds}: {e}")
    coletados.sort(key=lambda x: x["data_ordem"], reverse=True)
    vistos, unicos = set(), []
    for item in coletados:
        chave = item["id"] or f"{item['processo']}|{item['data_ordem']}|{item['ementa'][:60]}"
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(item)
    return unicos[:limite], erros


# ------------------------------------------------------------------ CNJ / DataJud
def _datajud_cabecalhos():
    chave = os.getenv("DATAJUD_API_KEY", "").strip() or DATAJUD_KEY_PADRAO
    return {"Authorization": f"APIKey {chave}", "Content-Type": "application/json"}


def _normalizar_processo(src):
    brutos = [((m.get("dataHora") or ""), (m.get("nome") or "").strip())
              for m in (src.get("movimentos") or [])]
    brutos.sort(key=lambda x: x[0], reverse=True)
    movimentos = [{"data": _data_br(dt), "nome": nome} for dt, nome in brutos]
    classe = src.get("classe") or {}
    orgao = src.get("orgaoJulgador") or {}
    assuntos = [a.get("nome", "") for a in (src.get("assuntos") or []) if a.get("nome")]
    return {
        "tribunal": (src.get("tribunal") or "").strip(),
        "grau": (src.get("grau") or "").strip(),
        "numero": formatar_numero(src.get("numeroProcesso") or ""),
        "classe": (classe.get("nome") or "").strip(),
        "orgao": (orgao.get("nome") or "").strip(),
        "ajuizamento": _data_br(src.get("dataAjuizamento")),
        "assuntos": assuntos,
        "movimentos": movimentos,
    }


def consultar_processo(alias, numero):
    """Consulta um processo pelo número único (CNJ) na API Pública do DataJud.

    Devolve a lista de processos encontrados (normalizada). Levanta erro amigável
    se o número for inválido ou se o serviço do CNJ não responder.
    """
    digitos = so_digitos(numero)
    if len(digitos) != 20:
        raise ValueError("O número do processo deve ter 20 dígitos (formato CNJ: "
                         "NNNNNNN-DD.AAAA.J.TR.OOOO).")
    url = f"{DATAJUD_BASE}/{alias}/_search"
    corpo = {"size": 5, "query": {"match": {"numeroProcesso": digitos}}}
    try:
        dados = _post_json(url, corpo, cabecalhos=_datajud_cabecalhos())
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise RuntimeError("A chave pública do DataJud foi recusada. O CNJ pode tê-la "
                               "trocado; atualize DATAJUD_API_KEY ou veja a Wiki do DataJud.") from e
        raise RuntimeError(f"O DataJud respondeu com erro {e.code}. Tente mais tarde.") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Não consegui falar com o DataJud (verifique a internet): {e.reason}") from e
    hits = (dados.get("hits") or {}).get("hits") or []
    return [_normalizar_processo(h.get("_source") or {}) for h in hits]


def link_processo(alias, numero):
    """Devolve o link para abrir o processo no site oficial do tribunal.

    Quando o tribunal não tem link direto conhecido, cai numa busca restrita
    ao domínio do Judiciário (jus.br) para localizar a página oficial.
    """
    dig = so_digitos(numero)
    modelo = DATAJUD_SITE.get(alias)
    if modelo:
        return modelo.format(dig=dig)
    consulta = urllib.parse.quote(f'"{formatar_numero(numero)}" site:jus.br')
    return f"https://www.google.com/search?q={consulta}"


def link_processo_nome(alias, nome):
    """Link para buscar por NOME DA PARTE no site oficial do tribunal.

    O DataJud não expõe nomes (LGPD); quando o tribunal não tem busca por nome
    mapeada, cai numa busca restrita ao domínio do Judiciário (jus.br).
    """
    nome = (nome or "").strip()
    modelo = DATAJUD_SITE_NOME.get(alias)
    if modelo:
        return modelo.format(nome=urllib.parse.quote(nome))
    consulta = urllib.parse.quote(f'"{nome}" processo site:jus.br')
    return f"https://www.google.com/search?q={consulta}"


# ------------------------------------------------------------------ busca de jurisprudência
# Colegiados do STJ: rótulo no app -> termo usado no filtro do SCON.
STJ_COLEGIADOS = {
    "Corte Especial": "CORTE ESPECIAL",
    "1ª Seção": "PRIMEIRA SEÇÃO",
    "2ª Seção": "SEGUNDA SEÇÃO",
    "3ª Seção": "TERCEIRA SEÇÃO",
    "1ª Turma": "PRIMEIRA TURMA",
    "2ª Turma": "SEGUNDA TURMA",
    "3ª Turma": "TERCEIRA TURMA",
    "4ª Turma": "QUARTA TURMA",
    "5ª Turma": "QUINTA TURMA",
    "6ª Turma": "SEXTA TURMA",
}


def link_stj(colegiado="", termos=""):
    """Link para a pesquisa oficial de jurisprudência do STJ (SCON).

    ``colegiado`` filtra pelo órgão julgador (ex.: '5ª Turma'); ``termos`` são as
    palavras a pesquisar. Sem nada, abre a página de busca do SCON.
    """
    partes = []
    termos = (termos or "").strip()
    if termos:
        partes.append(f"({termos})")
    org = STJ_COLEGIADOS.get((colegiado or "").strip())
    if org:
        partes.append(f'("{org}" inpath (//ORG))')
    base = "https://scon.stj.jus.br/SCON/pesquisar.jsp?b=ACOR&O=JT&thesaurus=JURIDICO"
    if partes:
        base += "&livre=" + urllib.parse.quote(" and ".join(partes))
    return base


# Onde o usuário pode pesquisar jurisprudência (rótulos exibidos no app).
FONTES_JURIS = [
    "STJ — Superior Tribunal de Justiça",
    "STF — Supremo Tribunal Federal",
    "TST — Tribunal Superior do Trabalho",
    "TSE — Tribunal Superior Eleitoral",
    "STM — Superior Tribunal Militar",
    "TCU — Tribunal de Contas da União",
    "TCE-CE — Tribunal de Contas do Estado do Ceará",
    "TJCE — Tribunal de Justiça do Ceará",
    "TJAC — Tribunal de Justiça do Acre",
    "TJMS — Tribunal de Justiça de Mato Grosso do Sul",
    "TJSP — Tribunal de Justiça de São Paulo",
]

# Domínio oficial usado quando não há link direto de busca (fallback via Google).
_DOMINIOS_JURIS = [
    ("TCE-CE", "tce.ce.gov.br"),
    ("TST", "tst.jus.br"),
    ("TSE", "tse.jus.br"),
    ("STM", "stm.jus.br"),
    ("TCU", "tcu.gov.br"),
]

# TJs (e-SAJ) com busca de jurisprudência por inteiro teor mapeada.
_ESAJ_JURIS = {"CE": "tjce", "AC": "tjac", "MS": "tjms", "SP": "tjsp"}


def link_juris(fonte="", termos="", colegiado=""):
    """Link de pesquisa de jurisprudência na fonte OFICIAL escolhida.

    ``fonte`` é o tribunal (ex.: 'STJ', 'TJCE'); ``termos`` são as palavras a
    pesquisar; ``colegiado`` (opcional) filtra o órgão julgador no STJ.
    """
    termos = (termos or "").strip()
    alvo = (fonte or "").upper()
    q = urllib.parse.quote(termos)
    if "STJ" in alvo or "SCON" in alvo:
        return link_stj(colegiado, termos)
    if "STF" in alvo:
        return f"https://jurisprudencia.stf.jus.br/pages/search?base=acordaos&queryString={q}"
    m = re.search(r"TJ\s*-?\s*([A-Z]{2})", alvo)
    if m and m.group(1) in _ESAJ_JURIS:
        return (f"https://esaj.{_ESAJ_JURIS[m.group(1)]}.jus.br/cjsg/resultadoCompleta.do?"
                f"dados.buscaInteiroTeor={q}&dados.pesquisarComSinonimos=S")
    dom = next((d for sigla, d in _DOMINIOS_JURIS if sigla in alvo), "jus.br")
    consulta = urllib.parse.quote(f'"{termos}" jurisprudência site:{dom}')
    return f"https://www.google.com/search?q={consulta}"


def link_busca_juris(tribunal="", termos="", fonte=""):
    """Link para abrir a busca de um julgado no site OFICIAL de origem.

    Usada pelos cards de sugestão da IA: junta o tribunal e a fonte indicada.
    """
    return link_juris(f"{tribunal} {fonte}", termos)


def parse_sugestoes_juris(texto):
    """Separa o texto sugerido pela IA em itens com tribunal, tese, busca e link.

    Espera blocos no formato da instrução (cabeçalho, ``Tese:``, ``Identificação:``,
    ``Busca:``, ``Fonte:``), separados por linha em branco. Tolerante a variações.
    """
    itens = []
    for bloco in re.split(r"\n\s*\n", texto or ""):
        bloco = bloco.strip()
        if not bloco:
            continue
        linhas = [l.strip() for l in bloco.splitlines() if l.strip()]
        item = {"cabecalho": linhas[0], "tese": "", "identificacao": "",
                "busca": "", "fonte": "", "texto": bloco}
        for l in linhas[1:]:
            chave, _, valor = l.partition(":")
            chave = chave.strip().lower()
            valor = valor.strip()
            if chave.startswith("tese"):
                item["tese"] = valor
            elif chave.startswith("identifica"):
                item["identificacao"] = valor
            elif chave.startswith("busca"):
                item["busca"] = valor
            elif chave.startswith("fonte"):
                item["fonte"] = valor
        cab = item["cabecalho"]
        item["tribunal"] = re.split(r"\s[—–-]\s", cab)[0].strip("[] ").strip()
        alvo = (item["busca"] or item["tese"] or item["tribunal"]).strip()
        item["url"] = link_busca_juris(item["tribunal"], alvo, item["fonte"])
        itens.append(item)
    return itens
