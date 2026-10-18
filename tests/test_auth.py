"""Connexion via le service `auth` : appel à /api/me, redirection de « / », barre de navigation."""
import pytest
import requests

from hub_web import create_app
from hub_web.auth import AuthConfigError

PUBLIC = "https://auth.exemple.fr"
INTERNAL = "http://auth:5000"
APP = "https://app.exemple.fr/"
SITE = "https://www.exemple.fr"


class FakeAuth:
    """Remplace requests.get : enregistre les appels et renvoie la réponse (ou l'erreur) programmée."""

    def __init__(self):
        self.status = 200
        self.error = None
        self.calls = []

    def __call__(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.error:
            raise self.error
        return type("Resp", (), {"status_code": self.status})()


@pytest.fixture()
def fake(monkeypatch):
    f = FakeAuth()
    monkeypatch.setattr("hub_web.auth.requests.get", f)
    return f


def make_app(**over):
    cfg = {"TESTING": True, "AUTH_PUBLIC_URL": PUBLIC, "AUTH_INTERNAL_URL": INTERNAL, "APP_URL": APP, "SITE_URL": SITE}
    cfg.update(over)
    return create_app(cfg)


@pytest.fixture()
def client(fake):
    return make_app().test_client()


def login(client, name="session", value="cookie-opaque"):
    client.set_cookie(name, value, domain="localhost")
    return client


# ── « / » ────────────────────────────────────────────────────────────────────

def test_logged_in_home_redirects_to_app(client, fake):
    resp = login(client).get("/")
    assert resp.status_code == 302 and resp.headers["Location"] == APP
    assert "no-store" in resp.headers["Cache-Control"]


def test_auth_is_asked_with_the_session_cookie_only(client, fake):
    client.set_cookie("session", "abc", domain="localhost")
    client.set_cookie("autre", "secret-sans-rapport", domain="localhost")
    client.get("/")
    (url, kwargs), = fake.calls
    assert url == "http://auth:5000/api/me"
    assert kwargs["cookies"] == {"session": "abc"}          # pas les autres cookies
    assert kwargs["allow_redirects"] is False and kwargs["timeout"] > 0


def test_anonymous_without_cookie_never_calls_auth(client, fake):
    assert client.get("/").status_code == 200
    client.get("/projets/")
    assert fake.calls == []


@pytest.mark.parametrize("status", [401, 403, 302, 404, 500])
def test_any_non_200_is_anonymous(client, fake, status):
    fake.status = status
    assert login(client).get("/").status_code == 200


@pytest.mark.parametrize("error", [requests.ConnectionError("down"), requests.Timeout("lent")])
def test_auth_down_keeps_public_site_working(client, fake, error):
    fake.error = error
    login(client)
    for url in ("/", "/projets/", "/apropos", "/contact"):
        resp = client.get(url)
        assert resp.status_code == 200, url
    assert "Connexion" in client.get("/projets/").get_data(as_text=True)


def test_other_cookie_name_is_ignored(client, fake):
    login(client, name="autre")
    assert client.get("/").status_code == 200 and fake.calls == []


def test_one_auth_call_per_request(client, fake):
    login(client).get("/projets/")           # la route ET la barre de navigation veulent savoir
    assert len(fake.calls) == 1
    fake.calls.clear()
    login(client).get("/")                   # redirection
    assert len(fake.calls) == 1


def test_public_pages_reachable_when_logged_in(client):
    login(client)
    for url in ("/apropos", "/contact", "/projets/", "/projets/splendor/"):
        assert client.get(url).status_code == 200, url


# ── Barre de navigation ──────────────────────────────────────────────────────

def test_anonymous_nav_login_goes_to_auth_then_home(client):
    html = client.get("/projets/splendor/").get_data(as_text=True)
    assert "Connexion" in html and "Mon espace" not in html
    # après connexion on revient sur « / » du site, qui redirige vers hub-app
    assert 'href="https://auth.exemple.fr/login?next=https%3A%2F%2Fwww.exemple.fr%2F"' in html


def test_logged_in_nav(client):
    html = login(client).get("/projets/").get_data(as_text=True)
    assert "Mon espace" in html and f'href="{APP}"' in html and ">Connexion<" not in html
    # après déconnexion on reste sur la page courante
    assert "https://auth.exemple.fr/logout?next=http%3A%2F%2Flocalhost%2Fprojets%2F" in html


def test_home_url_without_site_url_uses_request_host(fake):
    html = make_app(SITE_URL="").test_client().get("/apropos").get_data(as_text=True)
    assert "login?next=http%3A%2F%2Flocalhost%2F" in html


def test_vary_cookie_on_html_not_on_static(client):
    assert "Cookie" in client.get("/projets/").headers.get("Vary", "")
    assert "Cookie" not in client.get("/static/css/base.css").headers.get("Vary", "")


def test_error_pages_have_the_nav_too(client):
    resp = client.get("/nope")
    assert resp.status_code == 404 and "Connexion" in resp.get_data(as_text=True)


# ── Configuration ────────────────────────────────────────────────────────────

def test_disabled_by_default(fake):
    app = create_app({"TESTING": True})
    assert "Connexion" not in app.test_client().get("/").get_data(as_text=True)
    assert "auth" not in app.extensions


def test_internal_url_defaults_to_public(fake):
    app = make_app(AUTH_INTERNAL_URL="")
    assert app.extensions["auth"].internal_url == PUBLIC


@pytest.mark.parametrize("missing", ["AUTH_PUBLIC_URL", "APP_URL"])
def test_partial_config_fails_at_startup(missing):
    with pytest.raises(AuthConfigError, match=missing):
        make_app(**{missing: ""})


@pytest.mark.parametrize("over", [
    {"APP_URL": "javascript:alert(1)"}, {"AUTH_PUBLIC_URL": "/login"}, {"AUTH_INTERNAL_URL": "auth:5000"},
])
def test_invalid_url_fails_at_startup(over):
    with pytest.raises(AuthConfigError, match="http"):
        make_app(**over)


def test_trailing_slashes_are_normalised(fake):
    a = make_app(AUTH_PUBLIC_URL=PUBLIC + "/", AUTH_INTERNAL_URL=INTERNAL + "/", APP_URL="https://app.exemple.fr").extensions["auth"]
    assert (a.public_url, a.internal_url, a.app_url) == (PUBLIC, INTERNAL, APP)
