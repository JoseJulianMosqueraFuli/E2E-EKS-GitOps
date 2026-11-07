"""
Model Serving

Serves the registered model version behind an alias with the MLflow scoring protocol
(GET /ping, POST /invocations). KServe runs it from the same image as the pipeline steps,
so inference uses the exact dependencies the model was trained with.
"""

import logging
from typing import Any, Tuple

import mlflow.pyfunc
from mlflow.pyfunc import scoring_server
from mlflow.tracking import MlflowClient

logger = logging.getLogger(__name__)

MODEL_NAME_HEADER = "X-Model-Name"
MODEL_VERSION_HEADER = "X-Model-Version"


def resolve_alias(model_name: str, alias: str) -> str:
    """Return the registry version that ``alias`` points to when the server starts."""
    return str(MlflowClient().get_model_version_by_alias(model_name, alias).version)


def build_app(model_name: str, alias: str = "champion") -> Tuple[Any, str]:
    version = resolve_alias(model_name, alias)
    model = mlflow.pyfunc.load_model(f"models:/{model_name}/{version}")
    app = scoring_server.init(model)

    @app.middleware("http")
    async def add_model_headers(request, call_next):
        response = await call_next(request)
        response.headers[MODEL_NAME_HEADER] = model_name
        response.headers[MODEL_VERSION_HEADER] = version
        return response

    logger.info("Serving %s v%s resolved from @%s", model_name, version, alias)
    return app, version


def serve(model_name: str, alias: str = "champion", host: str = "0.0.0.0", port: int = 8080):
    import uvicorn

    app, _ = build_app(model_name, alias)
    uvicorn.run(app, host=host, port=port, log_level="info")
