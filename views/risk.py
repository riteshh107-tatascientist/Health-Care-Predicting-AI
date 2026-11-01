"""Diabetes-risk education on the real Pima Indians Diabetes dataset.

Shows preprocessing, cross-validated model selection, held-out test metrics, baseline comparison,
confusion matrix, ROC curve and feature importance. Every output is labelled as an educational
estimate, not a clinical diagnosis.
"""
from __future__ import annotations

import logging

import numpy as np
import plotly.graph_objects as go
import streamlit as st

import config
import ui
from ml.train import FEATURES, load_dataset, predict_probability, train_and_evaluate

LOG = logging.getLogger("healthcarex.risk")


@st.cache_resource(show_spinner="Training educational models on the Pima Indians Diabetes dataset…")
def get_model_bundle() -> dict:
    return train_and_evaluate(load_dataset())


def render(user: dict) -> None:
    ui.page_header("Diabetes Risk Assessment", "Educational ML demonstration built on a real public clinical dataset.", "📊")
    ui.disclaimer(config.DISCLAIMER_ML + " " + config.DISCLAIMER_GENERAL)
    try:
        bundle = get_model_bundle()
    except Exception:
        LOG.exception("Model training failed")
        st.error("The educational model could not be loaded right now. Please try again later.")
        return

    tab_predict, tab_perf, tab_data = st.tabs(["🔮 Estimate", "📈 Model performance", "🧾 Dataset & method"])
    with tab_predict:
        _predict(bundle)
    with tab_perf:
        _performance(bundle)
    with tab_data:
        _dataset(bundle)


def _predict(bundle: dict) -> None:
    st.caption("Enter values from a recent measurement. 0 means 'not measured' and is handled as missing data.")
    with st.form("risk_form"):
        c1, c2, c3, c4 = st.columns(4)
        pregnancies = c1.slider("Pregnancies", 0, 17, 1)
        age = c2.slider("Age (years)", 21, 81, 35)
        glucose = c3.slider("Plasma glucose (mg/dL)", 40, 250, 110)
        bp = c4.slider("Diastolic blood pressure (mmHg)", 40, 130, 72)
        c5, c6, c7 = st.columns(3)
        skin = c5.slider("Triceps skin fold (mm)", 0, 100, 20)
        insulin_known = c6.checkbox("Insulin measured", value=False)
        insulin = c6.slider("2-hour serum insulin (µU/mL)", 15, 900, 90, disabled=not insulin_known)
        bmi = c7.slider("BMI (kg/m²)", 15.0, 60.0, 27.0, step=0.1)
        dpf = st.slider("Diabetes pedigreefunction (family history score)", 0.05, 2.50, 0.40, step=0.01)
        submitted = st.form_submit_button("Estimate")
    if not submitted:
        return
    values = {
        "Pregnancies": pregnancies, "Glucose": glucose, "BloodPressure": bp, "SkinThickness": skin,
        "Insulin": insulin if insulin_known else 0, "BMI": bmi,
        "DiabetesPedigreeFunction": dpf, "Age": age,
    }
    best = bundle["best_model"]
    probability = predict_probability(bundle["models"][best], values)
    label = "Positive pattern" if probability >= 0.5 else "Negative pattern"
    st.markdown("---")
    c1, c2 = st.columns([1, 2])
    c1.metric("Model probability", f"{probability:.0%}")
    c2.markdown(f"**Model output at 0.5 threshold:** {label}  \nModel used: **{best}** (selected by cross-validation on training data only).")
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=probability * 100,
        gauge={"axis": {"range": [0, 100]}, "bar": {"color": "#0f9b8e"},
               "steps": [{"range": [0, 30], "color": "#dcfce7"}, {"range": [30, 60], "color": "#fef3c7"},
                         {"range": [60, 100], "color": "#fee2e2"}]},
        title={"text": "Estimated probability (%)"}))
    fig.update_layout(height=260, margin=dict(l=20, r=20, t=40, b=10))
    st.plotly_chart(fig)
    ui.disclaimer("Educational ML estimate — not a clinical diagnosis. A probability from this model does not "
                  "establish whether anyone has diabetes. Only a clinician using proper tests can do that.")


