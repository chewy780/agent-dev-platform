FROM node:18-bullseye-slim AS build
WORKDIR /app

# Copy package and lockfiles first
COPY package*.json ./

# Use clean, reproducible install from lockfile
RUN npm ci --omit=dev --no-audit --no-fund

# Copy source
COPY . .

# Build
ENV CI=false GENERATE_SOURCEMAP=false
RUN npm run build

# Runtime
FROM nginx:alpine
COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
