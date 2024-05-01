#!/bin/sh

echo "Setting up NocoDB connection string..."

# Set the NocoDB connection string since InfraCopilot doesn't natively support compound environment variables
export NC_DB="pg://${POSTGRES_HOST}:${POSTGRES_PORT}?u=${POSTGRES_USER}&p=${POSTGRES_PASSWORD}&d=${POSTGRES_DATABASE_NAME}"
export NC_REDIS_URL="redis://${REDIS_HOST}:${REDIS_PORT}"

echo "NocoDB connection string set to: $NC_DB"
echo "Redis connection string set to: $NC_REDIS_URL"
echo "Starting NocoDB..."
# execute the passed in command
exec "/usr/src/appEntry/start.sh"
