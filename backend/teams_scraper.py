"""
================================================================================
SCRAPER TEAMS — Versão Otimizada para o Microsoft Teams Web da Turma 5º G
================================================================================
Compatível com a interface atual do Teams Web (teams.cloud.microsoft):
  - Deteta automaticamente sessão ativa existente sem pedir login desnecessário
  - Navega diretamente entre o painel 'Aulas' / 'Todas as equipas' e as salas
  - Extrai os posts dos professores das 6 salas:
      * 5G EM 26-27 (Paulo Cairrão)
      * MAT 5G 26-27 (Inês Isabel Vaz Mendonça)
      * 5º G - HGP - História e Geografia de Portugal... (Abílio Mocho)
      * CN 5G 26-27 (Inês Isabel Vaz Mendonça)
      * 5º G - Português - 2026/2027 (Abílio Mocho)
      * DTA 5G 26-27
  - Deteta a matéria de estudo dos testes postada pelos professores
  - Deteta pedidos de tomada de conhecimento e se o Dinis já respondeu

Dependências: playwright, python-dotenv
================================================================================
"""

import asyncio
import json
import os
import re
import hashlib
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from playwright.async_api import (
    async_playwright, BrowserContext, Page,
    TimeoutError as PlaywrightTimeout
)

load_dotenv(Path(__file__).parent / ".env")

TEAMS_EMAIL    = os.getenv("TEAMS_EMAIL", "")
TEAMS_PASSWORD = os.getenv("TEAMS_PASSWORD", "")
TEAMS_URL      = "https://teams.cloud.microsoft/"
PROFILE_DIR    = Path(__file__).parent / ".chromium_profile_teams"
SEEN_POSTS_FILE = Path(__file__).parent / "seen_posts.json"

STUDENT_FIRST_NAME = "dinis"

# Salas da Turma 5º G a monitorizar
TEAMS_GROUPS = [
    {
        "nome":       "5G EM 26-27",
        "disciplina": "Educação Musical",
        "professor":  "Paulo Cairrão",
        "search":     "5G EM"
    },
    {
        "nome":       "MAT 5G 26-27",
        "disciplina": "Matemática",
        "professor":  "Inês Isabel Vaz Mendonça",
        "search":     "MAT 5G"
    },
    {
        "nome":       "5º G - HGP",
        "disciplina": "HGP",
        "professor":  "Abílio Mocho",
        "search":     "HGP"
    },
    {
        "nome":       "CN 5G 26-27",
        "disciplina": "Ciências Naturais",
        "professor":  "Inês Isabel Vaz Mendonça",
        "search":     "CN 5G"
    },
    {
        "nome":       "5º G - Português",
        "disciplina": "Português",
        "professor":  "Abílio Mocho",
        "search":     "Português"
    },
    {
        "nome":       "DTA 5G 26-27",
        "disciplina": "DTA",
        "professor":  "",
        "search":     "DTA 5G"
    },
]

PROFESSOR_NAMES = [
    "paulo cairrão", "paulo cairrao",
    "inês mendonça", "ines mendonca", "inês isabel vaz mendonça", "ines isabel vaz mendonca",
    "abílio mocho", "abilio mocho", "abílio josé mocho", "abilio jose mocho",
]


