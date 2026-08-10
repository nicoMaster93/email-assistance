FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN apt-get update \
    && apt-get install -y --no-install-recommends cron \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY docker/gmail-watch-renewal.cron /etc/cron.d/gmail-watch-renewal
COPY docker/start.sh /app/start.sh
RUN chmod 0644 /etc/cron.d/gmail-watch-renewal \
    && chmod +x /app/start.sh \
    && crontab /etc/cron.d/gmail-watch-renewal

RUN mkdir -p /app/storage/attachments

EXPOSE 8000

CMD ["/app/start.sh"]
