FROM python:3-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PIP_ROOT_USER_ACTION ignore
WORKDIR /app
COPY . /app

RUN pip install --no-cache --upgrade pip \
 && pip install --no-cache /app \
 && addgroup --system app && adduser --system --group --home /home/app app \
 && mkdir -p /tmp/code_gpt \
 && chown -R app:app /tmp/code_gpt

USER app

VOLUME /tmp/code_gpt

ENTRYPOINT ["cgpt"]
