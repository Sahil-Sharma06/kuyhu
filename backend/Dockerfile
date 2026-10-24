FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt "uvicorn[standard]==0.54.0" \
    && useradd --system --uid 10001 --no-create-home app

COPY app ./app
COPY data ./data

USER app
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=6 CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
