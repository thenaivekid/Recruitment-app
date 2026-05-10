#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "🚀 Starting TechKraft Recruitment Dashboard deployment..."

# Check if .env exists, if not create it from the example
if [ ! -f .env ]; then
    echo "📁 Creating .env file from .env.example..."
    cp .env.example .env
fi

# Build and start Docker containers in detached mode
echo "🐳 Building and spinning up Docker containers..."
docker compose up --build -d

# Wait a few seconds for services to become responsive
echo "⏳ Waiting for services to initialize..."
sleep 5

echo "=========================================================="
echo "✅ Deployment Successful!"
echo "=========================================================="
echo "🌐 Frontend (React + Vite):    http://localhost:5173"
echo "⚙️  Backend API (FastAPI):     http://localhost:8000"
echo "📜 API Docs (Swagger UI):      http://localhost:8000/docs"
echo "=========================================================="

echo "🧪 Running a quick API health check..."
if curl -s http://localhost:8000/health | grep -q '"status":"ok"'; then
    echo "✅ Backend is healthy and responding!"
else
    echo "❌ Backend health check failed or is still starting up."
fi
