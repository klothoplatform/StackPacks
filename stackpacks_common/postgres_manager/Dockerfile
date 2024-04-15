# First stage: full Python image
FROM python:3.11 as builder

WORKDIR /app

# Install any needed packages
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libpq-dev \
    && pip install psycopg2-binary \
    && apt-get purge -y --auto-remove gcc python3-dev libpq-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install -r requirements.txt

# Second stage: Lambda base image
FROM public.ecr.aws/lambda/python:3.11

# Copy Python dependencies from the first stage
COPY --from=builder /usr/local/lib/python3.11/site-packages ${LAMBDA_TASK_ROOT}

COPY . ${LAMBDA_TASK_ROOT}

RUN pip3 install \
        --target ${LAMBDA_TASK_ROOT} \
        -r ${LAMBDA_TASK_ROOT}/requirements.txt

ENV PYTHONPATH=${LAMBDA_TASK_ROOT}:${PYTHONPATH}

CMD [ "main.lambda_handler" ]