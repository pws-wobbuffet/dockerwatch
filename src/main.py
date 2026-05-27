"""
DockerWatch — FastAPI application.

Serves a JSON REST API at /api/* and the static dashboard at /.
"""

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

import docker.errors
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from . import docker_client
from .models import ActionResponse, ContainerInfo, LogResponse

logger = logging.getLogger("dockerwatch")
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

# Thread pool for blocking Docker SDK calls.
_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="docker-stats")

LOG_TAIL_MAX = int(os.getenv("LOG_TAIL_MAX", "500"))
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("DockerWatch starting — connecting to Docker daemon...")
    try:
        docker_client.get_client().ping()
        logger.info("Docker daemon reachable.")
    except Exception as exc:
        logger.error("Cannot reach Docker daemon: %s", exc)
    yield
    _executor.shutdown(wait=False)


app = FastAPI(title="DockerWatch", version="0.1.0", lifespan=lifespan)


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.get("/api/containers", response_model=list[ContainerInfo])
async def list_containers():
    """Return all containers with real-time stats for running ones."""
    loop = asyncio.get_event_loop()

    summaries = await loop.run_in_executor(
        _executor, lambda: docker_client.list_containers(all_containers=True)
    )

    async def enrich(summary: dict) -> ContainerInfo:
        if summary["status"] == "running":
            stats = await loop.run_in_executor(
                _executor, lambda: docker_client.get_stats(summary["id"])
            )
        else:
            stats = docker_client._zero_stats()
        return ContainerInfo(**summary, **stats)

    results = await asyncio.gather(*[enrich(s) for s in summaries])
    return list(results)


@app.get("/api/containers/{container_id}/logs", response_model=LogResponse)
async def get_logs(
    container_id: str,
    tail: int = Query(default=100, ge=1, le=LOG_TAIL_MAX),
):
    """Return the last `tail` log lines for a container."""
    loop = asyncio.get_event_loop()
    try:
        name, lines = await loop.run_in_executor(
            _executor, lambda: docker_client.get_logs(container_id, tail)
        )
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail=f"Container {container_id!r} not found")
    except docker.errors.APIError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return LogResponse(container_id=container_id, container_name=name, tail=tail, lines=lines)


@app.post("/api/containers/{container_id}/start", response_model=ActionResponse)
async def start_container(container_id: str):
    """Start a stopped container."""
    loop = asyncio.get_event_loop()
    try:
        name = await loop.run_in_executor(
            _executor, lambda: docker_client.start_container(container_id)
        )
        return ActionResponse(ok=True, message=f"Container {name!r} started.")
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail=f"Container {container_id!r} not found")
    except docker.errors.APIError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/containers/{container_id}/stop", response_model=ActionResponse)
async def stop_container(container_id: str):
    """Stop a running container."""
    loop = asyncio.get_event_loop()
    try:
        name = await loop.run_in_executor(
            _executor, lambda: docker_client.stop_container(container_id)
        )
        return ActionResponse(ok=True, message=f"Container {name!r} stopped.")
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail=f"Container {container_id!r} not found")
    except docker.errors.APIError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
async def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Static files (must be mounted last so API routes take priority)
# ---------------------------------------------------------------------------

app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
