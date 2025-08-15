#!/bin/bash

# Shrimp Service Deployment Script
# This script builds and runs the Shrimp service with frontend and MongoDB

echo "🦐 Starting Shrimp Service Deployment..."

# Check if Docker and Docker Compose are installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create logs directory
mkdir -p logs

# Function to show usage
show_usage() {
    echo "Usage: $0 [build|up|down|restart|logs|status]"
    echo ""
    echo "Commands:"
    echo "  build    - Build the Docker images"
    echo "  up       - Start all services"
    echo "  down     - Stop all services"
    echo "  restart  - Restart all services"
    echo "  logs     - Show logs from all services"
    echo "  status   - Show status of all services"
    echo ""
    exit 1
}

# Parse command
case "${1:-up}" in
    "build")
        echo "🔨 Building Docker images..."
        docker-compose build --no-cache
        echo "✅ Build completed successfully!"
        ;;
        
    "up")
        echo "🚀 Starting Shrimp services..."
        docker-compose down
        docker-compose up -d
        
        echo "⏳ Waiting for services to be ready..."
        sleep 10
        
        # Check if services are healthy
        echo "🔍 Checking service health..."
        
        # Wait for MongoDB
        echo "  Waiting for MongoDB..."
        timeout=60
        while [ $timeout -gt 0 ]; do
            if docker-compose exec -T mongodb mongosh --eval "db.adminCommand('ping')" > /dev/null 2>&1; then
                echo "  ✅ MongoDB is ready"
                break
            fi
            sleep 2
            timeout=$((timeout - 2))
        done
        
        if [ $timeout -le 0 ]; then
            echo "  ❌ MongoDB failed to start"
            exit 1
        fi
        
        # Wait for Shrimp app
        echo "  Waiting for Shrimp app..."
        timeout=60
        while [ $timeout -gt 0 ]; do
            if curl -f http://localhost:80/health > /dev/null 2>&1; then
                echo "  ✅ Shrimp app is ready"
                break
            fi
            sleep 2
            timeout=$((timeout - 2))
        done
        
        if [ $timeout -le 0 ]; then
            echo "  ❌ Shrimp app failed to start"
            exit 1
        fi
        
        echo ""
        echo "🎉 Shrimp services are now running!"
        echo ""
        echo "📱 Frontend: http://localhost:80"
        echo "🔗 API: http://localhost:4444"
        echo "🍃 MongoDB: localhost:27017"
        echo ""
        echo "Use '$0 logs' to view logs"
        echo "Use '$0 down' to stop services"
        ;;
        
    "down")
        echo "🛑 Stopping Shrimp services..."
        docker-compose down
        echo "✅ Services stopped successfully!"
        ;;
        
    "restart")
        echo "🔄 Restarting Shrimp services..."
        docker-compose restart
        echo "✅ Services restarted successfully!"
        ;;
        
    "logs")
        echo "📋 Showing logs from all services..."
        docker-compose logs -f
        ;;
        
    "status")
        echo "📊 Service status:"
        docker-compose ps
        
        echo ""
        echo "🔍 Health checks:"
        
        # Check MongoDB
        if docker-compose exec -T mongodb mongosh --eval "db.adminCommand('ping')" > /dev/null 2>&1; then
            echo "  MongoDB: ✅ Healthy"
        else
            echo "  MongoDB: ❌ Unhealthy"
        fi
        
        # Check Shrimp app
        if curl -f http://localhost:80/api/health > /dev/null 2>&1; then
            echo "  Shrimp App: ✅ Healthy"
        else
            echo "  Shrimp App: ❌ Unhealthy"
        fi
        ;;
        
    *)
        show_usage
        ;;
esac
