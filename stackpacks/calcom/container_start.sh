#!/usr/bin/sh

export DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${DATABASE_ENDPOINT}/${POSTGRES_DB}
export DATABASE_DIRECT_URL=${DATABASE_URL}

export NEXT_PUBLIC_WEBAPP_URL=http://${DNS_NAME}

exec "/calcom/scripts/start.sh"
