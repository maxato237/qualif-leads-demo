import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Literal

from app.api.schemas import LeadRequest
from app.infra.mailer import Mailer
from app.infra.sheets_client import LeadSink
from app.services import formatting
from app.services.extraction import ExtractionService, LeadExtraction
from app.services.scoring import Score, score_lead

logger = logging.getLogger(__name__)

DeliveryStatus = Literal["sent", "failed", "disabled"]


@dataclass(frozen=True)
class Qualification:
    lead: LeadExtraction
    score: Score
    email: DeliveryStatus
    sheet: DeliveryStatus


class QualificationService:
    def __init__(self, extractor: ExtractionService, sheet: LeadSink | None,
                 mailer: Mailer | None, now: Callable[[], datetime]):
        self._extractor = extractor
        self._sheet = sheet
        self._mailer = mailer
        self._now = now
        # Le Sheet et l'email partent en parallèle : le visiteur attend le plus lent, pas la somme.
        self._pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="delivery")

    def qualify(self, request: LeadRequest) -> Qualification:
        lead = self._extractor.extract(request.company, request.message)
        score = score_lead(lead)
        email = str(request.email)

        sheet_job = None
        if self._sheet is not None:
            row = formatting.sheet_row(self._now(), request.name, email, request.company, lead, score)
            sheet_job = self._pool.submit(self._sheet.append, row)
        mail_job = None
        if self._mailer is not None:
            mail_job = self._pool.submit(
                self._mailer.send,
                formatting.email_subject(request.name, request.company, lead, score),
                formatting.email_body(request.name, email, request.company, request.message, lead, score),
            )
        return Qualification(lead, score, email=_status(mail_job, "email"), sheet=_status(sheet_job, "sheet"))


def _status(job, channel: str) -> DeliveryStatus:
    if job is None:
        return "disabled"
    try:
        job.result()
        return "sent"
    except Exception:
        # DeliveryError ou erreur réseau imprévue : un canal en panne ne fait pas perdre le lead.
        logger.exception("Envoi %s en échec", channel)
        return "failed"
