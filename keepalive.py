"""Mantém o app do Streamlit acordado (evita a soneca por inatividade).

Um HTTP GET simples NÃO resolve: ele devolve só a "casca" HTML e o processo
Python nunca sobe, então o app continua dormindo. Só um navegador de verdade
(que executa JavaScript e abre o WebSocket) conta como visita.

Este script abre o app num Chromium headless; se estiver dormindo, clica em
"Yes, get this app back up!" e espera o app carregar.
"""
import asyncio
import os
import sys

try:
    from playwright.async_api import async_playwright
except ImportError:  # pragma: no cover - depende do ambiente do runner
    sys.exit("Instale o Playwright: pip install playwright && playwright install chromium")

URL_PADRAO = "https://sistema-pecas-judiciais.streamlit.app/"
APPS = [u.strip() for u in (os.environ.get("STREAMLIT_APP_URL") or URL_PADRAO).split(",")
        if u.strip()]
NAVEGADOR = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
TEXTO_ACORDAR = "Yes, get this app back up!"


async def _botao_acordar(pagina):
    """Devolve o botão de acordar (ou None se o app já estiver acordado)."""
    for localizador in (pagina.get_by_role("button", name=TEXTO_ACORDAR),
                        pagina.get_by_text(TEXTO_ACORDAR)):
        try:
            if await localizador.count() > 0:
                return localizador.first
        except Exception:
            pass
    return None


async def visitar(pagina, url):
    print(f"\n-> {url}")
    await pagina.goto(url, wait_until="domcontentloaded", timeout=120000)
    await pagina.wait_for_timeout(8000)
    botao = await _botao_acordar(pagina)
    if botao is not None:
        print("   dormindo - clicando para acordar...")
        await botao.click()
        await pagina.wait_for_timeout(60000)
        print("   clique feito; aguardando o app carregar")
    else:
        print("   ja estava acordado")
    await pagina.wait_for_timeout(3000)


async def main():
    if not APPS:
        sys.exit("Nenhum URL configurado em STREAMLIT_APP_URL")
    async with async_playwright() as p:
        navegador = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        contexto = await navegador.new_context(user_agent=NAVEGADOR)
        pagina = await contexto.new_page()
        for url in APPS:
            try:
                await visitar(pagina, url)
            except Exception as erro:
                print(f"   ERRO {type(erro).__name__}: {erro}")
        await navegador.close()


if __name__ == "__main__":
    asyncio.run(main())
