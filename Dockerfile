FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY main.py ./
COPY website ./website

# SQLite database lives in /app/instance (mounted as a volume)
RUN useradd --system --uid 10001 app \
    && mkdir -p /app/instance \
    && chown -R app:app /app
USER app

EXPOSE 5001
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-5001} --workers ${WEB_CONCURRENCY:-2} main:app"]
