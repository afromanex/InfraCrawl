import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from infracrawl.api.auth import require_admin


def _creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_require_admin_fails_closed_when_admin_token_missing(monkeypatch):
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)

    with pytest.raises(HTTPException) as e:
        require_admin(_creds("anything"))

    assert e.value.status_code == 503


def test_require_admin_rejects_wrong_token(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "secret")

    with pytest.raises(HTTPException) as e:
        require_admin(_creds("wrong"))

    assert e.value.status_code == 401


def test_require_admin_allows_correct_token(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "secret")

    assert require_admin(_creds("secret")) is True
