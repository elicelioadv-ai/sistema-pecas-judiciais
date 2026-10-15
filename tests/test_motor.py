"""Testes das funções críticas do motor (sem chamar a IA).

Rode na raiz do projeto:  python -m unittest discover -s tests
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import motor


BASE_EXEMPLO = [
    motor.novo_item_base("cdc_14", "Lei nº 8.078/1990 (CDC), art. 14",
                         "Responde objetivamente.", status="verificado",
                         fonte="https://planalto.gov.br"),
    motor.novo_item_base("cba_256", "Lei nº 7.565/1986 (CBA), art. 256, §3º",
                         "Caso fortuito.", status="conferir"),
]


class TestExtracaoDados(unittest.TestCase):
    def test_encontra_data_valor_hora(self):
        achados = motor.extrair_dados_sensiveis("Em 10/03/2026 gastei R$ 87,00 às 08h00.")
        self.assertIn("10/03/2026", achados["data"])
        self.assertIn("R$ 87,00", achados["valor"])
        self.assertTrue(any(h in ("08h00", "08:00") for h in achados["hora"]))


class TestConferenciaCitacoes(unittest.TestCase):
    def test_substitui_fonte_valida(self):
        texto = "A ré responde objetivamente [FONTE:cdc_14]."
        r = motor.conferir_citacoes(texto, BASE_EXEMPLO, "nada")
        self.assertIn("Lei nº 8.078/1990 (CDC), art. 14", r["texto"])
        self.assertEqual(len(r["usadas"]), 1)
        self.assertFalse(any(n == "erro" for n, _ in r["alertas"]))

    def test_fonte_inexistente_gera_erro(self):
        r = motor.conferir_citacoes("[FONTE:nao_existe]", BASE_EXEMPLO, "nada")
        self.assertTrue(any(n == "erro" for n, _ in r["alertas"]))
        self.assertIn("FONTE INEXISTENTE", r["texto"])

    def test_artigo_fora_da_base(self):
        r = motor.conferir_citacoes("Conforme art. 999 do CDC.", BASE_EXEMPLO, "nada")
        self.assertTrue(any("art. 999" in m for _, m in r["alertas"]))

    def test_fonte_conferir_gera_aviso(self):
        r = motor.conferir_citacoes("[FONTE:cba_256]", BASE_EXEMPLO, "nada")
        self.assertTrue(any("status 'conferir'" in m for _, m in r["alertas"]))

    def test_data_inventada_e_alertada(self):
        fatos = "O voo atrasou em 10/03/2026."
        r = motor.conferir_citacoes("O autor nasceu em 01/01/1999.", BASE_EXEMPLO, fatos)
        self.assertTrue(any("01/01/1999" in m for _, m in r["alertas"]))

    def test_valor_legitimo_nao_e_alertado(self):
        fatos = "Gastou R$ 87,00 no almoço."
        r = motor.conferir_citacoes("Comprovado o gasto de R$ 87,00.", BASE_EXEMPLO, fatos)
        self.assertFalse(any("R$ 87,00" in m for _, m in r["alertas"]))

    def test_campos_pendentes(self):
        r = motor.conferir_citacoes("Valor: [PREENCHER: dano moral].", BASE_EXEMPLO, "nada")
        self.assertTrue(any("PREENCHER" in m for _, m in r["alertas"]))

    def test_sem_alertas_retorna_ok(self):
        r = motor.conferir_citacoes("Texto limpo, sem citações.", BASE_EXEMPLO, "nada")
        self.assertEqual(r["alertas"][0][0], "ok")


class TestBase(unittest.TestCase):
    def test_status_invalido(self):
        with self.assertRaises(ValueError):
            motor.novo_item_base("x", "ref", "txt", status="talvez")

    def test_nome_base_invalido(self):
        with self.assertRaises(ValueError):
            motor.salvar_base("nome com espaço", [])

    def test_apagar_base(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = motor.PASTA_BASE
            motor.PASTA_BASE = Path(tmp)
            try:
                motor.salvar_base("base_teste", [motor.novo_item_base("a", "ref", "txt")])
                self.assertIn("base_teste", motor.listar_bases())
                motor.apagar_base("base_teste")
                self.assertNotIn("base_teste", motor.listar_bases())
            finally:
                motor.PASTA_BASE = original

    def test_apagar_base_nome_invalido(self):
        with self.assertRaises(ValueError):
            motor.apagar_base("nome com espaço")


class TestExportacao(unittest.TestCase):
    def test_exporta_docx_e_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            docx = Path(tmp) / "peca.docx"
            pdf = Path(tmp) / "peca.pdf"
            texto = "I – DOS FATOS\n\nO autor viajou em 10/03/2026.\n\nIV – DOS PEDIDOS"
            motor.salvar_docx(texto, docx)
            motor.salvar_pdf(texto, pdf)
            self.assertTrue(docx.exists() and docx.stat().st_size > 0)
            self.assertTrue(pdf.exists() and pdf.stat().st_size > 0)


class TestAnexo(unittest.TestCase):
    def test_extrai_txt(self):
        self.assertIn("Edital", motor.extrair_texto_anexo("e.txt", "Edital nº 1".encode("utf-8")))

    def test_extrai_docx(self):
        import io

        from docx import Document

        buf = io.BytesIO()
        d = Document()
        d.add_paragraph("Cláusula 3.2 — prazo de 5 dias")
        d.save(buf)
        self.assertIn("prazo de 5 dias", motor.extrair_texto_anexo("e.docx", buf.getvalue()))

    def test_formato_invalido(self):
        with self.assertRaises(RuntimeError):
            motor.extrair_texto_anexo("e.xlsx", b"x")


class TestIdentificarModelo(unittest.TestCase):
    MODELOS = ["peticao_inicial_jec", "contestacao_jec", "recurso_inominado_jec",
               "apelacao", "embargos_de_declaracao"]

    def test_sem_modelos(self):
        self.assertIsNone(motor.identificar_modelo("qualquer coisa", []))

    def test_padrao_um_modelo(self):
        self.assertEqual(motor.identificar_modelo("voo atrasado", ["peticao_inicial_jec"]),
                         "peticao_inicial_jec")

    def test_peticao_inicial(self):
        f = "a cliente comprou passagem e quer indenização por danos morais"
        self.assertEqual(motor.identificar_modelo(f, self.MODELOS), "peticao_inicial_jec")

    def test_recurso_inominado(self):
        f = "recurso inominado contra a sentença do juizado especial"
        self.assertEqual(motor.identificar_modelo(f, self.MODELOS), "recurso_inominado_jec")

    def test_contestacao(self):
        f = "contestação: o réu nega a compra alegada"
        self.assertEqual(motor.identificar_modelo(f, self.MODELOS), "contestacao_jec")

    def test_apelacao(self):
        f = "apelação contra sentença proferida pela 1ª vara"
        self.assertEqual(motor.identificar_modelo(f, self.MODELOS), "apelacao")

    def test_embargos(self):
        f = "pede embargos de declaração por omissão na sentença"
        self.assertEqual(motor.identificar_modelo(f, self.MODELOS), "embargos_de_declaracao")


class TestSenha(unittest.TestCase):
    """Portão de acesso: verificação de senha armazenada com hash no .env."""

    def _limpar_env(self):
        chave = os.environ.get("SENHA_ACESSO")
        os.environ.pop("SENHA_ACESSO", None)
        return chave

    def test_verificar_senha_hash(self):
        import hashlib

        original = self._limpar_env()
        try:
            os.environ["SENHA_ACESSO"] = "sha256:" + hashlib.sha256(b"f4cil#Senha").hexdigest()
            self.assertTrue(motor.senha_ativa())
            self.assertTrue(motor.verificar_senha("f4cil#Senha"))
            self.assertFalse(motor.verificar_senha("outra-senha"))
            self.assertFalse(motor.verificar_senha(""))
        finally:
            if original:
                os.environ["SENHA_ACESSO"] = original
            else:
                os.environ.pop("SENHA_ACESSO", None)

    def test_verificar_senha_texto_puro(self):
        original = self._limpar_env()
        try:
            os.environ["SENHA_ACESSO"] = "minha-senha"
            self.assertTrue(motor.verificar_senha("minha-senha"))
            self.assertFalse(motor.verificar_senha("errada"))
        finally:
            if original:
                os.environ["SENHA_ACESSO"] = original
            else:
                os.environ.pop("SENHA_ACESSO", None)

    def test_sem_senha_definida(self):
        original = self._limpar_env()
        try:
            self.assertFalse(motor.senha_ativa())
            self.assertFalse(motor.verificar_senha("qualquer"))
        finally:
            if original:
                os.environ["SENHA_ACESSO"] = original
            else:
                os.environ.pop("SENHA_ACESSO", None)

    def test_definir_senha_fraca(self):
        with self.assertRaises(ValueError):
            motor.definir_senha("ab")

    def test_verificar_acesso_usuario_e_senha(self):
        import hashlib

        user_orig, senha_orig = os.environ.get("ACESSO_USUARIO"), os.environ.get("SENHA_ACESSO")
        os.environ.pop("ACESSO_USUARIO", None)
        os.environ.pop("SENHA_ACESSO", None)
        try:
            os.environ["ACESSO_USUARIO"] = "admin"
            os.environ["SENHA_ACESSO"] = "sha256:" + hashlib.sha256(b"f4cil#Senha").hexdigest()
            self.assertTrue(motor.verificar_acesso("admin", "f4cil#Senha"))
            self.assertFalse(motor.verificar_acesso("admin", "errada"))
            self.assertFalse(motor.verificar_acesso("outro", "f4cil#Senha"))
            self.assertFalse(motor.verificar_acesso("", ""))
        finally:
            for k, v in (("ACESSO_USUARIO", user_orig), ("SENHA_ACESSO", senha_orig)):
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_definir_acesso_valida(self):
        with self.assertRaises(ValueError):
            motor.definir_acesso("a", "12345")
        with self.assertRaises(ValueError):
            motor.definir_acesso("admin", "12")

    def test_usuario_sem_acesso(self):
        user_orig = os.environ.get("ACESSO_USUARIO")
        os.environ.pop("ACESSO_USUARIO", None)
        try:
            self.assertFalse(motor.usuario_acesso())
        finally:
            if user_orig is None:
                os.environ.pop("ACESSO_USUARIO", None)
            else:
                os.environ["ACESSO_USUARIO"] = user_orig


if __name__ == "__main__":
    unittest.main()
