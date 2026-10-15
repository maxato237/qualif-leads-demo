"""Quota global de questions par jour : protège le budget de l'API.

En mémoire, donc propre à un processus : lancer gunicorn avec 1 worker.
"""

import threading
from datetime import date
from typing import Callable


class DailyQuota:
    def __init__(self, limit: int, today: Callable[[], date] = date.today):
        self._limit = limit
        self._today = today
        self._day = today()
        self._count = 0
        self._lock = threading.Lock()

    def try_consume(self) -> bool:
        with self._lock:
            if self._today() != self._day:
                self._day, self._count = self._today(), 0
            if self._count >= self._limit:
                return False
            self._count += 1
            return True
