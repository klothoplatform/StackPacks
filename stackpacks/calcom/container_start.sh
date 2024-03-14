#!/usr/bin/sh

export DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${DATABASE_ENDPOINT}/${POSTGRES_DB}
export DATABASE_DIRECT_URL=${DATABASE_URL}

exec "/calcom/scripts/start.sh"
