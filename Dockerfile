FROM python:3.11

WORKDIR /app
COPY . /app

RUN pip install -r requirements.txt

ENV TWITCH_CLIENT_ID=${TWITCH_CLIENT_ID}
ENV TWITCH_CLIENT_SECRET=${TWITCH_CLIENT_SECRET}

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
