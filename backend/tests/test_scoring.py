"""Grille de score et mise en forme : du Python pur, sans LLM."""

from datetime import datetime

import pytest

from app.services import formatting
from app.services.extraction import LeadExtraction
from app.services.scoring import score_lead


def make_lead(**overrides) -> LeadExtraction:
    fields = {
        "in_scope": True,
        "project_type": "e_commerce",
        "need": "Boutique en ligne de vins avec paiement",
        "budget_min_eur": 12000,
        "budget_max_eur": 18000,
        "deadline": "avant le 1er décembre",
        "urgency": "short",
        "is_decision_maker": True,
        "clarity": "precise",
        "red_flags": [],
        "summary": "Caviste qui veut vendre en ligne avant Noël.",
        "next_action": "Proposer un appel cette semaine.",
    }
    return LeadExtraction.model_validate({**fields, **overrides})


def test_lead_complet_et_finance_est_chaud():
    score = score_lead(make_lead())
    assert score.value == 10
    assert score.category == "chaud"
    assert [c.key for c in score.criteria] == ["budget", "urgency", "clarity", "decision_maker"]


def test_lead_flou_sans_budget_est_froid():
    score = score_lead(make_lead(
        budget_min_eur=None, budget_max_eur=None, urgency="unknown",
        is_decision_maker=None, clarity="vague",
    ))
    # Base 1 et budget non précisé 1 : le silence sur le budget n'est pas pénalisé.
    assert score.value == 2
    assert score.category == "froid"


def test_budget_irrealiste_ne_rapporte_rien():
    score = score_lead(make_lead(budget_min_eur=300, budget_max_eur=300))
    budget = next(c for c in score.criteria if c.key == "budget")
    assert budget.points == 0
    assert "300 €" in budget.reason


@pytest.mark.parametrize("low, high, points", [
    (None, 4000, 2),      # borne haute seule
    (6000, None, 3),      # borne basse seule
    (4000, 8000, 3),      # fourchette : milieu 6 000
    (20000, 20000, 4),
])
def test_paliers_de_budget(low, high, points):
    score = score_lead(make_lead(budget_min_eur=low, budget_max_eur=high))
    assert next(c for c in score.criteria if c.key == "budget").points == points


def test_seuils_tiede():
    # 1 + budget 2 + délai 1 + clarté 1 + décideur 0 = 5
    score = score_lead(make_lead(
        budget_min_eur=3000, budget_max_eur=3000, urgency="flexible",
        clarity="partial", is_decision_maker=False,
    ))
    assert (score.value, score.category) == (5, "tiede")


def test_hors_cible_vaut_1_quel_que_soit_le_reste():
    score = score_lead(make_lead(in_scope=False))
    assert (score.value, score.category) == (1, "hors_cible")


def test_cles_nulles_d_un_hors_cible_remplacees_par_des_valeurs_neutres():
    lead = make_lead(in_scope=False, project_type=None, need=None, urgency=None, red_flags=None)
    assert (lead.project_type, lead.need, lead.urgency, lead.red_flags) == ("autre", "", "unknown", [])


def test_ligne_du_sheet_masque_les_coordonnees():
    lead = make_lead()
    row = formatting.sheet_row(
        datetime(2026, 10, 15, 14, 30), "Claire Martin", "claire.martin@example.com",
        "Cave Martin", lead, score_lead(lead),
    )
    assert row[:3] == ["2026-10-15 14:30", "10/10", "Chaud"]
    assert row[5] == "12 000 € à 18 000 €"
    assert row[7:10] == ["Claire M.", "c***@example.com", "Cave Martin"]
    assert len(row) == len(formatting.SHEET_HEADER)


@pytest.mark.parametrize("low, high, text", [
    (None, None, "Non précisé"),
    (None, 5000, "5 000 € maximum"),
    (10000, None, "10 000 € minimum"),
    (15000, 15000, "15 000 €"),
])
def test_budget_en_toutes_lettres(low, high, text):
    assert formatting.budget_text(make_lead(budget_min_eur=low, budget_max_eur=high)) == text


def test_objet_de_l_email():
    lead = make_lead()
    subject = formatting.email_subject("Claire Martin", "Cave Martin", lead, score_lead(lead))
    assert subject == "[Lead 10/10, chaud] Boutique en ligne, Cave Martin"
