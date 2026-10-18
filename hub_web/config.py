"""Configuration, lue depuis les variables d'environnement (voir .env.example)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


class Config:
    # Dossier du contenu (projets). Séparé du code : on y ajoute des projets sans toucher au Python.
    CONTENT_DIR = Path(os.getenv("CONTENT_DIR", ROOT / "content" / "projets"))

    # None = suit le mode debug (rechargement du contenu à chaque requête en dev uniquement).
    CONTENT_AUTO_RELOAD = None

    # URL ntfy pour recevoir les messages du formulaire de contact. Vide = formulaire désactivé (503).
    NOTIFICATIONS_URL = os.getenv("NOTIFICATIONS_URL", "")
    SITE_URL = os.getenv("SITE_URL", "")  # lien cliquable dans la notification

    # Anti-spam du formulaire : N messages par fenêtre (secondes) et par IP.
    CONTACT_RATE_LIMIT = _int("CONTACT_RATE_LIMIT", 5)
    CONTACT_RATE_WINDOW = _int("CONTACT_RATE_WINDOW", 600)

    # Nombre de proxys de confiance devant l'app (ton reverse proxy Nginx = 1).
    # Nécessaire pour que l'IP du visiteur soit la vraie. 0 = accès direct.
    TRUSTED_PROXIES = _int("TRUSTED_PROXIES", 0)

    MAX_CONTENT_LENGTH = 16 * 1024  # un message de contact n'a pas besoin de plus

    # ── Connexion (optionnelle) : service `auth` (Keycloak) ──────────────────
    # Tout vide = site 100 % public, sans bouton Connexion. Détail : docs/liaison-des-repos.md
    AUTH_PUBLIC_URL = os.getenv("AUTH_PUBLIC_URL", "")      # auth vu par le navigateur (liens /login, /logout)
    AUTH_INTERNAL_URL = os.getenv("AUTH_INTERNAL_URL", "")  # auth vu par ce serveur (réseau Docker). Vide = AUTH_PUBLIC_URL
    APP_URL = os.getenv("APP_URL", "")                      # hub-app : où « / » envoie un utilisateur connecté
    AUTH_COOKIE_NAME = os.getenv("AUTH_COOKIE_NAME", "session")  # nom du cookie de session posé par auth
    AUTH_TIMEOUT = float(os.getenv("AUTH_TIMEOUT", "1.5"))  # secondes ; auth lent/en panne = visiteur anonyme
