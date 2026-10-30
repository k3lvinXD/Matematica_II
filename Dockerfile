FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLCONFIGDIR=/tmp/matplotlib \
    ACADEMY_PRODUCTION=1

# Microsoft ODBC Driver 18, según las instrucciones para Debian 12.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb -o /tmp/microsoft-prod.deb \
    && dpkg -i /tmp/microsoft-prod.deb \
    && rm /tmp/microsoft-prod.deb \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 unixodbc libgssapi-krb5-2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt requirements-sqlserver.txt ./
RUN pip install --no-cache-dir -r requirements-sqlserver.txt \
    && useradd --create-home --uid 10001 appuser

# Lista explícita: nunca copiar .env, instance, venv ni el repositorio .git.
COPY app.py gunicorn.conf.py ./
COPY academy ./academy
COPY modules ./modules
COPY templates ./templates
COPY static ./static
COPY deploy ./deploy
RUN mkdir -p /app/instance && chown -R appuser:appuser /app
USER appuser
EXPOSE 10000
CMD ["python", "-m", "deploy.render_start"]
