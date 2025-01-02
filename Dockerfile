FROM python:3.11-alpine

WORKDIR '/app'
ENV PYTHONPATH=/app

COPY requirements.txt .
RUN pip install -r requirements.txt

ENV TZ=Europe/Berlin
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY ./src .

ARG GROQ_API_KEY
ENV GROQ_API_KEY=$GROQ_API_KEY

ENV FLASK_APP=flask_interface.app
ENV FLASK_RUN_HOST=0.0.0.0

EXPOSE 8000

COPY nginx.conf /etc/nginx/nginx.conf

CMD exec gunicorn -b 0.0.0.0:8000 flask_interface.app:app
