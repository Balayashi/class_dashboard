"""
================================================================================
SCRAPER INOVAR — aepjm.inovarmais.com  (Versão Definitiva AEPJM)
================================================================================
Fluxo comprovado e testado:
  1. Login em https://aepjm.inovarmais.com/consulta/app/index.html#/login
     - Preenche Login e Senha via click + fill (essencial para ng-model do Angular)
     - Clica em 'Entrar'
  2. Página #studentPicker:
     - Clica no cartão do aluno Dinis: [title='Consultar detalhe do aluno']
     - Chega a #/home
  3. Navega para https://aepjm.inovarmais.com/consulta/app/index.html#/horarios
  4. Extrai a Tabela de Eventos (Testes, Questões de Aula, Trabalhos)
     - Colunas: Data/Hora, Evento, Professor

Dependências: playwright, python-dotenv
================================================================================
"""

import asyncio
import json
import os
import re
from datetime import datetime, date
from pathlib import Path
from dotenv import load_dotenv
from playwright.async_api import (
    async_playwright, Page, BrowserContext,
    TimeoutError as PlaywrightTimeout
)

load_dotenv(Path(__file__).parent / ".env")

INOVAR_EMAIL    = os.getenv("INOVAR_EMAIL", "")
INOVAR_PASSWORD = os.getenv("INOVAR_PASSWORD", "")
STUDENT_NAME    = os.getenv("STUDENT_NAME", "Dinis")
STUDENT_NUMBER  = os.getenv("STUDENT_NUMBER", "18968")

URL_LOGIN   = "https://aepjm.inovarmais.com/consulta/app/index.html#/login"
URL_HOME    = "https://aepjm.inovarmais.com/consulta/app/index.html#/home"
URL_EVENTOS = "https://aepjm.inovarmais.com/consulta/app/index.html#/horarios"

PROFILE_DIR = Path(__file__).parent / ".chromium_profile_inovar"

EVENT_TYPE_MAP = {
    "teste":        "Teste",
    "questão-aula": "Questão de Aula",
    "questao-aula": "Questão de Aula",
    "questão aula": "Questão de Aula",
    "questao aula": "Questão de Aula",
    "trabalho":     "Trabalho",
    "exercício":    "Trabalho",
    "exercicio":    "Trabalho",
    "atividade":    "Trabalho",
    "ficha":        "Ficha",
}

DISC_MAP = {
    "matemática":               "Matemática",
    "matematica":               "Matemática",
    "português":                "Português",
    "portugues":                "Português",
    "história e geografia":     "HGP",
    "historia e geografia":     "HGP",
    "hgp":                      "HGP",
    "ciências naturais":        "Ciências Naturais",
    "ciencias naturais":        "Ciências Naturais",
    "inglês":                   "Inglês",
    "ingles":                   "Inglês",
    "educação musical":         "Educação Musical",
    "educacao musical":         "Educação Musical",
    "educação física":          "Educação Física",
    "educacao fisica":          "Educação Física",
    "pensamento computacional": "Matemática",
    "le1":                      "Inglês",
}


