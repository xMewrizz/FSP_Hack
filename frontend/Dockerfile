# NOTE: frontend переносится из готовых макетов (React+Vite+Tailwind).
# Dockerfile-заглушка — бэкендер/фронт поправят под реальный package.json.
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install || true
COPY . .
RUN npm run build || (mkdir -p dist && echo "placeholder" > dist/index.html)

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
