FROM node:20-bookworm-slim

WORKDIR /app
RUN corepack enable && corepack prepare pnpm@9.15.4 --activate

COPY package.json pnpm-workspace.yaml turbo.json tsconfig.base.json ./
COPY apps ./apps
COPY packages ./packages
COPY services/api/app/data ./services/api/app/data

ARG APP_FILTER
RUN pnpm install --frozen-lockfile=false

EXPOSE 3000 3001
CMD ["pnpm", "dev"]
