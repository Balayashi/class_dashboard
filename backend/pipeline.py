"""
================================================================================
PIPELINE PRINCIPAL — ORQUESTRADOR DO DASHBOARD ESCOLAR
================================================================================
Coordena o fluxo de ponta a ponta:
  1. Teams Scraper  → extrai posts e matérias de estudo dos canais da Turma 5º G
  2. INOVAR Scraper → extrai o calendário de testes e avaliações de /horarios
  3. Gemini AI      → cruza INOVAR + TEAMS:
                      - Se há teste no INOVAR, funde com o que sai no teste do Teams
                      - Se há novos TPCs/Avisos, adiciona à lista
                      - Deteta pedidos de tomada de conhecimento ("Por Confirmar 🔔")
  4. Sheets Syncer  → escreve ou atualiza linhas na Google Sheet (lida pela TV LG)
  5. Log & Backup   → guarda auditoria e estado
================================================================================
"""

import asyncio
import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# Módulos do ecossistema
from teams_scraper    import TeamsScraper
from inovar_scraper   import InovarScraper
from gemini_extractor import GeminiExtractor
from sheets_syncer    import SheetsSyncer

LOG_DIR  = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"pipeline_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("dashboard.pipeline")


class DashboardPipeline:
    def __init__(self, dry_run: bool = False, only: str = "all"):
        self.dry_run = dry_run
        self.only    = only
        self.stats   = {
            "inicio":           datetime.now().isoformat(),
            "teams_msgs":       0,
            "inovar_eventos":   0,
            "gemini_eventos":   0,
            "sheets_inseridos": 0,
            "sheets_atualizados": 0,
            "erros":            [],
        }

    async def run(self) -> dict:
        log.info("=" * 65)
        log.info(f"DASHBOARD PIPELINE — INÍCIO ({datetime.now().strftime('%d/%m/%Y %H:%M:%S')})")
        log.info(f"Modo: {'DRY-RUN (Simulação sem escrita)' if self.dry_run else 'PRODUÇÃO (Sincronização ativa)'}")
        log.info("=" * 65)

        mensagens_teams = []
        dados_inovar    = {"eventos": [], "faltas": {}}

        # ------------------------------------------------------------------
        # FASE 1: Scraping do INOVAR (Calendário Oficial de Testes)
        # ------------------------------------------------------------------
        if self.only in ("all", "inovar"):
            log.info("\n🏫 FASE 1/4 — INOVAR Scraper (aepjm.inovarmais.com)")
            try:
                async with InovarScraper() as scraper:
                    dados_inovar = await scraper.extract_all_data()
                eventos_inovar = dados_inovar.get("eventos", [])
                self.stats["inovar_eventos"] = len(eventos_inovar)
                log.info(f"✅ INOVAR: {len(eventos_inovar)} avaliações agendadas extraídas.")
                faltas = dados_inovar.get("faltas", {})
                if faltas:
                    log.info(f"   Faltas do aluno: Total={faltas.get('total',0)} | Injustificadas={faltas.get('injustificadas',0)}")
            except Exception as e:
                log.error(f"❌ Erro no INOVAR Scraper: {e}")
                self.stats["erros"].append(f"INOVAR: {str(e)[:120]}")

        # ------------------------------------------------------------------
        # FASE 2: Scraping do Microsoft Teams (Canais dos Professores)
        # ------------------------------------------------------------------
        if self.only in ("all", "teams"):
            log.info("\n📋 FASE 2/4 — Microsoft Teams Scraper (Turma 5º G)")
            try:
                async with TeamsScraper() as scraper:
                    mensagens_teams = await scraper.extract_all_channels()
                self.stats["teams_msgs"] = len(mensagens_teams)
                log.info(f"✅ Teams: {len(mensagens_teams)} publicações dos professores extraídas.")
            except Exception as e:
                log.error(f"❌ Erro no Teams Scraper: {e}")
                self.stats["erros"].append(f"Teams: {str(e)[:120]}")

        # ------------------------------------------------------------------
        # FASE 3: Correlação e Enriquecimento Inteligente com Gemini AI
        # ------------------------------------------------------------------
        log.info("\n🤖 FASE 3/4 — Gemini AI (Cruzamento INOVAR + TEAMS)")
        todos_eventos = []

        try:
            extractor = GeminiExtractor()
            todos_eventos = await extractor.correlate_and_extract(
                inovar_eventos=dados_inovar.get("eventos", []),
                teams_messages=mensagens_teams
            )
            self.stats["gemini_eventos"] = len(todos_eventos)
            log.info(f"✅ Gemini: {len(todos_eventos)} eventos processados e correlacionados.")
        except ValueError as val_err:
            log.warning(f"⚠️  {val_err}")
            log.warning("   A usar fallback: eventos do INOVAR sem enriquecimento por IA.")
            todos_eventos = dados_inovar.get("eventos", [])
        except Exception as e:
            log.error(f"❌ Erro na extração com Gemini: {e}")
            self.stats["erros"].append(f"Gemini: {str(e)[:120]}")
            todos_eventos = dados_inovar.get("eventos", [])

        # ------------------------------------------------------------------
        # FASE 4: Sincronização com Google Sheet (Lida pela TV LG)
        # ------------------------------------------------------------------
        log.info("\n📊 FASE 4/4 — Sincronização com Google Sheet")

        if todos_eventos and not self.dry_run:
            try:
                syncer = SheetsSyncer()
                syncer.connect()
                res = syncer.sync_events(todos_eventos)
                self.stats["sheets_inseridos"]   = res.get("inseridos", 0)
                self.stats["sheets_atualizados"] = res.get("atualizados", 0)
                log.info(
                    f"✅ Sheets: {res.get('inseridos', 0)} novos inseridos | "
                    f"{res.get('atualizados', 0)} atualizados com matéria | "
                    f"{res.get('ignorados', 0)} sem alterações."
                )
            except Exception as e:
                log.error(f"❌ Erro ao sincronizar com Google Sheets: {e}")
                self.stats["erros"].append(f"Sheets: {str(e)[:120]}")
        elif self.dry_run:
            log.info(f"🔍 [DRY-RUN] Prévia dos {len(todos_eventos)} eventos que seriam sincronizados:")
            for ev in todos_eventos:
                log.info(
                    f"   [{ev.get('tipo')}] {ev.get('disciplina')} | {ev.get('titulo')} | "
                    f"Data: {ev.get('data')} {ev.get('hora')} | Fonte: {ev.get('fonte')} | Leitura: {ev.get('leitura')}"
                )
                if ev.get("descricao"):
                    log.info(f"       📝 Matéria: {ev.get('descricao')}")

        # Sumário
        self.stats["fim"] = datetime.now().isoformat()
        self._log_summary()
        self._save_last_run(todos_eventos)
        return self.stats

    def _log_summary(self):
        log.info("\n" + "=" * 65)
        log.info("SUMÁRIO DA EXECUÇÃO")
        log.info("=" * 65)
        log.info(f"  Testes INOVAR extraídos:     {self.stats['inovar_eventos']}")
        log.info(f"  Publicações Teams extraídas: {self.stats['teams_msgs']}")
        log.info(f"  Eventos Finais Correlacionados: {self.stats['gemini_eventos']}")
        log.info(f"  Inseridos na Sheet:          {self.stats['sheets_inseridos']}")
        log.info(f"  Atualizados com Matéria:     {self.stats['sheets_atualizados']}")
        if self.stats["erros"]:
            log.warning(f"  Erros registados ({len(self.stats['erros'])}):")
            for err in self.stats["erros"]:
                log.warning(f"    - {err}")
        log.info("=" * 65)

    def _save_last_run(self, eventos: list):
        path = Path(__file__).parent / "last_run.json"
        try:
            path.write_text(
                json.dumps({"stats": self.stats, "eventos": eventos}, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception:
            pass


async def main():
    parser = argparse.ArgumentParser(description="Dashboard Escolar Pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Simula sem gravar na Google Sheet")
    parser.add_argument("--only", choices=["all", "teams", "inovar"], default="all")
    args = parser.parse_args()

    pipeline = DashboardPipeline(dry_run=args.dry_run, only=args.only)
    await pipeline.run()


if __name__ == "__main__":
    asyncio.run(main())
