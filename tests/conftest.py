import pytest

from hub_web import create_app


@pytest.fixture()
def app():
    return create_app({
        "TESTING": True,
        "NOTIFICATIONS_URL": "http://ntfy.test/topic",
        "CONTACT_RATE_LIMIT": 3,
    })


@pytest.fixture()
def client(app):
    return app.test_client()
