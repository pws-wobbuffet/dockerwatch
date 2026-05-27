# ARCHITECTURE.md

## DockerWatch — System Architecture

### Overview

DockerWatch is a single-container web application that speaks to the host Docker daemon via the Unix socket and presents a real-time monitoring dashboard in the browser.

```
Browser
  │  HTTP polling (every 3 s)
  │  GET /api/containers
  │  GET /api/containers/{id}/logs
  │  POST /api/containers/{id}/start|stop
  ▼
┌─────────────────────────────────────┐
│  dockerwatch container              │
│                                     │
│  Uvicorn (port 8080)                │
│    └─ FastAPI app (src/main.py)     │
│         ├─ /api/*  (JSON REST)      │
│         └─ /       (static HTML)    │
│                                     │
│  src/docker_client.py               │
│    └─ docker.DockerClient           │
│         (concurrent stats fetch)    │
└──────────────┬──────────────────────┘
               │ unix socket
               ▼
       /var/run/docker.sock  (host)
               │
               ▼
       Docker daemon (host)
         ├─ polybot-live
         ├─ polybot-shadow
         └─ ... all containers
```

### Components

| File | Role |
|---|---|
| `src/main.py` | FastAPI application: routes, request/response models, startup |
| `src/docker_client.py` | Docker SDK wrapper: container listing, stats parsing, log fetching, start/stop |
| `src/models.py` | Pydantic response models (ContainerInfo, LogResponse) |
| `src/static/index.html` | Single-page dashboard: polling loop, cards, log viewer modal |
| `Dockerfile` | Non-root build using `python:3.11-slim`, GID 992 for socket access |
| `docker-compose.yml` | Service definition, socket mount, port binding |
| `.env.example` | Documents `DOCKERWATCH_PORT` and `LOG_TAIL_MAX` |

### Data Flow — Container Stats

```
GET /api/containers
  ├─ docker_client.list_containers(all=True)
  ├─ for each running container:
  │    asyncio.run_in_executor → docker.stats(stream=False)
  │    → parse cpu%, mem%, net I/O, block I/O
  └─ return JSON array
```

CPU% is calculated from the `precpu_stats` / `cpu_stats` delta provided in a single stats snapshot.

### Key Constants

- Default poll interval: 3 000 ms (client-side)
- Default log tail: 100 lines
- Max log tail: 500 lines
- Container stats timeout: 5 s per container

### Riskiest Assumption

The Docker SDK `container.stats(stream=False)` call blocks for ~1 second per container while it collects a stats sample. With concurrent fetching via ThreadPoolExecutor this is acceptable, but on a very busy host with many containers the API response could be slow. Mitigated by capping workers to 10 and returning partial results on timeout.
