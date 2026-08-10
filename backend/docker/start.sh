#!/bin/sh
set -eu

printenv > /etc/environment
service cron start

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
