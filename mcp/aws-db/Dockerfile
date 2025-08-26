# Use Python 3.13 as the base image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml README.md uv.lock ./
COPY db_evaluation_server/ ./db_evaluation_server/

# Install dependencies using uv
RUN uv sync

# Expose port (assuming the server runs on port 3000, adjust if different)
EXPOSE 3000

# Command to run the application
CMD ["uv", "run", "db-evaluation-server", "--transport", "http", "--port", "3000"]
