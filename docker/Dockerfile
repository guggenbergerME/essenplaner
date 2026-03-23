FROM python:3.12-slim

WORKDIR /app

# curl für healthcheck
RUN apt-get update -qq && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 80

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80", "--proxy-headers", "--forwarded-allow-ips=*"]
