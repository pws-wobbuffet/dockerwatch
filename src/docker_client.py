"""
Thin wrapper around the Docker SDK.

All SDK calls are synchronous (blocking). Callers that need async behaviour
should dispatch via asyncio.run_in_executor.
"""

import datetime
from typing import Any

import docker
import docker.errors

# Module-level client; created once and reused across requests.
_client: docker.DockerClient | None = None

MAX_LOG_TAIL = 500
STATS_TIMEOUT_S = 5


def get_client() -> docker.DockerClient:
    global _client
    if _client is None:
        _client = docker.from_env(timeout=STATS_TIMEOUT_S)
    return _client


# ---------------------------------------------------------------------------
# Container listing
# ---------------------------------------------------------------------------

def list_containers(all_containers: bool = True) -> list[dict[str, Any]]:
    """Return a list of lightweight container summary dicts (no stats)."""
    client = get_client()
    result = []
    for c in client.containers.list(all=all_containers):
        image_tag = (
            c.image.tags[0]
            if c.image.tags
            else c.image.short_id.replace("sha256:", "")
        )
        result.append(
            {
                "id": c.short_id,
                "name": c.name,
                "status": c.status,
                "image": image_tag,
                "created": _format_created(c.attrs.get("Created", "")),
            }
        )
    return result


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def get_stats(container_id: str) -> dict[str, Any]:
    """
    Fetch a single stats snapshot for a running container.

    Returns a dict with cpu_percent, mem_*, net_*, blk_* fields.
    Returns zeroed fields if the container is not running or stats are
    unavailable.
    """
    client = get_client()
    try:
        container = client.containers.get(container_id)
        if container.status != "running":
            return _zero_stats()
        raw = container.stats(stream=False)
        return _parse_stats(raw)
    except (docker.errors.NotFound, docker.errors.APIError):
        return _zero_stats()


def _parse_stats(raw: dict[str, Any]) -> dict[str, Any]:
    cpu_percent = _calc_cpu_percent(raw)

    mem_stats = raw.get("memory_stats", {})
    mem_usage = mem_stats.get("usage") or 0
    mem_limit = mem_stats.get("limit") or 0

    # cgroups v2 on some kernels (e.g. Raspberry Pi without cgroup_memory=1)
    # omits usage/limit and puts counters under the "stats" sub-key.
    # Fall back to anon (heap/stack) + file (page cache) if available.
    if mem_usage == 0:
        sub = mem_stats.get("stats") or {}
        mem_usage = sub.get("anon", 0) + sub.get("file", 0)

    # Subtract file-system cache from usage to get application memory.
    cache = (mem_stats.get("stats") or {}).get("cache", 0)
    mem_usage = max(0, mem_usage - cache)
    mem_percent = (mem_usage / mem_limit * 100.0) if mem_limit > 0 else 0.0

    net_rx = net_tx = 0
    for iface_stats in raw.get("networks", {}).values():
        net_rx += iface_stats.get("rx_bytes", 0)
        net_tx += iface_stats.get("tx_bytes", 0)

    blk_read = blk_write = 0
    for blk in raw.get("blkio_stats", {}).get("io_service_bytes_recursive") or []:
        if blk.get("op") == "Read":
            blk_read += blk.get("value", 0)
        elif blk.get("op") == "Write":
            blk_write += blk.get("value", 0)

    return {
        "cpu_percent": round(cpu_percent, 2),
        "mem_usage_bytes": mem_usage,
        "mem_limit_bytes": mem_limit,
        "mem_percent": round(mem_percent, 2),
        "net_rx_bytes": net_rx,
        "net_tx_bytes": net_tx,
        "blk_read_bytes": blk_read,
        "blk_write_bytes": blk_write,
    }


def _calc_cpu_percent(raw: dict[str, Any]) -> float:
    cpu_stats = raw.get("cpu_stats", {})
    precpu_stats = raw.get("precpu_stats", {})

    cpu_delta = (
        cpu_stats.get("cpu_usage", {}).get("total_usage", 0)
        - precpu_stats.get("cpu_usage", {}).get("total_usage", 0)
    )
    system_delta = cpu_stats.get("system_cpu_usage", 0) - precpu_stats.get(
        "system_cpu_usage", 0
    )

    if system_delta <= 0 or cpu_delta < 0:
        return 0.0

    num_cpus = cpu_stats.get("online_cpus") or len(
        cpu_stats.get("cpu_usage", {}).get("percpu_usage", [1])
    )
    return (cpu_delta / system_delta) * num_cpus * 100.0


def _zero_stats() -> dict[str, Any]:
    return {
        "cpu_percent": 0.0,
        "mem_usage_bytes": 0,
        "mem_limit_bytes": 0,
        "mem_percent": 0.0,
        "net_rx_bytes": 0,
        "net_tx_bytes": 0,
        "blk_read_bytes": 0,
        "blk_write_bytes": 0,
    }


# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------

def get_logs(container_id: str, tail: int = 100) -> tuple[str, list[str]]:
    """
    Return (container_name, lines) for the last `tail` log lines.
    `tail` is capped at MAX_LOG_TAIL.
    """
    tail = min(tail, MAX_LOG_TAIL)
    client = get_client()
    container = client.containers.get(container_id)
    raw: bytes = container.logs(tail=tail, timestamps=True, stream=False)
    lines = raw.decode("utf-8", errors="replace").splitlines()
    return container.name, lines


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

def start_container(container_id: str) -> str:
    client = get_client()
    container = client.containers.get(container_id)
    container.start()
    return container.name


def stop_container(container_id: str) -> str:
    client = get_client()
    container = client.containers.get(container_id)
    container.stop(timeout=10)
    return container.name


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_created(iso: str) -> str:
    if not iso:
        return "unknown"
    try:
        # Docker timestamps look like "2026-05-01T12:34:56.123456789Z"
        dt = datetime.datetime.fromisoformat(iso.rstrip("Z").split(".")[0])
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return iso[:16]
