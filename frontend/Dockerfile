# Multi-stage production build for the Next.js 16 frontend.
# next.config.ts sets `output: "standalone"`, so the runner only needs the
# self-contained .next/standalone server plus static assets.

# ── Stage 1: install dependencies ────────────────────────────────────────────
FROM node:25-alpine AS deps
WORKDIR /app
# libc6-compat is needed by some native deps on Alpine.
RUN apk add --no-cache libc6-compat
COPY package.json package-lock.json* ./
# Use a clean, reproducible install when a lockfile is present.
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

# ── Stage 2: build ───────────────────────────────────────────────────────────
FROM node:25-alpine AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# ── Stage 3: production runner ───────────────────────────────────────────────
FROM node:25-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

# Run as a non-root user.
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

# Copy the standalone output, static assets and public files with correct owner.
COPY --from=builder --chown=nextjs:nodejs /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000

# The standalone build emits server.js; `next start` is equivalent for it.
CMD ["node", "server.js"]
