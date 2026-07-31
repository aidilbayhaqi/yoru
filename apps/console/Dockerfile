FROM node:24-alpine AS dependencies
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/console/package.json apps/console/package.json
COPY packages/contracts/package.json packages/contracts/package.json
COPY packages/ui/package.json packages/ui/package.json
RUN pnpm install --frozen-lockfile

FROM dependencies AS builder
COPY apps/console apps/console
COPY packages packages
RUN pnpm --filter @yoru/console build

FROM node:24-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN corepack enable && addgroup -S yoru && adduser -S yoru -G yoru
COPY --from=builder --chown=yoru:yoru /app ./
USER yoru
EXPOSE 3001
CMD ["pnpm", "--filter", "@yoru/console", "start"]
