"""Envoi par l'API HTTP de Brevo, avec requests.post remplacé : pas de réseau."""

import pytest
import requests

from app import _build_mailer, _channel
from app.config import Config
from app.infra import mailer as mailer_module
from app.infra.delivery import DeliveryError
from app.infra.mailer import BrevoApiMailer, SmtpMailer

SENDER = "Atelier Ardoise (démo) <demo@example.com>"


class FakeResponse:
    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.text = text


class Recorder:
    def __init__(self):
        self.calls = []
        self.response = FakeResponse(201, '{"messageId": "<x@brevo>"}')


@pytest.fixture
def brevo(monkeypatch):
    recorder = Recorder()

    def fake_post(url, json, headers, timeout):
        recorder.calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        return recorder.response

    monkeypatch.setattr(mailer_module.requests, "post", fake_post)
    return recorder


def test_envoie_l_email_au_destinataire_fixe(brevo):
    BrevoApiMailer("cle-api", SENDER, "boite@example.com").send("[Lead 8/10]\r\nBcc: x", "Corps")
    call = brevo.calls[0]
    assert call["url"] == "https://api.brevo.com/v3/smtp/email"
    assert call["headers"]["api-key"] == "cle-api"
    assert call["json"] == {
        "sender": {"name": "Atelier Ardoise (démo)", "email": "demo@example.com"},
        "to": [{"email": "boite@example.com"}],
        "subject": "[Lead 8/10] Bcc: x",
        "textContent": "Corps",
    }
    assert call["timeout"] == 10


def test_expediteur_sans_nom():
    mailer = BrevoApiMailer("cle", "demo@example.com", "boite@example.com")
    assert mailer._sender == {"email": "demo@example.com"}


def test_expediteur_invalide_refuse():
    with pytest.raises(ValueError):
        BrevoApiMailer("cle", "Atelier Ardoise", "boite@example.com")


def test_refus_de_brevo_devient_delivery_error(brevo):
    brevo.response = FakeResponse(401, '{"code": "unauthorized", "message": "Key not found"}')
    with pytest.raises(DeliveryError, match="Brevo 401"):
        BrevoApiMailer("mauvaise", SENDER, "boite@example.com").send("Objet", "Corps")


def test_brevo_injoignable_devient_delivery_error(monkeypatch):
    def timeout(*_args, **_kwargs):
        raise requests.Timeout("délai dépassé")

    monkeypatch.setattr(mailer_module.requests, "post", timeout)
    with pytest.raises(DeliveryError, match="injoignable"):
        BrevoApiMailer("cle", SENDER, "boite@example.com").send("Objet", "Corps")


def config(**values):
    base = {key: getattr(Config, key) for key in dir(Config) if key.isupper()}
    base.update({
        "BREVO_API_KEY": "", "SMTP_HOST": "", "SMTP_USER": "", "SMTP_PASSWORD": "",
        "MAIL_FROM": SENDER, "MAIL_TO": "boite@example.com",
    })
    base.update(values)
    return base


def test_l_api_passe_avant_le_smtp():
    built = _build_mailer(config(BREVO_API_KEY="cle", SMTP_HOST="smtp", SMTP_USER="u", SMTP_PASSWORD="p"))
    assert isinstance(built, BrevoApiMailer)


def test_smtp_sans_cle_api():
    assert isinstance(_build_mailer(config(SMTP_HOST="smtp", SMTP_USER="u", SMTP_PASSWORD="p")), SmtpMailer)


def test_rien_de_configure():
    assert _build_mailer(config()) is None
    assert _build_mailer(config(BREVO_API_KEY="cle", MAIL_TO="")) is None


def test_canal_annonce_dans_health():
    # Une clé API absente en ligne retombait en silence sur le SMTP bloqué :
    # le canal affiché permet de le voir sans envoyer de lead.
    assert _channel(_build_mailer(config(BREVO_API_KEY="cle"))) == "brevo_api"
    assert _channel(_build_mailer(config(SMTP_HOST="smtp", SMTP_USER="u", SMTP_PASSWORD="p"))) == "smtp"
    assert _channel(_build_mailer(config())) is None
