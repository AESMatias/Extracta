# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1 (builder): install dependencies with Poetry into /app/.venv.
# Poetry itself stays in this stage and never reaches the final image.
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV POETRY_VERSION=2.5.1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    PIP_NO_CACHE_DIR=1

RUN pip install "poetry==${POETRY_VERSION}"

WORKDIR /app

# Optional LLM providers, e.g. --build-arg POETRY_EXTRAS=openai
ARG POETRY_EXTRAS=""

# Copy only the dependency manifests first so this layer is cached
# until pyproject.toml or poetry.lock change.
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root ${POETRY_EXTRAS:+--extras "$POETRY_EXTRAS"}

# ---------------------------------------------------------------------------
# Stage 2 (runtime): slim image with the virtualenv and the app code only.
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}"

# Unprivileged user; the uploads dir is created here so the named volume
# mounted on it inherits this ownership.
RUN useradd --create-home --uid 1000 appuser \
    && mkdir /tmp_uploads \
    && chown appuser:appuser /tmp_uploads

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY app ./app

USER appuser

EXPOSE 8000
