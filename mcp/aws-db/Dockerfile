# Use Python 3.13 as the base image
FROM python:3.13-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl mariadb-client \
    && curl -L "https://packagecloud.io/akopytov/sysbench/packages/ubuntu/focal/sysbench_1.0.20-1_amd64.deb/download.deb?distro_version_id=210" -o /tmp/sysbench.deb \
    && dpkg -i /tmp/sysbench.deb || true \
    && apt-get update \
    && apt-get -y install -f --no-install-recommends \
    && sed -i 's/#ssl-verify-server-cert = on/disable-ssl-verify-server-cert/' /etc/mysql/mariadb.conf.d/50-client.cnf \
    && rm /tmp/sysbench.deb \
    && apt-get purge -y --auto-remove curl \
    && rm -rf /var/lib/apt/lists/*

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
