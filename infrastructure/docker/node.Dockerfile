FROM node:22-bookworm-slim

WORKDIR /app
RUN corepack enable && corepack prepare pnpm@9.15.4 --activate

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml turbo.json tsconfig.base.json ./
COPY apps ./apps
COPY packages ./packages
COPY services/api/app/data ./services/api/app/data

ARG APP_FILTER
RUN pnpm install --frozen-lockfile

EXPOSE 3000 3001
CMD ["pnpm", "dev"]
