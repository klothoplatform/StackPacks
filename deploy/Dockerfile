FROM python:3.11-slim-bookworm

RUN mkdir /app
WORKDIR /app

VOLUME [ "/app/deployments" ]

ENV PYTHONPATH=.:${PYTHONPATH}
EXPOSE 80

COPY requirements.txt .

RUN pip3 install -r requirements.txt

RUN mkdir ./src
COPY ./src ./src

ENTRYPOINT [ "gunicorn" ]
CMD [ \
  "--timeout", \
  "0", \
  "-w", \
  "9", \
  "-k", \
  "uvicorn.workers.UvicornWorker", \
  "-b", \
  "0.0.0.0:80", \
  "src.main:app", \
  ]
