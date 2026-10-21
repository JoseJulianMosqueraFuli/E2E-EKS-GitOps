"""Initialize a new MLflow PostgreSQL database before replicas start serving."""

import logging
import os

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)


def initialize_database(database_uri: str) -> None:
    """Serialize initialization; require explicit migrations for existing databases."""
    if make_url(database_uri).get_backend_name() != "postgresql":
        raise ValueError("MLflow database bootstrap requires PostgreSQL")

    engine = create_engine(
        database_uri, poolclass=NullPool, connect_args={"connect_timeout": 10}
    )
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("SET statement_timeout = '120s'")
            connection.exec_driver_sql("SELECT pg_advisory_lock(1296844364, 1)")

            from mlflow import MlflowClient
            from mlflow.store.db import utils

            if inspect(engine).get_table_names():
                utils._verify_schema(engine)
            else:
                utils._initialize_tables(engine)

            client = MlflowClient(tracking_uri=database_uri, registry_uri=database_uri)
            client.search_experiments(max_results=1)
            client.search_registered_models(max_results=1)
            logger.info("MLflow database schema and default experiment are ready")
    finally:
        engine.dispose()


def main() -> None:
    """Read the database URI from the Secret-backed environment without logging it."""
    logging.basicConfig(level=logging.INFO)
    try:
        initialize_database(os.environ["MLFLOW_BACKEND_STORE_URI"])
    except Exception as exc:
        raise SystemExit(
            f"MLflow database bootstrap failed ({type(exc).__name__}). "
            "Check database connectivity and schema compatibility. "
            "Existing databases require a verified backup and an explicit mlflow db upgrade."
        ) from None


if __name__ == "__main__":
    main()
