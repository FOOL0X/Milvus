FROM python:3.11-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy pyproject.toml and lockfile and sync dependencies
# Install the project in editable mode so 'src' package is available
COPY pyproject.toml uv.lock /app/
RUN uv sync --frozen

# Copy source code
COPY src/ ./src/

# Expose port
EXPOSE 8000

# Run the application
ENV PYTHONPATH=/app
CMD [".venv/bin/python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
