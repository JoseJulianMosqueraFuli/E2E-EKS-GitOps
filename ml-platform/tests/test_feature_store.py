"""
Tests for Feature Store integration (Feast).

These tests verify the MLOpsFeatureStore client and local factory
without requiring external Redis/DynamoDB backends.
"""

import importlib.util
import os
import shutil

import pandas as pd
import pytest

from src.features.feature_store_client import (
    LocalFeatureStoreFactory,
    MLOpsFeatureStore,
    create_sample_feature_data,
)


class TestMLOpsFeatureStore:
    """Integration tests for MLOps Feature Store client."""

    @pytest.fixture(scope="class")
    def temp_store(self):
        """Create a temporary local feature store."""
        repo_path, store = LocalFeatureStoreFactory.create_temp_store()
        yield repo_path, store
        # Cleanup
        if os.path.isdir(repo_path):
            shutil.rmtree(os.path.dirname(repo_path), ignore_errors=True)

    def test_initialization(self, temp_store):
        """Test feature store client initialization."""
        repo_path, store = temp_store
        assert os.path.exists(repo_path)
        assert store.repo_path == repo_path
        assert store.store is not None

    def test_list_feature_views_empty(self, temp_store):
        """Test listing feature views on empty store."""
        _, store = temp_store
        fvs = store.list_feature_views()
        assert isinstance(fvs, list)

    def test_list_entities_empty(self, temp_store):
        """Test listing entities on empty store."""
        _, store = temp_store
        entities = store.list_entities()
        assert isinstance(entities, list)

    def test_create_sample_feature_data(self):
        """Test synthetic feature data generation."""
        df = create_sample_feature_data(n_samples=50, n_features=3)
        assert len(df) == 50
        assert "user_id" in df.columns
        assert "event_timestamp" in df.columns
        assert "feature_1" in df.columns
        assert "feature_2" in df.columns
        assert "feature_3" in df.columns

    def test_factory_creates_valid_repo(self):
        """Test that LocalFeatureStoreFactory creates a valid Feast repo."""
        repo_path, store = LocalFeatureStoreFactory.create_temp_store()
        assert os.path.exists(os.path.join(repo_path, "feature_store.yaml"))
        assert store.store.project == "test_feature_store"
        assert store.store.config.entity_key_serialization_version == 3
        # Cleanup
        if os.path.isdir(repo_path):
            shutil.rmtree(os.path.dirname(repo_path), ignore_errors=True)


class TestFeatureStoreWithDefinitions:
    """Tests using the project's actual feature definitions."""

    @pytest.fixture(scope="class")
    def project_store(self, tmp_path_factory):
        """Initialize store pointing to the project's feature_repo and apply definitions."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        repo_path = os.path.join(current_dir, "..", "feature_repo")
        repo_path = os.path.abspath(repo_path)

        temporary_repo = tmp_path_factory.mktemp("feast") / "feature_repo"
        temporary_repo.mkdir()
        for filename in ("feature_store.yaml", "feature_definitions.py"):
            shutil.copy2(os.path.join(repo_path, filename), temporary_repo / filename)
        data_dir = temporary_repo / "data"
        data_dir.mkdir()
        timestamp = pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=1)
        datasets = {
            "model_features": {
                f"feature_{i}": [float(i + j) for j in range(3)] for i in range(1, 6)
            },
            "transaction_stats": {
                "amount_mean": [10.0, 20.0, 30.0],
                "amount_std": [1.0, 2.0, 3.0],
                "transaction_count": [1, 2, 3],
                "days_since_last": [1.0, 2.0, 3.0],
            },
            "user_profile": {
                "age_group": ["adult", "adult", "adult"],
                "account_tenure_days": [10, 20, 30],
                "has_premium": [0, 1, 0],
                "engagement_score": [0.1, 0.2, 0.3],
            },
        }
        for name, features in datasets.items():
            pd.DataFrame(
                {"user_id": [1, 2, 3], "event_timestamp": [timestamp] * 3, **features}
            ).to_parquet(data_dir / f"{name}.parquet", index=False)
        spec = importlib.util.spec_from_file_location(
            "test_feature_definitions", temporary_repo / "feature_definitions.py"
        )
        feature_definitions = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(feature_definitions)
        store = MLOpsFeatureStore(repo_path=str(temporary_repo))

        store.store.apply(
            [
                feature_definitions.user_entity,
                feature_definitions.transaction_stats_view,
                feature_definitions.user_profile_view,
                feature_definitions.model_features_view,
            ]
        )
        return store

    def test_project_store_initialization(self, project_store):
        """Test that project feature repo loads correctly."""
        assert project_store.store is not None
        assert project_store.store.project == "mlops_feature_store"

    def test_feature_views_exist(self, project_store):
        """Test that defined feature views are registered."""
        fvs = project_store.list_feature_views()
        expected = ["transaction_stats", "user_profile", "model_features"]
        for name in expected:
            assert name in fvs, f"FeatureView '{name}' not found in registry"

    def test_entities_exist(self, project_store):
        """Test that entities are registered."""
        entities = project_store.list_entities()
        assert "user_id" in entities

    def test_get_feature_view_info(self, project_store):
        """Test retrieving feature view metadata."""
        info = project_store.get_feature_view_info("model_features")
        assert info["name"] == "model_features"
        assert "features" in info
        assert len(info["features"]) == 5
        assert info["online"] is True

    def test_feature_refs_format(self, project_store):
        """Test building feature references."""
        info = project_store.get_feature_view_info("model_features")
        refs = [f"model_features:{f}" for f in info["features"]]
        assert len(refs) == 5
        assert all(":" in ref for ref in refs)

    def test_historical_features(self, project_store):
        """Test retrieving historical features for training."""
        entity_df = pd.DataFrame(
            {
                "user_id": [1, 2, 3],
                "event_timestamp": pd.Timestamp.now(tz="UTC"),
            }
        )
        feature_refs = [
            "model_features:feature_1",
            "model_features:feature_2",
        ]
        df = project_store.get_historical_features(
            feature_refs=feature_refs,
            entity_df=entity_df,
        )
        assert isinstance(df, pd.DataFrame)
        assert df.sort_values("user_id")["feature_1"].tolist() == [1.0, 2.0, 3.0]

    def test_online_features(self, project_store):
        """Test retrieving online features."""
        # Materialize first so online store is populated
        project_store.materialize_incremental()
        entity_rows = [{"user_id": 1}, {"user_id": 2}]
        feature_refs = [
            "model_features:feature_1",
            "model_features:feature_2",
        ]
        df = project_store.get_online_features(
            feature_refs=feature_refs,
            entity_rows=entity_rows,
        )
        assert isinstance(df, pd.DataFrame)
        assert df.sort_values("user_id")["feature_1"].tolist() == [1.0, 2.0]


if __name__ == "__main__":
    pytest.main([__file__])
