FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini .

# root olarak çalışma
RUN useradd --create-home --uid 10001 atolye && mkdir -p /srv/var/media && chown -R atolye /srv/var
USER atolye

EXPOSE 8000
# Önce migration, sonra uygulama. --proxy-headers: Caddy arkasında gerçek IP/şema
CMD ["sh", "-c", "alembic upgrade head && uvicorn --factory app.main:create_app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
