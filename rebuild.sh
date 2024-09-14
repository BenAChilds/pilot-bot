#!/bin/bash

# Define your variables here
IMAGE_NAME="discord-bot"

# Rebuild the Docker image
docker build -t "$IMAGE_NAME" .

# Run the new container
docker compose up -d

# Optional: Clean up unused Docker images and containers
docker system prune -f

echo "Image rebuilt and container recreated successfully."
