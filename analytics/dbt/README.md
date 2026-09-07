# dbt Analytics Project

This directory contains the analytical transformation layer for the
Mobile Game Analytics project.

The engineering source layer is frozen at `engineering-v1.0`.

## Layering

- `sources` — PostgreSQL raw tables
- `staging` — renamed and typed source-level models
- `intermediate` — reusable analytical transformations
- `marts` — analyst and BI-facing datasets

Generator implementation and hidden simulation parameters must not be
used to derive analytical conclusions.

## Commands

Build the dbt image:

    docker compose build dbt

Check dbt and PostgreSQL connectivity:

    docker compose run --rm dbt debug

Parse the project:

    docker compose run --rm dbt parse

Check source freshness:

    docker compose run --rm dbt source freshness
