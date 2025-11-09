# =========================
# 1️⃣ Build Frontend
# =========================
FROM node:18 AS frontend-builder
WORKDIR /app/frontend

# copy and install
COPY frontend/package*.json ./
RUN npm install

# copy source code and build
COPY frontend/ ./
RUN npm run build

# =========================
# 2️⃣ Build Backend
# =========================
FROM python:3.13-slim AS backend
WORKDIR /app

# Copy .env for Supabase credentials
COPY .env .env
ENV PYTHONUNBUFFERED=1

# copy backend requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy backend source
COPY app/ ./app

# copy frontend build output to serve static files
COPY --from=frontend-builder /app/frontend/dist ./frontend_dist

# expose FastAPI port
EXPOSE 8000

# run FastAPI
CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]