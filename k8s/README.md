# NexusAI Talent OS — Kubernetes manifests

Production-oriented (but self-contained) Kubernetes manifests for deploying
NexusAI Talent OS: FastAPI backend, Celery worker, Next.js frontend, plus
in-cluster PostgreSQL 16 and Redis 7.

## Contents

| File | What it deploys |
|------|-----------------|
| `namespace.yaml` | `nexusai` namespace |
| `configmap.yaml` | Non-secret app + frontend config |
| `secret.yaml` | Secrets (PLACEHOLDERS — replace before deploy) |
| `postgres.yaml` | PostgreSQL 16 StatefulSet + headless Service + PVC |
| `redis.yaml` | Redis 7 Deployment + Service (appendonly) |
| `backend.yaml` | FastAPI Deployment (2 replicas) + Service + migration initContainer |
| `celery-worker.yaml` | Celery worker Deployment (no Service) |
| `frontend.yaml` | Next.js Deployment (2 replicas) + Service |
| `ingress.yaml` | nginx Ingress, `/api`→backend, `/`→frontend, TLS via cert-manager |
| `hpa.yaml` | HPAs for backend + frontend (CPU 70%, 2–10 replicas) |
| `networkpolicy.yaml` | Default-deny ingress + explicit allows (zero-trust east-west) |
| `pdb.yaml` | PodDisruptionBudgets for backend + frontend (`minAvailable: 1`) |
| `resourcequota.yaml` | Namespace ResourceQuota + LimitRange defaults |
| `serviceaccount.yaml` | Dedicated `nexusai-backend` SA (token automount off) |
| `external-secrets.yaml` | EXAMPLE External Secrets Operator config (needs ESO CRDs; not applied by default) |
| `servicemonitor.yaml` | EXAMPLE Prometheus Operator ServiceMonitor (needs CRDs; not applied by default) |
| `kustomization.yaml` | Ties it all together for `kubectl apply -k` |
| `kafka.optional.yaml` | OPTIONAL single-node Kafka (not applied by default) |

## 1. Build & push images

The manifests reference `nexusai/backend:latest` and `nexusai/frontend:latest`.
Replace `nexusai` with your registry (e.g. `ghcr.io/yourorg`).

```bash
# from repo root
docker build -t nexusai/backend:latest  ./backend
docker build -t nexusai/frontend:latest ./frontend
docker push nexusai/backend:latest
docker push nexusai/frontend:latest
```

Pin a real tag in production via the `images:` block in `kustomization.yaml`
rather than relying on `:latest`.

## 2. Set secrets

Edit `secret.yaml` and replace every `REPLACE_*` placeholder. At minimum:

- `JWT_SECRET`, `SECRET_KEY` — `openssl rand -base64 48`
- `POSTGRES_PASSWORD` and the matching password inside `DATABASE_URL`
- `LLM_API_KEY`, `OPENAI_API_KEY`

`DATABASE_URL` must use the asyncpg driver and the in-cluster host `postgres`,
and its user/password/db must match the `POSTGRES_*` keys in the same Secret.

> Do not commit real secrets. Use Sealed Secrets, External Secrets Operator,
> or SOPS in real environments.

## 3. Adjust config

In `configmap.yaml` and `ingress.yaml` replace `nexusai.example.com` with your
real domain (keep `APP_BASE_URL`, `API_BASE_URL`, `CORS_ORIGINS`,
`NEXT_PUBLIC_API_URL`, the Ingress `host`, and TLS `hosts` consistent).

## 4. Deploy

```bash
# Validate structure without contacting a cluster:
kubectl apply --dry-run=client -k k8s/

# Apply:
kubectl apply -k k8s/

# Watch rollout:
kubectl -n nexusai get pods -w
```

Database migrations (`alembic upgrade head`) run automatically via the
backend's `migrate` initContainer on every rollout.

### Alternative: migrations as a one-shot Job

The initContainer approach runs the migration in every backend pod (alembic's
lock makes concurrent runs safe; later runs are no-ops). For large clusters you
may prefer a dedicated `Job` that runs once per release and gate the Deployment
behind it. The initContainer is kept here for simplicity and ordering
guarantees.

## Enterprise hardening

This bundle ships several hardening manifests. Four are applied by default
via `kustomization.yaml`; two are CRD-dependent examples kept out of the
default apply.

### Applied by default

- **NetworkPolicies** (`networkpolicy.yaml`) — namespace-wide **default-deny
  ingress**, then explicit allows:
  - backend ← ingress-nginx **and** frontend on `8000`; backend egress →
    `postgres:5432`, `redis:6379`, DNS (`53` UDP/TCP), and `443` (external
    LLM/APIs/object storage).
  - frontend ← ingress-nginx on `3000`.
  - postgres ← backend + celery-worker **only** on `5432`.
  - redis ← backend + celery-worker **only** on `6379`.
  - Selectors match the existing `app.kubernetes.io/name` labels.
  - The ingress allows assume ingress-nginx runs in a namespace labelled
    `kubernetes.io/metadata.name: ingress-nginx` — adjust if yours differs.
  - **Enforcement requires a policy-capable CNI** (Calico/Cilium/Antrea/…).
    Plain Flannel accepts these objects but does not enforce them.

- **PodDisruptionBudgets** (`pdb.yaml`) — `minAvailable: 1` for backend and
  frontend so node drains/upgrades never take a web tier fully down. (Both
  run ≥2 replicas.) Postgres and celery-worker run a single replica and are
  intentionally left without a PDB — a `minAvailable: 1` PDB on a 1-replica
  workload would block node drains entirely.

