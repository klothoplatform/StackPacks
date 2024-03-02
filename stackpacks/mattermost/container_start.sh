#!/usr/bin/env bash

echo "Setting up Mattermost connection string..."

# Set the Mattermost connection string since InfraCopilot doesn't natively support compound environment variables
export MM_SQLSETTINGS_DATASOURCE="postgres://${MATTERMOST_DB_RDS_USERNAME}:${MATTERMOST_DB_RDS_PASSWORD}@${MATTERMOST_DB_RDS_ENDPOINT}/${MM_DB_NAME}?sslmode=disable&connect_timeout=10"

echo "Starting Mattermost..."
# execute the passed in command
exec "$@"
