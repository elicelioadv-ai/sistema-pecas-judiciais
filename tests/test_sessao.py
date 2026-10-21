"""Testes da sessao que sobrevive a atualizacao e das mensagens de erro da IA."""
import os
import sys
import time
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import motor


class TestSessao(unittest.TestCase):
    def setUp(self):
        self.senha_original = os.environ.get("SENHA_ACESSO")
        os.environ["SENHA_ACESSO"] = "sha256:teste-sessao"

    def tearDown(self):
        if self.senha_original is None:
            os.environ.pop("SENHA_ACESSO", None)
        else:
            os.environ["SENHA_ACESSO"] = self.senha_original

    def test_token_valido_leva_usuario_e_admin(self):
        token = motor.token_sessao("admin", True)
        dados = motor.ler_token_sessao(token)
        self.assertIsNotNone(dados)
        self.assertEqual(dados["usuario"], "admin")
        self.assertTrue(dados["admin"])

    def test_token_adulterado_e_recusado(self):
        token = motor.token_sessao("admin", True)
        partes = token.split("|")
        partes[0] = "intruso"
        self.assertIsNone(motor.ler_token_sessao("|".join(partes)))

    def test_token_vencido_e_recusado(self):
        token = motor.token_sessao("admin", True, dias=0)
        # forca o vencimento
        partes = token.split("|")
        partes[2] = str(int(time.time()) - 10)
        import hashlib
        import hmac
        dados = "|".join(partes[:3])
        assinatura = hmac.new(motor._segredo_sessao().encode("utf-8"), dados.encode("utf-8"),
                              hashlib.sha256).hexdigest()
        self.assertIsNone(motor.ler_token_sessao("|".join(partes[:3]) + "|" + assinatura))

    def test_token_vazio_e_recusado(self):
        self.assertIsNone(motor.ler_token_sessao(""))
        self.assertIsNone(motor.ler_token_sessao("lixo"))

    def test_mudanca_de_senha_invalida_o_token(self):
        token = motor.token_sessao("admin", True)
        os.environ["SENHA_ACESSO"] = "sha256:outra-senha"
        self.assertIsNone(motor.ler_token_sessao(token))


class TestMensagemAmigavel(unittest.TestCase):
    def test_servidor_sobrecarregado(self):
        msg = motor.mensagem_amigavel(Exception("503 UNAVAILABLE. This model is currently "
                                                 "experiencing high demand."))
        self.assertIn("sobrecarregada", msg.lower())
        self.assertIn("salvo", msg.lower())

    def test_cota_esgotada(self):
        msg = motor.mensagem_amigavel(Exception("429 RESOURCE_EXHAUSTED: quota"))
        self.assertIn("cota", msg.lower())

    def test_timeout(self):
        msg = motor.mensagem_amigavel(Exception("Request timed out after 120s"))
        self.assertIn("demorou", msg.lower())

    def test_erro_desconhecido_mantem_texto(self):
        self.assertEqual(motor.mensagem_amigavel(Exception("detalhe X")), "detalhe X")


class TestSessaoNoApp(unittest.TestCase):
    """O token entregue pelo navegador (campo escondido) deve abrir o app."""

    def setUp(self):
        self.senha_original = os.environ.get("SENHA_ACESSO")
        os.environ["SENHA_ACESSO"] = "sha256:teste-sessao"

    def tearDown(self):
        if self.senha_original is None:
            os.environ.pop("SENHA_ACESSO", None)
        else:
            os.environ["SENHA_ACESSO"] = self.senha_original

    def test_token_valido_no_campo_oculto_entra_sozinho(self):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(str(RAIZ / "app.py"), default_timeout=60)
        at.session_state["_token_widget"] = motor.token_sessao("admin", True)
        at.run()
        self.assertTrue(at.session_state.get("autenticado"))
        self.assertEqual(at.session_state.get("usuario"), "admin")

    def test_token_invalido_nao_entra(self):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(str(RAIZ / "app.py"), default_timeout=60)
        at.session_state["_token_widget"] = "token|falso|0|assinatura"
        at.run()
        self.assertFalse(at.session_state.get("autenticado"))


if __name__ == "__main__":
    unittest.main()
