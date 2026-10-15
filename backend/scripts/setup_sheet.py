"""Écrit la ligne d'en-tête du Google Sheet de démo, puis ajoute une ligne de test.

    python scripts/setup_sheet.py

À lancer une fois, après avoir partagé le Sheet avec le compte de service (droit Éditeur).
Lit GOOGLE_SERVICE_ACCOUNT, SHEET_ID et SHEET_RANGE dans backend/.env.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Config  # noqa: E402
from app.infra.sheets_client import GoogleSheetSink, load_service_account  # noqa: E402
from app.services.formatting import SHEET_HEADER  # noqa: E402


def main() -> int:
    if not (Config.GOOGLE_SERVICE_ACCOUNT and Config.SHEET_ID):
        print("GOOGLE_SERVICE_ACCOUNT et SHEET_ID sont requis dans backend/.env")
        return 1
    info = load_service_account(Config.GOOGLE_SERVICE_ACCOUNT)
    sink = GoogleSheetSink(info, Config.SHEET_ID, Config.SHEET_RANGE)
    sink.write_header(SHEET_HEADER)
    print(f"En-tête écrit ({len(SHEET_HEADER)} colonnes) dans {sink.public_url}")
    print(f"Compte de service : {info.get('client_email')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
