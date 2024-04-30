FROM nocodb/nocodb:latest

# Set the environment variables
ENV POSTGRES_USER=$POSTGRES_USER \
    POSTGRES_PASSWORD=$POSTGRES_PASSWORD \
    POSTGRES_DATABASE_NAME=$POSTGRES_DATABASE_NAME \
    POSTGRES_HOST=$POSTGRES_HOST \
    POSTGRES_PORT=$POSTGRES_PORT \
    REDIS_HOST=$REDIS_HOST \
    REDIS_PORT=$REDIS_PORT

# Print out the environment variables
RUN echo "Setting up Nocodb connection string..." \
    && export NC_DB="pg://${POSTGRES_HOST}:${POSTGRES_PORT}?u=${POSTGRES_USER}&p=${POSTGRES_PASSWORD}&d=${POSTGRES_DATABASE_NAME}" \
    && export NC_REDIS_URL="redis://${REDIS_HOST}:${REDIS_PORT}" \
    && echo "Connection string: $NC_DB" \
    && echo "Redis URL: $NC_REDIS_URL"

# Start Nocodb
CMD ["/usr/src/appEntry/start.sh"]