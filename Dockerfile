FROM python:3.10

WORKDIR /app

COPY backend/requirements.txt .

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY backend/ .

EXPOSE 10000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
