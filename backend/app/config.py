import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")


class Config:
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "ministral-14b-latest")

    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:4200")
    RATE_LIMIT_LEADS = os.getenv("RATE_LIMIT_LEADS", "10 per hour;3 per minute")
    # Plafond global : protège le budget Mistral et le quota d'envoi SMTP (Brevo gratuit : 300/jour).
    DAILY_QUOTA = int(os.getenv("DAILY_QUOTA", "100"))

    # Google Sheet de démo, en lecture seule pour le public.
    # Clé du compte de service : JSON brut ou encodé en base64 (plus simple dans une variable d'hébergeur).
    GOOGLE_SERVICE_ACCOUNT = os.getenv("GOOGLE_SERVICE_ACCOUNT", "")
    SHEET_ID = os.getenv("SHEET_ID", "")
    SHEET_RANGE = os.getenv("SHEET_RANGE", "Leads!A:L")

    # Email envoyé à l'agence fictive. Le destinataire est fixe : le visiteur ne le choisit jamais.
    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    MAIL_FROM = os.getenv("MAIL_FROM", "")
    MAIL_TO = os.getenv("MAIL_TO", "")

    MAX_EXTRACTION_TOKENS = 700
    TIMEZONE = "Europe/Paris"
    EXTRACTION_PROMPT_FILE = BACKEND_DIR / "app" / "prompts" / "extraction_prompt.txt"
