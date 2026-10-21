from types import SimpleNamespace

import pytest

from src.pipelines import mlflow_bootstrap


@pytest.fixture
def database(mocker):
    engine = mocker.MagicMock()
    mocker.patch.object(mlflow_bootstrap, "create_engine", return_value=engine)
    inspector = mocker.patch.object(mlflow_bootstrap, "inspect").return_value
    inspector.get_table_names.return_value = []
    return SimpleNamespace(
        engine=engine,
        connection=engine.connect.return_value.__enter__.return_value,
        inspector=inspector,
        initialize=mocker.patch("mlflow.store.db.utils._initialize_tables"),
        verify=mocker.patch("mlflow.store.db.utils._verify_schema"),
        stores=mocker.patch("mlflow.server.handlers.initialize_backend_stores"),
    )


def test_empty_database_is_initialized_while_holding_the_lock(database):
    def initialize(engine):
        assert engine is database.engine
        database.connection.exec_driver_sql.assert_called_with(
            "SELECT pg_advisory_lock(1296844364, 1)"
        )
        database.engine.connect.return_value.__exit__.assert_not_called()

    database.initialize.side_effect = initialize
    mlflow_bootstrap.initialize_database("postgresql://localhost/mlflow")
    database.initialize.assert_called_once_with(database.engine)
    database.verify.assert_not_called()
    database.stores.assert_called_once_with(
        backend_store_uri="postgresql://localhost/mlflow",
        registry_store_uri="postgresql://localhost/mlflow",
        default_artifact_root="mlflow-artifacts:/",
    )
    database.engine.connect.return_value.__exit__.assert_called_once()
    database.engine.dispose.assert_called_once()


def test_existing_database_is_verified_without_migration(database):
    database.inspector.get_table_names.return_value = ["experiments", "alembic_version"]
    mlflow_bootstrap.initialize_database("postgresql://localhost/mlflow")
    database.initialize.assert_not_called()
    database.verify.assert_called_once_with(database.engine)


def test_outdated_database_stops_without_modifying_tables(database):
    database.inspector.get_table_names.return_value = ["experiments"]
    database.verify.side_effect = RuntimeError("Schema upgrade required")
    with pytest.raises(RuntimeError, match="Schema upgrade required"):
        mlflow_bootstrap.initialize_database("postgresql://localhost/mlflow")
    database.initialize.assert_not_called()
    database.stores.assert_not_called()
    database.engine.connect.return_value.__exit__.assert_called_once()
    database.engine.dispose.assert_called_once()


def test_lock_timeout_does_not_start_initialization(database):
    database.connection.exec_driver_sql.side_effect = [
        None,
        TimeoutError("Lock timed out"),
    ]
    with pytest.raises(TimeoutError, match="Lock timed out"):
        mlflow_bootstrap.initialize_database("postgresql://localhost/mlflow")
    database.initialize.assert_not_called()
    database.stores.assert_not_called()
    database.engine.dispose.assert_called_once()


def test_bootstrap_rejects_backends_without_the_postgresql_lock(database):
    with pytest.raises(ValueError, match="requires PostgreSQL"):
        mlflow_bootstrap.initialize_database("sqlite:///test.db")
    mlflow_bootstrap.create_engine.assert_not_called()


def test_bootstrap_failure_does_not_expose_database_credentials(monkeypatch, mocker):
    uri = "postgresql://test-user:private-value@localhost/mlflow"
    monkeypatch.setenv("MLFLOW_BACKEND_STORE_URI", uri)
    mocker.patch.object(mlflow_bootstrap, "initialize_database", side_effect=RuntimeError(uri))
    with pytest.raises(SystemExit) as error:
        mlflow_bootstrap.main()
    assert "private-value" not in str(error.value)
    assert "verified backup" in str(error.value)
