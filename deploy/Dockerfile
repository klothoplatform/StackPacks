FROM python:3.11-slim-bookworm

RUN mkdir /app
WORKDIR /app

VOLUME [ "/app/deployments" ]

ENV PYTHONPATH=.:${PYTHONPATH}
EXPOSE 80

COPY deploy/container_start.sh .
RUN chmod +x container_start.sh

COPY requirements.txt .

RUN pip3 install -r requirements.txt

RUN mkdir ./src
COPY ./src ./src

COPY ./stackpacks ./stackpacks
COPY ./stackpacks_common ./stackpacks_common

ENTRYPOINT [ "container_start.sh" ]
