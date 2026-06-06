FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY setup.py /app/
RUN pip install --no-cache-dir gunicorn && \
    pip install --no-cache-dir -e .

COPY . /app/

EXPOSE 8000

CMD ["gunicorn", "viewflow_demo.wsgi", "--bind", "0.0.0.0:8000"]