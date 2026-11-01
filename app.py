"""HealthCareX entry point: bootstrap, landing splash, authentication gate and role-based routing."""
from __future__ import annotations

import streamlit as st

# The very first frame: a lightweight splash, painted before the heavy imports below run.
st.set_page_config(page_title="HealthCareX", page_icon="✚", layout="wide", initial_sidebar_state="auto")
_EARLY_SPLASH = None
if not st.session_state.get("splash_done"):
    _EARLY_SPLASH = st.empty()
    _EARLY_SPLASH.markdown(
        "<div style='position:fixed;inset:0;z-index:99999;display:flex;align-items:center;justify-content:center;"
        "background:linear-gradient(135deg,#06213F 0%,#0E5E8C 55%,#0E9F9A 100%);color:#fff;font-family:sans-serif'>"
        "<div style='text-align:center'><div style='font-size:58px'>✚</div>"
        "<div style='font-size:30px;font-weight:700;letter-spacing:.02em'>HealthCareX</div>"
        "<div style='opacity:.85;margin-top:6px'>Compassionate Care. Smarter Healthcare. Better Patient Support.</div>"
        "<div style='opacity:.7;margin-top:22px;font-size:13px'>Preparing your secure workspace…</div></div></div>",
        unsafe_allow_html=True)

import config
import ui
from auth import current_user, logout
from database import init_db
from navigation import go_to, nav_options
from utils import setup_logging
from views import (admin, analyzer, appointments, auth_pages, dashboard, emergency, feedback, guidance, health_plan, home,
                   medications, profile, records, risk, services)

LOG = setup_logging()

PAGE_RENDERERS = {
    "home": home.render,
    "services": services.render,
    "appointments": appointments.render,
    "records": records.render,
    "analyzer": analyzer.render,
    "guidance": guidance.render,
    "risk": risk.render,
    "medications": medications.render,
    "dashboard": dashboard.render,
    "health_plan": health_plan.render,
    "profile": profile.render,
    "admin": admin.render,
    "feedback": feedback.render,
    "emergency": emergency.render,
}


@st.cache_resource(show_spinner=False)
def bootstrap() -> bool:
    """Create tables and seed reference data once per server process (idempotent)."""
    init_db()
    return True


def render_sidebar(user: dict) -> str:
    options = nav_options(user["role"])
    labels = [label for label, _ in options]
    if st.session_state.get("nav") not in labels:
        st.session_state["nav"] = labels[0]
    with st.sidebar:
        ui.sidebar_brand()
        st.radio("Navigate", labels, key="nav", label_visibility="collapsed")
        ui.sidebar_user_card(user)
        st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
        if user["role"] == "patient":
            b1, b2 = st.columns(2)
            b1.button("👤 Profile", key="side_profile", on_click=go_to, args=("profile", user["role"]))
            b2.button("🚪 Sign out", key="sign_out", on_click=logout)
        else:
            st.button("🚪 Sign out", key="sign_out", on_click=logout)
        if config.DEMO_ENABLED:
            st.markdown("<small>Demo data is labelled wherever it appears.</small>", unsafe_allow_html=True)
    return dict(options)[st.session_state["nav"]]


def main() -> None:
    ui.inject_css()
    # Landing animation first, so the user sees it while the database is prepared on first start.
    if _EARLY_SPLASH is not None:
        _EARLY_SPLASH.empty()
    if not st.session_state.get("splash_done"):
        ui.show_splash()
        st.session_state["splash_done"] = True
    try:
        bootstrap()
    except Exception:
        LOG.exception("Startup failed")
        st.error("The system could not start. Please refresh the page or try again shortly.")
        st.stop()

    user = current_user()
    if user is None:
        auth_pages.render()
        return
    if st.session_state.pop("login_toast", False):
        st.toast(f"Welcome back, {user['name']} 👋", icon="🏥")

    page = render_sidebar(user)
    try:
        PAGE_RENDERERS[page](user)
    except Exception:
        LOG.exception("Page '%s' failed for user %s", page, user.get("id"))
        st.error("Something went wrong while loading this page. Please try again.")
    ui.footer()


main()
