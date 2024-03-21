#!/bin/sh

echo "Starting container..."

AWS_REGION=$(curl http://169.254.169.254/latest/meta-data/placement/region)
AWS_DEFAULT_REGION=$AWS_REGION
export AWS_REGION
export AWS_DEFAULT_REGION

echo "AWS_REGION=$AWS_REGION"
echo "AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION"

# Set the Pulumi access token
export PULUMI_ACCESS_TOKEN=$(aws secretsmanager get-secret-value --secret-id $PULUMI_ACCESS_TOKEN_ID --query SecretString --output text | tr -d '\n')

exec gunicorn --timeout 0 -w 9 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:80 src.main:app
