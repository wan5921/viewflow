FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=viewflow_demo.settings

WORKDIR /app

COPY . .

RUN python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir . gunicorn

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "viewflow_demo.wsgi"]
