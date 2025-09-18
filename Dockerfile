# Dockerfile for Shrimp Service with Frontend
FROM node:18-alpine AS frontend-builder

# Build frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --only=production
COPY frontend/ ./
RUN npm run build

# Main application stage
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    nginx \
    supervisor \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create app directory
WORKDIR /app
COPY shrimp/ ./

RUN pip config set global.index-url http://mirrors.aliyun.com/pypi/simple/ && \
    pip config set global.trusted-host mirrors.aliyun.com 

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Copy built frontend from builder stage
COPY --from=frontend-builder /app/frontend/build /usr/share/nginx/html

# Configure Nginx
COPY docker/nginx.conf /etc/nginx/nginx.conf

# Configure Supervisor to manage processes
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

RUN addgroup --system nginx
RUN adduser --system --no-create-home --ingroup nginx nginx && mkdir -p /var/log/nginx && touch /var/log/nginx/error.log && touch /var/log/nginx/access.log && chown -R nginx:nginx /var/log/nginx && chmod -R 755 /var/log/nginx

# Expose ports
EXPOSE 80 4444

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:80/api/health || exit 1

# Start supervisor to manage all services
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
