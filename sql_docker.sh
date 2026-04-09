#!/bin/bash

docker run -e "ACCEPT_EULA=Y" \
  -e "MSSQL_SA_PASSWORD=Passw0rd!" \
  -p 1433:1433 \
  --name sql2025 \
  -v sql2025data:/var/opt/mssql \
  -d mcr.microsoft.com/mssql/server:2025-latest
