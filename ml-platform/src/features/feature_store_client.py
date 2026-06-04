"""
Feature Store Client

Python wrapper around Feast for the MLOps platform.
Provides simplified APIs for feature retrieval, ingestion, and materialization.
Supports both local (SQLite/Parquet) and cloud (Redis/DynamoDB) backends.
"""

import logging
import os
import tempfile
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from feast import FeatureStore

logger = logging.getLogger(__name__)


class MLOpsFeatureStore:
    """MLOps Feature Store client wrapping Feast."""

    def __init__(self, repo_path: Optional[str] = None):
        """
        Initialize feature store client.

        Args:
            repo_path: Path to Feast feature repository.
                       Defaults to 'feature_repo' relative to project root.
        """
        if repo_path is None:
            # Try to find feature_repo relative to src
            current_dir = os.path.dirname(os.path.abspath(__file__))
            repo_path = os.path.join(current_dir, "..", "..", "feature_repo")
            repo_path = os.path.abspath(repo_path)

        self.repo_path = repo_path
        self.store = FeatureStore(repo_path=repo_path)
        logger.info(f"Initialized FeatureStore from {repo_path}")

    # ------------------------------------------------------------------
    # Feature Retrieval
    # ------------------------------------------------------------------

    def get_online_features(
        self,
        feature_refs: List[str],
        entity_rows: List[Dict[str, Any]],
    ) -> pd.DataFrame:
        """
        Fetch online (real-time) features.

        Args:
            feature_refs: List of feature references, e.g. ["fv_name:feature_name"]
            entity_rows: List of entity dictionaries, e.g. [{"user_id": 1}]

        Returns:
            DataFrame with entity keys + feature values
        """
        features = self.store.get_online_features(
            features=feature_refs,
            entity_rows=entity_rows,
        ).to_df()

        logger.info(
            f"Retrieved online features for {len(entity_rows)} rows, "
            f"refs={feature_refs}"
        )
        return features

    def get_historical_features(
        self,
        feature_refs: List[str],
        entity_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Fetch point-in-time correct historical features for training.

        Args:
            feature_refs: List of feature references.
            entity_df: DataFrame with entity columns + event_timestamp.

        Returns:
            DataFrame joined with historical feature values.
        """
        training_df = self.store.get_historical_features(
            features=feature_refs,
            entity_df=entity_df,
        ).to_df()

        logger.info(
            f"Retrieved historical features for {len(training_df)} rows"
        )
        return training_df

    # ------------------------------------------------------------------
    # Data Ingestion
    # ------------------------------------------------------------------

    def ingest_features(
        self,
        feature_view_name: str,
        df: pd.DataFrame,
    ) -> None:
        """
        Ingest data into a feature view's offline store.

        Args:
            feature_view_name: Name of the target FeatureView.
            df: DataFrame containing entity columns, event_timestamp, and features.
        """
        # Push to offline store
        self.store.push(feature_view_name, df)
        logger.info(
            f"Ingested {len(df)} rows into FeatureView '{feature_view_name}'"
        )

    def materialize(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> None:
        """
        Materialize offline features into the online store.

        Args:
            start_date: Start of materialization window.
            end_date: End of materialization window.
        """
        if end_date is None:
            end_date = datetime.utcnow()
        if start_date is None:
            start_date = end_date - timedelta(days=1)

        self.store.materialize(
            start_date=start_date,
            end_date=end_date,
        )
        logger.info(
            f"Materialized features from {start_date} to {end_date}"
        )

    def materialize_incremental(self, end_date: Optional[datetime] = None) -> None:
        """
        Incrementally materialize new data since last materialization.

        Args:
            end_date: End of materialization window (defaults to now).
        """
        if end_date is None:
            end_date = datetime.utcnow()

        self.store.materialize_incremental(end_date=end_date)
        logger.info(f"Incremental materialization up to {end_date}")

    # ------------------------------------------------------------------
    # Training Dataset Utilities
    # ------------------------------------------------------------------

    def build_training_dataset(
        self,
        entity_df: pd.DataFrame,
        feature_views: List[str],
        label_column: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Build a training dataset by joining entity dataframe with historical features.

        Args:
            entity_df: DataFrame with entity IDs and event_timestamp.
            feature_views: List of feature view names to retrieve features from.
            label_column: Optional name of the label column in entity_df.

        Returns:
            Training DataFrame ready for model training.
        """
        # Build feature references from all feature views
        feature_refs = []
        for fv_name in feature_views:
            fv = self.store.get_feature_view(fv_name)
            for feature in fv.features:
                feature_refs.append(f"{fv_name}:{feature.name}")

        # Retrieve historical features
        training_df = self.get_historical_features(
            feature_refs=feature_refs,
            entity_df=entity_df,
        )

        logger.info(
            f"Built training dataset: shape={training_df.shape}, "
            f"features={len(feature_refs)}"
        )
        return training_df

    # ------------------------------------------------------------------
    # Registry Inspection
    # ------------------------------------------------------------------

    def list_feature_views(self) -> List[str]:
        """Return names of all registered feature views."""
        return [fv.name for fv in self.store.list_feature_views()]

    def list_entities(self) -> List[str]:
        """Return names of all registered entities."""
        return [e.name for e in self.store.list_entities()]

    def get_feature_view_info(self, name: str) -> Dict[str, Any]:
        """Get metadata about a feature view."""
        fv = self.store.get_feature_view(name)
        return {
            "name": fv.name,
            "entities": list(fv.entities) if fv.entities else [],
            "features": [f.name for f in fv.features],
            "ttl": str(fv.ttl),
            "online": fv.online,
            "tags": fv.tags,
        }


class LocalFeatureStoreFactory:
    """Factory to create an in-memory/local FeatureStore for testing."""

    @staticmethod
    def create_temp_store() -> Tuple[str, MLOpsFeatureStore]:
        """
        Create a temporary local feature store.

        Returns:
            Tuple of (repo_path, MLOpsFeatureStore instance)
        """
        tmpdir = tempfile.mkdtemp(prefix="feast_test_")
        repo_path = os.path.join(tmpdir, "feature_repo")
        os.makedirs(repo_path, exist_ok=True)

        # Write minimal feature_store.yaml
        config = f"""project: test_feature_store
registry: {os.path.join(tmpdir, "registry.db")}
provider: local
online_store:
    type: sqlite
    path: {os.path.join(tmpdir, "online_store.db")}
offline_store:
    type: file
entity_key_serialization_version: 2
"""
        with open(os.path.join(repo_path, "feature_store.yaml"), "w") as f:
            f.write(config)

        store = MLOpsFeatureStore(repo_path=repo_path)
        return repo_path, store


def create_sample_feature_data(
    n_samples: int = 1000,
    n_features: int = 5,
    entity_name: str = "user_id",
) -> pd.DataFrame:
    """
    Create synthetic feature data compatible with Feast ingestion.

    Args:
        n_samples: Number of rows.
        n_features: Number of feature columns.
        entity_name: Name of the entity column.

    Returns:
        DataFrame with entity_id, event_timestamp, and feature columns.
    """
    import numpy as np

    np.random.seed(42)

    df = pd.DataFrame()
    df[entity_name] = range(n_samples)
    for i in range(n_features):
        df[f"feature_{i+1}"] = np.random.randn(n_samples)

    df["event_timestamp"] = pd.Timestamp.now()
    return df


# Example / smoke-test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Create a temporary store
    repo_path, store = LocalFeatureStoreFactory.create_temp_store()
    print(f"Created temp store at: {repo_path}")
    print(f"Feature views: {store.list_feature_views()}")
    print(f"Entities: {store.list_entities()}")
