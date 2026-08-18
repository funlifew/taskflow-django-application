# syntax=docker/dockerfile:1

# ---------------------------------------------------------
# Builder
# ---------------------------------------------------------

FROM python:3.14-slim-bookworm AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true

WORKDIR /app

RUN python -m pip install \
    --no-cache-dir \
    "poetry>=2.0,<3.0"

COPY pyproject.toml poetry.lock ./

RUN poetry install \
    --only main \
    --no-root \
    --no-ansi


# ---------------------------------------------------------
# Runtime
# ---------------------------------------------------------

FROM python:3.14-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y \
        --no-install-recommends \
        ca-certificates \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd \
        --system \
        taskflow \
    && useradd \
        --system \
        --gid taskflow \
        --create-home \
        taskflow

COPY --from=builder \
    --chown=taskflow:taskflow \
    /app/.venv \
    /app/.venv

COPY --chown=taskflow:taskflow \
    . \
    .

RUN mkdir -p \
        /app/staticfiles \
        /app/media \
    && chmod +x \
        /app/docker/entrypoint.sh \
    && chown -R \
        taskflow:taskflow \
        /app

USER taskflow

EXPOSE 8000

ENTRYPOINT [
    "/app/docker/entrypoint.sh"
]

CMD [
    "gunicorn",
    "config.wsgi:application",
    "--config",
    "gunicorn.conf.py"
]