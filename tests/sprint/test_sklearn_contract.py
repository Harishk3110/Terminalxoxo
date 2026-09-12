"""Exercise the real pinned library surface behind the local research stubs."""

import io
from collections.abc import Callable
from typing import BinaryIO

import joblib
import numpy as np
import pandas as pd
import pytest
from app.model_lab import ModelSettings, estimator
from app.model_results import ModelName
from sklearn.base import clone
from sklearn.metrics import (
    accuracy_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    roc_auc_score,
)
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


@pytest.mark.parametrize(
    "name",
    [
        "LINEAR",
        "LOGISTIC",
        "RIDGE",
        "LASSO",
        "ELASTIC_NET",
        "TREE",
        "FOREST",
        "GRADIENT_BOOSTING",
        "ENSEMBLE",
        "KMEANS",
    ],
)
def test_real_pipeline_scaler_clone_prediction_and_artifact_contract(name: ModelName) -> None:
    x = pd.DataFrame(
        {
            "trend": np.arange(120, dtype=np.float64),
            "cycle": np.tile([-2.0, -1.0, 0.0, 1.0, 2.0], 24),
        }
    )
    returns = pd.Series(np.sin(np.arange(120) / 4))
    target = (returns > 0).astype(int) if name == "LOGISTIC" else returns
    model = estimator(ModelSettings(model=name, trees=10, depth=3))
    assert isinstance(model, Pipeline)
    assert model.fit(x.iloc[:90], target.iloc[:90]) is model
    scaler = model.steps[0][1]
    assert isinstance(scaler, StandardScaler)
    np.testing.assert_array_equal(scaler.mean_, np.array([44.5, 0.0]))
    assert scaler.scale_ is not None and np.isfinite(scaler.scale_).all()
    held_out = model.predict(x.iloc[90:])
    assert held_out.shape == (30,) and np.isfinite(held_out).all()
    assert held_out.dtype == (
        np.dtype(np.int32)
        if name == "KMEANS"
        else np.dtype(np.int64)
        if name == "LOGISTIC"
        else np.dtype(np.float64)
    )
    if name == "LOGISTIC":
        probabilities = model.predict_proba(x.iloc[90:])
        assert probabilities.shape == (30, 2) and probabilities.dtype == np.float64
        assert ((probabilities >= 0) & (probabilities <= 1)).all()
        np.testing.assert_allclose(probabilities.sum(axis=1), 1, rtol=0, atol=np.finfo(float).eps)
        np.testing.assert_array_equal(probabilities.argmax(axis=1), held_out)
    elif name == "KMEANS":
        assert set(held_out) <= {0, 1, 2}
    copied = clone(model)
    assert isinstance(copied, Pipeline) and copied is not model
    assert copied.steps[0][1] is not scaler
    assert not hasattr(copied.steps[0][1], "mean_")
    copied.fit(x.iloc[:90], target.iloc[:90])
    np.testing.assert_array_equal(copied.predict(x.iloc[90:]), held_out)
    stream = io.BytesIO()
    # Independently check the runtime return, rather than assuming the stub is correct.
    dump_to_stream: Callable[[object, BinaryIO], object] = joblib.dump
    assert dump_to_stream({"model": model, "features": list(x.columns)}, stream) is None
    assert stream.getvalue()
    np.testing.assert_array_equal(scaler.mean_, np.array([44.5, 0.0]))


def test_real_walk_forward_indices_are_chronological_and_purged() -> None:
    x = pd.DataFrame({"value": np.arange(120, dtype=np.float64)})
    splits = list(TimeSeriesSplit(n_splits=3, gap=6).split(x))
    assert len(splits) == 3
    for fold, (train, test) in enumerate(splits):
        assert train.dtype == np.int64 and test.dtype == np.int64
        np.testing.assert_array_equal(train, np.arange(0, 24 + 30 * fold))
        np.testing.assert_array_equal(test, np.arange(30 + 30 * fold, 60 + 30 * fold))
        assert test[0] - train[-1] - 1 == 6


def test_real_scalar_metric_defaults_match_independent_arithmetic() -> None:
    assert accuracy_score([0, 1, 1, 0], [0, 1, 0, 1]) == 0.5
    assert roc_auc_score([0, 1, 0, 1], [0.1, 0.9, 0.2, 0.8]) == 1
    assert mean_absolute_error([1, 2, 3], [1, 2, 4]) == 1 / 3
    assert mean_squared_error([1, 2, 3], [1, 2, 4]) == 1 / 3
    assert r2_score([1, 2, 3], [1, 2, 4]) == 0.5
