FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/app \
    HOIKU_FACILITY_BUNREI_DB_PATH=/data/facility.sqlite

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app
COPY gen_bunnrei ./gen_bunnrei
COPY deploy/docker/entrypoint.sh /usr/local/bin/hoiku-plan-docs-entrypoint

RUN pip install --no-cache-dir -e . \
    && sed -i 's/\r$//' /usr/local/bin/hoiku-plan-docs-entrypoint \
    && chmod +x /usr/local/bin/hoiku-plan-docs-entrypoint \
    && useradd --create-home --shell /usr/sbin/nologin appuser \
    && mkdir -p /data \
    && chown -R appuser:appuser /data

USER appuser

EXPOSE 8020

ENTRYPOINT ["hoiku-plan-docs-entrypoint"]
CMD ["uvicorn", "hoiku_plan_docs.main:app", "--host", "0.0.0.0", "--port", "8020"]
