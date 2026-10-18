"""Pages simples : accueil, à propos, contact, plus robots / sitemap / healthcheck."""
from flask import Blueprint, Response, current_app, jsonify, redirect, render_template, request, url_for

from ..auth import is_logged_in
from ..contact import validate
from ..notifications import notify
from .projets import project_url

bp = Blueprint("pages", __name__)


@bp.get("/")
def index():
    # Utilisateur connecté : sa page d'accueil est hub-app (autre repo / service).
    if is_logged_in():
        resp = redirect(current_app.extensions["auth"].app_url, code=302)
        resp.headers["Cache-Control"] = "private, no-store"
        return resp
    return render_template("index.html")


@bp.get("/apropos")
def apropos():
    return render_template("apropos.html")


@bp.get("/contact")
def contact():
    return render_template("contact.html")


@bp.post("/contact/send")
def send_mail():
    cfg = current_app.config
    data = request.get_json(silent=True)

    # Honeypot : un humain ne voit pas ce champ. On répond « succès » sans rien envoyer.
    if isinstance(data, dict) and data.get("website"):
        return jsonify(success=True, error="")

    clean, error = validate(data)
    if error:
        return jsonify(success=False, error=error), 400

    if not current_app.extensions["contact_limiter"].allow(request.remote_addr or "?"):
        return jsonify(success=False, error="Trop de messages envoyés. Réessayez plus tard."), 429

    if not cfg["NOTIFICATIONS_URL"]:
        return jsonify(success=False, error="Le formulaire est momentanément indisponible."), 503

    sent = notify(
        cfg["NOTIFICATIONS_URL"],
        titre=f"Mail de : {clean['nom']}",
        message=f"from : {clean['email']}\nmessage :\n{clean['message']}",
        priorite="high",
        tags=["Contact"],
        lien=cfg["SITE_URL"],
    )
    if not sent:
        return jsonify(success=False, error="L'envoi a échoué."), 502
    return jsonify(success=True, error="")


@bp.get("/healthz")
def healthz():
    return "ok", 200, {"Content-Type": "text/plain"}


@bp.get("/robots.txt")
def robots():
    body = f"User-agent: *\nAllow: /\nSitemap: {url_for('pages.sitemap', _external=True)}\n"
    return Response(body, mimetype="text/plain")


@bp.get("/sitemap.xml")
def sitemap():
    store = current_app.extensions["content"]
    urls = [url_for(ep, _external=True) for ep in ("pages.index", "pages.apropos", "pages.contact", "projets.hub")]
    urls += [project_url(p, _external=True) for p in store.all()]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    xml += [f"  <url><loc>{u}</loc></url>" for u in urls]
    xml.append("</urlset>")
    return Response("\n".join(xml), mimetype="application/xml")
