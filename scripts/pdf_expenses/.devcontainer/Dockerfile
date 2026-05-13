FROM python:3.14.4-trixie

WORKDIR /app

COPY main.py requirements.txt /app/

RUN python -m venv /app/venv
RUN source /app/venv/bin/activate
RUN pip install -r requirements.txt