import logging
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Flask
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from app.api.errors import register_error_handlers
from app.api.routes import api
from app.config import Config
from app.extensions import limiter
from app.infra.llm_client import MistralLLMClient
from app.infra.mailer import BrevoApiMailer, SmtpMailer
from app.infra.quota import DailyQuota
from app.infra.sheets_client import GoogleSheetSink, load_service_account
from app.services.extraction import ExtractionService
from app.services.qualification_service import QualificationService

logger = logging.getLogger(__name__)


@dataclass
class LeadServices:
    qualification: QualificationService
    quota: DailyQuota
    sheet_url: str | None
    email_enabled: bool


def create_app(overrides: dict | None = None, services: LeadServices | None = None) -> Flask:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    app = Flask(__name__)
    app.config.from_object(Config)
    app.config.update(overrides or {})

    # Derrière nginx et le proxy de l'hébergeur : lire la vraie IP du visiteur pour le rate limit.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
    CORS(app, resources={r"/api/*": {"origins": app.config["FRONTEND_ORIGIN"]}})
    limiter.init_app(app)

    app.extensions["leads"] = services or build_services(app.config)
    app.register_blueprint(api)
    register_error_handlers(app)
    return app


def build_services(config) -> LeadServices:
    timezone = ZoneInfo(config["TIMEZONE"])
    llm = MistralLLMClient(config["MISTRAL_API_KEY"], config["LLM_MODEL"])
    extractor = ExtractionService(
        llm,
        config["EXTRACTION_PROMPT_FILE"].read_text(encoding="utf-8"),
        config["MAX_EXTRACTION_TOKENS"],
        today=lambda: datetime.now(timezone).date(),
    )
    sheet = _build_sheet(config)
    mailer = _build_mailer(config)
    return LeadServices(
        qualification=QualificationService(extractor, sheet, mailer, lambda: datetime.now(timezone)),
        quota=DailyQuota(config["DAILY_QUOTA"]),
        sheet_url=sheet.public_url if sheet else None,
        email_enabled=mailer is not None,
    )


def _build_sheet(config) -> GoogleSheetSink | None:
    if not (config["GOOGLE_SERVICE_ACCOUNT"] and config["SHEET_ID"]):
        logger.warning("Google Sheet non configuré : les leads ne seront pas enregistrés")
        return None
    try:
        info = load_service_account(config["GOOGLE_SERVICE_ACCOUNT"])
        return GoogleSheetSink(info, config["SHEET_ID"], config["SHEET_RANGE"])
    except (ValueError, KeyError) as exc:
        # Clé mal collée : la démo démarre quand même, le Sheet est seulement désactivé.
        logger.error("Clé du compte de service Google invalide : %s", exc)
        return None


def _build_mailer(config) -> BrevoApiMailer | SmtpMailer | None:
    if not (config["MAIL_FROM"] and config["MAIL_TO"]):
        logger.warning("Email non configuré (MAIL_FROM ou MAIL_TO manquant) : aucune notification")
        return None
    # L'API HTTP passe partout ; le SMTP reste possible là où le port 587 est ouvert.
    if config["BREVO_API_KEY"]:
        try:
            return BrevoApiMailer(config["BREVO_API_KEY"], config["MAIL_FROM"], config["MAIL_TO"])
        except ValueError as exc:
            logger.error("Email désactivé : %s", exc)
            return None
    required = ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD")
    missing = [key for key in required if not config[key]]
    if missing:
        logger.warning("Email non configuré (BREVO_API_KEY, ou %s manquant) : aucune notification",
                       ", ".join(missing))
        return None
    return SmtpMailer(
        config["SMTP_HOST"], config["SMTP_PORT"], config["SMTP_USER"], config["SMTP_PASSWORD"],
        config["MAIL_FROM"], config["MAIL_TO"],
    )
