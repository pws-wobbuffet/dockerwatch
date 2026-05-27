from pydantic import BaseModel


class ContainerInfo(BaseModel):
    id: str
    name: str
    status: str
    image: str
    created: str
    cpu_percent: float
    mem_usage_bytes: int
    mem_limit_bytes: int
    mem_percent: float
    net_rx_bytes: int
    net_tx_bytes: int
    blk_read_bytes: int
    blk_write_bytes: int


class LogResponse(BaseModel):
    container_id: str
    container_name: str
    tail: int
    lines: list[str]


class ActionResponse(BaseModel):
    ok: bool
    message: str
