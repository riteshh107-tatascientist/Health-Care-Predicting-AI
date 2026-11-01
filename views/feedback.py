"""Feedback and support: anyone submits; patients see their own history; staff and admin resolve."""
from __future__ import annotations

import streamlit as st

import config
import ui
from database import add_feedback, list_all_feedback, list_own_feedback, log_action, update_feedback
from utils import clean_text, format_date


def render(user: dict) -> None:
    ui.page_header("Feedback & Support", "Tell us about a service complaint, technical issue or general query.", "💬")
    role = user["role"]
    if role in ("staff", "admin"):
        tab_desk, tab_submit = st.tabs(["🗂️ Feedback desk", "✍️ Submit feedback"])
        with tab_desk:
            _desk(user)
        with tab_submit:
            _submit(user)
    else:
        tab_submit, tab_history = st.tabs(["✍️ Submit feedback", "🗂️ My submissions"])
        with tab_submit:
            _submit(user)
        with tab_history:
            _history(user)


def _submit(user: dict) -> None:
    with st.form("feedback_form", clear_on_submit=True):
        category = st.selectbox("Category", config.FEEDBACK_CATEGORIES)
        message = st.text_area("Your message", height=150, max_chars=1500,
                               placeholder="Please describe what happened, where, and what you expected.")
        submitted = st.form_submit_button("Send to HealthCareX support")
    if submitted:
        text = clean_text(message, 1500)
        if len(text) < 10:
            st.error("Please provide a little more detail (at least 10 characters).")
        else:
            add_feedback(user["id"], category, text)
            log_action(user["id"], "feedback_submitted", category)
            st.success("Thank you. Your message has been received and will be reviewed by our team.")


def _history(user: dict) -> None:
    rows = list_own_feedback(user["id"])
    if not rows:
        ui.empty_state("You have not submitted any feedback yet.")
    for fb in rows:
        status_css = fb["status"].replace(" ", "-")
        st.markdown(f"**{fb['category']}** · {format_date(fb['created_at'])} "
                    f"<span class='hx-status-{status_css}'>{fb['status'].title()}</span>", unsafe_allow_html=True)
        st.write(fb["message"])
        if fb["response"]:
            st.info(f"Response from HealthCareX: {fb['response']}")
        st.markdown("---")


def _desk(user: dict) -> None:
    status = st.selectbox("Filter by status", ["All"] + list(config.FEEDBACK_STATUSES), key="fb_filter")
    rows = list_all_feedback(None if status == "All" else status)
    if not rows:
        ui.empty_state("No feedback matches this filter.")
        return
    st.dataframe([{"ID": r["id"], "From": r["name"], "Role": r["role"], "Category": r["category"],
                   "Status": r["status"], "Date": format_date(r["created_at"])} for r in rows], hide_index=True)
    st.markdown("#### Update a submission")
    labels = {f"#{r['id']} · {r['category']} · {r['name']}": r for r in rows}
    chosen = labels[st.selectbox("Submission", list(labels), key="fb_pick")]
    st.write(chosen["message"])
    c1, c2 = st.columns(2)
    new_status = c1.selectbox("Status", config.FEEDBACK_STATUSES,
                              index=config.FEEDBACK_STATUSES.index(chosen["status"]), key="fb_status")
    response = c2.text_area("Response to the submitter (optional)", value=chosen["response"] or "", key="fb_response")
    if st.button("Save update", key="fb_save"):
        update_feedback(chosen["id"], new_status, clean_text(response, 1000) or None)
        log_action(user["id"], "feedback_updated", f"feedback {chosen['id']} -> {new_status}")
        st.success("Updated.")
        st.rerun()
