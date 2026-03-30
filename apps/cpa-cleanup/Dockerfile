FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir curl_cffi

COPY . /app

EXPOSE 8123

ENV CPA_WEB_HOST=0.0.0.0
ENV CPA_WEB_PORT=8123

CMD ["python", "cpa_codex_cleanup_web.py"]
