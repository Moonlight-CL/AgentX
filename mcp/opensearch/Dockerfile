# Use Python 3.13 as the base image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install dependencies and curl
RUN pip install --no-cache-dir opensearch-mcp-server-py && \
    apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose port for streaming transport
EXPOSE 3000

# Create directory for configuration files
RUN mkdir -p /app/config

# Copy configuration file
COPY cluster.yaml /app/config/

# Command to run the server with multi-mode and stream transport
CMD ["python", "-m", "mcp_server_opensearch", "--mode", "multi", "--port", "3000", "--config", "/app/config/cluster.yaml", "--transport", "stream"]
