FROM node:22-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY tsconfig.json vite.config.ts ./
COPY src ./src
RUN npm run build

FROM node:22-slim
ENV NODE_ENV=production
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force
COPY --from=build /app/dist ./dist
COPY public ./public

# SQLite database lives in /app/instance (mounted as a volume)
RUN useradd --system --uid 10001 app \
    && mkdir -p /app/instance \
    && chown -R app:app /app/instance
USER app

EXPOSE 5001
CMD ["node", "dist/server.js"]
