# Dockerfile
FROM python:3.12-slim

# 必要パッケージ（gpgで鍵を格納するので gnupg を入れる）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gnupg ca-certificates apt-transport-https \
    build-essential unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# Microsoft SQL ODBC Driver 18 のリポジトリ登録（apt-keyは使わない）
RUN set -eux; \
    curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
    | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg; \
    echo "deb [arch=amd64,arm64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
    > /etc/apt/sources.list.d/mssql-release.list; \
    apt-get update; \
    ACCEPT_EULA=Y apt-get install -y msodbcsql18; \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
