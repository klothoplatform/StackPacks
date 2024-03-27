#/usr/bin/sh

export DATABASE_URL="postgres://${RALLLY_DB_USER}:${RALLLY_DB_PASSWORD}@${RALLLY_DB_ENDPOINT}/${RALLLY_DB_NAME}"
export NEXT_PUBLIC_BASE_URL="http://${DOMAIN_NAME}"
export NEXT_PUBLIC_APP_BASE_URL="http://${DOMAIN_NAME}"

exec ./docker-start.sh
