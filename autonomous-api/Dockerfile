FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY pyproject.toml README.md uv.lock ./
COPY app ./app
COPY src ./src

# Install from the committed lock: `uv export --locked` fails the build if
# uv.lock is stale, and the constraints file pins the resolved versions.
RUN pip install --upgrade pip && pip install uv==0.11.3 \
    && uv export --locked --no-hashes --no-emit-project -o /tmp/uv-constraints.txt \
    && pip install . -c /tmp/uv-constraints.txt \
    && pip uninstall -y uv

RUN mkdir -p /app/data /app/logs && chown -R app:app /app

USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
