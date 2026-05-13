#!/usr/bin/env bash
set -e

echo "Building weather-html image..."
docker build -t weather-html .

# Remove any previous containers created from this image so reruns do not fail on port binds.
existing_containers=$(docker ps -aq --filter ancestor=weather-html)
if [ -n "$existing_containers" ]; then
	echo "Removing existing weather-html containers..."
	docker rm -f $existing_containers >/dev/null 2>&1 || true
fi

# Ensure the container name can always be reused.
docker rm -f weather-html-portal >/dev/null 2>&1 || true

echo "Starting weather portal at http://localhost"
echo "Press Ctrl+C to stop."
docker run --name weather-html-portal -p 80:8000 weather-html

