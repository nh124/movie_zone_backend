FROM python:3-alpine3.15

WORKDIR /app
COPY . /app

RUN apk add --no-cache \
    build-base \
    python3-dev \
    libffi-dev \
    openssl-dev \
    pkgconf \
    mariadb-dev

RUN pip install -r requirements.txt

EXPOSE 5000
CMD python ./app.py
