"""Smoke test da interface: garante que o app.py sobe sem exceção.

Rode:  python -m unittest discover -s tests
"""
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from streamlit.testing.v1 import AppTest


class TestApp(unittest.TestCase):
    def test_app_roda_sem_excecao(self):
        at = AppTest.from_file(str(RAIZ / "app.py"), default_timeout=30)
        at.run()
        self.assertEqual(len(at.exception), 0, [e.value for e in at.exception])


if __name__ == "__main__":
    unittest.main()