- **ResourceQuota + LimitRange** (`resourcequota.yaml`) — caps total
  namespace CPU/memory requests+limits and key object counts, and supplies
  default per-container requests/limits + min/max bounds. Note: once a quota
  on requests/limits exists, every container must declare them — the
  LimitRange defaults cover any container that forgets.

- **Dedicated ServiceAccount** (`serviceaccount.yaml`) — `nexusai-backend`
  with `automountServiceAccountToken: false`. The backend does not call the
  Kubernetes API, so it runs least-privilege with no projected token.
  **Wiring:** add to the pod template `spec` in both `backend.yaml` and
  `celery-worker.yaml`:

  ```yaml
  spec:
    template:
      spec:
        serviceAccountName: nexusai-backend
        automountServiceAccountToken: false   # belt-and-suspenders
        # ...existing securityContext / containers...
  ```

### Requires extra operators/CRDs (excluded from default kustomization)

- **External Secrets** (`external-secrets.yaml`) — example `SecretStore` +
  `ExternalSecret` (`external-secrets.io/v1beta1`) sourcing `nexusai-secrets`
  from AWS Secrets Manager **or** HashiCorp Vault. Needs the **External
  Secrets Operator** + CRDs installed. When adopting it, also remove
  `secret.yaml` from `kustomization.yaml` so the placeholder Secret no longer
  overwrites the ESO-owned one, then add `external-secrets.yaml` to
  `resources`.

- **ServiceMonitor** (`servicemonitor.yaml`) — Prometheus Operator
  `ServiceMonitor` (`monitoring.coreos.com/v1`) scraping the backend Service's
  named `http` port at `/metrics`. Needs the **Prometheus Operator** + CRDs.
  It's an alternative to the `prometheus.io/scrape` pod annotations already on
  `backend.yaml`; use one or the other. The ServiceMonitor's own labels must
  satisfy your Prometheus CR's `serviceMonitorSelector` (the `release:`
  label).

### OpenTelemetry tracing

The backend already supports OTLP export via settings — set
`OTEL_EXPORTER_OTLP_ENDPOINT` (and optionally `OTEL_SERVICE_NAME`,
`OTEL_EXPORTER_OTLP_HEADERS`) in `configmap.yaml` to ship traces to a
collector (e.g. the OpenTelemetry Collector, Tempo, or Jaeger), e.g.:

```yaml
# configmap.yaml -> nexusai-config data:
OTEL_EXPORTER_OTLP_ENDPOINT: "http://otel-collector.observability:4317"
```

If you adopt the NetworkPolicies, add an egress allow for the collector's
port/namespace to the backend (and celery-worker) — the current backend
egress policy only opens `443`, DNS, postgres, and redis.

### Still needs cluster-level setup (honest list)

These cannot be expressed in these manifests alone and must be provisioned
at the cluster/platform layer:

- **A NetworkPolicy-enforcing CNI** (Calico/Cilium/Antrea/Weave). Without it
  `networkpolicy.yaml` is inert.
- **External Secrets Operator** and **Prometheus Operator** (+ their CRDs)
  before applying `external-secrets.yaml` / `servicemonitor.yaml`, plus the
  rest of the observability stack (Prometheus/Grafana/Alertmanager, log
  aggregation, an OTel collector backend).
- **mTLS / a service mesh** (Istio/Linkerd) for encrypted, authenticated
  pod-to-pod traffic — NetworkPolicy controls *who* can connect, not
  *encryption*.
- **Image supply-chain security** — image signing & verification with
  cosign/Sigstore, an admission policy that rejects unsigned images, plus
  vulnerability scanning and pinned digests instead of `:latest`.
- **Pod Security Admission** — enforce the `restricted` PSA level on the
  `nexusai` namespace (label
  `pod-security.kubernetes.io/enforce: restricted`). The workloads already
  set non-root, dropped capabilities, read-only root FS, and the
  RuntimeDefault seccomp profile, so they should comply.

## Cluster prerequisites

- `ingress-nginx` controller (for `ingress.yaml`)
- `cert-manager` + a `ClusterIssuer` named `letsencrypt-prod` (for TLS)
- `metrics-server` (for the HPAs)
- A default StorageClass (for the Postgres PVC)

## MVP vs. real production — honest gaps

This bundle is a solid, internally-consistent MVP that runs end-to-end, but a
hardened production cluster still needs:

- **Managed datastores.** The in-cluster Postgres is a single replica with no
  automated backups/HA, and Redis here is ephemeral (`emptyDir`). Use a managed
  DB (RDS/Cloud SQL/Neon) and managed/HA Redis in real prod. Comments in the
  manifests call this out.
- **Secrets management.** Replace `secret.yaml` with Sealed Secrets / External
  Secrets Operator / Vault. Never commit real values.
- **PodDisruptionBudgets** for backend/frontend/worker so voluntary
  disruptions (node drains) don't take a service fully down.
- **NetworkPolicies** to restrict pod-to-pod traffic (e.g. only backend +
  worker may reach Postgres/Redis).
- **Observability stack.** Pods expose `/metrics` with Prometheus scrape
  annotations, but you still need Prometheus + Grafana + Alertmanager and log
  aggregation (Loki/ELK). Wire `SENTRY_DSN` for error tracking.
- **Resource tuning & autoscaling on real metrics.** Requests/limits here are
  starting estimates; tune from observed usage. Consider HPA on RPS/latency
  (custom metrics) not just CPU, and a worker HPA based on queue depth.
- **Image supply chain.** Pin digests, scan images, and avoid `:latest`.
- **Backups & DR**, **HTTPS-only redirects / WAF**, and **RBAC/ServiceAccounts**
  scoped per workload.
- **Optional Kafka** (`kafka.optional.yaml`) is a single-node demo; use Strimzi
  or a managed Kafka for production streaming.
