FROM python:3-slim

WORKDIR /app
COPY . /app

RUN apt-get update && apt-get install -y gcc
RUN pip install --no-cache /app && mkdir -p /tmp/code_gpt

VOLUME /tmp/code_gpt

ENTRYPOINT ["cgpt"]
