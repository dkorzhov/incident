FROM node:22-slim

# DMI-12: кэш Vite — в /tmp, а не в node_modules внутри смонтированного worktree.
# Иначе dev-сервер в контейнере с bind-mount оставляет root-owned
# `node_modules/.vite`, и `git worktree remove` / `orca worktree rm` падают
# с Permission denied. Значение можно переопределить: `-e VITE_CACHE_DIR=...`.
ENV VITE_CACHE_DIR=/tmp/vite-cache

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev"]