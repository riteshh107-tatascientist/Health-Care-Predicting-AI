import config
import database as dbm
from auth import SESSION_KEY, authenticate, current_user, login_user, logout
from security import hash_password, password_problems, verify_password


def test_password_hash_roundtrip_and_no_plaintext():
    stored = hash_password("Sup3rSecret")
    assert stored != "Sup3rSecret"
    assert verify_password("Sup3rSecret", stored)
    assert not verify_password("wrong", stored)
    assert not verify_password("x", "not-a-hash")


def test_password_policy():
    assert password_problems("short1") == ["at least 8 characters"]
    assert "at least one number" in password_problems("lettersonly")
    assert "at least one letter" in password_problems("12345678")
    assert password_problems("GoodPass1") == []


def test_admin_login_success_and_failure(db):
    state = {}
    user, err = authenticate(config.ADMIN_EMAIL, config.ADMIN_PASSWORD, state=state, now=1000)
    assert user and err is None and user["role"] == "admin"
    user, err = authenticate(config.ADMIN_EMAIL, "nope", state=state, now=1001)
    assert user is None and "Invalid" in err


def test_lockout_after_repeated_failures(db):
    state = {}
    for i in range(config.MAX_LOGIN_ATTEMPTS):
        authenticate(config.ADMIN_EMAIL, "bad", state=state, now=2000 + i)
    user, err = authenticate(config.ADMIN_EMAIL, config.ADMIN_PASSWORD, state=state, now=2010)
    assert user is None and "Too many failed attempts" in err


def test_disabled_account_cannot_sign_in(db):
    uid = dbm.create_user("Disabled", "disabled@example.com", hash_password("Passw0rd!"), "staff")
    dbm.set_user_active(uid, False)
    user, err = authenticate("disabled@example.com", "Passw0rd!", state={}, now=5000)
    assert user is None and "disabled" in err


def test_session_login_logout_and_timeout(db):
    state = {}
    user, _ = authenticate(config.ADMIN_EMAIL, config.ADMIN_PASSWORD, state=state, now=100)
    login_user(user, state=state, now=100)
    assert current_user(state=state, now=200)["role"] == "admin"
    # idle beyond the timeout (measured from last activity at t=200) ends the session
    later = 200 + config.SESSION_TIMEOUT_MINUTES * 60 + 5
    assert current_user(state=state, now=later) is None
    assert SESSION_KEY not in state


def test_logout_clears_session_and_navigation(db):
    state = {"nav": "x", "welcome_pending": True}
    user, _ = authenticate(config.ADMIN_EMAIL, config.ADMIN_PASSWORD, state={}, now=1)
    login_user(user, state=state, now=1)
    logout(state=state)
    assert SESSION_KEY not in state and "nav" not in state


def test_inactive_user_session_is_dropped(db):
    uid = dbm.create_user("Temp", "temp@example.com", hash_password("Passw0rd!"), "staff")
    state = {}
    login_user({"id": uid, "name": "Temp", "email": "temp@example.com", "role": "staff"}, state=state, now=10)
    dbm.set_user_active(uid, False)
    assert current_user(state=state, now=11) is None
