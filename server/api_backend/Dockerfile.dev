# This Dockerfile is for the API backend of the application.
# Use it only for local development (not for production).
# For production, please use the Dockerfile.prod file.

# 1. Python official image
FROM python:3.12-slim

# 2. Useful environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Working directory inside container
WORKDIR /app

# 4. Build-essential is needed if some Python packages require compilation tools at build time.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 5. Copy and install Python packages
# Update pip and install dependencies from your file
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 6. Copy the rest of the backend code
COPY . .

# 7. Start FastAPI
# --host 0.0.0.0 is required to make the app accessible outside the container
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
