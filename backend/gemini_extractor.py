"""
================================================================================
DASHBOARD ESCOLAR — MÓDULO DE PROCESSAMENTO E CORRELAÇÃO COM GEMINI AI
================================================================================
Usa a biblioteca oficial `google-genai` (modelo 'gemini-1.5-flash').

Missão:
  1. Cruzar a informação do INOVAR (datas oficiais de testes e questões-aula)
     com os canais do TEAMS (onde os professores colocam o que vai sair nos
     testes, matérias, TPCs e pedidos de tomada de conhecimento).
  2. Enriquecer os testes do INOVAR com a matéria detalhada pelo professor no Teams.
  3. Extrair TPCs, Trabalhos e Materiais que só existem no Teams.
  4. Detetar avisos/publicações que requerem que o aluno Dinis confirme que
     "tomou conhecimento", mantendo o alerta ativo até confirmação.

Dependências: google-genai, python-dotenv
================================================================================
"""

import asyncio
import json
import re
import os
from datetime import datetime, date
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from google import genai
from google.genai import types

# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = "gemini-1.5-flash"

TODAY_STR = date.today().strftime("%Y-%m-%d")
YEAR      = date.today().year

STUDENT_NAME = os.getenv("STUDENT_NAME", "Dinis Henriques de Freixo Pereira Mouro")

# Professores conhecidos da Turma 5º G
TEACHERS_MAP = {
    "EM":   "Paulo Cairrão",
    "MAT":  "Inês Isabel Vaz Mendonça",
    "HGP":  "Abílio Mocho",
    "CN":   "Inês Isabel Vaz Mendonça",
    "PORT": "Abílio Mocho",
    "ING":  "Carina Ribeiro"
}

# ==============================================================================
# PROMPT ESPECIALIZADO DE CORRELAÇÃO INOVAR + TEAMS
# ==============================================================================
SYSTEM_INSTRUCTION = f"""
És o assistente de inteligência artificial pedagógico do aluno {STUDENT_NAME} (Turma 5º G, EB Pedro Jacques de Magalhães).

Recebes duas fontes de dados escolares:
1. DADOS OFICIAIS DO INOVAR: Lista de testes, questões de aula e trabalhos com datas e horas marcadas na pauta oficial.
2. MENSAGENS E POSTS DOS PROFESSORES NO TEAMS: Mensagens informais, tabelas e avisos colocados pelos professores nos canais (MAT, Português, HGP, CN, Inglês, EM, DTA).

OS PROFESSORES DA TURMA:
- Paulo Cairrão: Educação Musical (EM)
- Inês Isabel Vaz Mendonça: Matemática (MAT) e Ciências Naturais (CN)
- Abílio Mocho: História e Geografia de Portugal (HGP) e Português
- Carina Ribeiro: Inglês

O TEU OBJETIVO:
1. CORRELAÇÃO INTELIGENTE (Cruzar INOVAR + TEAMS):
   - Se o INOVAR tem um teste marcado (ex: Teste de HGP a 02-11-2026) e o professor publicou no Teams o que vai sair no teste (conteúdos, páginas do manual, temas, orientações de estudo), DEVES FUNDIR a informação!
   - A data e o tipo vêm do INOVAR, mas a "descricao" DEVE conter o que vai sair no teste extraído do Teams.
   - O campo "fonte" deve ser "INOVAR + Teams".

2. NOVOS TPCs E AVISOS DO TEAMS:
   - Se o professor colocou no Teams um TPC, trabalho, material de estudo ou ficha que NÃO está no INOVAR, cria um novo evento com fonte "Teams".

3. TOMADA DE CONHECIMENTO / LEITURA OBRIGATÓRIA:
   - Se o professor colocou um aviso importante ou pediu explicitamente confirmação ("quem tomou conhecimento", "confirmem leitura", etc.), o campo "leitura" deve ser "Por Confirmar 🔔".
   - Caso contrário, ou se for apenas calendário normal, usa "Confirmado ✅".

FORMATO DO JSON DE SAÍDA:
Devolve SEMPRE e APENAS um array JSON de objetos com esta estrutura exata:
[
  {{
    "tipo": "Teste" | "Questão de Aula" | "TPC" | "Trabalho" | "Aviso" | "Material",
    "disciplina": "Matemática" | "Português" | "HGP" | "Ciências Naturais" | "Inglês" | "Educação Musical" | "Geral",
    "titulo": "Título claro e conciso (máx. 70 carateres)",
    "data": "YYYY-MM-DD" (se não souberes a data exata, deixa vazio ""),
    "hora": "HH:MM" (ou vazio ""),
    "descricao": "Resumo do que vai sair no teste, exercícios pedidos ou recado do professor (máx. 250 carateres)",
    "fonte": "INOVAR" | "Teams" | "INOVAR + Teams",
    "leitura": "Por Confirmar 🔔" | "Confirmado ✅",
    "professor": "Nome do professor responsável",
    "post_id": "identificador ou hash curto"
  }}
]

Data de hoje para referência: {TODAY_STR} (Ano letivo {YEAR}/{YEAR+1}).
""".strip()


