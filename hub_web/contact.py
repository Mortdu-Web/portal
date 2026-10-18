"""Logique du formulaire de contact : validation et limitation de débit."""
from __future__ import annotations

import re
import threading
import time
from collections import defaultdict, deque

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LIMITS = {"nom": 100, "email": 254, "message": 5000}


def validate(data: dict | None) -> tuple[dict | None, str | None]:
    """Retourne (champs nettoyés, None) ou (None, message d'erreur)."""
    if not isinstance(data, dict):
        return None, "Requête invalide."
    clean = {k: str(data.get(k, "")).strip() for k in LIMITS}
    if not all(clean.values()):
        return None, "Champs manquants."
    for key, maxlen in LIMITS.items():
        if len(clean[key]) > maxlen:
            return None, f"Le champ « {key} » est trop long."
    if not EMAIL_RE.match(clean["email"]):
        return None, "Adresse e-mail invalide."
    return clean, None


class RateLimiter:
    """N événements par fenêtre glissante et par clé (IP). En mémoire : suffisant pour 1-2 workers."""

    def __init__(self, limit: int, window: int):
        self.limit, self.window = limit, window
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            return True
