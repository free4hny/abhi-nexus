# ── Abhi-Nexus Dockerfile ────────────────────
# Runs both FastAPI and Streamlit in one container
# using a simple process manager (supervisord)

FROM python:3.12-slim

WORKDIR /app

# Install supervisord to run multiple processes
RUN apt-get update && apt-get install -y \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Create data directory
RUN mkdir -p data

# Copy supervisord config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose both ports
EXPOSE 8000 8501 8502 7070

# Start both services via supervisord
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
