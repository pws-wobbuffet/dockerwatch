# DockerWatch

A lightweight, self-contained web dashboard for monitoring all Docker containers on a host in real time.

```
+-----------------------------------------------------+
| DW  DockerWatch              Updated 22:47:28  4 running / 6 total |
+-----------------------------------------------------+
| [All] [Running] [Exited]    [search...]             |
+-----------------------------------------------------+
| polybot-live   running                              |
|  CPU: 0.2%  [===                    ]               |
|  MEM: N/A (cgroup disabled)                         |
|  RX: 1.9 GB   TX: 290 MB                           |
|  [Logs]  [Stop]                                     |
+-----------------------------------------------------+
```

## What it does

- Lists all containers on the host (running and stopped)
- Shows real-time CPU%, memory (when cgroup memory accounting is enabled), network I/O, and block I/O per container
- Lets you view the last N log lines for any container directly in the browser
- Start and stop containers with a single click (confirmation required)
- Auto-refreshes every 3 seconds with no page reload
- Filter by status (running / exited) or search by name and image

## Requirements

- Docker with Compose plugin (v2)
- The host `docker` group GID must be `992` (configurable via `DOCKER_GID` build arg if different on your system — see below)

## Quick start

```bash
git clone https://github.com/pws-wobbuffet/dockerwatch
cd dockerwatch
docker compose up --build
```

Open http://localhost:8080 in your browser.

To run on a different port:

```bash
DOCKERWATCH_PORT=9090 docker compose up --build
```

## Configuration

Copy `.env.example` to `.env` and adjust as needed:

```bash
cp .env.example .env
```

| Variable            | Default | Description                                          |
|---------------------|---------|------------------------------------------------------|
| `DOCKERWATCH_PORT`  | `8080`  | Host port the dashboard is served on                 |
| `LOG_TAIL_MAX`      | `500`   | Maximum log lines returnable per request             |

### Custom Docker GID

If your host Docker group has a different GID than 992:

```bash
docker compose build --build-arg DOCKER_GID=$(stat -c '%g' /var/run/docker.sock)
docker compose up
```

## Architecture

```
Browser (polling every 3 s)
  │
  │  GET /api/containers
  │  GET /api/containers/{id}/logs
  │  POST /api/containers/{id}/start|stop
  ▼
dockerwatch container (Python 3.11 + FastAPI + Uvicorn)
  │
  │  Docker SDK (concurrent ThreadPoolExecutor)
  ▼
/var/run/docker.sock  (mounted read-only)
  │
  ▼
Docker daemon + all containers
```

Single service. No database. No external dependencies at runtime.

| File | Role |
|---|---|
| `src/main.py` | FastAPI app, routes, async fan-out for stats |
| `src/docker_client.py` | Docker SDK wrapper, stats parsing, log fetching |
| `src/models.py` | Pydantic response models |
| `src/static/index.html` | Single-page dashboard (vanilla JS, no build step) |

## Known limitations

- **Memory stats show N/A on kernels without cgroup memory accounting** (e.g. Raspberry Pi without `cgroup_memory=1 cgroup_enable=memory` in `/boot/cmdline.txt`). CPU and network stats are unaffected.
- The dashboard does not persist historical data. Metrics are live point-in-time only.
- Start/stop actions call `docker stop --timeout 10` and `docker start`. They are intentionally not exposed without a confirmation dialog.

## Development

Run the API directly (without Docker) for rapid iteration:

```bash
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8080
```

Requires the current user to have access to `/var/run/docker.sock`.

## License

MIT
