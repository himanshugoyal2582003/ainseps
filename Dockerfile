# Use Python 3.10
FROM python:3.10

WORKDIR /app

# 🔥 Install git (MUST be before pip install)
RUN apt-get update && apt-get install -y git

# Copy only requirements first (better caching)
COPY backend/requirements.txt .

# Upgrade pip + install deps
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copy rest of backend
COPY backend/ .

# Expose port
EXPOSE 10000

# Run app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
