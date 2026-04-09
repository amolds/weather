FROM python:3.11-slim

# Install ODBC + SQL Server driver
RUN apt-get update && apt-get install -y \
    curl gnupg2 unixodbc unixodbc-dev \
    && curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /usr/share/keyrings/microsoft.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft.gpg] https://packages.microsoft.com/ubuntu/22.04/prod jammy main" \
       > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install pyodbc

# Copy your server script
WORKDIR /app
COPY serve_latest.py .

# Expose Python server port
EXPOSE 8080

##USER root
CMD ["python", "serve_latest.py"]

