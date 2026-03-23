FROM node:20-alpine AS frontend-builder

WORKDIR /frontend_react

COPY frontend_react/package.json frontend_react/package-lock.json ./
RUN npm ci

COPY frontend_react/ ./
RUN npm run build

FROM python:3.11-slim

WORKDIR /app

# Avoid cache to reduce image and build memory usage.
ENV PIP_NO_CACHE_DIR=1

COPY backend_code/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend_code/ ./backend_code/
COPY --from=frontend-builder /frontend_react/dist ./frontend_react/dist

# Stream logs immediately in container environments.
ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "backend_code.main:app", "--host", "0.0.0.0", "--port", "10000"]
