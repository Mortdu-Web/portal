"""
Chargement du contenu des projets depuis le disque.

Un projet = un dossier :

    content/projets/<slug>/
        header.json   métadonnées (voir REQUIRED / OPTIONAL)
        page.html     fragment HTML : uniquement les <section> du corps de la page
        <sous-dossiers avec leur propre header.json = projets enfants>

Le nom du dossier est le slug de l'URL : /projets/<slug>/ ou /projets/<parent>/<slug>/.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

TYPES = {"academique": "Académique", "personnel": "Personnel"}
REQUIRED = ("nom", "date", "type", "court", "accroche", "stack")
MAX_DEPTH = 2  # projet + enfants (les routes ne gèrent pas plus)
PLACEHOLDERS = ("A COMPLETER", "XXX")


class ContentError(ValueError):
    """Contenu invalide : le message indique le fichier fautif."""


@dataclass(frozen=True)
class Project:
    slug: str
    parent: str | None
    nom: str
    date: str
    type: str
    court: str
    accroche: str
    stack: tuple[str, ...]
    git: str | None
    ordre: int
    enfants_titre: str
    enfants_retour: str
    directory: Path
    children: tuple["Project", ...] = ()

    @property
    def key(self) -> str:
        return f"{self.parent}/{self.slug}" if self.parent else self.slug

    @property
    def template(self) -> str:
        """Nom Jinja du fragment de page (préfixe « content/ » enregistré dans create_app)."""
        return f"content/{self.key}/page.html"

    def todo(self) -> list[str]:
        """Champs ou passages encore à compléter (« A COMPLETER », « XXX »)."""
        found = []
        for field in ("nom", "date", "court", "accroche"):
            if any(p in getattr(self, field) for p in PLACEHOLDERS):
                found.append(f"header.json : {field}")
        page = self.directory / "page.html"
        if page.is_file():
            text = page.read_text(encoding="utf-8")
            n = sum(text.count(p) for p in PLACEHOLDERS)
            if n:
                found.append(f"page.html : {n} passage(s) à compléter")
        return found


def _load_dir(directory: Path, parent: str | None, depth: int) -> Project:
    path = directory / "header.json"
    try:
        header = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContentError(f"{path} : JSON invalide ({exc})") from exc

    missing = [k for k in REQUIRED if k not in header]
    if missing:
        raise ContentError(f"{path} : clés manquantes {missing}")
    if header["type"] not in TYPES:
        raise ContentError(f"{path} : type doit être l'un de {sorted(TYPES)}")
    if not isinstance(header["stack"], list):
        raise ContentError(f"{path} : stack doit être une liste")

    slug = directory.name
    children = []
    for sub in sorted(p for p in directory.iterdir() if p.is_dir() and (p / "header.json").is_file()):
        if depth + 1 > MAX_DEPTH:
            raise ContentError(f"{sub} : profondeur maximale ({MAX_DEPTH}) dépassée")
        children.append(_load_dir(sub, slug, depth + 1))
    children.sort(key=lambda p: (p.ordre, p.nom.lower()))

    return Project(
        slug=slug,
        parent=parent,
        nom=header["nom"],
        date=str(header["date"]),
        type=header["type"],
        court=header["court"],
        accroche=header["accroche"],
        stack=tuple(header["stack"]),
        git=header.get("git"),
        ordre=int(header.get("ordre", 1000)),
        enfants_titre=header.get("enfants_titre", "Sous-projets"),
        enfants_retour=header.get("enfants_retour", "← Retour"),
        directory=directory,
        children=tuple(children),
    )


def load_projects(root: Path) -> tuple[Project, ...]:
    """Charge tous les projets de premier niveau (avec leurs enfants), triés par `ordre`."""
    if not root.is_dir():
        raise ContentError(f"Dossier de contenu introuvable : {root}")
    projects = [
        _load_dir(d, None, 1)
        for d in sorted(root.iterdir())
        if d.is_dir() and (d / "header.json").is_file()
    ]
    projects.sort(key=lambda p: (p.ordre, p.nom.lower()))
    return tuple(projects)


class ContentStore:
    """Accès au contenu. Chargé au démarrage (échec immédiat si un JSON est cassé)."""

    def __init__(self, root: Path, auto_reload: bool = False):
        self.root = Path(root)
        self.auto_reload = auto_reload
        self._projects = load_projects(self.root)

    def top_level(self) -> tuple[Project, ...]:
        if self.auto_reload:
            self._projects = load_projects(self.root)
        return self._projects

    def get(self, slug: str, parent: str | None = None) -> Project | None:
        level = self.top_level()
        if parent is not None:
            holder = next((p for p in level if p.slug == parent), None)
            level = holder.children if holder else ()
        return next((p for p in level if p.slug == slug), None)

    def all(self) -> list[Project]:
        out: list[Project] = []
        for p in self.top_level():
            out.append(p)
            out.extend(p.children)
        return out
