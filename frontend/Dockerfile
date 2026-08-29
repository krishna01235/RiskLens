# ── Stage 1: deps ─────────────────────────────────────────────────────────────
# Install dependencies separately so Docker layer cache is not busted by
# source-code changes when deps have not changed.
FROM node:20-alpine AS deps

WORKDIR /frontend

COPY package.json package-lock.json* ./
RUN npm ci

# ── Stage 2: builder ──────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /frontend

COPY --from=deps /frontend/node_modules ./node_modules
COPY . .

# NEXT_PUBLIC_API_URL is baked in at build time; default points to the
# Compose API service.
ARG NEXT_PUBLIC_API_URL=http://api:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm run build

# ── Stage 3: runner ───────────────────────────────────────────────────────────
# Minimal production image — only the Next.js server artefacts.
FROM node:20-alpine AS runner

ENV NODE_ENV=production
WORKDIR /frontend

# next.config.js and public assets
COPY --from=builder /frontend/public ./public
COPY --from=builder /frontend/.next/standalone ./
COPY --from=builder /frontend/.next/static ./.next/static

EXPOSE 3000

CMD ["node", "server.js"]
