FROM node:22-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG VITE_API_URL=http://localhost:8080
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# Stage 2: Serve static files
FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN npm install serve --omit=dev
COPY --from=builder /app/dist ./dist
USER node
EXPOSE 3000
CMD ["npx", "serve", "-s", "dist", "-l", "3000"]