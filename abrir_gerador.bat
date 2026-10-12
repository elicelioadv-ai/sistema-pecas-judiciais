@echo off
title Sistema de Pecas Judiciais
cd /d "%~dp0"
echo ============================================
echo   Sistema de Pecas Judiciais - ligando...
echo   NAO FECHE ESTA JANELA enquanto usar.
echo   Para desligar: feche esta janela.
echo ============================================
python -m streamlit run app.py
pause