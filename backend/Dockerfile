FROM python:3.12-slim AS runtime
WORKDIR /app
COPY pyproject.toml .
COPY app ./app
RUN pip install --no-cache-dir .
COPY alembic ./alembic
COPY alembic.ini entrypoint.sh ./
RUN chmod +x /app/entrypoint.sh && useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM runtime AS test
USER root
RUN pip install --no-cache-dir ".[dev,quality]"
COPY tests ./tests
USER appuser
CMD ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider"]
