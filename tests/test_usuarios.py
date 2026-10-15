"""Testes do cadastro de usuários (sem nuvem: usa arquivo local temporário).

Rode na raiz do projeto:  python -m unittest discover -s tests
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import usuarios


class TestUsuarios(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._pasta = usuarios.PASTA
        self._nuvem = usuarios._usar_nuvem
        usuarios.PASTA = Path(self.tmp.name)
        usuarios._usar_nuvem = lambda: False

    def tearDown(self):
        usuarios.PASTA = self._pasta
        usuarios._usar_nuvem = self._nuvem
        self.tmp.cleanup()

    def test_criar_fica_pendente(self):
        usuarios.criar("Maria", "maria@x.com", "segredo1")
        self.assertTrue(usuarios.existe("maria@x.com"))
        self.assertEqual(usuarios.autenticar("maria@x.com", "segredo1"), usuarios.PENDENTE)

    def test_aprovar_permite_login(self):
        usuarios.criar("Maria", "maria@x.com", "segredo1")
        usuarios.aprovar("maria@x.com")
        self.assertEqual(usuarios.autenticar("maria@x.com", "segredo1"), usuarios.OK)

    def test_senha_errada_e_usuario_inexistente(self):
        usuarios.criar("Maria", "maria@x.com", "segredo1")
        usuarios.aprovar("maria@x.com")
        self.assertEqual(usuarios.autenticar("maria@x.com", "outra"), usuarios.INVALIDO)
        self.assertEqual(usuarios.autenticar("ninguem@x.com", "segredo1"), usuarios.INVALIDO)

    def test_duplicado(self):
        usuarios.criar("Maria", "maria@x.com", "segredo1")
        with self.assertRaises(ValueError):
            usuarios.criar("Outra", "Maria@X.com", "outra123")

    def test_senha_curta(self):
        with self.assertRaises(ValueError):
            usuarios.criar("Maria", "maria@x.com", "123")

    def test_remover(self):
        usuarios.criar("Maria", "maria@x.com", "segredo1")
        self.assertTrue(usuarios.remover("maria@x.com"))
        self.assertFalse(usuarios.existe("maria@x.com"))

    def test_listar_nao_expoe_hash(self):
        usuarios.criar("Maria", "maria@x.com", "segredo1")
        item = usuarios.listar()[0]
        self.assertNotIn("hash", item)
        self.assertNotIn("salt", item)

    def test_redefinir_senha(self):
        usuarios.criar("Maria", "maria@x.com", "segredo1")
        usuarios.aprovar("maria@x.com")
        usuarios.redefinir_senha("maria@x.com", "novasenha")
        self.assertEqual(usuarios.autenticar("maria@x.com", "segredo1"), usuarios.INVALIDO)
        self.assertEqual(usuarios.autenticar("maria@x.com", "novasenha"), usuarios.OK)

    def test_redefinir_senha_curta_e_inexistente(self):
        usuarios.criar("Maria", "maria@x.com", "segredo1")
        with self.assertRaises(ValueError):
            usuarios.redefinir_senha("maria@x.com", "123")
        with self.assertRaises(ValueError):
            usuarios.redefinir_senha("ninguem@x.com", "novasenha")


if __name__ == "__main__":
    unittest.main()
