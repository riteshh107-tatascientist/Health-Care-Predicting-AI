import numpy as np
import pytest

from ml.train import (COLUMNS, FEATURES, ZeroToNaN, build_pipeline, dataset_summary, load_dataset,
                      predict_probability, train_and_evaluate)


@pytest.fixture(scope="module")
def bundle():
    return train_and_evaluate(load_dataset())


def test_real_dataset_shape_and_values():
    df = load_dataset()
    assert list(df.columns) == COLUMNS
    assert len(df) == 768
    assert set(df["Outcome"].unique()) == {0, 1}
    summary = dataset_summary(df)
    assert summary["positive_cases"] == 268 and summary["negative_cases"] == 500


def test_zero_to_nan_transformer_marks_only_listed_columns():
    X = np.array([[1.0, 0.0, 0.0], [2.0, 5.0, 0.0]])
    out = ZeroToNaN(column_indices=(1,)).fit_transform(X)
    assert np.isnan(out[0, 1]) and out[0, 2] == 0.0 and out[1, 1] == 5.0


def test_pipeline_has_no_leakage_structure():
    pipe = build_pipeline("Logistic Regression")
    assert [name for name, _ in pipe.steps] == ["zero_to_nan", "impute", "scale", "model"]


def test_evaluation_outputs_are_valid(bundle):
    assert bundle["split"]["train_rows"] == 614 and bundle["split"]["test_rows"] == 154
    for name in ("Logistic Regression", "Random Forest"):
        m = bundle["test"][name]
        for key in ("accuracy", "precision", "recall", "f1", "roc_auc"):
            assert 0.0 <= m[key] <= 1.0
        assert m["roc_auc"] > 0.7
        assert len(m["confusion"]) == 2 and sum(map(sum, m["confusion"])) == 154
        assert bundle["cv"][name]["roc_auc_mean"] > 0.7


def test_baseline_is_majority_class(bundle):
    assert abs(bundle["baseline_accuracy"] - 0.649) < 0.01


def test_best_model_selected_on_cv_not_test(bundle):
    best = max(bundle["cv"], key=lambda n: bundle["cv"][n]["roc_auc_mean"])
    assert bundle["best_model"] == best


def test_prediction_returns_probability(bundle):
    pipe = bundle["models"][bundle["best_model"]]
    values = {"Pregnancies": 2, "Glucose": 130, "BloodPressure": 80, "SkinThickness": 25, "Insulin": 0,
              "BMI": 31.5, "DiabetesPedigreeFunction": 0.5, "Age": 45}
    p = predict_probability(pipe, values)
    assert 0.0 <= p <= 1.0
    assert set(values) == set(FEATURES)


def test_higher_risk_profile_scores_higher(bundle):
    pipe = bundle["models"][bundle["best_model"]]
    low = {"Pregnancies": 0, "Glucose": 85, "BloodPressure": 66, "SkinThickness": 29, "Insulin": 0,
           "BMI": 22.0, "DiabetesPedigreeFunction": 0.2, "Age": 24}
    high = {"Pregnancies": 6, "Glucose": 170, "BloodPressure": 92, "SkinThickness": 35, "Insulin": 300,
            "BMI": 38.0, "DiabetesPedigreeFunction": 1.2, "Age": 60}
    assert predict_probability(pipe, high) > predict_probability(pipe, low)


def test_missing_dataset_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_dataset(tmp_path / "nope.csv")
