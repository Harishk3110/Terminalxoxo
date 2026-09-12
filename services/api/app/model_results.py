"""Model research evidence, distinct from trading and portfolio performance."""

from typing import Literal, TypedDict

from pydantic import JsonValue

from .backtest_results import SimulationResult
from .quant_data import DatasetProvenance

type ModelName = Literal[
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
]
type Partition = Literal["TRAIN", "VALIDATION", "TEST"]


class PartitionWindow(TypedDict):
    partition: Partition
    start: str
    end: str
    observations: int


class RegressionMetrics(PartitionWindow):
    r_squared: float
    rmse: float
    mae: float
    rank_ic: float | None


class ClassificationMetrics(PartitionWindow):
    accuracy: float
    auc: float | None


class ClusterMetrics(PartitionWindow):
    state: Literal["CLUSTER ASSIGNMENT"]
    clusters: int
    r_squared: None
    rmse: None


class ModelPrediction(TypedDict):
    date: str
    partition: Partition
    prediction: float
    actual: float
    probability: float | None


class AvailableFold(TypedDict):
    fold: int
    state: Literal["AVAILABLE"]
    train_end: str
    test_start: str
    test_end: str
    training_observations: int
    test_observations: int
    gap: int
    rmse: float | None
    accuracy: float | None


class InsufficientClassesFold(TypedDict):
    fold: int
    state: Literal["INSUFFICIENT_CLASSES"]


class FeatureImportance(TypedDict):
    feature: str
    value: float


class ModelResearchResult(TypedDict):
    model: ModelName
    settings: dict[str, JsonValue]
    feature_version: str
    target_version: str
    features: list[str]
    metrics: list[RegressionMetrics | ClassificationMetrics | ClusterMetrics]
    predictions: list[ModelPrediction]
    walk_forward: list[AvailableFold | InsufficientClassesFold]
    feature_importance: list[FeatureImportance]
    review_state: Literal["RESEARCH"]
    calculation_version: str
    warnings: list[str]


class PartitionBacktest(SimulationResult):
    partition: Literal["VALIDATION", "TEST"]
    currency: str | None
    signal_policy: str


class StoredModelArtifact(TypedDict):
    object_key: str
    content_hash: str
    size_bytes: int
    format: str


class ModelRunResult(ModelResearchResult):
    cost_backtests: list[PartitionBacktest]
    inputs: DatasetProvenance
    source: str
    quality: str
    as_of: str
    artifact: StoredModelArtifact
