FROM python:3.11-slim

WORKDIR /app

# Install system deps for psycopg2 / bcrypt
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python deps first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY . .

EXPOSE 5000

# Default: production gunicorn. docker-compose overrides for dev.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "run:app"]
