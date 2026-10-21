"""Testes da revisao de escrita (correcoes de ortografia/gramatica)."""
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import motor


class TestExtrairCorrecoes(unittest.TestCase):
    def test_json_puro(self):
        saida = '{"correcoes":[{"errado":"recebeu","certo":"recebeu","motivo":"x"}]}'
        self.assertEqual(motor._extrair_correcoes(saida), [])

    def test_lista_com_um_item(self):
        saida = ('{"correcoes":[{"errado":"advocadao","certo":"advocacia",'
                 '"motivo":"falta a letra i"}]}')
        itens = motor._extrair_correcoes(saida)
        self.assertEqual(len(itens), 1)
        self.assertEqual(itens[0]["errado"], "advocadao")
        self.assertEqual(itens[0]["certo"], "advocacia")
        self.assertEqual(itens[0]["motivo"], "falta a letra i")

    def test_aceita_cercas_de_codigo(self):
        saida = '```json\n{"correcoes":[{"errado":"x","certo":"y"}]}\n```'
        itens = motor._extrair_correcoes(saida)
        self.assertEqual(len(itens), 1)
        self.assertEqual(itens[0]["certo"], "y")

    def test_aceita_texto_ao_lado_do_json(self):
        saida = 'Aqui estao as correcoes: {"correcoes":[{"errado":"a","certo":"b"}]} espero ajudar'
        itens = motor._extrair_correcoes(saida)
        self.assertEqual(len(itens), 1)

    def test_json_invalido_vira_lista_vazia(self):
        self.assertEqual(motor._extrair_correcoes("nao e json"), [])
        self.assertEqual(motor._extrair_correcoes(""), [])

    def test_ignora_itens_incompletos(self):
        saida = '{"correcoes":[{"errado":"a","certo":""},{"errado":"","certo":"b"},{"errado":"c","certo":"c"}]}'
        self.assertEqual(motor._extrair_correcoes(saida), [])


class TestRevisarEscrita(unittest.TestCase):
    def test_revisar_escrita_chama_a_ia_e_devolve_lista(self):
        original = motor._chamar_ia
        motor._chamar_ia = lambda system, contents, max_tokens=6000: (
            '{"correcoes":[{"errado":"advocadao","certo":"advocacia","motivo":"i"}]}'
        )
        try:
            itens = motor.revisar_escrita("AADVOCADAO escreveu.")
        finally:
            motor._chamar_ia = original
        self.assertEqual(len(itens), 1)
        self.assertEqual(itens[0]["certo"], "advocacia")


class TestAplicarCorrecao(unittest.TestCase):
    def test_troca_a_primeira_ocorrencia(self):
        self.assertEqual(motor.aplicar_correcao("foi recorrencia, recorrencia", "recorrencia", "recorrência"),
                         "foi recorrência, recorrencia")

    def test_palavra_ausente_devolve_none(self):
        self.assertIsNone(motor.aplicar_correcao("sem erro", "x", "y"))

    def test_texto_vazio_devolve_none(self):
        self.assertIsNone(motor.aplicar_correcao("", "x", "y"))


class TestFluxoCorrecaoNoApp(unittest.TestCase):
    def test_correcao_pendente_e_aplicada_no_campo(self):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(str(RAIZ / "app.py"), default_timeout=60)
        at.session_state["autenticado"] = True
        at.session_state["usuario"] = "teste"
        at.run()
        self.assertEqual(len(at.exception), 0, [e.value for e in at.exception])
        at.session_state["narrativa"] = "A cliente reclamou de volcsao do voo."
        at.session_state["_corr_pendente"] = ("volcsao", "volução")
        at.run()
        self.assertEqual(len(at.exception), 0, [e.value for e in at.exception])
        self.assertIn("volução", at.session_state["narrativa"])


if __name__ == "__main__":
    unittest.main()
