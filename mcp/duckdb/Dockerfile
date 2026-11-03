FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Create and set working directory
WORKDIR /app

# Create a directory for DuckDB database files
RUN mkdir -p /data

# Install DuckDB and mcp-server-motherduck
RUN uv venv && uv pip install duckdb mcp-server-motherduck

# Copy the map_application.duckdb file into the image
COPY map_application.duckdb /data/map_application.duckdb

# Expose the port the server will run on
EXPOSE ${PORT}

# Set up a volume for persistent data
VOLUME /data

# Command to run the server
# Using the map_application.duckdb file as the database
CMD ["uvx", "mcp-server-motherduck", "--transport", "stream", "--port", "8000", "--db-path", "/data/map_application.duckdb"]

# To use MotherDuck:
# docker run -e MOTHERDUCK_TOKEN=your_token -e PORT=8000 image_name uvx mcp-server-motherduck --transport stream --port 8000 --db-path md: --motherduck-token ${MOTHERDUCK_TOKEN} --host 0.0.0.0
