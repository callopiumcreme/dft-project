FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq-dev \
    gcc \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir fastapi 'uvicorn[standard]' 'sqlalchemy[asyncio]' asyncpg \
        alembic 'pydantic[email]' 'python-jose[cryptography]' 'passlib[bcrypt]' \
        python-multipart weasyprint jinja2 pypdf openpyxl pandas apscheduler

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
