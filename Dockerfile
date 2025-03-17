FROM python:3.11-alpine

ENV PYTHONFAULTHANDLER=1 \
     PYTHONUNBUFFERED=1 \
     PYTHONDONTWRITEBYTECODE=1 \
     PIP_DISABLE_PIP_VERSION_CHECK=on

RUN apk add --no-cache ffmpeg \
    build-base \
    rust \
    cargo


RUN mkdir -p /app

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip

RUN pip install -r requirements.txt

COPY /src .

CMD  ["python3", "main.py"]