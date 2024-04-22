#!/usr/bin/env bash

echo "Setting up Nocodb connection string..."

# Set the Mattermost connection string since InfraCopilot doesn't natively support compound environment variables
# Construct the connection string
export NC_DB="pg://${POSTGRES_HOST}:${POSTGRES_PORT}?u=${POSTGRES_USER}&p=${POSTGRES_PASSWORD}&d=${POSTGRES_DATABASE_NAME}"
export NC_REDIS_URL="redis://$REDIS_HOST:$REDIS_PORT"

RUN echo "Connection string: $NC_DB"
RUN echo "Redis URL: $NC_REDIS_URL"

echo "Starting Nocodb..."
# execute the passed in command
exec "$@"
