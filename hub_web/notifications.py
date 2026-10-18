"""Envoi de notifications push via ntfy (utilisé par le formulaire de contact)."""
from __future__ import annotations

import base64
import logging

import requests

log = logging.getLogger(__name__)

PRIORITES = {"min": 1, "low": 2, "default": 3, "high": 4, "urgent": 5}


def _header(value: str) -> str:
    """Valeur d'en-tête HTTP sûre : sans retour à la ligne, encodée RFC 2047 si besoin."""
    value = " ".join(value.split())
    try:
        value.encode("latin-1")
        return value
    except UnicodeEncodeError:
        return "=?UTF-8?B?" + base64.b64encode(value.encode("utf-8")).decode() + "?="


def notify(
    url: str,
    titre: str,
    message: str,
    priorite: str = "default",
    tags: list[str] | None = None,
    lien: str = "",
) -> bool:
    """Retourne True si la notification est partie, False sinon (jamais d'exception)."""
    if not url:
        return False
    headers = {
        "Title": _header(titre),
        "Priority": str(PRIORITES.get(priorite, 3)),
        "Content-Type": "text/plain; charset=utf-8",
    }
    if tags:
        headers["Tags"] = ",".join(tags)
    if lien:
        headers["Click"] = _header(lien)
    try:
        resp = requests.post(url, data=message.encode("utf-8"), headers=headers, timeout=5)
        resp.raise_for_status()
        return True
    except requests.RequestException as exc:
        log.warning("Notification ntfy échouée : %s", exc)
        return False
