from __future__ import annotations

import os
import secrets
import time

from fastapi import HTTPException, Request

_WINDOW = 15 * 60
_LIMIT = 5
_ATTEMPTS: dict[str, list[float]] = {}


def credentials() -> tuple[str, str] | None:
    user = os.environ.get("SITE_ADMIN_USER", "").strip()
    password = os.environ.get("SITE_ADMIN_PASSWORD", "")
    if not user or not password:
        return None
    return user, password


def check_credentials(username: str, password: str) -> bool:
    expected = credentials()
    if not expected:
        return False
    user, secret = expected
    return secrets.compare_digest(username, user) and secrets.compare_digest(password, secret)


def _key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def allowed(request: Request) -> bool:
    now = time.time()
    attempts = [t for t in _ATTEMPTS.get(_key(request), []) if now - t < _WINDOW]
    _ATTEMPTS[_key(request)] = attempts
    return len(attempts) < _LIMIT


def record_failure(request: Request) -> None:
    _ATTEMPTS.setdefault(_key(request), []).append(time.time())


def reset(request: Request) -> None:
    _ATTEMPTS.pop(_key(request), None)


def ensure_csrf(request: Request) -> str:
    token = request.session.get("csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf"] = token
    return token


def verify_csrf(request: Request, token: str | None) -> None:
    expected = request.session.get("csrf")
    if not expected or not token or not secrets.compare_digest(str(expected), str(token)):
        raise HTTPException(status_code=400, detail="invalid CSRF token")


def current_user(request: Request) -> str | None:
    user = request.session.get("user")
    return str(user) if user else None


def require_user(request: Request) -> str:
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/admin/login"})
    return user
