# Build stage
FROM node:18-alpine as builder

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy project
COPY ./gui ./gui
COPY ./tsconfig.json ./tsconfig.json
COPY ./vite.config.ts ./vite.config.ts
COPY ./vitest.config.ts ./vitest.config.ts
COPY ./.eslintrc.json ./.eslintrc.json

# Build the app
WORKDIR /app
RUN npm run build

# Development stage
FROM node:18-alpine as development

WORKDIR /app

# Copy package.json and package-lock.json
COPY package.json package-lock.json ./

# Install dependencies with development dependencies
RUN npm ci

# Copy source code for development with hot reload
COPY ./gui ./gui
COPY ./tsconfig.json ./tsconfig.json
COPY ./vite.config.ts ./vite.config.ts
COPY ./vitest.config.ts ./vitest.config.ts
COPY ./.eslintrc.json ./.eslintrc.json

# Expose development port
EXPOSE 5173

# Start development server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# Production stage
FROM nginx:alpine as production

# Copy built files from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY infra/docker/nginx.conf /etc/nginx/conf.d/default.conf

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://localhost:80/ || exit 1

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]