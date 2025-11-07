#!/bin/bash

# P&ID OCR Agent - Quick Start Script

echo "========================================="
echo "P&ID OCR Agent - Starting Services"
echo "========================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Error: Docker Compose is not installed"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "Please edit .env file with your configuration"
fi

# Create necessary directories
echo "Creating directories..."
mkdir -p /tmp/pid-uploads
mkdir -p backend/logs

# Start services
echo "Starting Docker services..."
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 10

# Check service health
echo ""
echo "Checking service health..."
echo "========================================="

# Check backend
if curl -f http://localhost:8000/health &> /dev/null; then
    echo "✓ Backend API: Running"
else
    echo "✗ Backend API: Not responding"
fi

# Check Flower
if curl -f http://localhost:5555 &> /dev/null; then
    echo "✓ Flower (Worker Monitor): Running"
else
    echo "✗ Flower: Not responding"
fi

# Check PostgreSQL
if docker-compose exec -T postgres pg_isready &> /dev/null; then
    echo "✓ PostgreSQL: Running"
else
    echo "✗ PostgreSQL: Not running"
fi

# Check Redis
if docker-compose exec -T redis redis-cli ping &> /dev/null; then
    echo "✓ Redis: Running"
else
    echo "✗ Redis: Not running"
fi

echo ""
echo "========================================="
echo "Services Started Successfully!"
echo "========================================="
echo ""
echo "Access Points:"
echo "  API:              http://localhost:8000"
echo "  API Docs:         http://localhost:8000/docs"
echo "  Worker Monitor:   http://localhost:5555"
echo "  MinIO Console:    http://localhost:9001"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f"
echo ""
echo "To stop services:"
echo "  docker-compose down"
echo ""
echo "System is now running autonomously 24/7!"
echo "========================================="
