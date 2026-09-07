FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir \
    "dbt-core==1.12.3" \
    "dbt-postgres==1.11.0"

WORKDIR /usr/app

ENTRYPOINT ["dbt"]
