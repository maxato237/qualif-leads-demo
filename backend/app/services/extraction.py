"""Extraction des informations d'un lead par le LLM.

Le message du visiteur est une donnée non fiable : le LLM ne fait qu'extraire des champs,
validés ici par un schéma strict. Le score, lui, est calculé en Python (scoring.py),
pour rester explicable et impossible à manipuler depuis le message.
"""

import json
import logging
from datetime import date
from typing import Callable, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.infra.llm_client import LLMClient

logger = logging.getLogger(__name__)

ProjectType = Literal[
    "site_vitrine", "e_commerce", "application_web", "application_mobile",
    "refonte", "maintenance", "autre",
]
Urgency = Literal["immediate", "short", "flexible", "unknown"]
Clarity = Literal["precise", "partial", "vague"]


class LeadExtraction(BaseModel):
    model_config = ConfigDict(extra="ignore")

    in_scope: bool
    project_type: ProjectType
    need: str = Field(max_length=300)
    budget_min_eur: int | None = Field(default=None, ge=0, le=10_000_000)
    budget_max_eur: int | None = Field(default=None, ge=0, le=10_000_000)
    deadline: str | None = Field(default=None, max_length=120)
    urgency: Urgency
    is_decision_maker: bool | None = None
    clarity: Clarity
    red_flags: list[str] = Field(default_factory=list, max_length=4)
    summary: str = Field(max_length=600)
    next_action: str = Field(max_length=240)

    @field_validator("project_type", "urgency", "clarity", "need", "red_flags", mode="before")
    @classmethod
    def null_to_neutral(cls, value, info):
        # Sur une demande hors cible, le LLM laisse parfois ces clés à null : valeur neutre.
        if value is not None:
            return value
        return {"project_type": "autre", "urgency": "unknown", "clarity": "vague",
                "need": "", "red_flags": []}[info.field_name]

    @field_validator("red_flags")
    @classmethod
    def short_flags(cls, flags: list[str]) -> list[str]:
        return [flag.strip()[:120] for flag in flags if flag.strip()]


class ExtractionError(Exception):
    """Le LLM a répondu, mais pas avec un JSON conforme au schéma."""


MONTHS = (
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
)


class ExtractionService:
    def __init__(self, llm: LLMClient, system_prompt: str, max_tokens: int,
                 today: Callable[[], date] = date.today):
        self._llm = llm
        self._system_prompt = system_prompt
        self._max_tokens = max_tokens
        self._today = today

    def extract(self, company: str, message: str) -> LeadExtraction:
        # Sans la date du jour, "avant le 1er décembre" ne peut pas être classé en urgence.
        today = self._today()
        received = f"{today.day} {MONTHS[today.month - 1]} {today.year}"
        lead = f"Société : {company or 'non précisée'}\nMessage :\n{message}"
        messages = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": f"Demande reçue le {received}.\n<lead>\n{lead}\n</lead>"},
        ]
        # Un JSON mal formé arrive parfois : un seul nouvel essai, puis on abandonne.
        for attempt in (1, 2):
            raw = self._llm.complete_json(messages, self._max_tokens)
            try:
                return LeadExtraction.model_validate(json.loads(raw))
            except (json.JSONDecodeError, ValidationError) as exc:
                logger.warning("Extraction non conforme (essai %d) : %s", attempt, exc)
        raise ExtractionError("Le LLM n'a pas renvoyé d'extraction valide")
