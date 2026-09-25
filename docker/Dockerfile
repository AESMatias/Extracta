# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1 (builder): install dependencies with Poetry into /app/.venv.
# Poetry itself stays in this stage and never reaches the final image.
# ---------------------------------------------------------------------------
FROM python:3.14-slim AS builder

ENV POETRY_VERSION=2.5.1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_VIRTUALENVS_OPTIONS_NO_PIP=true \
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
# Stage "dev": builder + dev tools (pytest, ruff, mypy) + all extras. Local use only:
#   docker build -f docker/Dockerfile --target dev -t pdf-process-pipeline:dev .
#   docker run --rm -v "$PWD":/src -w /src pdf-process-pipeline:dev pytest
# The code is mounted at /src so it never hides the venv in /app/.venv.
# ---------------------------------------------------------------------------
FROM builder AS dev

# All extras (e.g. openai) so every provider is tested; the runtime image stays lean.
RUN poetry install --no-root --with dev --all-extras

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1

# ---------------------------------------------------------------------------
# Stage 2 (runtime): slim image with the virtualenv and the app code only.
# ---------------------------------------------------------------------------
FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}"

# No package installer at runtime: pip is not needed to run the app, and the copy in the base
# image bundles libraries with known vulnerabilities (found by Trivy). The venv is created
# without pip (POETRY_VIRTUALENVS_OPTIONS_NO_PIP above).
# Unprivileged user; the uploads dir is created here so the named volume
# mounted on it inherits this ownership.
# Security patches from Debian on every build: fixes published after the base image was
# released reach the next deploy without waiting for a new python:3.12-slim tag.
RUN apt-get update \
    && apt-get upgrade --yes --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip uninstall --yes --quiet pip \
    && useradd --create-home --uid 1000 appuser \
    && mkdir /tmp_uploads \
    && chown appuser:appuser /tmp_uploads

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY app ./app

USER appuser

EXPOSE 8000
