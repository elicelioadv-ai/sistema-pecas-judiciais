"""Testes da separação de casos por dono (sem nuvem).

Rode na raiz do projeto:  python -m unittest discover -s tests
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import motor
import nuvem


class TestCasosPorDono(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._pasta = motor.PASTA_HISTORICO
        motor.PASTA_HISTORICO = Path(self.tmp.name)
        self._disp = nuvem.disponivel
        nuvem.disponivel = lambda: False

    def tearDown(self):
        motor.PASTA_HISTORICO = self._pasta
        nuvem.disponivel = self._disp
        self.tmp.cleanup()

    def test_separa_por_dono(self):
        motor.salvar_caso("Caso A", {"f_juizo": "Vara 1"}, dono="ana@x.com")
        motor.salvar_caso("Caso B", {"f_juizo": "Vara 2"}, dono="bruno@x.com")
        self.assertEqual(motor.listar_casos("ana@x.com"), ["Caso_A"])
        self.assertEqual(motor.listar_casos("bruno@x.com"), ["Caso_B"])
        self.assertEqual(motor.listar_casos(""), [])

    def test_carregar_e_apagar(self):
        motor.salvar_caso("Caso A", {"f_juizo": "Vara 1"}, dono="ana@x.com")
        dados = motor.carregar_caso("Caso_A", dono="ana@x.com")
        self.assertEqual(dados["f_juizo"], "Vara 1")
        self.assertEqual(dados["_dono"], "ana@x.com")
        motor.apagar_caso("Caso_A", dono="ana@x.com")
        self.assertEqual(motor.listar_casos("ana@x.com"), [])

    def test_admin_usa_a_raiz(self):
        motor.salvar_caso("Antigo", {"f_juizo": "Vara 0"}, dono="")
        self.assertEqual(motor.listar_casos(""), ["Antigo"])
        self.assertEqual(motor.listar_casos("ana@x.com"), [])


if __name__ == "__main__":
    unittest.main()
