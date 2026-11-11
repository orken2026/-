# ҚР аумағындағы VPS үшін (дербес деректерді оқшаулау талабы): база /data томында сақталады.
#   docker build -t qazaq-pdd .
#   docker run -d --restart=always -p 8000:8000 -v qazaq_pdd_data:/data \
#     -e BOT_TOKEN=... -e PUBLIC_URL=https://bot.сіздің-домен.kz -e MINI_APP_URL=https://bot.сіздің-домен.kz qazaq-pdd
# HTTPS үшін алдына Caddy/Nginx қойыңыз (Telegram тек HTTPS қабылдайды).
FROM python:3.12-slim
WORKDIR /app
COPY server.py ./
COPY data ./data
COPY webapp ./webapp
ENV PORT=8000 DATA_DIR=/data PYTHONUNBUFFERED=1
VOLUME ["/data"]
EXPOSE 8000
HEALTHCHECK --interval=60s --timeout=5s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=4)"
CMD ["python", "server.py"]
