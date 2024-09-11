@echo off
REM Define your variables here
set IMAGE_NAME=discord-bot

REM Rebuild the Docker image
docker build -t %IMAGE_NAME% .

REM Run the new container
docker compose up -d

REM Optional: Clean up unused Docker images and containers
docker system prune -f

echo Image rebuilt and container recreated successfully.
pause
