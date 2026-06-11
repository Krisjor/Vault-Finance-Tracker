FROM node:20-alpine

WORKDIR /app

# Install deps first for layer caching
COPY package*.json ./
RUN npm install

# Application code
COPY . .

EXPOSE 5173

# Dev server by default (docker-compose overrides if needed)
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
