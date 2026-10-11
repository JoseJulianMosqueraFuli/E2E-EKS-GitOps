FROM python:3.11.17-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

FROM base AS builder

ARG POETRY_VERSION=2.5.1

RUN python -m venv /opt/poetry \
    && /opt/poetry/bin/pip install "poetry==${POETRY_VERSION}" \
    && python -m venv /opt/venv

ENV VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    POETRY_NO_INTERACTION=1

WORKDIR /build
COPY pyproject.toml poetry.lock README.md ./
RUN /opt/poetry/bin/poetry check --lock \
    && /opt/poetry/bin/poetry install --only main --no-root

FROM builder AS test

RUN /opt/poetry/bin/poetry install --no-root -E dev
COPY src ./src
COPY tests ./tests
RUN python -m pytest tests -q -p no:cacheprovider

FROM base AS runtime

ARG GIT_COMMIT=unknown
ARG IMAGE_REF=mlops-platform

RUN useradd --uid 8737 --gid 0 --home-dir /tmp --no-create-home --shell /usr/sbin/nologin mlops

COPY --from=builder /opt/venv /opt/venv
COPY src /app/src

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONPATH=/app \
    HOME=/tmp \
    MPLCONFIGDIR=/tmp \
    GIT_COMMIT=${GIT_COMMIT} \
    IMAGE_REF=${IMAGE_REF}

WORKDIR /tmp
USER 8737

ENTRYPOINT ["python", "-m", "src.cli"]
CMD ["--help"]