class InovarScraper:
    """Scraper robusto para a plataforma INOVAR Consulta da AEPJM."""

    def __init__(self):
        self._playwright = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    async def __aenter__(self):
        await self._init_browser()
        return self

    async def __aexit__(self, *_):
        await self._close()

    async def _init_browser(self):
        PROFILE_DIR.mkdir(exist_ok=True)
        self._playwright = await async_playwright().start()
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled", "--lang=pt-PT"],
            locale="pt-PT",
            timezone_id="Europe/Lisbon",
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
        print("[INOVAR] Browser inicializado.")

    async def _close(self):
        if self._context:
            await self._context.close()
        if self._playwright:
            await self._playwright.stop()

    async def _ensure_logged_in_and_selected(self) -> bool:
        page = self._page
        print("[INOVAR] A aceder ao portal INOVAR Consulta...")
        await page.goto(URL_LOGIN, wait_until="networkidle")
        await asyncio.sleep(2)

        # Se já estiver autenticado e com o aluno selecionado
        if "/home" in page.url or "/horarios" in page.url:
            print("[INOVAR] ✅ Já autenticado dentro do aluno Dinis.")
            return True

        # Se estiver no seletor de alunos
        if "/studentPicker" in page.url or await page.locator("[title='Consultar detalhe do aluno']").count() > 0:
            print("[INOVAR] Na seleção de alunos — a escolher Dinis...")
            return await self._select_dinis()

        # Efetua login
        print(f"[INOVAR] 🔐 A autenticar com a conta do encarregado ({INOVAR_EMAIL})...")
        try:
            login_el = page.locator("input[placeholder*='Login'], input[type='text']").first
            senha_el = page.locator("input[placeholder*='Senha'], input[type='password']").first

            await login_el.click()
            await login_el.fill(INOVAR_EMAIL)
            await senha_el.click()
            await senha_el.fill(INOVAR_PASSWORD)

            entrar_btn = page.locator("button:has-text('Entrar')").first
            await entrar_btn.click()
            await asyncio.sleep(4)

            # Seleciona o aluno Dinis
            return await self._select_dinis()

        except Exception as e:
            print(f"[INOVAR] ❌ Erro durante o login: {e}")
            await page.screenshot(path=str(Path(__file__).parent / "inovar_error.png"))
            return False

    async def _select_dinis(self) -> bool:
        page = self._page
        print(f"[INOVAR] 👦 A selecionar aluno: {STUDENT_NAME}...")

        try:
            # Aguarda carregar o cartão
            await page.wait_for_selector("[title='Consultar detalhe do aluno']", timeout=12_000)

            # Clica no cartão do Dinis (primeiro aluno da lista com title='Consultar detalhe do aluno')
            dinis_card = page.locator("[title='Consultar detalhe do aluno']").first
            await dinis_card.click()
            await asyncio.sleep(3.5)

            if "/home" in page.url or await page.locator("text='Dinis'").count() > 0:
                print("[INOVAR] ✅ Aluno Dinis selecionado com sucesso!")
                return True

        except Exception as e:
            print(f"[INOVAR] ⚠️ Erro ao selecionar aluno: {e}")

        return False

    async def extract_all_data(self) -> dict:
        """Ponto de entrada: extrai eventos do calendário oficial e faltas."""
        if not await self._ensure_logged_in_and_selected():
            print("[INOVAR] ❌ Não foi possível entrar no perfil do aluno.")
            return {"eventos": [], "faltas": {}}

        eventos = await self._extract_eventos()
        faltas  = await self._extract_faltas()

        print(f"\n[INOVAR] 🎯 Concluído: {len(eventos)} avaliações/eventos agendados no calendário oficial.")
        return {"eventos": eventos, "faltas": faltas}

    async def _extract_eventos(self) -> list[dict]:
        page = self._page
        eventos = []

        print("[INOVAR] 📅 A carregar página de horários e eventos...")
        try:
            await page.goto(URL_EVENTOS, wait_until="networkidle")
            await asyncio.sleep(4)

            # Localiza todas as tabelas
            tabelas = await page.query_selector_all("table")
            tabela_eventos = None

            # Procura especificamente a tabela que tem as colunas "Data/Hora", "Evento", "Professor"
            for t in tabelas:
                header_text = (await t.inner_text()).lower()
                if "data/hora" in header_text and "evento" in header_text:
                    tabela_eventos = t
                    break

            if not tabela_eventos and tabelas:
                # Fallback: a tabela de eventos é tipicamente a última da página
                tabela_eventos = tabelas[-1]

            if not tabela_eventos:
                print("[INOVAR] ⚠️ Tabela de eventos não encontrada.")
                return []

            # Extrai as linhas da tabela
            rows = await tabela_eventos.query_selector_all("tbody tr, tr")
            print(f"[INOVAR] {len(rows)} linhas encontradas na tabela de eventos.")

            for r in rows:
                cells = await r.query_selector_all("td")
                if len(cells) < 2:
                    continue

                cell_texts = [(await c.inner_text()).strip() for c in cells]
                raw_data_hora = cell_texts[0]
                raw_evento    = cell_texts[1]
                raw_prof      = cell_texts[2] if len(cell_texts) > 2 else ""

                if not raw_data_hora or not raw_evento or "data/hora" in raw_data_hora.lower():
                    continue

                data_iso, hora_ini, hora_fim = self._parse_data_hora(raw_data_hora)
                tipo, disciplina, titulo     = self._parse_evento(raw_evento)
                professor_limpo              = raw_prof.strip().split(",")[0].strip()

                evento = {
                    "tipo":          tipo,
                    "disciplina":    disciplina,
                    "titulo":        titulo,
                    "data":          data_iso,
                    "hora":          hora_ini,
                    "hora_fim":      hora_fim,
                    "descricao":     f"Professor: {professor_limpo}" if professor_limpo else "",
                    "professor":     professor_limpo,
                    "fonte":         "INOVAR",
                    "leitura":       "Confirmado ✅",
                    "data_hora_raw": raw_data_hora
                }
                eventos.append(evento)
                print(f"[INOVAR]   → [{tipo}] {disciplina}: {titulo} ({data_iso} {hora_ini})")

        except Exception as e:
            print(f"[INOVAR] ❌ Erro ao extrair eventos da tabela: {e}")

        return eventos

    async def _extract_faltas(self) -> dict:
        page = self._page
        faltas = {"total": 0, "injustificadas": 0}
        try:
            body = await page.inner_text("body")
            m_total = re.search(r"Total de faltas[:\s]+(\d+)", body, re.IGNORECASE)
            m_inju  = re.search(r"Injustificadas[:\s]+(\d+)", body, re.IGNORECASE)
            if m_total:
                faltas["total"] = int(m_total.group(1))
            if m_inju:
                faltas["injustificadas"] = int(m_inju.group(1))
        except Exception:
            pass
        return faltas

    def _parse_data_hora(self, raw: str) -> tuple[str, str, str]:
        data_iso = ""
        hora_ini = ""
        hora_fim = ""

        # Formato: "02-11-2026 (08:15-09:05)"
        m_date = re.search(r"(\d{2})-(\d{2})-(\d{4})", raw)
        if m_date:
            d, m, y = m_date.groups()
            data_iso = f"{y}-{m}-{d}"

        m_time = re.search(r"\((\d{2}:\d{2})-(\d{2}:\d{2})\)", raw)
        if m_time:
            hora_ini, hora_fim = m_time.groups()

        return data_iso, hora_ini, hora_fim

    def _parse_evento(self, raw: str) -> tuple[str, str, str]:
        raw_lower = raw.lower()

        tipo = "Teste"
        for kw, t in EVENT_TYPE_MAP.items():
            if kw in raw_lower:
                tipo = t
                break

        disciplina = "Geral"
        for kw, d in DISC_MAP.items():
            if kw in raw_lower:
                disciplina = d
                break

        # Remove nome do professor após vírgula se estiver no título
        titulo = raw.split(",")[0].strip()
        if len(titulo) > 80:
            titulo = titulo[:77] + "..."

        return tipo, disciplina, titulo


if __name__ == "__main__":
    async def _test():
        async with InovarScraper() as s:
            dados = await s.extract_all_data()
            print(f"\nTotal eventos: {len(dados['eventos'])}")
            for ev in dados['eventos'][:8]:
                print(f"  [{ev['tipo']}] {ev['disciplina']} | {ev['titulo']} | {ev['data']} {ev['hora']}")
            print("Faltas:", dados['faltas'])

    asyncio.run(_test())
