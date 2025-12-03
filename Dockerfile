# ----------------------------------------------------------------------
# Stage 1: Builder (Install Python Dependencies)
# ----------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /app

# Install Python dependencies (FastAPI, uvicorn, cryptography, totp library)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ----------------------------------------------------------------------
# Stage 2: Runtime (Setup Environment, Cron, and App)
# ----------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# CRITICAL: Set Timezone to UTC (Requirement)
ENV TZ=UTC
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies (cron and timezone data)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        cron \
        tzdata \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create volume mount points and set permissions
RUN mkdir -p /data /cron \
    && chmod 755 /data /cron

WORKDIR /app

# Copy installed Python packages from the builder stage
# This significantly reduces image size compared to installing everything in Stage 2
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copy application code, scripts, and committed keys
COPY . .

# CRITICAL: Setup cron job (Requirement)
# Copy the cron configuration file (ensuring LF line endings via .gitattributes)
COPY cron/2fa-cron /etc/cron.d/2fa-cron
# Give proper permissions for cron to read and install the job
RUN chmod 0644 /etc/cron.d/2fa-cron \
    && crontab /etc/cron.d/2fa-cron

# Copy and set execution permission for the entrypoint script
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Expose port 8080 (documentation)
EXPOSE 8080

# CRITICAL: Use the entrypoint script to start multiple services
CMD ["/usr/local/bin/entrypoint.sh"]