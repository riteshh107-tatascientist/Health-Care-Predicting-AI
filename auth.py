"""Session-based authentication with lockout, idle timeout and role checks.

Functions accept an optional `state` mapping so they can be unit-tested without a Streamlit
server. In the app they use st.session_state.
"""
from __future__ import annotations

import time
from typing import Any, MutableMapping

import streamlit as st

import config
from database import get_user_by_email, get_user_by_id, log_action
from security import verify_password

SESSION_KEY = "auth_user"


def _state(state: MutableMapping | None) -> MutableMapping:
    return st.session_state if state is None else state


def authenticate(email: str, password: str, state: MutableMapping | None = None,
                 now: float | None = None) -> tuple[dict | None, str | None]:
    state = _state(state)
    now = time.time() if now is None else now
    locked_until = state.get("locked_until", 0)
    if now < locked_until:
        return None, f"Too many failed attempts. Please wait {int(locked_until - now)} seconds and try again."
    user = get_user_by_email(email) if email else None
    if user and verify_password(password, user["password_hash"]):
        if not user["is_active"]:
            return None, "This account is currently disabled. Please contact the front desk."
        state["failed_attempts"] = 0
        return user, None
    attempts = state.get("failed_attempts", 0) + 1
    state["failed_attempts"] = attempts
    if attempts >= config.MAX_LOGIN_ATTEMPTS:
        state["locked_until"] = now + config.LOCKOUT_SECONDS
        state["failed_attempts"] = 0
    log_action(user["id"] if user else None, "login_failed", "invalid credentials")
    return None, "Invalid email or password."


def login_user(user: dict, state: MutableMapping | None = None, now: float | None = None) -> None:
    state = _state(state)
    state[SESSION_KEY] = {
        "id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"],
        "last_seen": time.time() if now is None else now,
    }
    log_action(user["id"], "login", "session started")


def logout(reason: str = "logout", state: MutableMapping | None = None) -> None:
    state = _state(state)
    data = state.pop(SESSION_KEY, None)
    if data:
        log_action(data["id"], "logout", reason)
    for key in ("nav", "welcome_pending", "booking_prefill"):
        state.pop(key, None)


def current_user(state: MutableMapping | None = None, now: float | None = None) -> dict | None:
    """Return the signed-in user, enforcing idle timeout and re-checking account status."""
    state = _state(state)
    data: dict[str, Any] | None = state.get(SESSION_KEY)
    if not data:
        return None
    now = time.time() if now is None else now
    if now - data.get("last_seen", 0) > config.SESSION_TIMEOUT_MINUTES * 60:
        logout("idle timeout", state)
        return None
    fresh = get_user_by_id(data["id"])
    if not fresh or not fresh["is_active"]:
        logout("account inactive", state)
        return None
    data.update({"name": fresh["name"], "role": fresh["role"], "last_seen": now})
    return dict(data)


def require_role(user: dict, roles: tuple[str, ...]) -> bool:
    if user.get("role") in roles:
        return True
    st.error("You do not have permission to open this page.")
    return False
