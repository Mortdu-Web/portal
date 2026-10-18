"""
Pages projets : le hub (/projets/) puis une route générique par niveau.

Aucune route par projet : ajouter un projet = ajouter un dossier dans content/projets/.
"""
from flask import Blueprint, abort, current_app, render_template, url_for

from ..content import TYPES, Project

bp = Blueprint("projets", __name__, url_prefix="/projets")


def project_url(project: Project, **kwargs) -> str:
    if project.parent:
        return url_for("projets.detail_enfant", parent=project.parent, slug=project.slug, **kwargs)
    return url_for("projets.detail", slug=project.slug, **kwargs)


@bp.record_once
def _register_helpers(state):
    state.app.add_template_global(project_url, "project_url")


def _store():
    return current_app.extensions["content"]


@bp.get("/")
def hub():
    projects = _store().top_level()
    sections = [
        {"key": key, "titre": label, "projets": [p for p in projects if p.type == key]}
        for key, label in TYPES.items()
    ]
    stacks = sorted({s for p in projects for s in p.stack}, key=str.lower)
    return render_template("projets/hub.html", sections=sections, stacks=stacks)


@bp.get("/<slug>/")
def detail(slug):
    project = _store().get(slug) or abort(404)
    return render_template(
        "projets/project.html",
        project=project,
        back_href=url_for("projets.hub"),
        back_label="← Retour aux projets",
        show_type=True,
    )


@bp.get("/<parent>/<slug>/")
def detail_enfant(parent, slug):
    store = _store()
    project = store.get(slug, parent) or abort(404)
    holder = store.get(parent)
    return render_template(
        "projets/project.html",
        project=project,
        back_href=url_for("projets.detail", slug=parent),
        back_label=holder.enfants_retour,
        show_type=False,
    )
