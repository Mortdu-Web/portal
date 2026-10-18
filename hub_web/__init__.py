"""hub-web : pages publiques (sans connexion) de mon site personnel."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import click
from flask import Flask, jsonify, render_template, request, url_for
from jinja2 import ChoiceLoader, FileSystemLoader, PrefixLoader
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

from .auth import Authenticator, is_logged_in
from .config import Config
from .contact import RateLimiter
from .content import TYPES, ContentStore


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    n_proxies = app.config["TRUSTED_PROXIES"]
    if n_proxies:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=n_proxies, x_proto=n_proxies, x_host=n_proxies)

    # ── Contenu ──────────────────────────────────────────────────────────────
    auto_reload = app.config["CONTENT_AUTO_RELOAD"]
    store = ContentStore(
        Path(app.config["CONTENT_DIR"]),
        auto_reload=app.debug if auto_reload is None else auto_reload,
    )
    app.extensions["content"] = store
    app.extensions["contact_limiter"] = RateLimiter(
        app.config["CONTACT_RATE_LIMIT"], app.config["CONTACT_RATE_WINDOW"]
    )

    # ── Connexion (optionnelle) : on interroge le service `auth` ──────────────
    auth = Authenticator.from_config(app.config)  # lève AuthConfigError si la config est incomplète
    if auth:
        app.extensions["auth"] = auth

    # Les page.html des projets vivent dans content/, pas dans templates/ :
    # on les expose sous le préfixe « content/ » (ex. "content/homelab/vpn/page.html").
    app.jinja_env.loader = ChoiceLoader(
        [app.jinja_env.loader, PrefixLoader({"content": FileSystemLoader(str(store.root))})]
    )

    # ── Variables communes aux templates ─────────────────────────────────────
    app.add_template_global(TYPES, "PROJECT_TYPES")

    @app.context_processor
    def inject_common():
        ctx = {"year": datetime.now().year, "auth_enabled": bool(auth), "logged_in": False}
        if auth:
            site_url = app.config["SITE_URL"].rstrip("/")
            home = f"{site_url}/" if site_url else url_for("pages.index", _external=True)
            ctx.update(
                logged_in=is_logged_in(),
                app_url=auth.app_url,
                login_href=auth.login_href(home),            # après connexion : « / » → hub-app
                logout_href=auth.logout_href(request.url),   # après déconnexion : on reste sur la page
            )
        return ctx

    # ── Routes ───────────────────────────────────────────────────────────────
    from .routes import pages, projets

    app.register_blueprint(pages.bp)
    app.register_blueprint(projets.bp)

    # ── Erreurs ──────────────────────────────────────────────────────────────
    @app.errorhandler(HTTPException)
    def http_error(exc: HTTPException):
        if request.path.startswith("/contact/send"):
            return jsonify(success=False, error=exc.description), exc.code
        return render_template("errors/error.html", code=exc.code, name=exc.name), exc.code

    @app.after_request
    def security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")  # SAMEORIGIN : le CV s'affiche en iframe
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if auth and request.endpoint != "static":
            resp.vary.add("Cookie")  # la barre de navigation dépend de l'utilisateur : pas de cache partagé
        return resp

    # ── Commandes ────────────────────────────────────────────────────────────
    @app.cli.command("todo")
    def todo_command():
        """Liste les projets qui contiennent encore des « A COMPLETER » / « XXX »."""
        total = 0
        for project in store.all():
            items = project.todo()
            if items:
                total += 1
                click.echo(click.style(project.key, bold=True))
                for item in items:
                    click.echo(f"  - {item}")
        click.echo(f"\n{total} projet(s) à compléter sur {len(store.all())}.")

    return app
