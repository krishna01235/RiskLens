# RiskLens Deployment Guide

This guide describes how to deploy the RiskLens stack to production. The architecture is split between **Render** (for all backend services, workers, database, and Redis) and **Vercel** (for the Next.js frontend).

## 1. Backend Deployment (Render)

We use Render's Infrastructure-as-Code (`render.yaml`) to define the entire backend stack.

### Prerequisites
- A Render account (and a connected GitHub account).
- The `render.yaml` file committed to the `main` branch.

### Deployment Steps
1. Go to the [Render Dashboard](https://dashboard.render.com).
2. Click **New +** and select **Blueprint**.
3. Connect this GitHub repository.
4. Render will read the `render.yaml` file and propose creating:
   - 1 Postgres Database (`risklens-db`)
   - 1 Redis Instance (`risklens-redis`)
   - 1 Web Service (`risklens-api`)
   - 7 Background Workers (Ingestion, Fast-Path, Slow-Path, GARCH, Regime, Decision Engine, Job/Arq Worker)
   - 1 Slack Bot Worker
5. Click **Apply**.
6. Render will begin provisioning the services. Note that for free/starter tiers, initial builds might take 5-10 minutes.

### Setting Secrets
The `render.yaml` specifies certain variables as `sync: false`. You MUST manually set these in the Render Dashboard -> Environment Groups or on each service:
- `JWT_SECRET_KEY`: A strong, random string (e.g. generated via `openssl rand -hex 32`).
- `FINNHUB_API_KEY`: Your Finnhub API Key.
- `ANTHROPIC_API_KEY`: Your Anthropic (Claude) API Key.
- `SLACK_BOT_TOKEN` & `SLACK_APP_TOKEN`: From your Slack App configuration.

### Database Migrations
The `render.yaml` configures a `preDeployCommand` for the API service:
```bash
cd backend && alembic upgrade head
```
This ensures the production database schema is automatically updated *before* the new API code runs.

## 2. Frontend Deployment (Vercel)

Vercel provides native Next.js hosting.

### Deployment Steps
1. Go to the [Vercel Dashboard](https://vercel.com/dashboard).
2. Click **Add New** -> **Project**.
3. Import this GitHub repository.
4. Expand the **Build and Output Settings** section. Ensure the Framework Preset is **Next.js**.
5. Change the **Root Directory** to `frontend`.
6. Expand **Environment Variables** and add the following:
   - `NEXT_PUBLIC_API_URL`: The public URL of your Render API service (e.g. `https://risklens-api.onrender.com`).
   - `NEXT_PUBLIC_WS_URL`: The WebSocket URL (e.g. `wss://risklens-api.onrender.com/ws`).
7. Click **Deploy**.

## 3. CI/CD Integration

We have two GitHub Actions configured:
1. `.github/workflows/ci.yml`: Runs on all PRs. Runs linting, type-checking, backend `pytest`, frontend `vitest`, and Playwright E2E tests against a docker-compose stack.
2. `.github/workflows/deploy.yml`: Runs on merge to `main`. This triggers deploy hooks to ensure Vercel and Render update simultaneously. 

To use the automated deploy hooks, set these Secrets in your GitHub Repository settings:
- `RENDER_API_DEPLOY_HOOK`: The deploy hook URL for the API service (found in Render Settings).
- `RENDER_WORKER_DEPLOY_HOOK`: Deploy hook URL(s) for the workers (if you want them triggered via GH Actions).
- `VERCEL_DEPLOY_HOOK`: Vercel deploy hook URL (optional, Vercel natively monitors `main`).
- `PROD_API_URL`: Used for the post-deploy smoke test (e.g., `https://risklens-api.onrender.com`).
