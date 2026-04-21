# Use Python 3.10 (compatible with TensorFlow)
FROM python:3.10

# Set working directory
WORKDIR /app

# Copy backend code
COPY backend/ .

# Upgrade pip
RUN pip install --upgrade pip

# Install dependencies
RUN pip install -r requirements.txt

# Expose port (Render uses 10000 internally)
EXPOSE 10000

# Start FastAPI app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
