#!/bin/sh

export PULUMI_ACCESS_TOKEN=$(aws secretsmanager get-secret-value --secret-id $PULUMI_ACCESS_TOKEN_ID --query SecretString --output text | tr -d '\n')


exec gunicorn --timeout 0 -w 9 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:80 src.main:app
