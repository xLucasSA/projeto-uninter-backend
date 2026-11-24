FROM ghcr.io/astral-sh/uv:0.11.26 AS uv

FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"
COPY --from=uv /uv /usr/local/bin/uv
RUN useradd --create-home --uid 10001 raizes
WORKDIR /app

FROM base AS deps
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

FROM deps AS final
COPY . .
RUN DJANGO_SECRET_KEY=somente-para-o-collectstatic-do-build \
    BACKOFFICE_DATABASE_URL=postgres://build:build@localhost:5432/build \
    python manage.py collectstatic --noinput
USER raizes
EXPOSE 8000
CMD ["gunicorn", "config.wsgi", "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-"]
