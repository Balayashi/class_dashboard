from dotenv import load_dotenv
from pathlib import Path
import os
import subprocess

load_dotenv(Path(__file__).parent / ".env")

teams_email  = os.getenv("TEAMS_EMAIL", "")
teams_pwd    = os.getenv("TEAMS_PASSWORD", "")
inovar_email = os.getenv("INOVAR_EMAIL", "")
inovar_pwd   = os.getenv("INOVAR_PASSWORD", "")
sheet        = os.getenv("GOOGLE_SHEET_ID", "")
gemini       = os.getenv("GEMINI_API_KEY", "")

print("=== Verificação do Ecossistema Dashboard Escolar ===")
print(f"Microsoft Teams (Aluno): {teams_email if teams_email else 'NAO CONFIGURADO'}")
print(f"  Senha Teams:           {'Configurada (' + str(len(teams_pwd)) + ' caracteres)' if teams_pwd else 'NAO'}")
print(f"INOVAR (Encarregado):    {inovar_email if inovar_email else 'NAO CONFIGURADO'}")
print(f"  Senha INOVAR:          {'Configurada (' + str(len(inovar_pwd)) + ' caracteres)' if inovar_pwd else 'NAO'}")
print(f"Aluno selecionado:       {os.getenv('STUDENT_NAME', 'Dinis Mouro')}")
print(f"Google Sheet ID:         {sheet[:20]}...")
print(f"Gemini API Key:          {'Configurada' if gemini and gemini != 'a_sua_chave_gemini_aqui' else 'NAO CONFIGURADA (insira no .env)'}")
print()

# Teste de importações
try:
    from google import genai
    import playwright
    import gspread
    print("Bibliotecas Python:      OK (google-genai, playwright, gspread, dotenv)")
except Exception as e:
    print(f"Bibliotecas Python:      ERRO: {e}")

print()
print("Tarefas Windows Task Scheduler (Execução Automática Diária):")
for task in ["DashboardEscolar_Manha", "DashboardEscolar_Tarde"]:
    r = subprocess.run(["schtasks", "/query", "/tn", task, "/fo", "LIST"], capture_output=True, text=True)
    next_run = "Desconhecido"
    status = "Desconhecido"
    for line in r.stdout.splitlines():
        if "Next Run Time:" in line:
            next_run = line.split(":", 1)[1].strip()
        if "Status:" in line:
            status = line.split(":", 1)[1].strip()
    print(f"  - {task}: {status} | Próxima: {next_run}")
