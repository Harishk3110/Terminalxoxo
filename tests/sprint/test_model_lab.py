import numpy as np
import pandas as pd
import pytest
from app.model_lab import ModelSettings, features_and_target, model_research


def bars():
    rng = np.random.default_rng(3110)
    close = 100 * np.cumprod(1 + rng.normal(0.0003, 0.008, 450))
    return pd.DataFrame(
        {"open": close * 0.999, "high": close * 1.01, "low": close * 0.99, "close": close},
        index=pd.bdate_range("2024-01-01", periods=len(close)),
    )


def test_feature_pipeline_cannot_see_future_and_target_starts_next_open() -> None:
    frame = bars()
    x, y = features_and_target(frame, 5)
    changed = frame.copy()
    changed.iloc[300:] *= 2
    other, _ = features_and_target(changed, 5)
    pd.testing.assert_frame_equal(x.loc[: frame.index[299]], other.loc[: frame.index[299]])
    assert y.loc[frame.index[100]] == pytest.approx(frame.open.iloc[106] / frame.open.iloc[101] - 1)


@pytest.mark.parametrize("model", ["RIDGE", "LOGISTIC", "FOREST", "KMEANS"])
def test_chronological_models_purge_labels_and_produce_artifacts(model):
    result, artifact = model_research(bars(), ModelSettings(model=model, trees=10))
    assert artifact and len(result["walk_forward"]) == 3
    train, validation, test = result["metrics"]
    assert train["end"] < validation["start"] < validation["end"] < test["start"]
    assert {row["partition"] for row in result["predictions"]} == {"TRAIN", "VALIDATION", "TEST"}
    for fold in result["walk_forward"]:
        assert fold["train_end"] < fold["test_start"] and fold["gap"] == 6


def test_no_random_holdout_refit_and_deterministic_predictions() -> None:
    frame = bars()
    first, _ = model_research(frame, ModelSettings(trees=10))
    repeat, _ = model_research(frame, ModelSettings(trees=10))
    assert first == repeat
    changed = frame.copy()
    changed.iloc[-20:] *= 1.5
    second, _ = model_research(changed, ModelSettings(trees=10))
    assert first["feature_importance"] == second["feature_importance"]


def test_short_history_rejected() -> None:
    with pytest.raises(ValueError, match="240"):
        model_research(bars().iloc[:200], ModelSettings())
