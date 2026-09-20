from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def _generate_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ).decode()
    public_pem = (
        private_key.public_key()
        .public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private_pem, public_pem


PRIVATE_KEY, PUBLIC_KEY = _generate_keypair()


def _make_token(private_key=PRIVATE_KEY, exp_delta=timedelta(minutes=5)):
    now = datetime.now(tz=timezone.utc)
    return jwt.encode(
        {"sub": "scraper", "iat": now, "exp": now + exp_delta},
        private_key,
        algorithm="RS256",
    )


@pytest.fixture(autouse=True)
def set_public_key(monkeypatch):
    monkeypatch.setenv("SYNC_PUBLIC_KEY", PUBLIC_KEY)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test.db")

    import importlib

    import hasl_calendar.app as app_mod
    import hasl_calendar.models as models_mod

    importlib.reload(models_mod)
    models_mod.init_db()
    importlib.reload(app_mod)

    app_mod.app.config["TESTING"] = True
    with app_mod.app.test_client() as c:
        yield c


@pytest.fixture
def auth():
    return {"Authorization": f"Bearer {_make_token()}"}


EVENTS = [
    {
        "id": "aaaa0000000000001",
        "date": "2099-01-01",
        "time": "21:00",
        "datetime_local": "2099-01-01T21:00:00",
        "timezone": "America/New_York",
        "location": "Sinatra Park",
        "league": "MEN'S REC LEAGUE",
        "home_team_slug": "home-fc",
        "home_team_name": "Home FC",
        "away_team_slug": "away-fc",
        "away_team_name": "Away FC",
    }
]


class TestAuth:
    def test_no_token_returns_401(self, client):
        assert client.get("/sync/state").status_code == 401

    def test_wrong_token_returns_401(self, client):
        assert (
            client.get(
                "/sync/state", headers={"Authorization": "Bearer notajwt"}
            ).status_code
            == 401
        )

    def test_expired_token_returns_401(self, client):
        token = _make_token(exp_delta=timedelta(seconds=-1))
        assert (
            client.get(
                "/sync/state", headers={"Authorization": f"Bearer {token}"}
            ).status_code
            == 401
        )

    def test_correct_token_returns_200(self, client, auth):
        assert client.get("/sync/state", headers=auth).status_code == 200


class TestSyncState:
    def test_empty_db_returns_empty_list(self, client, auth):
        resp = client.get("/sync/state", headers=auth)
        assert resp.json["game_ids"] == []

    def test_returns_ids_after_upsert(self, client, auth):
        client.post("/sync/upsert", json={"events": EVENTS}, headers=auth)
        resp = client.get("/sync/state", headers=auth)
        assert EVENTS[0]["id"] in resp.json["game_ids"]


class TestSyncUpsert:
    def test_upsert_returns_204(self, client, auth):
        resp = client.post("/sync/upsert", json={"events": EVENTS}, headers=auth)
        assert resp.status_code == 204

    def test_upserted_game_appears_in_state(self, client, auth):
        client.post("/sync/upsert", json={"events": EVENTS}, headers=auth)
        state = client.get("/sync/state", headers=auth).json["game_ids"]
        assert EVENTS[0]["id"] in state

    def test_upsert_is_idempotent(self, client, auth):
        client.post("/sync/upsert", json={"events": EVENTS}, headers=auth)
        client.post("/sync/upsert", json={"events": EVENTS}, headers=auth)
        state = client.get("/sync/state", headers=auth).json["game_ids"]
        assert state.count(EVENTS[0]["id"]) == 1


class TestSyncDelete:
    def test_deletes_future_game(self, client, auth):
        client.post("/sync/upsert", json={"events": EVENTS}, headers=auth)
        client.post("/sync/delete", json={"game_ids": [EVENTS[0]["id"]]}, headers=auth)
        state = client.get("/sync/state", headers=auth).json["game_ids"]
        assert EVENTS[0]["id"] not in state

    def test_does_not_delete_past_game(self, client, auth):
        past_event = {**EVENTS[0], "id": "past000000000001", "date": "2000-01-01"}
        client.post("/sync/upsert", json={"events": [past_event]}, headers=auth)
        client.post("/sync/delete", json={"game_ids": [past_event["id"]]}, headers=auth)
        state = client.get("/sync/state", headers=auth).json["game_ids"]
        assert past_event["id"] in state

    def test_delete_returns_204(self, client, auth):
        resp = client.post("/sync/delete", json={"game_ids": []}, headers=auth)
        assert resp.status_code == 204
