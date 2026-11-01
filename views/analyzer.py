"""Medical report analyzer: PDF text extraction or pasted values, compared with reference ranges."""
from __future__ import annotations

import logging

import pandas as pd
import streamlit as st

import config
import ui
from database import get_patient_by_user
from lab_analysis import analyze_report
from utils import extract_pdf_text, validate_upload

LOG = logging.getLogger("healthcarex.analyzer")

SAMPLE = """Hemoglobin 13.9 g/dL (12.0 - 15.5)
Fasting glucose 104 mg/dL
HbA1c 6.1 %
Total cholesterol 228 mg/dL
LDL cholesterol 130 mg/dL
HDL cholesterol 45 mg/dL
Triglycerides 180 mg/dL
Serum creatinine 1.0 mg/dL
WBC 7.2 x10^9/L"""


def _load_sample() -> None:
    st.session_state["analyzer_text"] = SAMPLE


def render(user: dict) -> None:
    ui.page_header("Medical Report Analyzer", "Turn lab values into plain-language status, then discuss them with your clinician.", "🧪")
    ui.disclaimer(config.DISCLAIMER_GENERAL)
    ui.disclaimer("Reference ranges shown here are illustrative unless the value is stated with a range in your "
                  "report. Ranges differ between laboratories, age groups and methods.")

    patient = get_patient_by_user(user["id"]) or {}
    sex = (patient.get("gender") or "").lower()
    sex = sex if sex in ("male", "female") else None

    tab_file, tab_text = st.tabs(["📤 Upload a PDF or image", "📝 Paste report text"])
    extracted = ""
    with tab_file:
        uploaded = st.file_uploader("Lab report (PDF recommended)", type=["pdf", "png", "jpg", "jpeg"],
                                    key="analyzer_file")
        if uploaded is not None:
            data = uploaded.getvalue()
            ok, message, ext = validate_upload(uploaded.name, data)
            if not ok:
                st.error(message)
            elif ext == ".pdf":
                try:
                    extracted = extract_pdf_text(data)
                    if not extracted.strip():
                        st.warning("No text layer was found in this PDF. Please paste the values in the text tab.")
                    else:
                        st.success("Text read from your PDF. Press Analyze below.")
                except Exception:
                    LOG.exception("PDF text extraction failed")
                    st.error("We could not read this PDF. Please paste the values in the text tab.")
            else:
                st.info("Images are shown for reference. Automatic text reading from images is not included in this "
                        "lightweight build, so please paste the values in the text tab.")
                st.image(data, width=340)

    with tab_text:
        pasted = st.text_area("Paste lab values, one per line", height=190, placeholder=SAMPLE,
                              key="analyzer_text")
        st.button("Load sample report", key="load_sample", on_click=_load_sample)

    if st.button("Analyze report", type="primary"):
        source = pasted if pasted.strip() else extracted
        if not source.strip():
            st.error("Please upload a PDF or paste some report text first.")
            return
        rows = analyze_report(source, sex)
        _render_results(rows, sex)


def _render_results(rows: list[dict], sex: str | None) -> None:
    st.markdown("---")
    if not rows:
        st.warning("No recognised lab values were found. Try lines such as "
                   "'Hemoglobin 13.9 g/dL' or 'Fasting glucose 104 mg/dL'.")
        return
    within = sum(r["Status"] == "Within range" for r in rows)
    below = sum(r["Status"] == "Below range" for r in rows)
    above = sum(r["Status"] == "Above range" for r in rows)
    c1, c2, c3 = st.columns(3)
    c1.metric("✔ Within range", within)
    c2.metric("▼ Below range", below)
    c3.metric("▲ Above range", above)
    if sex is None:
        st.caption("Tip: set your gender in My Profile to use sex-specific reference ranges where they apply.")

    st.dataframe(pd.DataFrame(rows), hide_index=True)
    st.markdown("#### What this means")
    for r in rows:
        if r["Status"] == "Within range":
            icon, text = "✔", "is inside the reference range provided."
        elif r["Status"] == "Below range":
            icon, text = "▼", "is below the reference range provided."
        elif r["Status"] == "Above range":
            icon, text = "▲", "is above the reference range provided."
        else:
            icon, text = "•", "has no reference range available to compare against."
        st.markdown(f"**{icon} {r['Test']}: {r['Result']:g} {r['Unit']}** {text} "
                    f"*(Reference source: {r['Reference source']})*")
    st.markdown(
        '<div class="hx-note"><b>Next step:</b> A value outside a reference range is a prompt for a conversation, '
        'not a diagnosis. Please discuss these results with a qualified healthcare professional, who can consider '
        'your full history and the laboratory\'s own ranges.</div>', unsafe_allow_html=True)
