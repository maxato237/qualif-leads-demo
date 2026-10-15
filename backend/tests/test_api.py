"""Tests de l'API avec de faux clients : pas de clé, pas de réseau, pas de compte Google."""

import json
from datetime import date, datetime

from app import LeadServices, create_app
from app.extensions import limiter
from app.infra.delivery import DeliveryError
from app.infra.mistral_http import ProviderError
from app.infra.quota import DailyQuota
from app.services.extraction import ExtractionService
from app.services.qualification_service import QualificationService

EXTRACTION = {
    "in_scope": True,
    "project_type": "refonte",
    "need": "Refonte du site vitrine d'un cabinet d'architectes",
    "budget_min_eur": 6000,
    "budget_max_eur": 9000,
    "deadline": "d'ici février",
    "urgency": "short",
    "is_decision_maker": True,
    "clarity": "partial",
    "red_flags": [],
    "summary": "Cabinet qui veut moderniser son site.",
    "next_action": "Demander l'adresse du site actuel.",
}

LEAD = {
    "name": "Paul Girard",
    "email": "paul.girard@example.com",
    "company": "Girard Architectes",
    "message": "Notre site a dix ans, nous voulons le refaire d'ici février, budget 6 à 9 k€.",
}


class FakeLLM:
    def __init__(self, replies=None, error=False):
        self.replies = list(replies or [json.dumps(EXTRACTION)])
        self.error = error
        self.calls = []

    def complete_json(self, messages, max_tokens):
        self.calls.append(messages)
        if self.error:
            raise ProviderError("panne simulée")
        return self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]


class FakeSink:
    public_url = "https://docs.google.com/spreadsheets/d/demo"

    def __init__(self, error=False):
        self.rows = []
        self.error = error

    def append(self, row):
        if self.error:
            raise DeliveryError("quota Google dépassé")
        self.rows.append(row)


class FakeMailer:
    recipient = "agence@example.com"

    def __init__(self, error=False):
        self.sent = []
        self.error = error

    def send(self, subject, body):
        if self.error:
            raise DeliveryError("SMTP refusé")
        self.sent.append((subject, body))


def make_client(llm=None, sink=None, mailer=None, quota=10, disabled=False):
    sink = None if disabled else (sink or FakeSink())
    mailer = None if disabled else (mailer or FakeMailer())
    services = LeadServices(
        qualification=QualificationService(
            ExtractionService(llm or FakeLLM(), "Règles", 700, today=lambda: date(2026, 10, 15)),
            sink, mailer, lambda: datetime(2026, 10, 15, 9, 0),
        ),
        quota=DailyQuota(quota, today=lambda: date(2026, 10, 15)),
        sheet_url=sink.public_url if sink else None,
        email_enabled=mailer is not None,
    )
    app = create_app({"TESTING": True}, services=services)
    with app.app_context():
        limiter.reset()
    return app.test_client(), sink, mailer


def test_health_indique_les_sorties_actives():
    client, *_ = make_client()
    assert client.get("/api/health").get_json() == {
        "status": "ok",
        "sheet_url": "https://docs.google.com/spreadsheets/d/demo",
        "email_enabled": True,
    }


def test_lead_qualifie_enregistre_et_notifie():
    llm = FakeLLM()
    client, sink, mailer = make_client(llm=llm)
    response = client.post("/api/leads", json=LEAD)

    assert response.status_code == 200
    data = response.get_json()
    # 1 + budget 3 (milieu 7 500) + délai 2 + clarté 1 + décideur 1
    assert data["score"]["value"] == 8
    assert data["score"]["category"] == "chaud"
    assert data["lead"]["budget"] == "6 000 € à 9 000 €"
    assert data["lead"]["project_label"] == "Refonte"
    assert data["delivery"] == {
        "email": "sent", "sheet": "sent",
        "sheet_url": "https://docs.google.com/spreadsheets/d/demo",
    }

    assert sink.rows[0][7:9] == ["Paul G.", "p***@example.com"]
    subject, body = mailer.sent[0]
    assert subject == "[Lead 8/10, chaud] Refonte, Girard Architectes"
    assert "paul.girard@example.com" in body
    # Le message du visiteur est encadré comme une donnée, pas comme une consigne,
    # et la date du jour accompagne la demande pour évaluer l'urgence.
    user_message = llm.calls[0][1]["content"]
    assert user_message.startswith("Demande reçue le 15 octobre 2026.")
    assert "<lead>" in user_message


def test_champs_invalides_listes_un_par_un():
    client, *_ = make_client()
    response = client.post("/api/leads", json={**LEAD, "email": "pas-un-email", "message": "court"})
    assert response.status_code == 400
    error = response.get_json()["error"]
    assert error["code"] == "invalid_lead"
    assert [f["field"] for f in error["fields"]] == ["email", "message"]


def test_champ_inconnu_refuse():
    client, *_ = make_client()
    response = client.post("/api/leads", json={**LEAD, "to": "victime@example.com"})
    assert response.status_code == 400


def test_retour_a_la_ligne_retire_du_nom():
    client, _, mailer = make_client()
    client.post("/api/leads", json={**LEAD, "company": "Girard\r\nBcc: x@example.com"})
    assert "\n" not in mailer.sent[0][0]


def test_robot_piege_par_le_champ_cache():
    llm = FakeLLM()
    client, sink, _ = make_client(llm=llm)
    response = client.post("/api/leads", json={**LEAD, "website": "http://spam.example"})
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "spam_detected"
    assert llm.calls == [] and sink.rows == []


def test_json_invalide_reessaye_une_fois():
    llm = FakeLLM(replies=["pas du json", json.dumps(EXTRACTION)])
    client, *_ = make_client(llm=llm)
    assert client.post("/api/leads", json=LEAD).status_code == 200
    assert len(llm.calls) == 2


def test_json_invalide_deux_fois_donne_502():
    client, *_ = make_client(llm=FakeLLM(replies=['{"in_scope": "peut-etre"}']))
    response = client.post("/api/leads", json=LEAD)
    assert response.status_code == 502
    assert response.get_json()["error"]["code"] == "llm_unavailable"


def test_panne_du_llm_donne_502():
    client, sink, _ = make_client(llm=FakeLLM(error=True))
    response = client.post("/api/leads", json=LEAD)
    assert response.status_code == 502
    assert sink.rows == []


def test_un_canal_en_panne_ne_perd_pas_le_lead():
    client, sink, _ = make_client(mailer=FakeMailer(error=True))
    response = client.post("/api/leads", json=LEAD)
    assert response.status_code == 200
    assert response.get_json()["delivery"]["email"] == "failed"
    assert response.get_json()["delivery"]["sheet"] == "sent"
    assert len(sink.rows) == 1


def test_sorties_non_configurees():
    client, *_ = make_client(disabled=True)
    data = client.post("/api/leads", json=LEAD).get_json()
    assert data["delivery"] == {"email": "disabled", "sheet": "disabled", "sheet_url": None}


def test_quota_journalier():
    client, *_ = make_client(quota=1)
    assert client.post("/api/leads", json=LEAD).status_code == 200
    response = client.post("/api/leads", json=LEAD)
    assert response.status_code == 503
    assert response.get_json()["error"]["code"] == "demo_paused"


def test_limite_par_visiteur():
    client, *_ = make_client(quota=100)
    statuses = [client.post("/api/leads", json=LEAD).status_code for _ in range(4)]
    assert statuses == [200, 200, 200, 429]
