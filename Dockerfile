FROM python:3.11

WORKDIR /app
COPY . /app

RUN apt-get update && apt-get install -y libcups2-dev && pip install -r requirements.txt

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
