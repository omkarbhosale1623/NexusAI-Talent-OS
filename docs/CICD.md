# CI/CD & Developer Tooling

This repo ships a GitHub Actions pipeline plus local developer tooling so the
same checks run on every push, pull request, and on your machine before you
push.

## Pipeline overview

The workflow lives at [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)
and triggers on **push** and **pull_request** to `main`. Superseded runs on the
same ref are auto-cancelled to save CI minutes.

| Job | Runner | What it does |
| --- | --- | --- |
| **backend** | ubuntu-latest, Python 3.11 | Spins up `postgres:16` and `redis:7` service containers (health-checked), installs `backend/requirements.txt` (with pip cache), and runs `pytest` from `backend/` against the live services. Must pass. |
| **backend-lint** | ubuntu-latest, Python 3.11 | Installs `ruff` + `pip-audit`. Runs `ruff check app` (uses `backend/ruff.toml`). Then runs `pip-audit` on `backend/requirements.txt` as `continue-on-error` (report-only — known CVEs do not fail the build). |
| **frontend** | ubuntu-latest, Node 20 | `npm ci` in `frontend/` (falls back to `npm install` when no lockfile), `npm run lint --if-present`, then `npx next build`. |
| **docker** | ubuntu-latest | Validates that both `backend/Dockerfile` and `frontend/Dockerfile` build via `docker/build-push-action` with `push: false` (GHA build cache enabled). `needs: [backend, frontend]`. |
| **security-scan** | ubuntu-latest | `aquasecurity/trivy-action` filesystem scan, severity `HIGH,CRITICAL`, `exit-code: 0` (report-only, non-blocking). |

### Backend test environment

The `backend` job sets these env vars for `pytest`:

| Variable | Value | Notes |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+asyncpg://nexusai:nexusai@localhost:5432/nexusai_talent` | Points at the postgres service container. |
| `REDIS_URL` | `redis://localhost:6379/0` | Points at the redis service container. |
| `JWT_SECRET` | test value | Not for production. |
| `ENCRYPTION_KEY` | a valid Fernet key (test value) | `app.core.crypto` requires a urlsafe-base64 32-byte Fernet key; the dev fallback derives from `SECRET_KEY`, but CI sets a real one so encryption paths are exercised. |

## Required repo secrets

**For CI as configured: none beyond the GitHub defaults.** The service
containers, lint, build, and Trivy steps all run with the automatically
provided `GITHUB_TOKEN`; the test secrets are hard-coded throwaway values.

### Pushing images to a registry (when you enable it)

The `docker` job builds images but **does not push** them. To publish, add a
login step and flip `push: true`. Example for GitHub Container Registry (no extra
secret needed — `GITHUB_TOKEN` works):

```yaml
- name: Log in to GHCR
  uses: docker/login-action@v3
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}   # built-in
```

For Docker Hub or another registry, add repository secrets under
**Settings → Secrets and variables → Actions** and reference them:

| Secret | Used for |
| --- | --- |
| `DOCKERHUB_USERNAME` | `docker/login-action` username |
| `DOCKERHUB_TOKEN` | Docker Hub access token (password) |

Then set `push: true`, give the images real tags
(e.g. `ghcr.io/<owner>/nexusai-backend:${{ github.sha }}`), and grant the job
`permissions: { packages: write }` for GHCR.

## Dependabot

[`.github/dependabot.yml`](../.github/dependabot.yml) opens **weekly** update PRs
for: pip (`/backend`), npm (`/frontend`), github-actions (`/`), and docker
(`/backend` and `/frontend`).

## Running the same checks locally

### Backend tests

```bash
cd backend
# start postgres + redis however you prefer; the repo docker-compose.yml has them
export DATABASE_URL="postgresql+asyncpg://nexusai:nexusai@localhost:5432/nexusai_talent"
export REDIS_URL="redis://localhost:6379/0"
export JWT_SECRET="test-jwt-secret-not-for-production"
export ENCRYPTION_KEY="zZ2vH1nQ9k3mX7tY0pL5sR8wB4cD6fG1jK2lM3nO4pQ="
pytest
```

### Backend lint

```bash
pip install ruff pip-audit
cd backend
ruff check app          # uses backend/ruff.toml
ruff format --check app # formatting check
pip-audit -r requirements.txt   # advisory only
```

### Frontend

```bash
cd frontend
npm ci          # or: npm install
npm run lint
npx next build
```

### Docker builds

```bash
docker build -t nexusai-backend:local  -f backend/Dockerfile  backend
docker build -t nexusai-frontend:local -f frontend/Dockerfile frontend
```

> The frontend image uses Next.js **standalone** output
> (`output: "standalone"` in `next.config.ts`), so the container starts with
> `node server.js` — the standalone equivalent of `next start`. It runs as a
> non-root `nextjs` user and listens on port **3000**.

### Pre-commit hooks

[`.pre-commit-config.yaml`](../.pre-commit-config.yaml) wires up the hygiene
and lint checks, plus a **pre-push** hook that runs `pytest -q` in `backend/`.

```bash
pip install pre-commit
pre-commit install --install-hooks      # commit-time hooks
pre-commit install --hook-type pre-push # the backend test gate
pre-commit run --all-files              # run everything on demand
```

Hooks configured:

- **ruff** (lint, with `--fix`) and **ruff-format** (`--check`) on `backend/`
- **trailing-whitespace**, **end-of-file-fixer**
- **check-yaml**, **check-added-large-files**
- local **backend-pytest** running `pytest -q` in `backend/` on push
