#/usr/bin/sh

export DATABASE_URL="postgresql://${RALLY_DB_USER}:${RALLY_DB_PASSWORD}@${RALLY_DB_ENDPOINT}/${RALLY_DB_NAME}"

exec ./docker-start.sh
