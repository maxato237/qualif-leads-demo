"""Appel HTTP minimal à l'API Mistral, partagé par le client LLM et le client embeddings."""

import time

import requests

BASE_URL = "https://api.mistral.ai/v1"
# L'offre gratuite limite à environ 1 requête/seconde : on réessaie après une courte pause.
RETRY_DELAYS = (1.2, 2.5, 5.0)


class ProviderError(Exception):
    """Le fournisseur IA ne répond pas ou renvoie une erreur."""


def post_json(path: str, payload: dict, api_key: str, timeout: float) -> dict:
    if not api_key:
        raise ProviderError("MISTRAL_API_KEY manquante")
    for attempt in range(len(RETRY_DELAYS) + 1):
        try:
            response = requests.post(
                f"{BASE_URL}{path}",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=timeout,
            )
        except requests.ConnectionError as exc:
            # Coupure réseau passagère : on réessaie. Un timeout, lui, n'est pas réessayé.
            if attempt < len(RETRY_DELAYS):
                time.sleep(RETRY_DELAYS[attempt])
                continue
            raise ProviderError(f"Mistral injoignable : {exc}") from exc
        except requests.RequestException as exc:
            raise ProviderError(f"Mistral injoignable : {exc}") from exc
        if response.status_code == 429 and attempt < len(RETRY_DELAYS):
            time.sleep(_retry_delay(response, RETRY_DELAYS[attempt]))
            continue
        if response.status_code != 200:
            raise ProviderError(f"Mistral {response.status_code} : {response.text[:300]}")
        return response.json()
    raise AssertionError("inatteignable")


def _retry_delay(response: requests.Response, default: float) -> float:
    try:
        return min(float(response.headers.get("Retry-After", default)), 10.0)
    except ValueError:
        return default
