"""Envoi de l'email de notification à l'agence : API HTTP de Brevo, ou SMTP (STARTTLS)."""

import smtplib
from email.message import EmailMessage
from email.utils import parseaddr
from typing import Protocol

import requests

from app.infra.delivery import DeliveryError

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


class Mailer(Protocol):
    sender: str
    recipient: str

    def send(self, subject: str, body: str) -> None: ...


class BrevoApiMailer:
    """Envoi par l'API HTTP de Brevo, sur le port 443.

    Certains hébergeurs bloquent la sortie SMTP : depuis Sevalla, la connexion au
    port 587 restait suspendue jusqu'au délai d'attente. HTTPS n'est jamais bloqué.
    """

    def __init__(self, api_key: str, sender: str, recipient: str, timeout: float = 10):
        name, address = parseaddr(sender)
        if "@" not in address:
            raise ValueError("MAIL_FROM sans adresse email")
        self._api_key = api_key
        self._sender = {"email": address, **({"name": name} if name else {})}
        self.sender = sender
        self.recipient = recipient
        self._timeout = timeout

    def send(self, subject: str, body: str) -> None:
        payload = {
            "sender": self._sender,
            # Destinataire fixe, issu de la configuration : jamais une adresse saisie par le visiteur.
            "to": [{"email": self.recipient}],
            "subject": " ".join(subject.split()),
            "textContent": body,
        }
        try:
            response = requests.post(
                BREVO_API_URL,
                json=payload,
                headers={"api-key": self._api_key, "accept": "application/json"},
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise DeliveryError(f"Brevo injoignable : {exc}") from exc
        if response.status_code not in (200, 201, 202):
            raise DeliveryError(f"Brevo {response.status_code} : {response.text[:300]}")


class SmtpMailer:
    def __init__(self, host: str, port: int, user: str, password: str,
                 sender: str, recipient: str, timeout: float = 10):
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self.sender = sender
        self.recipient = recipient
        self._timeout = timeout

    def send(self, subject: str, body: str) -> None:
        message = EmailMessage()
        # Destinataire fixe, issu de la configuration : jamais une adresse saisie par le visiteur.
        message["From"] = self.sender
        message["To"] = self.recipient
        message["Subject"] = " ".join(subject.split())
        message.set_content(body)
        try:
            with smtplib.SMTP(self._host, self._port, timeout=self._timeout) as smtp:
                smtp.starttls()
                smtp.login(self._user, self._password)
                smtp.send_message(message)
        except (smtplib.SMTPException, OSError) as exc:
            raise DeliveryError(f"SMTP : {exc}") from exc
