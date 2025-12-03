#!/bin/bash
set -e

# Start the cron service in the background
echo "Starting cron daemon..."
service cron start

# Start the API server in the foreground
exec uvicorn main:app --host 0.0.0.0 --port 8080