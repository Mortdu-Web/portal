import json

import pytest

from hub_web.content import ContentError, load_projects


def make(root, rel, **over):
    d = root / rel
    d.mkdir(parents=True, exist_ok=True)
    header = {"nom": "N", "date": "2025", "type": "personnel", "court": "c", "accroche": "a", "stack": []}
    header.update(over)
    (d / "header.json").write_text(json.dumps(header), encoding="utf-8")
    return d


def test_real_content_is_valid(app):
    store = app.extensions["content"]
    assert len(store.top_level()) >= 1
    for p in store.all():
        assert p.nom and p.type in ("academique", "personnel")


def test_every_project_has_a_page(app):
    for p in app.extensions["content"].all():
        assert (p.directory / "page.html").is_file(), f"page.html manquant pour {p.key}"


def test_children_are_attached_to_parent(app):
    homelab = app.extensions["content"].get("homelab")
    assert homelab is not None and len(homelab.children) == 8
    assert all(c.parent == "homelab" for c in homelab.children)


def test_ordre_is_respected(tmp_path):
    make(tmp_path, "b", nom="B", ordre=20)
    make(tmp_path, "a", nom="A", ordre=30)
    make(tmp_path, "c", nom="C", ordre=10)
    assert [p.slug for p in load_projects(tmp_path)] == ["c", "b", "a"]


def test_missing_key_is_reported(tmp_path):
    d = make(tmp_path, "x")
    h = json.loads((d / "header.json").read_text())
    del h["court"]
    (d / "header.json").write_text(json.dumps(h))
    with pytest.raises(ContentError, match="court"):
        load_projects(tmp_path)


def test_invalid_type(tmp_path):
    make(tmp_path, "x", type="pro")
    with pytest.raises(ContentError, match="type"):
        load_projects(tmp_path)


def test_invalid_json(tmp_path):
    d = tmp_path / "x"
    d.mkdir()
    (d / "header.json").write_text("{pas du json")
    with pytest.raises(ContentError, match="JSON invalide"):
        load_projects(tmp_path)


def test_depth_limit(tmp_path):
    make(tmp_path, "a")
    make(tmp_path, "a/b")
    make(tmp_path, "a/b/c")
    with pytest.raises(ContentError, match="profondeur"):
        load_projects(tmp_path)
