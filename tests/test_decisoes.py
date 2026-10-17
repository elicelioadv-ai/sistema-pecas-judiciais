"""Testes dos links de processo (abrir direto no site oficial).

Rode: python -m unittest discover -s tests
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import decisoes


class TestLinksProcesso(unittest.TestCase):
    def test_esaj_tjce_abre_direto_primeiro_grau(self):
        links = decisoes.links_processo("api_publica_tjce", "0200677-09.2023.8.06.0160", "G1")
        url = links[0][1]
        self.assertIn("esaj.tjce.jus.br/cpopg/search.do", url)
        self.assertIn("cbPesquisa=NUMPROC", url)
        self.assertIn("0200677-09.2023.8.06.0160", url)

    def test_esaj_tjce_segundo_grau(self):
        links = decisoes.links_processo("api_publica_tjce", "0200677-09.2023.8.06.0160", "G2")
        self.assertIn("esaj.tjce.jus.br/cposg/search.do", links[0][1])

    def test_pje_tjce_consulta_por_grau(self):
        self.assertEqual(
            decisoes._pje_consulta("api_publica_tjce", "G1"),
            "https://pje-consulta.tjce.jus.br/pje1grau/ConsultaPublica/listView.seam")
        self.assertEqual(
            decisoes._pje_consulta("api_publica_tjce", "G2"),
            "https://pje-consulta.tjce.jus.br/pje2grau/ConsultaPublica/listView.seam")

    def test_tjce_nao_mostra_formulario_quando_ha_link_direto(self):
        links = decisoes.links_processo("api_publica_tjce", "0200677-09.2023.8.06.0160", "G1")
        rotulos = [r for r, _ in links]
        self.assertTrue(any("e-SAJ" in r for r in rotulos))
        self.assertTrue(any("Comunica" in r for r in rotulos))
        self.assertFalse(any("formulário" in r for r in rotulos))

    def test_pje_trt_abre_direto(self):
        links = decisoes.links_processo("api_publica_trt7", "0001234-56.2024.5.07.0001")
        url = links[0][1]
        self.assertEqual(
            url,
            "https://pje.trt7.jus.br/consultaprocessual/detalhe-processo/00012345620245070001",
        )

    def test_link_processo_compat(self):
        url = decisoes.link_processo("api_publica_trt7", "0001234-56.2024.5.07.0001")
        self.assertIn("detalhe-processo", url)

    def test_comunica_pje(self):
        links = decisoes.links_processo("api_publica_tjce", "0200677-09.2023.8.06.0160", "G1")
        comunica = [u for r, u in links if "comunica" in r.lower()][0]
        self.assertIn("comunica.pje.jus.br/consulta", comunica)
        self.assertIn("numeroProcesso=0200677-09.2023.8.06.0160", comunica)
        self.assertIn("siglaTribunal=TJCE", comunica)

    def test_sigla_tribunal(self):
        self.assertEqual(decisoes._sigla_tribunal("api_publica_tjce"), "TJCE")
        self.assertEqual(decisoes._sigla_tribunal("api_publica_trf5"), "TRF5")
        self.assertEqual(decisoes._sigla_tribunal("api_publica_tre-ce"), "TRE-CE")

    def test_comunicacoes_numero_invalido(self):
        self.assertIsNone(decisoes.comunicacoes_processo("api_publica_tjce", "123"))


if __name__ == "__main__":
    unittest.main()
