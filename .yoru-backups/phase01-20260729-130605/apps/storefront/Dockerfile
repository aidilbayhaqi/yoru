FROM node:24-alpine AS dependencies
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/storefront/package.json apps/storefront/package.json
COPY packages/contracts/package.json packages/contracts/package.json
COPY packages/ui/package.json packages/ui/package.json
RUN pnpm install --frozen-lockfile

FROM dependencies AS builder
COPY apps/storefront apps/storefront
COPY packages packages
RUN pnpm --filter @yoru/storefront build

FROM node:24-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN corepack enable && addgroup -S yoru && adduser -S yoru -G yoru
COPY --from=builder --chown=yoru:yoru /app ./
USER yoru
EXPOSE 3000
CMD ["pnpm", "--filter", "@yoru/storefront", "start"]
