FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
COPY config ./config

RUN python -m pip install --no-cache-dir .

CMD ["python", "-c", "print('game-analytics app image ready')"]
