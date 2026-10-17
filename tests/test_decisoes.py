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

    def test_pje_tjce_host_correto_por_grau(self):
        g1 = decisoes.links_processo("api_publica_tjce", "0200677-09.2023.8.06.0160", "G1")
        g2 = decisoes.links_processo("api_publica_tjce", "0200677-09.2023.8.06.0160", "G2")
        pje1 = [u for r, u in g1 if "PJe" in r][0]
        pje2 = [u for r, u in g2 if "PJe" in r][0]
        self.assertEqual(pje1, "https://pje-consulta.tjce.jus.br/pje1grau/ConsultaPublica/listView.seam")
        self.assertEqual(pje2, "https://pje-consulta.tjce.jus.br/pje2grau/ConsultaPublica/listView.seam")

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


if __name__ == "__main__":
    unittest.main()
