FROM python:3.11-slim-bookworm

RUN mkdir /app
WORKDIR /app

VOLUME [ "/app/deployments" ]

# Install utilities
RUN apt-get update && apt-get install -y curl

# Install Docker
# 1. Install the Docker GPG key
RUN apt-get install -y ca-certificates curl;\
    install -m 0755 -d /etc/apt/keyrings;\
    curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc;\
    chmod a+r /etc/apt/keyrings/docker.asc
# 2. Add the Docker repository
RUN echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null;\
  apt-get update
# 3. Install Docker
RUN apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - &&\
    apt-get install -y nodejs

# Install Pulumi
RUN curl -fsSL https://get.pulumi.com | sh
ENV PATH=$PATH:/root/.pulumi/bin

# Install AWS CLI
RUN pip3 install awscli

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

ENTRYPOINT [ "./container_start.sh" ]