class GeminiExtractor:
    """
    Extrator e Correlacionador com Gemini 1.5 Flash via biblioteca oficial google-genai.
    """

    def __init__(self):
        if not GEMINI_API_KEY or GEMINI_API_KEY.strip() == "":
            raise ValueError(
                "❌ GEMINI_API_KEY não configurada no ficheiro .env!\n"
                "   Obtenha gratuitamente em: https://aistudio.google.com/app/apikey"
            )

        # Inicializa o cliente oficial google-genai
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        print(f"[Gemini] ✅ Cliente google-genai inicializado com modelo: {GEMINI_MODEL}")

    # ------------------------------------------------------------------
    # MÉTODO PRINCIPAL: CORRELAÇÃO DE INOVAR + TEAMS
    # ------------------------------------------------------------------
    async def correlate_and_extract(
        self, inovar_eventos: list[dict], teams_messages: list[dict]
    ) -> list[dict]:
        """
        Cruza os eventos do INOVAR com as mensagens do Teams usando o Gemini 1.5 Flash.
        """
        # Se não há mensagens nem eventos, retorna vazio
        if not inovar_eventos and not teams_messages:
            return []

        # Se não houver mensagens do Teams, formata apenas os eventos do INOVAR
        if not teams_messages and inovar_eventos:
            return self._format_inovar_only(inovar_eventos)

        # Monta o prompt para o modelo
        prompt_content = self._build_correlation_prompt(inovar_eventos, teams_messages)

        try:
            print(f"[Gemini] 🤖 A processar com {GEMINI_MODEL}...")

            # Executa de forma assíncrona usando o executor para não bloquear o loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt_content,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        temperature=0.1,  # Determinístico
                        response_mime_type="application/json",
                    ),
                ),
            )

            response_text = response.text or ""
            return self._parse_json_response(response_text, inovar_eventos)

        except Exception as e:
            print(f"[Gemini] ❌ Erro ao chamar a API Gemini: {e}")
            # Em caso de falha na IA, usa fallback inteligente dos dados brutos do INOVAR
            return self._format_inovar_only(inovar_eventos)

    # ------------------------------------------------------------------
    # MÉTODO SECUNDÁRIO: APENAS MENSAGENS DO TEAMS
    # ------------------------------------------------------------------
    async def extract_events_from_messages(self, messages: list[dict]) -> list[dict]:
        """Método de compatibilidade para extrair apenas de mensagens de canais."""
        return await self.correlate_and_extract(inovar_eventos=[], teams_messages=messages)

    # ------------------------------------------------------------------
    # CONSTRUÇÃO DO PROMPT
    # ------------------------------------------------------------------
    def _build_correlation_prompt(
        self, inovar_eventos: list[dict], teams_messages: list[dict]
    ) -> str:
        prompt_parts = []

        prompt_parts.append("=== 1. EVENTOS OFICIAIS DO INOVAR (Calendário de Testes e Questões de Aula) ===")
        if inovar_eventos:
            for i, ev in enumerate(inovar_eventos, 1):
                prompt_parts.append(
                    f"[{i}] Data: {ev.get('data','')} {ev.get('hora','')} | "
                    f"Disciplina: {ev.get('disciplina','')} | "
                    f"Evento: {ev.get('titulo','')} | "
                    f"Professor: {ev.get('professor','')}"
                )
        else:
            prompt_parts.append("(Nenhum evento do INOVAR disponível)")

        prompt_parts.append("\n=== 2. MENSAGENS E POSTS DOS PROFESSORES NOS CANAIS DO TEAMS ===")
        if teams_messages:
            for i, msg in enumerate(teams_messages, 1):
                post_id = msg.get("post_id", f"post_{i}")
                prompt_parts.append(
                    f"--- Mensagem Teams #{i} [ID: {post_id}] ---\n"
                    f"Canal/Disciplina: {msg.get('disciplina','')} ({msg.get('canal','')})\n"
                    f"Autor: {msg.get('autor','Professor')}\n"
                    f"Data da publicação: {msg.get('data_raw','')}\n"
                    f"Conteúdo:\n{msg.get('texto','')}\n"
                )
        else:
            prompt_parts.append("(Nenhuma mensagem recente do Teams)")

        prompt_parts.append(
            "\nAnalisa as informações acima, cruza os testes do INOVAR com o que vai sair nos testes postado no Teams, "
            "adiciona os novos TPCs e gera o array JSON completo conforme as instruções."
        )

        return "\n".join(prompt_parts)

    # ------------------------------------------------------------------
    # PARSING E VALIDAÇÃO DA RESPOSTA JSON
    # ------------------------------------------------------------------
    def _parse_json_response(self, text: str, inovar_backup: list[dict]) -> list[dict]:
        # Limpa possíveis blocos markdown ```json ... ```
        cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip())
        cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            data = json.loads(cleaned)
            if isinstance(data, dict):
                # Se o modelo devolveu {"eventos": [...]}
                for key in ["eventos", "items", "results"]:
                    if key in data and isinstance(data[key], list):
                        data = data[key]
                        break
                else:
                    data = [data]

            if not isinstance(data, list):
                return self._format_inovar_only(inovar_backup)

            # Normaliza cada evento
            eventos_finais = []
            for item in data:
                ev = self._normalize_event(item)
                if ev:
                    eventos_finais.append(ev)

            return eventos_finais

        except Exception as e:
            print(f"[Gemini] ⚠️ Falha ao parsear JSON retornado: {e}")
            return self._format_inovar_only(inovar_backup)

    def _normalize_event(self, item: dict) -> dict | None:
        if not isinstance(item, dict):
            return None

        titulo = str(item.get("titulo", "")).strip()
        disciplina = str(item.get("disciplina", "Geral")).strip()
        if not titulo:
            return None

        # Valida e normaliza tipo
        tipo = str(item.get("tipo", "Aviso")).strip()
        tipo_lower = tipo.lower()
        if "teste" in tipo_lower:
            tipo = "Teste"
        elif "quest" in tipo_lower:
            tipo = "Questão de Aula"
        elif "tpc" in tipo_lower:
            tipo = "TPC"
        elif "trab" in tipo_lower:
            tipo = "Trabalho"
        elif "mat" in tipo_lower:
            tipo = "Material"
        else:
            tipo = "Aviso"

        # Data no formato YYYY-MM-DD
        data = str(item.get("data", "")).strip()
        if data and not re.match(r"^\d{4}-\d{2}-\d{2}$", data):
            # Tenta converter se vier DD-MM-YYYY
            match_d = re.match(r"^(\d{2})[-/](\d{2})[-/](\d{4})$", data)
            if match_d:
                d, m, y = match_d.groups()
                data = f"{y}-{m}-{d}"
            else:
                data = ""

        # Hora
        hora = str(item.get("hora", "")).strip()
        if hora and not re.match(r"^\d{2}:\d{2}$", hora):
            hora = ""

        descricao = str(item.get("descricao", "")).strip()[:300]
        fonte = str(item.get("fonte", "INOVAR + Teams")).strip()
        leitura = str(item.get("leitura", "Confirmado ✅")).strip()
        professor = str(item.get("professor", "")).strip()
        post_id = str(item.get("post_id", "")).strip()

        return {
            "tipo":       tipo,
            "disciplina": disciplina,
            "titulo":     titulo,
            "data":       data,
            "hora":       hora,
            "descricao":  descricao,
            "fonte":      fonte,
            "leitura":    leitura,
            "professor":  professor,
            "post_id":    post_id
        }

    def _format_inovar_only(self, inovar_eventos: list[dict]) -> list[dict]:
        """Formata eventos brutos do INOVAR caso a IA não esteja disponível."""
        eventos = []
        for ev in inovar_eventos:
            eventos.append({
                "tipo":       ev.get("tipo", "Teste"),
                "disciplina": ev.get("disciplina", "Geral"),
                "titulo":     ev.get("titulo", "Avaliação"),
                "data":       ev.get("data", ""),
                "hora":       ev.get("hora", ""),
                "descricao":  ev.get("descricao", ""),
                "fonte":      "INOVAR",
                "leitura":    "Confirmado ✅",
                "professor":  ev.get("professor", ""),
                "post_id":    ""
            })
        return eventos
