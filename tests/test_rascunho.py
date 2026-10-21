"""Testes do rascunho automático (não deixa o trabalho se perder)."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import motor


class TestRascunho(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="spj_rascunho_"))
        self.orig = motor.PASTA_RASCUNHOS
        motor.PASTA_RASCUNHOS = self.dir
        self.orig_pasta = motor.PASTA_RASCUNHOS
        motor.PASTA_RASCUNHOS.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        motor.PASTA_RASCUNHOS = self.orig
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_salva_e_recupera(self):
        motor.salvar_rascunho({"narrativa": "A cliente comprou passagem."}, dono="joao")
        r = motor.carregar_rascunho("joao")
        self.assertIsNotNone(r)
        self.assertEqual(r["narrativa"], "A cliente comprou passagem.")
        self.assertIn("_salvo_em", r)

    def test_dono_diferente_nao_enxerga(self):
        motor.salvar_rascunho({"narrativa": "segredo do joao"}, dono="joao")
        self.assertIsNone(motor.carregar_rascunho("maria"))

    def test_apaga_rascunho(self):
        motor.salvar_rascunho({"narrativa": "x"}, dono="joao")
        motor.apagar_rascunho("joao")
        self.assertIsNone(motor.carregar_rascunho("joao"))

    def test_texto_para_ia_tira_marcacoes(self):
        t = motor._texto_para_ia("==destaque== e **negrito** e __sublinhado__")
        self.assertIn("**destaque**", t)
        self.assertIn("**negrito**", t)
        self.assertNotIn("__", t)
        self.assertNotIn("==", t)

    def test_texto_para_ia_vazio(self):
        self.assertEqual(motor._texto_para_ia(""), "")
        self.assertEqual(motor._texto_para_ia(None), "")


if __name__ == "__main__":
    unittest.main()
