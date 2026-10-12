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
import urllib.error
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

# Atalhos oficiais (não é "feed": abre a busca no site do próprio órgão)
ATALHOS = [
    ("STF", [
        ("STF - Pesquisa de jurisprudência e súmulas", "https://jurisprudencia.stf.jus.br/pages/search"),
    ]),
    ("STJ", [
        ("STJ - Pesquisa de jurisprudência (SCON)", "https://scon.stj.jus.br/SCON/"),
        ("STJ - Portal de Dados Abertos (acórdãos em JSON)", "https://dadosabertos.web.stj.jus.br/"),
    ]),
    ("CNJ", [
        ("CNJ - Portal", "https://www.cnj.jus.br/"),
        ("CNJ - DataJud (processos)", "https://www.cnj.jus.br/sistemas/datajud/"),
    ]),
    ("TJCE", [
        ("TJCE - Consulta de jurisprudência (e-SAJ)", "https://esaj.tjce.jus.br/cjsg/resultadoCompleta.do"),
        ("TJCE - Informativo de jurisprudência", "https://www.tjce.jus.br/informativo-jurisprudencia/"),
    ]),
    ("Federal / Trabalho / Eleitoral", [
        ("TRF 5ª Região", "https://www.trf5.jus.br/"),
        ("TRT 7ª Região", "https://www.trt7.jus.br/"),
        ("TRE do Ceará", "https://www.tre-ce.jus.br/"),
    ]),
    ("Leis", [
        ("Constituição Federal", "https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm"),
        ("Legislação federal (Planalto)", "https://www.planalto.gov.br/ccivil_03/"),
    ]),
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
