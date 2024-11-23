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

ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

EXPOSE 5000

CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
