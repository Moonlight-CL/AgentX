# Build stage
FROM oven/bun:latest AS build

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json bun.lockb ./

# Install dependencies
RUN bun install --frozen-lockfile

# Copy all files
COPY . .

# Build the application
RUN bun run build

# Production stage
FROM nginx:stable-alpine

# Copy built files from build stage to nginx serve directory
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy environment variable injection script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Expose port
EXPOSE 80

# Modify nginx keepalive_timeout to 600
RUN sed -i 's/keepalive_timeout[[:space:]]*[0-9]\+;/keepalive_timeout 600;/g' /etc/nginx/nginx.conf

# Use custom entrypoint to inject environment variables
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
