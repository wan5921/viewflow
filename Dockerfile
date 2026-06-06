FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY setup.py ./
COPY viewflow ./viewflow
RUN pip install --no-cache-dir -e .
RUN pip install --no-cache-dir gunicorn django-filter pytest pytest-cov pytest-django flake8 black

# Expose port 8000
EXPOSE 8000

# Default command to run gunicorn
CMD ["gunicorn", "viewflow_demo.wsgi"]
