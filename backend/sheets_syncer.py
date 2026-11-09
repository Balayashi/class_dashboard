"""
================================================================================
DASHBOARD ESCOLAR — MÓDULO DE SINCRONIZAÇÃO COM GOOGLE SHEETS
================================================================================
Escreve os eventos estruturados e correlacionados (INOVAR + Teams + Gemini)
diretamente na Google Sheet pública que a TV LG lê.

Suporta:
  - Inserção de novos eventos (Testes, TPCs, Questões de Aula, Avisos)
  - Atualização de eventos existentes (quando o Teams detalha o que vai sair num teste já existente)
  - Preservação do estado manual ("Concluído ✅" / "Pendente ⏳")
  - Registo de leitura obrigatória ("Por Confirmar 🔔" / "Confirmado ✅")
"""

import asyncio
import json
import os
import time
from datetime import datetime, date
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

import gspread
from google.oauth2.service_account import Credentials
import requests

# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================
GOOGLE_SHEET_ID  = os.getenv("GOOGLE_SHEET_ID", "")
SHEET_TAB_NAME   = os.getenv("GOOGLE_SHEET_TAB", "Folha1")
SA_JSON_PATH     = Path(__file__).parent / os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")
WEBHOOK_URL      = os.getenv("APPS_SCRIPT_WEBHOOK_URL", "")

