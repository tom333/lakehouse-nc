# Code Dagster du lakehouse-nc : ingestion dlt et projet dbt.
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.12 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH=/app/.venv/bin:$PATH \
    HOME=/app \
    DBT_PROFILES_DIR=/app/transformation

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY ingestion ingestion
COPY orchestration orchestration
COPY transformation transformation
# Le manifeste dbt est lu par Dagster au chargement du code. Seuls /app (état
# dlt dans ~/.dlt) et transformation/ (cibles dbt) doivent rester inscriptibles :
# un chown -R de /app dupliquerait tout l'environnement Python dans une couche.
RUN cd transformation && dbt deps && dbt parse \
    && useradd --uid 1000 --home-dir /app dagster \
    && chown dagster /app && chown -R dagster /app/transformation

USER 1000
EXPOSE 4000
CMD ["dagster", "api", "grpc", "-m", "orchestration.definitions", "-a", "defs", "-h", "0.0.0.0", "-p", "4000"]
