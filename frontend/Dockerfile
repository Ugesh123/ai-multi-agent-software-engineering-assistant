# syntax=docker/dockerfile:1

# ---- Builder: install deps and produce the production build -----------
FROM node:22-slim AS builder

WORKDIR /build
COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

# ---- Runtime: nginx serving the static build + API reverse proxy ------
FROM nginx:1.27-alpine AS runtime

COPY --from=builder /build/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost:80/ >/dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
