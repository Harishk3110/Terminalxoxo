FROM node:22-bookworm-slim

WORKDIR /app
RUN corepack enable && corepack prepare pnpm@9.15.4 --activate

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml turbo.json tsconfig.base.json ./
COPY apps ./apps
COPY packages ./packages
COPY services/api/app/data ./services/api/app/data

ARG APP_FILTER=@knk/terminal-web
ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_PUBLIC_APP_ENV=local
ENV KNK_API_URL=http://api:8000
RUN pnpm install --frozen-lockfile
RUN pnpm --filter "${APP_FILTER}" build
RUN chown -R node:node /app/apps/terminal-web/.next

ENV NODE_ENV=production
USER node
EXPOSE 3001
CMD ["pnpm", "--filter", "@knk/terminal-web", "start", "--hostname", "0.0.0.0", "--port", "3001"]
