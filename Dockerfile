# Use a single stage to save build time
FROM python:3.11-slim

# Set required environment variables
ENV TZ=UTC
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies in one command
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    tzdata \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set up directories
RUN mkdir -p /data /cron /app
WORKDIR /app

# Step: Install Python packages (Caching this layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Step: Copy application code
COPY . .

# Step: Setup Cron
COPY cron/2fa-cron /etc/cron.d/2fa-cron
RUN chmod 0644 /etc/cron.d/2fa-cron \
    && crontab /etc/cron.d/2fa-cron

# Step: Setup Entrypoint
RUN chmod +x entrypoint.sh

EXPOSE 8080

# Use the script to start the app
ENTRYPOINT ["./entrypoint.sh"]