# Cabeçalhos padronizados da folha
SHEET_HEADERS = ["tipo", "disciplina", "titulo", "data", "hora", "descricao", "estado", "leitura", "fonte"]

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class SheetsSyncer:
    """
    Sincronizador bidirecional tolerante a falhas com a Google Sheet.
    """

    def __init__(self):
        self._client: gspread.Client | None = None
        self._sheet: gspread.Worksheet | None = None
        self._use_gspread = False

    def connect(self) -> bool:
        if not GOOGLE_SHEET_ID:
            print("[Sheets] ❌ GOOGLE_SHEET_ID não configurado no .env")
            return False

        if not SA_JSON_PATH.exists():
            print(f"[Sheets] ℹ️  Service Account JSON não encontrado em: {SA_JSON_PATH.name}")
            print("[Sheets]    A usar webhook Apps Script como método de escrita...")
            return False

        try:
            creds = Credentials.from_service_account_file(
                str(SA_JSON_PATH), scopes=SCOPES
            )
            self._client = gspread.authorize(creds)
            spreadsheet = self._client.open_by_key(GOOGLE_SHEET_ID)
            self._sheet = spreadsheet.worksheet(SHEET_TAB_NAME)
            self._use_gspread = True
            print(f"[Sheets] ✅ Conectado à Google Sheet via Service Account (Aba: '{SHEET_TAB_NAME}')")
            return True
        except Exception as e:
            print(f"[Sheets] ❌ Erro ao conectar via gspread: {e}")
            return False

    def sync_events(self, novos_eventos: list[dict]) -> dict:
        if not novos_eventos:
            return {"inseridos": 0, "atualizados": 0, "ignorados": 0, "total": 0, "erros": 0}

        if self._use_gspread and self._sheet:
            return self._sync_via_gspread(novos_eventos)
        elif WEBHOOK_URL and WEBHOOK_URL.strip():
            return self._sync_via_webhook(novos_eventos)
        else:
            print("[Sheets] ⚠️ Nenhum método de escrita direta configurado (service_account.json ou webhook).")
            # Guarda em cache local JSON para ser usado pelo servidor local ou inspeção
            self._save_local_backup(novos_eventos)
            return {"inseridos": 0, "atualizados": 0, "ignorados": len(novos_eventos), "total": len(novos_eventos), "erros": 1}

    def _sync_via_gspread(self, novos_eventos: list[dict]) -> dict:
        sheet = self._sheet
        stats = {"inseridos": 0, "atualizados": 0, "ignorados": 0, "total": len(novos_eventos), "erros": 0}

        try:
            todos_dados = sheet.get_all_values()

            # Se a folha estiver vazia, cria os cabeçalhos
            if not todos_dados:
                sheet.append_row(SHEET_HEADERS)
                todos_dados = [SHEET_HEADERS]

            headers_row = [h.lower().strip() for h in todos_dados[0]]
            col_tipo       = self._find_col(headers_row, ["tipo", "type"])
            col_disciplina = self._find_col(headers_row, ["disciplina", "materia", "subject"])
            col_titulo     = self._find_col(headers_row, ["titulo", "título", "title"])
            col_data       = self._find_col(headers_row, ["data", "date"])
            col_hora       = self._find_col(headers_row, ["hora", "time"])
            col_desc       = self._find_col(headers_row, ["descricao", "descrição", "description"])
            col_estado     = self._find_col(headers_row, ["estado", "status"])
            col_leitura    = self._find_col(headers_row, ["leitura", "conhecimento"])
            col_fonte      = self._find_col(headers_row, ["fonte", "source"])

            # Mapa de eventos existentes na folha (chave: disc|titulo|data -> número da linha)
            linhas_existentes = {}
            for r_idx, row in enumerate(todos_dados[1:], start=2):
                disc_val = row[col_disciplina].lower().strip() if col_disciplina < len(row) else ""
                tit_val  = row[col_titulo].lower().strip() if col_titulo < len(row) else ""
                data_val = row[col_data].strip() if col_data < len(row) else ""
                chave = f"{disc_val}|{tit_val}"
                linhas_existentes[chave] = {
                    "linha": r_idx,
                    "row": row,
                    "data": data_val,
                    "desc": row[col_desc] if col_desc < len(row) else "",
                    "estado": row[col_estado] if col_estado < len(row) else "Pendente ⏳",
                }

            linhas_a_inserir = []

            for ev in novos_eventos:
                disc = ev.get("disciplina", "").lower().strip()
                tit  = ev.get("titulo", "").lower().strip()
                chave = f"{disc}|{tit}"
                nova_desc = ev.get("descricao", "").strip()
                nova_fonte = ev.get("fonte", "INOVAR + Teams")
                nova_leitura = ev.get("leitura", "Confirmado ✅")

                # Se já existe na folha
                if chave in linhas_existentes:
                    info_existente = linhas_existentes[chave]
                    desc_atual = info_existente["desc"]

                    # Atualiza a descrição se o Teams tiver trazido novos detalhes ("o que vai sair no teste")
                    if nova_desc and (nova_desc != desc_atual) and len(nova_desc) > len(desc_atual):
                        r_num = info_existente["linha"]
                        try:
                            if col_desc < len(headers_row):
                                sheet.update_cell(r_num, col_desc + 1, nova_desc)
                            if col_fonte < len(headers_row):
                                sheet.update_cell(r_num, col_fonte + 1, nova_fonte)
                            stats["atualizados"] += 1
                            print(f"[Sheets] 🔄 Atualizada matéria/detalhes na linha {r_num}: {ev.get('disciplina')} - {ev.get('titulo')}")
                        except Exception as up_err:
                            print(f"[Sheets] Erro ao atualizar célula: {up_err}")
                    else:
                        stats["ignorados"] += 1
                else:
                    # Linha nova para adicionar
                    linha = [
                        ev.get("tipo", "Aviso"),
                        ev.get("disciplina", ""),
                        ev.get("titulo", ""),
                        ev.get("data", ""),
                        ev.get("hora", ""),
                        nova_desc,
                        "Pendente ⏳",
                        nova_leitura,
                        nova_fonte
                    ]
                    linhas_a_inserir.append(linha)
                    linhas_existentes[chave] = {"linha": len(todos_dados) + len(linhas_a_inserir), "row": linha}

            if linhas_a_inserir:
                sheet.append_rows(linhas_a_inserir, value_input_option="USER_ENTERED")
                stats["inseridos"] = len(linhas_a_inserir)
                print(f"[Sheets] ✅ {len(linhas_a_inserir)} novos eventos inseridos na Google Sheet.")

        except Exception as e:
            print(f"[Sheets] ❌ Erro ao sincronizar via gspread: {e}")
            stats["erros"] += 1

        return stats

    def _sync_via_webhook(self, novos_eventos: list[dict]) -> dict:
        stats = {"inseridos": 0, "atualizados": 0, "ignorados": 0, "total": len(novos_eventos), "erros": 0}
        for ev in novos_eventos:
            try:
                res = requests.post(
                    WEBHOOK_URL,
                    json={
                        "acao": "inserir_ou_atualizar",
                        "tipo": ev.get("tipo", "Aviso"),
                        "disciplina": ev.get("disciplina", ""),
                        "titulo": ev.get("titulo", ""),
                        "data": ev.get("data", ""),
                        "hora": ev.get("hora", ""),
                        "descricao": ev.get("descricao", ""),
                        "leitura": ev.get("leitura", "Confirmado ✅"),
                        "fonte": ev.get("fonte", "INOVAR + Teams")
                    },
                    timeout=8
                )
                if res.status_code == 200:
                    stats["inseridos"] += 1
            except Exception:
                stats["erros"] += 1
        return stats

    def _save_local_backup(self, eventos: list[dict]):
        path = Path(__file__).parent / "sheet_events_backup.json"
        try:
            path.write_text(json.dumps(eventos, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    @staticmethod
    def _find_col(headers: list[str], candidates: list[str]) -> int:
        for c in candidates:
            if c in headers:
                return headers.index(c)
        return 0
