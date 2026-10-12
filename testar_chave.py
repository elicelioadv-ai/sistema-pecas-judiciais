"""Testa a chave do .env nos dois modos. Rode no terminal:  python testar_chave.py"""
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
chave = os.getenv("GEMINI_API_KEY", "").strip().strip('"').strip("'")
modelo = os.getenv("MODELO", "gemini-2.5-flash").strip()
print("Chave encontrada no .env:", "SIM" if chave else "NÃO")
print("Tamanho:", len(chave), "| começa com:", chave[:3])
print("Modelo:", modelo)
print()
for nome, args in [("MODO GEMINI (padrão)", dict(api_key=chave)),
                   ("MODO VERTEX (para chaves AQ.)", dict(vertexai=True, api_key=chave))]:
    try:
        cliente = genai.Client(**args)
        r = cliente.models.generate_content(model=modelo, contents="Responda somente: ok")
        print("OK  ", nome, "->", (r.text or "").strip()[:30])
    except Exception as e:
        print("ERRO", nome, "->", str(e)[:200].replace(chave, "***"))