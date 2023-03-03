FROM python:3.11-alpine

RUN mkdir -p /app

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip

RUN pip install -r requirements.txt

COPY /src .

CMD  ["python3", "main.py"]