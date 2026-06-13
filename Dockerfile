FROM python:3.11-slim

LABEL maintainer="PoCL Team"
LABEL description="PoCL Hospital Node — CNN training environment"

WORKDIR /app

# System dependencies for opencv-headless
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY hospital_node_client.py .

# Output directory for model + metadata
RUN mkdir -p /app/output /app/data

# Non-root user for security
RUN useradd -m -u 1001 pocl && chown -R pocl:pocl /app
USER pocl

ENTRYPOINT ["python", "hospital_node_client.py"]