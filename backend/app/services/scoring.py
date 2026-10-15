"""Score d'un lead de 1 à 10, calculé à partir des champs extraits.

Grille fixe et publique (affichée dans la démo) : base 1, budget 0 à 4, délai 0 à 2,
clarté 0 à 2, décideur 0 à 1. Un lead hors cible vaut 1, quoi qu'il contienne.
"""

from dataclasses import dataclass
from typing import Literal

from app.services.extraction import LeadExtraction

Category = Literal["chaud", "tiede", "froid", "hors_cible"]

BASE_POINTS = 1
HOT_THRESHOLD = 8
WARM_THRESHOLD = 5


@dataclass(frozen=True)
class Criterion:
    key: str
    label: str
    points: int
    max_points: int
    reason: str


@dataclass(frozen=True)
class Score:
    value: int
    category: Category
    criteria: list[Criterion]


def budget_reference(lead: LeadExtraction) -> int | None:
    """Une fourchette compte pour son milieu ; une borne seule compte pour elle-même."""
    low, high = lead.budget_min_eur, lead.budget_max_eur
    if low is not None and high is not None:
        return (low + high) // 2
    return high if high is not None else low


def _budget(lead: LeadExtraction) -> Criterion:
    amount = budget_reference(lead)
    if amount is None:
        # Ne pas citer de budget est courant : signal neutre, pas négatif.
        return Criterion("budget", "Budget", 1, 4, "Budget non précisé")
    if amount < 1_500:
        points, reason = 0, "Budget très bas pour un projet sur mesure"
    elif amount < 5_000:
        points, reason = 2, "Petit budget"
    elif amount < 15_000:
        points, reason = 3, "Budget confortable"
    else:
        points, reason = 4, "Budget élevé"
    return Criterion("budget", "Budget", points, 4, f"{reason} ({amount:,} €)".replace(",", " "))


_URGENCY = {
    "immediate": (2, "Besoin immédiat"),
    "short": (2, "Échéance proche, dans les 3 mois"),
    "flexible": (1, "Pas d'échéance ferme"),
    "unknown": (0, "Délai non précisé"),
}

_CLARITY = {
    "precise": (2, "Besoin précis"),
    "partial": (1, "Besoin en partie défini"),
    "vague": (0, "Besoin flou"),
}


def score_lead(lead: LeadExtraction) -> Score:
    if not lead.in_scope:
        criteria = [Criterion("scope", "Pertinence", 0, 0, "Demande hors du métier de l'agence")]
        return Score(BASE_POINTS, "hors_cible", criteria)

    urgency_points, urgency_reason = _URGENCY[lead.urgency]
    clarity_points, clarity_reason = _CLARITY[lead.clarity]
    decider = lead.is_decision_maker is True
    criteria = [
        _budget(lead),
        Criterion("urgency", "Délai", urgency_points, 2, urgency_reason),
        Criterion("clarity", "Clarté du besoin", clarity_points, 2, clarity_reason),
        Criterion(
            "decision_maker", "Interlocuteur", int(decider), 1,
            "Décideur identifié" if decider else "Décideur non identifié",
        ),
    ]
    value = BASE_POINTS + sum(c.points for c in criteria)
    if value >= HOT_THRESHOLD:
        category: Category = "chaud"
    elif value >= WARM_THRESHOLD:
        category = "tiede"
    else:
        category = "froid"
    return Score(value, category, criteria)
