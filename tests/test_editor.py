"""Testes do editor formatado: conversao de HTML para texto e seguranca do HTML."""
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import motor


class TestTextoSimples(unittest.TestCase):
    def test_texto_sem_tag_ficam_igual(self):
        self.assertEqual(motor.texto_simples("A cliente reclamou."), "A cliente reclamou.")

    def test_tira_negrito_e_italico(self):
        self.assertEqual(motor.texto_simples("A <b>cliente</b> <i>reclamou</i>."),
                         "A cliente reclamou.")

    def test_lista_vira_linhas_com_ponto(self):
        html = "<ul><li>primeiro</li><li>segundo</li></ul>"
        self.assertEqual(motor.texto_simples(html), "- primeiro\n- segundo")

    def test_quebra_de_linha(self):
        self.assertEqual(motor.texto_simples("um<br>dois"), "um\ndois")

    def test_descodifica_entidades(self):
        self.assertEqual(motor.texto_simples("Tom &amp; Jerry &nbsp;x"), "Tom & Jerry  x")

    def test_vazio(self):
        self.assertEqual(motor.texto_simples(""), "")
        self.assertEqual(motor.texto_simples(None), "")


class TestHtmlSeguro(unittest.TestCase):
    def test_mantem_formatacao(self):
        self.assertIn("<b>forte</b>", motor.html_seguro("<b>forte</b>"))

    def test_remove_script(self):
        saida = motor.html_seguro("<b>ok</b><script>alert(1)</script>")
        self.assertNotIn("script", saida)
        self.assertIn("<b>ok</b>", saida)

    def test_remove_evento_e_javascript(self):
        saida = motor.html_seguro('<a href="javascript:alert(1)" onclick="rouba()">x</a>')
        self.assertNotIn("onclick", saida)
        self.assertNotIn("javascript:", saida)

    def test_remove_iframe(self):
        self.assertEqual(motor.html_seguro("<iframe src='x'></iframe>"), "")


class TestSubstituirEmHtml(unittest.TestCase):
    def test_troca_dentro_do_texto(self):
        html = "A <b>Sao</b> Paulo"
        self.assertEqual(motor.substituir_em_html(html, "Sao", "São"), "A <b>São</b> Paulo")

    def test_nao_quebra_tag(self):
        html = "<b>Sao Paulo</b>"
        self.assertEqual(motor.substituir_em_html(html, "Sao", "São"), "<b>São Paulo</b>")

    def test_palavra_ausente(self):
        self.assertIsNone(motor.substituir_em_html("<b>ok</b>", "Sao", "São"))

    def test_texto_simples_tambem_funciona(self):
        self.assertEqual(motor.substituir_em_html("Sao Paulo", "Sao", "São"), "São Paulo")


if __name__ == "__main__":
    unittest.main()
