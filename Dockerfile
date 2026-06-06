FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "viewflow_demo.wsgi:application"]
