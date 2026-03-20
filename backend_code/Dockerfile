FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV NODE_OPTIONS=--max-old-space-size=384

WORKDIR /app

COPY backend_code/requirements.txt /app/backend_code/requirements.txt
RUN pip install --no-cache-dir -r /app/backend_code/requirements.txt

COPY backend_code /app/backend_code
COPY frontend_code /app/frontend_code

WORKDIR /app/backend_code
EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
