import logging
import time
from dataclasses import asdict

from flask import Blueprint, current_app, jsonify, request
from pydantic import ValidationError

from app.api.errors import ApiError
from app.api.schemas import LeadRequest
from app.extensions import limiter
from app.infra.mistral_http import ProviderError
from app.services.extraction import ExtractionError
from app.services.formatting import PROJECT_LABELS, budget_text

logger = logging.getLogger(__name__)

api = Blueprint("api", __name__, url_prefix="/api")

FIELD_MESSAGES = {
    "name": "Indiquez un nom (2 à 80 caractères).",
    "email": "Indiquez une adresse email valide.",
    "company": "Le nom de société fait 80 caractères au plus.",
    "message": "Décrivez votre projet en 20 à 2 000 caractères.",
}


def _services():
    return current_app.extensions["leads"]


@api.get("/health")
def health():
    services = _services()
    return jsonify({
        "status": "ok",
        "sheet_url": services.sheet_url,
        "email_enabled": services.email_enabled,
    })


@api.post("/leads")
@limiter.limit(lambda: current_app.config["RATE_LIMIT_LEADS"])
def create_lead():
    try:
        payload = LeadRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        fields = sorted({str(err["loc"][0]) for err in exc.errors() if err["loc"]})
        raise ApiError(
            400, "invalid_lead", "Certains champs sont à corriger.",
            [{"field": f, "message": FIELD_MESSAGES.get(f, "Champ invalide.")} for f in fields],
        )
    if payload.website:
        raise ApiError(400, "spam_detected", "Demande refusée.")

    services = _services()
    if not services.quota.try_consume():
        raise ApiError(
            503, "demo_paused",
            "La démo a atteint son nombre de demandes pour aujourd'hui. Revenez demain !",
        )

    started = time.perf_counter()
    try:
        result = services.qualification.qualify(payload)
    except (ProviderError, ExtractionError):
        logger.exception("Qualification impossible")
        raise ApiError(
            502, "llm_unavailable",
            "L'analyse est momentanément indisponible. Réessayez dans un instant.",
        )
    latency_ms = round((time.perf_counter() - started) * 1000)

    # Pas de nom ni d'email dans les journaux : seulement de quoi suivre la qualité.
    logger.info(
        "lead score=%d category=%s type=%s email=%s sheet=%s latency_ms=%d",
        result.score.value, result.score.category, result.lead.project_type,
        result.email, result.sheet, latency_ms,
    )
    lead = result.lead
    return jsonify({
        "score": {
            "value": result.score.value,
            "category": result.score.category,
            "criteria": [asdict(c) for c in result.score.criteria],
        },
        "lead": {
            **lead.model_dump(),
            "project_label": PROJECT_LABELS[lead.project_type],
            "budget": budget_text(lead),
        },
        "delivery": {
            "email": result.email,
            "sheet": result.sheet,
            "sheet_url": services.sheet_url,
        },
        "email_preview": asdict(result.email_preview),
        "latency_ms": latency_ms,
    })
