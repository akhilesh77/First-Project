# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    ENV=production

# Set the working directory
WORKDIR /app

# Install system dependencies (build tools may be needed for some packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Run the ingestion script during container build to populate the SQLite database
# This bakes the ~600MB database directly into the final docker image.
RUN python -m scripts.ingest -v

# Expose the default port
EXPOSE 8000

# Start the API server
CMD ["python", "-m", "scripts.serve"]
