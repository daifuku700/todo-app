# Dockerfile
FROM python:3.12-slim

# ODBC Driver 18 for SQL Server の依存を入れる
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gnupg apt-transport-https ca-certificates \
    build-essential unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# Microsoft SQL ODBC Driver 18
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql18 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# 非rootでもOK
ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
