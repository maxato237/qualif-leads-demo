"""Mise en forme d'un lead qualifié : ligne du Google Sheet et email à l'agence."""

from datetime import datetime

from app.services.extraction import LeadExtraction
from app.services.scoring import Score

PROJECT_LABELS = {
    "site_vitrine": "Site vitrine",
    "e_commerce": "Boutique en ligne",
    "application_web": "Application web",
    "application_mobile": "Application mobile",
    "refonte": "Refonte",
    "maintenance": "Maintenance",
    "autre": "Autre",
}

CATEGORY_LABELS = {
    "chaud": "Chaud",
    "tiede": "Tiède",
    "froid": "Froid",
    "hors_cible": "Hors cible",
}

SHEET_HEADER = [
    "Date", "Score", "Catégorie", "Type de projet", "Besoin", "Budget", "Délai",
    "Contact", "Email", "Société", "Résumé", "Prochaine action",
]


def euros(amount: int) -> str:
    return f"{amount:,} €".replace(",", " ")


def budget_text(lead: LeadExtraction) -> str:
    low, high = lead.budget_min_eur, lead.budget_max_eur
    if low is not None and high is not None:
        return euros(low) if low == high else f"{euros(low)} à {euros(high)}"
    if high is not None:
        return f"{euros(high)} maximum"
    if low is not None:
        return f"{euros(low)} minimum"
    return "Non précisé"


def mask_email(email: str) -> str:
    """Le Sheet est public : on n'y écrit jamais une adresse en clair."""
    local, _, domain = email.partition("@")
    return f"{local[:1]}***@{domain}"


def short_name(name: str) -> str:
    """Prénom et initiale du nom, pour la même raison."""
    parts = name.split()
    if len(parts) < 2:
        return parts[0] if parts else ""
    return f"{parts[0]} {parts[-1][0]}."


def sheet_row(received_at: datetime, name: str, email: str, company: str,
              lead: LeadExtraction, score: Score) -> list[str]:
    return [
        received_at.strftime("%Y-%m-%d %H:%M"),
        f"{score.value}/10",
        CATEGORY_LABELS[score.category],
        PROJECT_LABELS[lead.project_type],
        lead.need,
        budget_text(lead),
        lead.deadline or "Non précisé",
        short_name(name),
        mask_email(email),
        company,
        lead.summary,
        lead.next_action,
    ]


def email_subject(name: str, company: str, lead: LeadExtraction, score: Score) -> str:
    who = company or name
    return (
        f"[Lead {score.value}/10, {CATEGORY_LABELS[score.category].lower()}] "
        f"{PROJECT_LABELS[lead.project_type]}, {who}"
    )


def email_body(name: str, email: str, company: str, message: str,
               lead: LeadExtraction, score: Score) -> str:
    lines = [
        f"Nouveau lead : {score.value}/10 ({CATEGORY_LABELS[score.category]})",
        "",
        lead.summary,
        "",
        f"Prochaine action : {lead.next_action}",
        "",
        "Qualification",
        f"  Type de projet : {PROJECT_LABELS[lead.project_type]}",
        f"  Besoin : {lead.need}",
        f"  Budget : {budget_text(lead)}",
        f"  Délai : {lead.deadline or 'Non précisé'}",
    ]
    lines += [f"  {c.label} : {c.points}/{c.max_points}, {c.reason}" for c in score.criteria]
    if lead.red_flags:
        lines += ["", "Points d'attention"] + [f"  - {flag}" for flag in lead.red_flags]
    lines += [
        "",
        "Contact",
        f"  {name}{f', {company}' if company else ''}",
        f"  {email}",
        "",
        "Message reçu",
        message,
        "",
        "Email envoyé par la démo de qualification de leads d'Atelier Ardoise (agence fictive).",
    ]
    return "\n".join(lines)
