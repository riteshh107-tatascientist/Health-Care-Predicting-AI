"""Medical record library: validated uploads, private storage, download and deletion.

Every read and delete filters by the signed-in patient's id, so one patient can never open
another patient's file, even by guessing an identifier.
"""
from __future__ import annotations

import logging

import streamlit as st

import config
import ui
from database import add_record, delete_record, get_patient_by_user, list_records, log_action
from utils import (MIME_BY_EXT, delete_record_file, format_date, new_stored_name, read_record_file,
                   safe_display_name, save_record_file, validate_upload)

LOG = logging.getLogger("healthcarex.records")


def render(user: dict) -> None:
    ui.page_header("Medical Records", "Store reports, prescriptions and documents privately in one place.", "📁")
    patient = get_patient_by_user(user["id"])
    if not patient:
        st.warning("Your patient profile could not be found.")
        return
    tab_upload, tab_library = st.tabs(["⬆️ Upload a document", "🗂️ My library"])
    with tab_upload:
        _upload(patient, user)
    with tab_library:
        _library(patient, user)


def _upload(patient: dict, user: dict) -> None:
    st.caption(f"Accepted: PDF, PNG, JPEG · up to {config.MAX_UPLOAD_MB} MB. File content is checked, "
               "not just the file name.")
    with st.form("upload_form", clear_on_submit=True):
        uploaded = st.file_uploader("Choose a file", type=["pdf", "png", "jpg", "jpeg"])
        category = st.selectbox("Category", config.RECORD_CATEGORIES)
        description = st.text_input("Short description (optional)", max_chars=200)
        submitted = st.form_submit_button("Save to my library")
    if not submitted:
        return
    if uploaded is None:
        st.error("Please choose a file to upload.")
        return
    data = uploaded.getvalue()
    ok, message, ext = validate_upload(uploaded.name, data)
    if not ok:
        st.error(message)
        return
    stored = new_stored_name(ext)
    try:
        save_record_file(patient["id"], stored, data)
        add_record(patient["id"], safe_display_name(uploaded.name), stored, ext, len(data), category,
                   description.strip() or None)
    except Exception:
        LOG.exception("Record upload failed for patient %s", patient["id"])
        delete_record_file(patient["id"], stored)
        st.error("The document could not be saved. Please try again.")
        return
    log_action(user["id"], "record_uploaded", f"category={category}")
    st.success(f"Saved '{safe_display_name(uploaded.name)}' to your library.")


def _library(patient: dict, user: dict) -> None:
    records = list_records(patient["id"])
    total_mb = sum(r["size_bytes"] for r in records) / (1024 * 1024)
    c1, c2 = st.columns(2)
    c1.metric("Documents", len(records))
    c2.metric("Storage used", f"{total_mb:.2f} MB")
    if not records:
        ui.empty_state("Your library is empty. Upload a report or prescription to get started.")
        return
    by_category: dict[str, list[dict]] = {}
    for rec in records:
        by_category.setdefault(rec["category"], []).append(rec)
    for category, items in by_category.items():
        st.markdown(f"#### {category}")
        for rec in items:
            with st.expander(f"📄 {rec['original_name']} · {format_date(rec['uploaded_at'])}"):
                if rec["description"]:
                    st.write(rec["description"])
                data = read_record_file(patient["id"], rec["stored_name"])
                if data is None:
                    st.error("This file is no longer available on the server.")
                    continue
                if rec["file_ext"] in (".png", ".jpg"):
                    st.image(data, width=320)
                c1, c2 = st.columns(2)
                c1.download_button("Download", data=data, file_name=rec["original_name"],
                                   mime=MIME_BY_EXT.get(rec["file_ext"], "application/octet-stream"),
                                   key=f"dl_{rec['id']}")
                c2.button("Delete", key=f"del_{rec['id']}", on_click=_delete, args=(rec["id"], patient["id"], user["id"]))


def _delete(record_id: int, patient_id: int, user_id: int) -> None:
    stored = delete_record(record_id, patient_id)
    if stored:
        delete_record_file(patient_id, stored)
        log_action(user_id, "record_deleted", f"record {record_id}")
        st.toast("Document deleted.")
    else:
        st.toast("That document could not be found.")
