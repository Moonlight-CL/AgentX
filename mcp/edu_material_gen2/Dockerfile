# Use Python 3.13 as the base image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml README.md uv.lock ./
COPY edu_material_server/ ./edu_material_server/
COPY .env ./

# Install dependencies using uv
RUN uv sync

# Expose port (assuming the server runs on port 3001, adjust if different)
EXPOSE 3666

# Command to run the application
CMD ["uv", "run", "edu_material_server", "--transport", "http", "--port", "3666"]
