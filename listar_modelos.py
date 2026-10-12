"""Mostra quais modelos a SUA chave consegue usar. Rode:  python listar_modelos.py"""
import os
from dotenv import load_dotenv
from google import genai
load_dotenv()
c = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
for m in c.models.list():
    if "generateContent" in (m.supported_actions or []):
        print(m.name.replace("models/", ""))
