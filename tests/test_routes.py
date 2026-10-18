import pytest

from hub_web.routes import pages


@pytest.mark.parametrize("url", ["/", "/apropos", "/contact", "/projets/", "/healthz", "/robots.txt", "/sitemap.xml"])
def test_static_pages(client, url):
    assert client.get(url).status_code == 200


def test_every_project_page_renders(app, client):
    with app.test_request_context():
        from hub_web.routes.projets import project_url

        urls = [(p, project_url(p)) for p in app.extensions["content"].all()]
    assert len(urls) >= 20
    for project, url in urls:
        resp = client.get(url)
        assert resp.status_code == 200, url
        assert project.nom in resp.get_data(as_text=True), url


def test_old_urls_are_preserved(client):
    # URLs de l'ancien site Flask
    for url in ("/projets/splendor/", "/projets/homelab/", "/projets/homelab/wikijs/", "/projets/loup-garou/"):
        assert client.get(url).status_code == 200, url


def test_homelab_lists_its_services(client):
    html = client.get("/projets/homelab/").get_data(as_text=True)
    assert "Services du HomeLab" in html and "/projets/homelab/wikijs/" in html


def test_child_back_link_goes_to_parent(client):
    html = client.get("/projets/homelab/wikijs/").get_data(as_text=True)
    assert 'href="/projets/homelab/"' in html and "Retour au HomeLab" in html


def test_hub_lists_only_top_level(client):
    html = client.get("/projets/").get_data(as_text=True)
    assert "/projets/splendor/" in html and "/projets/homelab/wikijs/" not in html


@pytest.mark.parametrize("url", ["/nope", "/projets/nope/", "/projets/homelab/nope/", "/projets/splendor/nope/"])
def test_404(client, url):
    resp = client.get(url)
    assert resp.status_code == 404
    assert "404" in resp.get_data(as_text=True)


def test_sitemap_contains_projects(client):
    xml = client.get("/sitemap.xml").get_data(as_text=True)
    assert "/projets/splendor/" in xml and "/projets/homelab/vpn/" in xml


# ── Formulaire de contact ────────────────────────────────────────────────────

GOOD = {"nom": "Alice", "email": "alice@example.org", "message": "Bonjour !"}


@pytest.fixture()
def sent(monkeypatch):
    calls = []
    monkeypatch.setattr(pages, "notify", lambda *a, **k: calls.append((a, k)) or True)
    return calls


def test_contact_ok(client, sent):
    resp = client.post("/contact/send", json=GOOD)
    assert resp.status_code == 200 and resp.json["success"] is True
    assert len(sent) == 1
    assert "alice@example.org" in sent[0][1]["message"]


@pytest.mark.parametrize("bad", [
    {}, {"nom": "A"}, {**GOOD, "email": "pas-un-mail"}, {**GOOD, "message": "x" * 5001}, {**GOOD, "nom": "   "},
])
def test_contact_validation(client, sent, bad):
    resp = client.post("/contact/send", json=bad)
    assert resp.status_code == 400 and resp.json["success"] is False
    assert not sent


def test_contact_rejects_non_json(client, sent):
    assert client.post("/contact/send", data="x").status_code == 400


def test_contact_honeypot_is_silent(client, sent):
    resp = client.post("/contact/send", json={**GOOD, "website": "http://spam"})
    assert resp.status_code == 200 and resp.json["success"] is True
    assert not sent


def test_contact_rate_limit(client, sent):
    codes = [client.post("/contact/send", json=GOOD).status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]


def test_contact_unconfigured(app, client):
    app.config["NOTIFICATIONS_URL"] = ""
    assert client.post("/contact/send", json=GOOD).status_code == 503


def test_contact_notification_failure(client, monkeypatch):
    monkeypatch.setattr(pages, "notify", lambda *a, **k: False)
    assert client.post("/contact/send", json=GOOD).status_code == 502


def test_contact_get_not_allowed_returns_json(client):
    resp = client.get("/contact/send")
    assert resp.status_code == 405 and resp.json["success"] is False


# ── Thème clair / sombre ─────────────────────────────────────────────────────

def test_theme_toggle_is_on_every_page(client):
    for url in ("/", "/apropos", "/contact", "/projets/", "/projets/splendor/", "/nope"):
        html = client.get(url).get_data(as_text=True)
        assert 'id="theme-toggle"' in html and "js/theme.js" in html, url
