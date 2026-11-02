# Multi-stage or lightweight Python build for Teleop-Sim Backend
FROM python:3.11-slim

# Prevent Python from writing .pyc and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install runtime Linux diagnostic utilities required for Linux operations module
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    iproute2 \
    procps \
    net-tools \
    iputils-ping \
    lsof \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create a non-root user and group
RUN groupadd -r teleop && useradd -r -g teleop -u 1000 -m -s /bin/bash teleop

# Copy requirements and install
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Create runtime directories and assign permissions
RUN mkdir -p /app/data /app/logs && chown -R teleop:teleop /app

# Copy application source code
COPY --chown=teleop:teleop backend/app /app/app
COPY --chown=teleop:teleop frontend /app/frontend

USER teleop

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
