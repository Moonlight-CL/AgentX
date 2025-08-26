# Use Python 3.13 as the base image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml README.md uv.lock ./
COPY rds_aurora_multi_generation_pricing_analyzer_taz.py ./
COPY db-evaluation-server/ ./db-evaluation-server/
COPY .env ./

# Install dependencies using uv
RUN uv sync

# Expose port (assuming the server runs on port 3001, adjust if different)
EXPOSE 3001

# Command to run the application
CMD ["python", "-m", "db-evaluation-server", "--transport", "http", "--port", "3001", "--env_file", "./.env"]
