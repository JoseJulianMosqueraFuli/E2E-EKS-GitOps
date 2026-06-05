"""
Feast Feature Repository Configuration

Local development setup using SQLite for online store and Parquet for offline store.
For production, replace with Redis/DynamoDB backends.
"""

import os
from datetime import timedelta

from feast import Entity, Field, FeatureView, ValueType
from feast.types import Float64, Int64, String
from feast.infra.offline_stores.file_source import FileSource

# Base path for data sources (relative to this file)
_REPO_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(_REPO_DIR, "data")


def _data_path(filename: str) -> str:
    """Return absolute path to a data file in the repo data directory."""
    return os.path.join(_DATA_DIR, filename)


# Define the entity that all features share
user_entity = Entity(
    name="user_id",
    join_keys=["user_id"],
    value_type=ValueType.INT64,
    description="Unique identifier for the user/record",
)

# Offline data source for feature ingestion
transaction_stats_source = FileSource(
    path=_data_path("transaction_stats.parquet"),
    event_timestamp_column="event_timestamp",
)

# Feature View: transaction statistics (batch features)
transaction_stats_view = FeatureView(
    name="transaction_stats",
    entities=[user_entity],
    ttl=timedelta(days=1),
    schema=[
        Field(name="amount_mean", dtype=Float64),
        Field(name="amount_std", dtype=Float64),
        Field(name="transaction_count", dtype=Int64),
        Field(name="days_since_last", dtype=Float64),
    ],
    online=True,
    source=transaction_stats_source,
    tags={"team": "mlops", "domain": "fraud"},
)

# Feature View: user profile (batch features)
user_profile_source = FileSource(
    path=_data_path("user_profile.parquet"),
    event_timestamp_column="event_timestamp",
)

user_profile_view = FeatureView(
    name="user_profile",
    entities=[user_entity],
    ttl=timedelta(days=7),
    schema=[
        Field(name="age_group", dtype=String),
        Field(name="account_tenure_days", dtype=Int64),
        Field(name="has_premium", dtype=Int64),
        Field(name="engagement_score", dtype=Float64),
    ],
    online=True,
    source=user_profile_source,
    tags={"team": "mlops", "domain": "user"},
)

# Feature View: model-specific features generated from raw data
# These can be reused across multiple models
model_features_source = FileSource(
    path=_data_path("model_features.parquet"),
    event_timestamp_column="event_timestamp",
)

model_features_view = FeatureView(
    name="model_features",
    entities=[user_entity],
    ttl=timedelta(hours=6),
    schema=[
        Field(name="feature_1", dtype=Float64),
        Field(name="feature_2", dtype=Float64),
        Field(name="feature_3", dtype=Float64),
        Field(name="feature_4", dtype=Float64),
        Field(name="feature_5", dtype=Float64),
    ],
    online=True,
    source=model_features_source,
    tags={"team": "mlops", "domain": "model"},
)
