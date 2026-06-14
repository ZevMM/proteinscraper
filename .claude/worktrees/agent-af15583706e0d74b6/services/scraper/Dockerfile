# Containerized scraper — an alternative to running the pipeline on GitHub
# Actions (e.g. on a cron in any container host). Build context is this dir.
FROM python:3.12-slim

# Install uv (fast, reproducible installs from uv.lock).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src

# Install into a project venv from the lockfile.
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:${PATH}"

# DATABASE_URL (and optionally ANTHROPIC_API_KEY) are provided at runtime.
ENTRYPOINT ["scraper"]
CMD ["run", "--all"]
