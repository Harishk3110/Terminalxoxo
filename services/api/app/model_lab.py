"""Chronological supervised research with fitted-on-train transforms and purged labels."""

from __future__ import annotations

import io
from typing import Literal

import joblib
import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field
from sklearn.base import clone
from sklearn.cluster import KMeans
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor, VotingRegressor
from sklearn.linear_model import ElasticNet, Lasso, LinearRegression, LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    roc_auc_score,
)
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeRegressor


class ModelSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: Literal[
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
    ] = "RIDGE"
    horizon: int = Field(default=5, ge=1, le=21)
    regularisation: float = Field(default=1, gt=0, le=100, allow_inf_nan=False)
    train_fraction: float = Field(default=0.6, ge=0.4, le=0.7, allow_inf_nan=False)
    validation_fraction: float = Field(default=0.2, ge=0.1, le=0.2, allow_inf_nan=False)
    folds: int = Field(default=3, ge=2, le=5)
    seed: int = Field(default=3110, ge=0, le=2147483647)
    trees: int = Field(default=100, ge=10, le=300)
    depth: int = Field(default=4, ge=2, le=12)
    fee_bps: float = Field(default=5, ge=0, le=500, allow_inf_nan=False)
    slippage_bps: float = Field(default=5, ge=0, le=500, allow_inf_nan=False)


def features_and_target(frame: pd.DataFrame, horizon: int):
    if not {"open", "high", "low", "close"} <= set(frame):
        raise ValueError("Model research requires complete OHLC bars")
    if not frame.index.is_unique or not frame.index.is_monotonic_increasing:
        raise ValueError("Model bars must be unique and chronological")
    prices = frame[["open", "high", "low", "close"]].astype(float)
    if not np.isfinite(prices).all().all() or (prices <= 0).any().any():
        raise ValueError("Model prices must be finite and positive; missing bars are not filled")
    if ((prices.high < prices.max(axis=1)) | (prices.low > prices.min(axis=1))).any():
        raise ValueError("Model OHLC bounds are inconsistent")
    close = prices.close
    daily = close.pct_change(fill_method=None)
    features = pd.DataFrame(
        {
            "return_1": daily,
            "momentum_5": close.pct_change(5, fill_method=None),
            "momentum_21": close.pct_change(21, fill_method=None),
            "volatility_21": daily.rolling(21).std(),
            "trend_20": close / close.rolling(20).mean() - 1,
            "range": (prices.high - prices.low) / close,
        },
        index=frame.index,
    )
    # A feature observed at today's close predicts a next-open to future-open return.
    target = prices.open.shift(-horizon - 1) / prices.open.shift(-1) - 1
    valid = features.notna().all(axis=1) & target.notna()
    return features.loc[valid], target.loc[valid]


def estimator(settings: ModelSettings):
    arguments = {"random_state": settings.seed}
    models_by_name = {
        "LINEAR": lambda: LinearRegression(),
        "LOGISTIC": lambda: LogisticRegression(
            C=1 / settings.regularisation, max_iter=2000, **arguments
        ),
        "RIDGE": lambda: Ridge(alpha=settings.regularisation),
        "LASSO": lambda: Lasso(alpha=settings.regularisation, max_iter=5000, **arguments),
        "ELASTIC_NET": lambda: ElasticNet(
            alpha=settings.regularisation, max_iter=5000, **arguments
        ),
        "TREE": lambda: DecisionTreeRegressor(
            max_depth=settings.depth, min_samples_leaf=5, **arguments
        ),
        "FOREST": lambda: RandomForestRegressor(
            n_estimators=settings.trees,
            max_depth=settings.depth,
            min_samples_leaf=5,
            n_jobs=1,
            **arguments,
        ),
        "GRADIENT_BOOSTING": lambda: GradientBoostingRegressor(
            n_estimators=settings.trees, max_depth=settings.depth, **arguments
        ),
        "ENSEMBLE": lambda: VotingRegressor(
            [
                ("ridge", Ridge(alpha=settings.regularisation)),
                (
                    "forest",
                    RandomForestRegressor(
                        n_estimators=settings.trees, max_depth=settings.depth, n_jobs=1, **arguments
                    ),
                ),
            ],
            n_jobs=1,
        ),
        "KMEANS": lambda: KMeans(n_clusters=3, n_init=10, **arguments),
    }
    return make_pipeline(StandardScaler(), models_by_name[settings.model]())


