"""Ajout d'une ligne dans le Google Sheet de démo, via un compte de service."""

import base64
import binascii
import json
from typing import Protocol

from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

from app.infra.delivery import DeliveryError

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
API_URL = "https://sheets.googleapis.com/v4/spreadsheets"


class LeadSink(Protocol):
    public_url: str | None

    def append(self, row: list[str]) -> None: ...


def load_service_account(raw: str) -> dict:
    """Accepte la clé JSON telle quelle ou encodée en base64."""
    raw = raw.strip()
    if not raw.startswith("{"):
        try:
            raw = base64.b64decode(raw, validate=True).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError) as exc:
            raise ValueError("GOOGLE_SERVICE_ACCOUNT n'est ni du JSON ni du base64") from exc
    return json.loads(raw)


class GoogleSheetSink:
    def __init__(self, service_account_info: dict, sheet_id: str, sheet_range: str, timeout: float = 10):
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info, scopes=SCOPES
        )
        self._session = AuthorizedSession(credentials)
        self._sheet_id = sheet_id
        self._range = sheet_range
        self._timeout = timeout
        self.public_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"

    def append(self, row: list[str]) -> None:
        # RAW : une valeur qui commence par "=" reste du texte, jamais une formule.
        response = self._session.post(
            f"{API_URL}/{self._sheet_id}/values/{self._range}:append",
            params={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"},
            json={"values": [row]},
            timeout=self._timeout,
        )
        if response.status_code != 200:
            raise DeliveryError(f"Google Sheets {response.status_code} : {response.text[:300]}")

    def write_header(self, header: list[str]) -> None:
        response = self._session.put(
            f"{API_URL}/{self._sheet_id}/values/{self._range.split('!')[0]}!A1",
            params={"valueInputOption": "RAW"},
            json={"values": [header]},
            timeout=self._timeout,
        )
        if response.status_code != 200:
            raise DeliveryError(f"Google Sheets {response.status_code} : {response.text[:300]}")
