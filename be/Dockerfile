# Use Python 3.13 as the base image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml README.md ./
COPY app/ ./app/

# Install dependencies
# RUN pip install --no-cache-dir .
RUN uv sync

# Expose port
EXPOSE 8000

# Command to run the application
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--loop", "asyncio"]
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--loop", "asyncio"]