"""Envoi de l'email de notification à l'agence, par SMTP (STARTTLS)."""

import smtplib
from email.message import EmailMessage
from typing import Protocol

from app.infra.delivery import DeliveryError


class Mailer(Protocol):
    sender: str
    recipient: str

    def send(self, subject: str, body: str) -> None: ...


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
