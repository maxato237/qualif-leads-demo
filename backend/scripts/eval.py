"""Passe les leads de tests/eval_leads.json dans le vrai Mistral et vérifie leur catégorie.

    python scripts/eval.py

Ni Google Sheet ni email : seulement l'extraction et le score. Sort en code 1 si un lead
tombe hors de la catégorie attendue ou dépasse 10 secondes.
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Config  # noqa: E402
from app.infra.llm_client import MistralLLMClient  # noqa: E402
from app.services.extraction import ExtractionService  # noqa: E402
from app.services.scoring import score_lead  # noqa: E402

LEADS_FILE = Path(__file__).resolve().parents[1] / "tests" / "eval_leads.json"
MAX_SECONDS = 10
# Offre gratuite de Mistral : environ une requête par seconde.
PAUSE_SECONDS = 1.5


def main() -> int:
    extractor = ExtractionService(
        MistralLLMClient(Config.MISTRAL_API_KEY, Config.LLM_MODEL),
        Config.EXTRACTION_PROMPT_FILE.read_text(encoding="utf-8"),
        Config.MAX_EXTRACTION_TOKENS,
    )
    failures = 0
    for case in json.loads(LEADS_FILE.read_text(encoding="utf-8")):
        started = time.perf_counter()
        lead = extractor.extract(case["company"], case["message"])
        score = score_lead(lead)
        seconds = time.perf_counter() - started
        ok = score.category in case["expected"] and seconds <= MAX_SECONDS
        failures += not ok
        print(f"{'OK ' if ok else 'KO '} {case['id']:<24} {score.value:>2}/10 {score.category:<10} {seconds:4.1f} s")
        print(f"     {', '.join(f'{c.key}={c.points}' for c in score.criteria)}")
        if lead.red_flags:
            print(f"     alertes : {' | '.join(lead.red_flags)}")
        time.sleep(PAUSE_SECONDS)
    print(f"\n{failures} échec(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