class TeamsScraper:
    """Scraper robusto para a interface web moderna do Microsoft Teams."""

    def __init__(self):
        self._playwright = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._seen_posts = self._load_seen_posts()

    async def __aenter__(self):
        await self._init_browser()
        return self

    async def __aexit__(self, *_):
        await self._close()
        self._save_seen_posts()

    # ------------------------------------------------------------------
    # PERSISTÊNCIA DE POSTS E CONFIRMAÇÕES
    # ------------------------------------------------------------------
    def _load_seen_posts(self) -> dict:
        try:
            if SEEN_POSTS_FILE.exists():
                return json.loads(SEEN_POSTS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    def _save_seen_posts(self):
        try:
            SEEN_POSTS_FILE.write_text(
                json.dumps(self._seen_posts, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception:
            pass

    def _make_post_id(self, disciplina: str, texto: str, data_raw: str = "") -> str:
        raw = f"{disciplina}|{data_raw}|{texto[:120]}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    # ------------------------------------------------------------------
    # BROWSER
    # ------------------------------------------------------------------
    async def _init_browser(self):
        PROFILE_DIR.mkdir(exist_ok=True)
        self._playwright = await async_playwright().start()
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=True,  # Execução silenciosa em background
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--lang=pt-PT"
            ],
            locale="pt-PT",
            timezone_id="Europe/Lisbon",
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
        print("[Teams] Browser inicializado.")

    async def _close(self):
        if self._context:
            await self._context.close()
        if self._playwright:
            await self._playwright.stop()

    # ------------------------------------------------------------------
    # AUTENTICAÇÃO E VERIFICAÇÃO DE SESSÃO
    # ------------------------------------------------------------------
    async def _ensure_logged_in(self) -> bool:
        page = self._page
        print(f"[Teams] A aceder a {TEAMS_URL}...")
        try:
            await page.goto(TEAMS_URL, wait_until="domcontentloaded", timeout=30_000)
            await asyncio.sleep(4)
        except Exception as e:
            print(f"[Teams] Aviso no carregamento inicial: {e}")

        # Verifica se já está dentro do Teams (em português)
        url_atual = page.url.lower()
        if "teams.cloud.microsoft" in url_atual or "teams.microsoft.com" in url_atual:
            # Testa a presença de elementos típicos da interface já autenticada
            dentro_do_teams = await page.locator(
                "text='Equipas', text='Aulas', text='Todas as equipas', [aria-label*='Equipas']"
            ).count()
            if dentro_do_teams > 0 or "login" not in url_atual:
                print("[Teams] ✅ Sessão ativa — dentro do Microsoft Teams!")
                return True

        # Se cair na página de login da Microsoft
        print("[Teams] 🔐 Sessão não ativa. A iniciar processo de login...")
        return await self._do_login()

    async def _do_login(self) -> bool:
        page = self._page
        if not TEAMS_EMAIL or not TEAMS_PASSWORD:
            print("[Teams] ❌ TEAMS_EMAIL ou TEAMS_PASSWORD não definidos no .env")
            return False

        try:
            # 1. Email
            email_input = page.locator("input[type='email']")
            if await email_input.count() > 0:
                print(f"[Teams] A introduzir email ({TEAMS_EMAIL})...")
                await email_input.first.fill(TEAMS_EMAIL)
                await page.click("input[type='submit'], #idSIButton9")
                await asyncio.sleep(2)
                await page.wait_for_load_state("networkidle", timeout=12_000)

            # 2. Password
            pwd_input = page.locator("input[type='password']")
            if await pwd_input.count() > 0:
                print("[Teams] A introduzir password...")
                await pwd_input.first.fill(TEAMS_PASSWORD)
                await page.click("input[type='submit'], #idSIButton9")
                await asyncio.sleep(2)
                await page.wait_for_load_state("networkidle", timeout=12_000)

            # 3. "Manter sessão?" (KMSI)
            kmsi_btn = page.locator("#idSIButton9")
            if await kmsi_btn.count() > 0:
                await kmsi_btn.click()
                await asyncio.sleep(3)

            # Aguarda o Teams carregar
            print("[Teams] ⏳ A aguardar entrada no Teams...")
            await page.wait_for_selector(
                "text='Equipas', text='Aulas', [aria-label*='Equipas']",
                timeout=60_000
            )
            print("[Teams] ✅ Login concluído com sucesso!")
            return True

        except Exception as e:
            print(f"[Teams] ❌ Erro durante login: {e}")
            await page.screenshot(path=str(Path(__file__).parent / "teams_login_error.png"))
            return False

    # ------------------------------------------------------------------
    # NAVEGAÇÃO ENTRE SALAS
    # ------------------------------------------------------------------
    async def _return_to_teams_grid(self) -> bool:
        """Garante que estamos na grelha de salas/aulas."""
        page = self._page
        try:
            # 1. Se estiver dentro de uma sala, clica em "Todas as equipas"
            back_btn = page.locator("text='Todas as equipas', [aria-label*='Todas as equipas']")
            if await back_btn.count() > 0:
                await back_btn.first.click()
                await asyncio.sleep(2)
                return True

            # 2. Alternativa: clica no ícone "Equipas" na barra lateral esquerda
            equipas_icon = page.locator("[aria-label*='Equipas'], button:has-text('Equipas')").first
            if await equipas_icon.count() > 0:
                await equipas_icon.click()
                await asyncio.sleep(2)
                return True
        except Exception:
            pass

        return True

    async def _open_group(self, group: dict) -> bool:
        """Clica no cartão da sala correspondente."""
        page = self._page
        search_term = group["search"]
        print(f"[Teams] 🔍 A abrir sala: '{group['nome']}' ({group['disciplina']})...")

        await self._return_to_teams_grid()

        # Procura o cartão da sala na grelha
        card = page.locator(f":text-matches('{search_term}', 'i')").first
        if await card.count() > 0:
            try:
                await card.click()
                await asyncio.sleep(3.5)
                return True
            except Exception as e:
                print(f"[Teams] Erro ao clicar no cartão de {group['nome']}: {e}")

        print(f"[Teams] ⚠️ Sala '{group['nome']}' não encontrada na grelha.")
        return False

    # ------------------------------------------------------------------
    # EXTRAÇÃO DE MENSAGENS E RECADOS DA SALA
    # ------------------------------------------------------------------
    async def _extract_group_messages(self, group: dict) -> list[dict]:
        page = self._page
        disciplina = group["disciplina"]
        professor_default = group["professor"]
        mensagens = []

        try:
            # Garante que está no separador 'Publicações'
            pub_tab = page.locator("text='Publicações'").first
            if await pub_tab.count() > 0:
                await pub_tab.click()
                await asyncio.sleep(1.5)

            # Rola para cima para carregar histórico recente
            for _ in range(2):
                await page.keyboard.press("Control+Home")
                await asyncio.sleep(0.8)

            # Extrai todo o texto da área de publicações
            body_text = await page.inner_text("body")
            linhas = [l.strip() for l in body_text.splitlines() if l.strip()]

            # Analisa blocos de mensagens de professores
            blocos = self._parse_text_into_posts(linhas, disciplina, professor_default)
            mensagens.extend(blocos)

        except Exception as e:
            print(f"[Teams] Erro ao ler publicações de {disciplina}: {e}")

        print(f"[Teams]   ✅ {len(mensagens)} post(s) relevante(s) extraído(s) de {disciplina}.")
        return mensagens

    def _parse_text_into_posts(self, lines: list[str], disciplina: str, professor_default: str) -> list[dict]:
        """
        Organiza as linhas de texto em publicações individuais de professores,
        detetando:
          - Autor do post
          - Data do post
          - Conteúdo do post (matéria do teste, TPC, recado)
          - Se o post pede "tomada de conhecimento"
          - Se o Dinis já respondeu a confirmar
        """
        posts = []
        i = 0
        total_lines = len(lines)

        while i < total_lines:
            line = lines[i]

            # Deteta início de um post de professor
            autor_encontrado = None
            for p in PROFESSOR_NAMES:
                if p in line.lower():
                    autor_encontrado = line
                    break

            if not autor_encontrado and professor_default and professor_default.lower() in line.lower():
                autor_encontrado = professor_default

            # Se encontrou uma publicação ou palavras-chave de teste/tpc
            is_post_header = autor_encontrado or any(
                k in line.lower() for k in ["teste", "avaliação", "questão-aula", "tpc", "trabalho", "critérios"]
            )

            if is_post_header:
                data_post = ""
                # A linha seguinte costuma ser o timestamp (ex: "21/10 18:54" ou "16/09 17:37")
                if i + 1 < total_lines and re.search(r"\d{1,2}/\d{1,2}", lines[i + 1]):
                    data_post = lines[i + 1]
                    conteudo_start = i + 2
                else:
                    conteudo_start = i + 1

                # Junta o conteúdo até ao próximo post ou resposta
                conteudo_linhas = []
                dinis_confirmou = False
                pede_conhecimento = False

                j = conteudo_start
                while j < min(total_lines, conteudo_start + 25):
                    sub_line = lines[j]
                    sub_lower = sub_line.lower()

                    # Verifica se o post do professor pede confirmação
                    if any(w in sub_lower for w in ["tomaram conhecimento", "tomou conhecimento", "tomei conhecimento", "confirmem"]):
                        pede_conhecimento = True

                    # Verifica se o Dinis já respondeu nas respostas deste post
                    if STUDENT_FIRST_NAME in sub_lower and "conhecimento" in sub_lower:
                        dinis_confirmou = True

                    # Se encontrou o início de um novo post grande, para
                    if j > conteudo_start + 2 and any(p in sub_lower for p in PROFESSOR_NAMES):
                        break

                    conteudo_linhas.append(sub_line)
                    j += 1

                texto_completo = "\n".join(conteudo_linhas).strip()
                if len(texto_completo) > 15:
                    post_id = self._make_post_id(disciplina, texto_completo, data_post)

                    # Verifica se já tinha sido confirmado anteriormente na app
                    ja_visto = self._seen_posts.get(post_id, {})
                    confirmado = dinis_confirmou or ja_visto.get("confirmado", False)

                    # Se pede conhecimento e o Dinis ainda não confirmou nem no Teams nem na App:
                    # 'nao_lido' permanece True!
                    nao_lido = pede_conhecimento and not confirmado

                    # Regista no ficheiro de posts
                    if post_id not in self._seen_posts:
                        self._seen_posts[post_id] = {
                            "confirmado": confirmado,
                            "disciplina": disciplina,
                            "data_post":  data_post,
                            "titulo":     texto_completo[:80],
                            "primeira_vez": datetime.now().isoformat()
                        }
                    elif confirmado and not self._seen_posts[post_id].get("confirmado"):
                        self._seen_posts[post_id]["confirmado"] = True

                    posts.append({
                        "autor":             autor_encontrado or professor_default or "Professor",
                        "data_raw":          data_post,
                        "texto":             texto_completo,
                        "disciplina":        disciplina,
                        "canal":             disciplina,
                        "post_id":           post_id,
                        "pede_conhecimento": pede_conhecimento,
                        "nao_lido":          nao_lido,
                        "confirmado":        confirmado
                    })

                i = max(i + 1, j)
            else:
                i += 1

        return posts

    # ------------------------------------------------------------------
    # PONTO DE ENTRADA PRINCIPAL
    # ------------------------------------------------------------------
    async def extract_all_channels(self) -> list[dict]:
        """
        Navega por todas as salas configuradas da Turma 5º G e extrai mensagens.
        """
        if not await self._ensure_logged_in():
            print("[Teams] ❌ Não foi possível autenticar.")
            return []

        all_messages = []

        for group in TEAMS_GROUPS:
            if await self._open_group(group):
                msgs = await self._extract_group_messages(group)
                all_messages.extend(msgs)
            await asyncio.sleep(1)

        # Volta à grelha no final
        await self._return_to_teams_grid()

        nao_lidos = sum(1 for m in all_messages if m.get("nao_lido"))
        print(f"\n[Teams] 🎯 Concluído: {len(all_messages)} posts extraídos ({nao_lidos} pendentes de confirmação de leitura).")
        return all_messages


if __name__ == "__main__":
    async def _test():
        async with TeamsScraper() as s:
            msgs = await s.extract_all_channels()
            print(f"\nTotal: {len(msgs)}")
            for m in msgs:
                status = "🔔 NÃO LIDO" if m.get("nao_lido") else "✅ CONFIRMADO"
                print(f"[{m['disciplina']}] {m['autor']} ({m['data_raw']}) - {status}")
                print(f"  {m['texto'][:120]}...\n")

    asyncio.run(_test())
