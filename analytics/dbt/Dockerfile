FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN python -m pip install --no-cache-dir     "dbt-postgres==1.11.0"

WORKDIR /usr/app

ENTRYPOINT ["dbt"]