def _performance(bundle: dict) -> None:
    st.markdown("#### Cross-validation on training data (model selection)")
    cv_rows = [{"Model": name, "ROC-AUC (mean)": round(v["roc_auc_mean"], 3),
                "ROC-AUC (± std)": round(v["roc_auc_std"], 3), "F1 (mean)": round(v["f1_mean"], 3),
                "Recall (mean)": round(v["recall_mean"], 3)} for name, v in bundle["cv"].items()]
    st.table(cv_rows)
    st.markdown("#### Held-out test set (reported once)")
    test_rows = []
    for name, m in bundle["test"].items():
        test_rows.append({"Model": name, "Accuracy": round(m["accuracy"], 3), "Precision": round(m["precision"], 3),
                          "Recall": round(m["recall"], 3), "F1": round(m["f1"], 3),
                          "ROC-AUC": round(m["roc_auc"], 3), "Brier score (lower is better)": round(m["brier"], 3)})
    st.table(test_rows)
    st.info(f"Baseline that always predicts the majority class scores **{bundle['baseline_accuracy']:.1%} accuracy**. "
            "Accuracy alone can look good on imbalanced data, so recall, F1 and ROC-AUC matter here too.")
    st.success(f"Selected model: **{bundle['best_model']}** (highest cross-validated ROC-AUC on the training split).")

    left, right = st.columns(2)
    with left:
        st.markdown("#### Confusion matrix (test set, threshold 0.5)")
        cm = np.array(bundle["test"][bundle["best_model"]]["confusion"])
        fig = go.Figure(go.Heatmap(z=cm, x=["Predicted negative", "Predicted positive"],
                                   y=["Actual negative", "Actual positive"], text=cm, texttemplate="%{text}",
                                   colorscale="Teal", showscale=False))
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig)
    with right:
        st.markdown("#### ROC curve (test set)")
        fig = go.Figure()
        for name, m in bundle["test"].items():
            fig.add_trace(go.Scatter(x=m["fpr"], y=m["tpr"], mode="lines", name=f"{name} (AUC {m['roc_auc']:.2f})"))
        fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Chance", line=dict(dash="dash", color="#94a3b8")))
        fig.update_layout(height=320, xaxis_title="False positive rate", yaxis_title="True positive rate",
                          margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.3))
        st.plotly_chart(fig)

    st.markdown("#### Feature importance")
    imp = bundle["importance"][bundle["best_model"]]
    ordered = sorted(imp.items(), key=lambda kv: kv[1])
    fig = go.Figure(go.Bar(x=[v for _, v in ordered], y=[k for k, _ in ordered], orientation="h",
                           marker_color="#0f9b8e"))
    method = ("Relative magnitude of standardised logistic-regression coefficients"
              if bundle["best_model"] == "Logistic Regression" else "Random-forest impurity importance")
    fig.update_layout(height=340, xaxis_title=method, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig)
    st.caption("Importance shows what the model relied on, not what causes diabetes.")


def _dataset(bundle: dict) -> None:
    ds = bundle["dataset"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Records", ds["rows"])
    c2.metric("Positive cases", ds["positive_cases"])
    c3.metric("Negative cases", ds["negative_cases"])
    st.markdown(
        "**Source:** Pima Indians Diabetes Database, National Institute of Diabetes and Digestive and Kidney "
        "Diseases, distributed through the UCI Machine Learning Repository. It contains 768 women aged 21 and over "
        "of Pima Indian heritage. Results may not generalise to other populations, sexes or ages."
    )
    st.markdown("**Physiologically impossible zeros treated as missing (median-imputed inside the pipeline):**")
    st.table([{"Column": k, "Zero values": v} for k, v in ds["zero_values_treated_as_missing"].items()])
    st.markdown(
        f"**Split:** {bundle['split']['train_rows']} training / {bundle['split']['test_rows']} test rows, "
        "stratified by outcome, random_state=42.  \n"
        "**Leakage control:** imputation, scaling and class weighting are fitted inside each pipeline on training "
        "folds only. The test set is used once for the final report."
    )
    st.markdown("**Feature list:** " + ", ".join(FEATURES))
