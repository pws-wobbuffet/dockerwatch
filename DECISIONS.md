# DECISIONS.md

## Phase 0 — Ideation

### Candidate Ideas

#### Idea 1: DockerWatch — Container Resource Monitor
- **Description:** A real-time web dashboard that monitors all Docker containers on the host (CPU, memory, network I/O, logs, start/stop).
- **Tech stack:** Python 3.11 + FastAPI + Docker Python SDK + Server-Sent Events + vanilla JS
- **Why it fits:** Uses Docker socket (available, no external API), single container with socket mount, directly useful on this Pi which runs production containers.
- **Score estimate:** 86/100
  - Technical depth: 22/25 (SSE streaming, Docker stats parsing, async API)
  - Practical utility: 24/25 (genuinely needed on this host)
  - Code quality: 17/20 (clean FastAPI, typed models)
  - Docker portability: 13/15 (single service, socket mount, .env.example)
  - README clarity: 10/15

#### Idea 2: FeedForge — Self-hosted RSS Digest
- **Description:** A self-hosted RSS aggregator that fetches, stores, and serves a clean reading interface with full-text search.
- **Tech stack:** Python + SQLite + feedparser + vanilla JS
- **Score estimate:** 74/100
  - Requires network for feed fetching (acceptable but less interesting offline)
  - Lower technical depth; RSS is a solved problem
  - Deferred in favor of Idea 1

#### Idea 3: GitPulse — Local Git Repository Health Analyzer
- **Description:** Scans mounted git repos and produces health metrics (commit frequency, stale branches, contributor stats, code churn) in a web dashboard.
- **Tech stack:** Python + FastAPI + GitPython + SQLite + Chart.js + vanilla JS
- **Score estimate:** 79/100
  - Good technical depth but requires mounting arbitrary paths
  - DockerWatch is more immediately applicable to this host
  - Deferred in favor of Idea 1

---

## Decision: DockerWatch selected

**Rationale:** Highest score (86/100), directly solves a real need on this host (monitoring `polybot-live` and `polybot-shadow`), requires no external APIs, and the Docker SDK + SSE combination provides meaningful technical depth without overreaching on resources (1.8 GiB RAM).

---

## Build-phase decisions

<!-- Appended as decisions are made during Phase 2 -->

### D-001: Run container process as non-root with docker GID 992
**Decision:** Create a non-root user `app` (uid 1000) inside the container and add it to a group with GID 992 (the host docker group) so it can access the socket without running as root.
**Rationale:** Running as root inside a container that mounts the Docker socket is effectively root on the host. GID-matching is the correct minimal-privilege approach.

### D-002: Use polling (3 s interval) instead of persistent SSE stream per container
**Decision:** The frontend polls `GET /api/containers` every 3 seconds rather than opening a long-lived SSE connection per container.
**Rationale:** The Docker stats API with `stream=False` requires one HTTP call per container per tick regardless. SSE would add complexity without removing the per-container blocking calls. Polling keeps the backend stateless and the frontend simple.

### D-003: Stats fetched concurrently with ThreadPoolExecutor
**Decision:** Container stats calls are dispatched concurrently using `asyncio.run_in_executor` (ThreadPoolExecutor) to avoid blocking the event loop while Docker SDK makes blocking calls.
**Rationale:** The Docker Python SDK is synchronous. Without concurrency, fetching stats for N running containers takes N * ~1 s sequentially. Concurrent fetching caps latency at ~1 s regardless of container count.

### D-004: Log viewer uses tail-100 by default, user-selectable up to 500
**Decision:** Logs endpoint accepts `?tail=N` capped at 500 lines.
**Rationale:** Unbounded log fetch on a resource-constrained Pi could OOM the process. 500 lines covers any reasonable inspection need.
