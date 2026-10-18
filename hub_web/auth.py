"""
Savoir si le visiteur est connecté, en le demandant au service `auth`.

hub-web ne vérifie PAS le cookie lui-même (la session est signée avec un secret qui reste dans `auth`) :
il transmet le cookie à `GET {AUTH_INTERNAL_URL}/api/me`. 200 = connecté ; tout le reste = anonyme.

Si `auth` est lent ou en panne, le visiteur est considéré comme anonyme : le site public continue de
fonctionner. Les visiteurs sans cookie (la grande majorité) ne déclenchent aucun appel à `auth`.
"""
from __future__ import annotations

import logging
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests
from flask import current_app, g, request

log = logging.getLogger(__name__)


class AuthConfigError(RuntimeError):
    """Configuration de connexion incomplète ou invalide (détectée au démarrage)."""


def _check_url(name: str, value: str) -> str:
    p = urlparse(value)
    if p.scheme not in ("http", "https") or not p.netloc:
        raise AuthConfigError(f"{name} doit être une URL http(s) absolue (reçu : {value!r})")
    return value.rstrip("/")


def _with_next(url: str, next_url: str) -> str:
    parts = urlparse(url)
    query = [(k, v) for k, v in parse_qsl(parts.query) if k != "next"] + [("next", next_url)]
    return urlunparse(parts._replace(query=urlencode(query)))


class Authenticator:
    def __init__(self, *, public_url: str, internal_url: str, app_url: str, cookie_name: str, timeout: float):
        self.public_url = public_url
        self.internal_url = internal_url
        self.app_url = app_url
        self.cookie_name = cookie_name
        self.timeout = timeout

    @classmethod
    def from_config(cls, cfg) -> "Authenticator | None":
        names = ("AUTH_PUBLIC_URL", "AUTH_INTERNAL_URL", "APP_URL")
        if not any(cfg[n] for n in names):
            return None  # connexion non configurée : site public uniquement

        missing = [n for n in ("AUTH_PUBLIC_URL", "APP_URL") if not cfg[n]]
        if missing:
            raise AuthConfigError("Configuration de connexion incomplète, variables manquantes : " + ", ".join(missing))

        public = _check_url("AUTH_PUBLIC_URL", cfg["AUTH_PUBLIC_URL"])
        internal = _check_url("AUTH_INTERNAL_URL", cfg["AUTH_INTERNAL_URL"]) if cfg["AUTH_INTERNAL_URL"] else public
        app_url = _check_url("APP_URL", cfg["APP_URL"]) + "/"
        return cls(public_url=public, internal_url=internal, app_url=app_url,
                   cookie_name=cfg["AUTH_COOKIE_NAME"], timeout=cfg["AUTH_TIMEOUT"])

    def is_logged_in(self, req) -> bool:
        token = req.cookies.get(self.cookie_name)
        if not token:
            return False
        try:
            # requests.get et NON une Session : une Session mémoriserait les cookies renvoyés par auth
            # et les mélangerait entre visiteurs.
            resp = requests.get(
                f"{self.internal_url}/api/me",
                cookies={self.cookie_name: token},
                headers={"Accept": "application/json"},
                timeout=self.timeout,
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            log.warning("auth injoignable (%s) : visiteur traité comme anonyme", exc)
            return False
        return resp.status_code == 200

    def login_href(self, next_url: str) -> str:
        return _with_next(f"{self.public_url}/login", next_url)

    def logout_href(self, next_url: str) -> str:
        return _with_next(f"{self.public_url}/logout", next_url)


def is_logged_in() -> bool:
    """Visiteur connecté ? Au plus un appel à `auth` par requête, quel que soit le nombre d'usages."""
    auth = current_app.extensions.get("auth")
    if not auth:
        return False
    if "logged_in" not in g:
        g.logged_in = auth.is_logged_in(request)
    return g.logged_in
