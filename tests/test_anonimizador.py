"""Testes do Anonimizador (modo seguro / LGPD). Rode: python -m unittest discover -s tests"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import motor


class TestAnonimizador(unittest.TestCase):
    def setUp(self):
        self.anon = motor.Anonimizador()

    def test_cpf_email_cep(self):
        texto = "CPF 123.456.789-00, e-mail maria@exemplo.com, CEP 60000-000."
        mascarado, mapa = self.anon.mascarar(texto)
        self.assertNotIn("123.456.789-00", mascarado)
        self.assertNotIn("maria@exemplo.com", mascarado)
        self.assertNotIn("60000-000", mascarado)
        self.assertEqual(self.anon.restaurar(mascarado, mapa), texto)

    def test_nome_de_pessoa_por_rotulo(self):
        texto = "Autor: Maria Souza Lima, brasileira, solteira, professora."
        mascarado, mapa = self.anon.mascarar(texto)
        self.assertIn("[PESSOA_1]", mascarado)
        self.assertNotIn("Maria", mascarado)
        self.assertNotIn("Souza", mascarado)
        restaurado = self.anon.restaurar(mascarado, mapa)
        self.assertIn("Maria Souza Lima", restaurado)
        self.assertIn("brasileira", restaurado)

    def test_organizacao_re(self):
        texto = "Ré: Companhia Aérea Exemplo S.A., CNPJ 00.000.000/0001-00."
        mascarado, mapa = self.anon.mascarar(texto)
        self.assertIn("[ORGANIZACAO_1]", mascarado)
        self.assertIn("[CNPJ_1]", mascarado)
        self.assertEqual(self.anon.restaurar(mascarado, mapa), texto)

    def test_consistencia_repetido(self):
        anon = motor.Anonimizador(["Maria"])
        texto = "Maria foi ao aeroporto. Depois Maria ligou. Maria esperou."
        mascarado, mapa = anon.mascarar(texto)
        self.assertEqual(mascarado.count("[PESSOA_1]"), 3)
        self.assertEqual(anon.restaurar(mascarado, mapa), texto)

    def test_termos_extras(self):
        anon = motor.Anonimizador(["João da Silva", "Hospital São Lucas"])
        texto = "O cliente João da Silva foi atendido no Hospital São Lucas."
        mascarado, mapa = anon.mascarar(texto)
        self.assertNotIn("João", mascarado)
        self.assertNotIn("Hospital", mascarado)
        self.assertIn("[PESSOA_1]", mascarado)
        self.assertEqual(anon.restaurar(mascarado, mapa), texto)

    def test_nao_mexe_em_fonte_da_base(self):
        texto = "Conforme entendimento [FONTE:cdc_14], aplica-se o CDC."
        mascarado, mapa = self.anon.mascarar(texto)
        self.assertIn("[FONTE:cdc_14]", mascarado)
        self.assertEqual(self.anon.restaurar(mascarado, mapa), texto)

    def test_detecta_marcador_nao_restaurado(self):
        restos = self.anon.marcadores_restantes("Texto com [PESSOA_2] e [CPF 3] soltos.")
        self.assertEqual(sorted(restos), ["[CPF 3]", "[PESSOA_2]"])

    def test_conferencia_alerta_marcador(self):
        base = [motor.novo_item_base("x", "Lei X", "texto", status="verificado")]
        r = motor.conferir_citacoes("A autora [PESSOA_9] pediu.", base, "nada")
        self.assertTrue(any(n == "erro" and "anonimização" in m for n, m in r["alertas"]))


class TestConfig(unittest.TestCase):
    def test_modo_uso_tem_chaves(self):
        m = motor.modo_uso()
        for chave in ("provedor", "modelo", "modo_chave", "regiao", "uso_pago"):
            self.assertIn(chave, m)


if __name__ == "__main__":
    unittest.main()
