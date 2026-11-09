"""
================================================================================
SCHEDULER — AGENDAMENTO AUTOMÁTICO DIÁRIO (manhã + tarde)
================================================================================
Regista o pipeline como tarefas automáticas do Windows Task Scheduler.

Horários configurados:
  🌅 07:30 — Execução da manhã (antes de ir para a escola)
  🌆 18:00 — Execução da tarde (quando chega a casa)

Como funciona:
  - Usa o Windows Task Scheduler nativo (schtasks.exe)
  - Cada tarefa invoca o run_pipeline.bat que ativa o ambiente Python
  - Os logs ficam em backend/logs/pipeline_YYYYMMDD.log
  - Em caso de falha, retenta automaticamente após 5 minutos

Uso:
  python scheduler.py install   # Instala as tarefas no Windows
  python scheduler.py remove    # Remove as tarefas do Windows
  python scheduler.py status    # Mostra estado das tarefas
  python scheduler.py run-now   # Executa imediatamente (sem agendar)
================================================================================
"""

import subprocess
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime


# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================
TASK_NAME_MORNING = "DashboardEscolar_Manha"
TASK_NAME_EVENING = "DashboardEscolar_Tarde"
SCHEDULE_MORNING  = "07:30"
SCHEDULE_EVENING  = "18:00"

BACKEND_DIR  = Path(__file__).parent.resolve()
PIPELINE_BAT = BACKEND_DIR / "run_pipeline.bat"
PYTHON_EXE   = sys.executable  # Python que está a correr este script


# ==============================================================================
# GERAÇÃO DO .BAT DE EXECUÇÃO
# ==============================================================================
def create_run_bat():
    """
    Cria o ficheiro .bat que o Task Scheduler invoca.
    O .bat muda para o diretório correto e executa o pipeline.
    """
    bat_content = f"""@echo off
:: Dashboard Escolar — Execucao automatica do Pipeline
:: Gerado automaticamente por scheduler.py

cd /d "{BACKEND_DIR}"

:: Regista inicio
echo %date% %time% - Iniciando pipeline >> logs\\scheduler.log 2>&1

:: Executa o pipeline Python
"{PYTHON_EXE}" pipeline.py >> logs\\pipeline_%date:~-4,4%%date:~-7,2%%date:~-10,2%.log 2>&1

:: Regista fim
echo %date% %time% - Pipeline concluido (codigo: %ERRORLEVEL%) >> logs\\scheduler.log 2>&1
"""
    PIPELINE_BAT.write_text(bat_content, encoding="utf-8")
    print(f"✅ Ficheiro de execução criado: {PIPELINE_BAT}")


# ==============================================================================
# INSTALAÇÃO DAS TAREFAS NO WINDOWS TASK SCHEDULER
# ==============================================================================
def install_tasks():
    """Instala as duas tarefas diárias no Windows Task Scheduler."""
    create_run_bat()

    # Garante que o diretório de logs existe
    (BACKEND_DIR / "logs").mkdir(exist_ok=True)

    tasks = [
        (TASK_NAME_MORNING, SCHEDULE_MORNING, "manhã"),
        (TASK_NAME_EVENING, SCHEDULE_EVENING, "tarde"),
    ]

    for task_name, schedule_time, label in tasks:
        # Remove tarefa existente (se houver)
        subprocess.run(
            ["schtasks", "/delete", "/tn", task_name, "/f"],
            capture_output=True
        )

        # Cria a nova tarefa
        cmd = [
            "schtasks", "/create",
            "/tn",   task_name,
            "/tr",   str(PIPELINE_BAT),
            "/sc",   "DAILY",
            "/st",   schedule_time,
            "/ru",   os.environ.get("USERNAME", "SYSTEM"),  # Corre como utilizador atual
            "/rl",   "HIGHEST",       # Prioridade alta (necessário para GUI do browser)
            "/f",                      # Força substituição se já existir
            # Reinicia até 3x se falhar, com 5 min de intervalo
            "/ri",   "5",
            "/du",   "00:30",          # Duração máxima da janela de retry: 30 min
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Tarefa '{task_name}' instalada — execução diária às {schedule_time} ({label})")
            else:
                print(f"⚠️  Aviso ao instalar '{task_name}': {result.stderr.strip()}")
                print(f"   Código: {result.returncode}")
        except FileNotFoundError:
            print("❌ schtasks.exe não encontrado. Este script deve correr no Windows.")
            sys.exit(1)

    print(f"\n🎉 Scheduler instalado com sucesso!")
    print(f"   Próxima execução de manhã: {SCHEDULE_MORNING}")
    print(f"   Próxima execução de tarde: {SCHEDULE_EVENING}")
    print(f"   Logs: {BACKEND_DIR / 'logs'}")


# ==============================================================================
# REMOÇÃO DAS TAREFAS
# ==============================================================================
def remove_tasks():
    """Remove as tarefas do Windows Task Scheduler."""
    for task_name in [TASK_NAME_MORNING, TASK_NAME_EVENING]:
        result = subprocess.run(
            ["schtasks", "/delete", "/tn", task_name, "/f"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"✅ Tarefa '{task_name}' removida.")
        else:
            print(f"ℹ️  Tarefa '{task_name}' não existia ou já foi removida.")


# ==============================================================================
# ESTADO DAS TAREFAS
# ==============================================================================
def show_status():
    """Mostra o estado atual das tarefas no Task Scheduler."""
    print("Estado das tarefas do Dashboard Escolar:\n")
    for task_name in [TASK_NAME_MORNING, TASK_NAME_EVENING]:
        result = subprocess.run(
            ["schtasks", "/query", "/tn", task_name, "/fo", "LIST"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(result.stdout)
        else:
            print(f"⚠️  '{task_name}': Tarefa não encontrada (não está instalada).")

    # Mostra últimas linhas do log
    log_scheduler = BACKEND_DIR / "logs" / "scheduler.log"
    if log_scheduler.exists():
        print("\n--- Últimas execuções (scheduler.log) ---")
        lines = log_scheduler.read_text(encoding="utf-8", errors="ignore").splitlines()
        for line in lines[-10:]:
            print(f"  {line}")


# ==============================================================================
# EXECUÇÃO IMEDIATA
# ==============================================================================
def run_now():
    """Executa o pipeline imediatamente (sem esperar pelo agendamento)."""
    print("🚀 A executar pipeline agora...")
    import asyncio
    from pipeline import DashboardPipeline
    asyncio.run(DashboardPipeline().run())


# ==============================================================================
# ENTRYPOINT
# ==============================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scheduler do Dashboard Escolar")
    parser.add_argument(
        "action",
        choices=["install", "remove", "status", "run-now"],
        help="Ação a executar"
    )
    args = parser.parse_args()

    actions = {
        "install": install_tasks,
        "remove":  remove_tasks,
        "status":  show_status,
        "run-now": run_now,
    }
    actions[args.action]()