def model_research(frame: pd.DataFrame, settings: ModelSettings) -> tuple[dict, bytes]:
    if len(frame) > 5000:
        raise ValueError("Model research is bounded to 5,000 bars")
    x, target = features_and_target(frame, settings.horizon)
    count = len(x)
    if count < 240:
        raise ValueError("Model training requires at least 240 complete labelled observations")
    split1 = int(count * settings.train_fraction)
    split2 = int(count * (settings.train_fraction + settings.validation_fraction))
    gap = settings.horizon + 1
    splits = {
        "TRAIN": np.arange(0, split1 - gap),
        "VALIDATION": np.arange(split1, split2 - gap),
        "TEST": np.arange(split2, count),
    }
    if min(map(len, splits.values())) < 20:
        raise ValueError("Each chronological partition requires at least twenty observations")
    classification = settings.model == "LOGISTIC"
    clustering = settings.model == "KMEANS"
    y = (target > 0).astype(int) if classification else target
    fitted = estimator(settings)
    train = splits["TRAIN"]
    if classification and y.iloc[train].nunique() != 2:
        raise ValueError("Training labels require both return directions")
    fitted.fit(x.iloc[train], y.iloc[train])
    predictions, metrics = [], []
    for name, indices in splits.items():
        observed = y.iloc[indices]
        predicted = fitted.predict(x.iloc[indices])
        probabilities = fitted.predict_proba(x.iloc[indices])[:, 1] if classification else None
        metric = {
            "partition": name,
            "start": str(x.index[indices[0]]),
            "end": str(x.index[indices[-1]]),
            "observations": len(indices),
        }
        if clustering:
            metric.update(
                {
                    "state": "CLUSTER ASSIGNMENT",
                    "clusters": len(np.unique(predicted)),
                    "r_squared": None,
                    "rmse": None,
                }
            )
        elif classification:
            metric.update(
                {
                    "accuracy": float(accuracy_score(observed, predicted)),
                    "auc": float(roc_auc_score(observed, probabilities))
                    if observed.nunique() == 2
                    else None,
                }
            )
        else:
            metric.update(
                {
                    "r_squared": float(r2_score(observed, predicted)),
                    "rmse": float(np.sqrt(mean_squared_error(observed, predicted))),
                    "mae": float(mean_absolute_error(observed, predicted)),
                    "rank_ic": float(
                        pd.Series(observed.to_numpy()).rank().corr(pd.Series(predicted).rank())
                    )
                    if len(set(predicted)) > 1 and observed.nunique() > 1
                    else None,
                }
            )
        metrics.append(metric)
        predictions.extend(
            {
                "date": str(x.index[index]),
                "partition": name,
                "prediction": float(predicted[j]),
                "actual": float(target.iloc[index]),
                "probability": float(probabilities[j]) if probabilities is not None else None,
            }
            for j, index in enumerate(indices)
        )
    walk = []
    splitter = TimeSeriesSplit(n_splits=settings.folds, gap=gap)
    for fold, (train_indices, test_indices) in enumerate(splitter.split(x)):
        fold_model = clone(fitted)
        if classification and y.iloc[train_indices].nunique() != 2:
            walk.append({"fold": fold + 1, "state": "INSUFFICIENT_CLASSES"})
            continue
        fold_model.fit(x.iloc[train_indices], y.iloc[train_indices])
        pred = fold_model.predict(x.iloc[test_indices])
        walk.append(
            {
                "fold": fold + 1,
                "state": "AVAILABLE",
                "train_end": str(x.index[train_indices[-1]]),
                "test_start": str(x.index[test_indices[0]]),
                "test_end": str(x.index[test_indices[-1]]),
                "training_observations": len(train_indices),
                "test_observations": len(test_indices),
                "gap": gap,
                "rmse": float(np.sqrt(mean_squared_error(y.iloc[test_indices], pred)))
                if not (classification or clustering)
                else None,
                "accuracy": float(accuracy_score(y.iloc[test_indices], pred))
                if classification
                else None,
            }
        )
    final_model = fitted.steps[-1][1]
    values = getattr(final_model, "feature_importances_", None)
    if values is None and hasattr(final_model, "coef_"):
        values = np.asarray(final_model.coef_).reshape(-1)
    importance = (
        [{"feature": name, "value": float(values[i])} for i, name in enumerate(x.columns)]
        if values is not None and len(values) == len(x.columns)
        else []
    )
    artifact = io.BytesIO()
    joblib.dump(
        {
            "model": fitted,
            "features": list(x.columns),
            "settings": settings.model_dump(),
            "train_end": str(x.index[train[-1]]),
            "version": "knk-model-1.0",
        },
        artifact,
    )
    return {
        "model": settings.model,
        "settings": settings.model_dump(),
        "feature_version": "past-close-technical-1",
        "target_version": "next-open-forward-return-1",
        "features": list(x.columns),
        "metrics": metrics,
        "predictions": predictions,
        "walk_forward": walk,
        "feature_importance": importance,
        "review_state": "RESEARCH",
        "calculation_version": "knk-model-1.0 / scikit-learn 1.9.0",
        "warnings": [
            "Example research model, not an investment recommendation. No broker action is available.",
            "Scaler and model fit only the purged training partition; held-out validation and test predictions do not refit. Walk-forward is a separate expanding-window evaluation.",
            "Features use the current completed close; targets start at the next open. Split gaps purge the full forward label horizon.",
            "Reported prediction errors and rank correlation are not a cost-adjusted trading backtest. Overlapping labels, model selection and multiple testing remain review risks.",
        ],
    }, artifact.getvalue()
