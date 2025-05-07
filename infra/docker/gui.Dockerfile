FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy project
COPY . .

# Expose port
EXPOSE 5173

# Run the development server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]