FROM nocodb/nocodb:latest

# Set the environment variables
ENV POSTGRES_USER=$POSTGRES_USER \
    POSTGRES_PASSWORD=$POSTGRES_PASSWORD \
    POSTGRES_DATABASE_NAME=$POSTGRES_DATABASE_NAME \
    POSTGRES_HOST=$POSTGRES_HOST \
    POSTGRES_PORT=$POSTGRES_PORT \
    REDIS_HOST=$REDIS_HOST \
    REDIS_PORT=$REDIS_PORT 


# Start Nocodb
COPY --chmod=755 container_start.sh /usr/src


CMD [ "/usr/src/container_start.sh" ]
