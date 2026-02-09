import os
import re
import socket
from typing import Optional

from fastapi import FastAPI, HTTPException


APP = FastAPI(title="Weighbridge Service", version="0.1.0")

DEFAULT_DEVICE_IP = os.getenv("WEIGHBRIDGE_DEVICE_IP", "")
DEFAULT_DEVICE_PORT = int(os.getenv("WEIGHBRIDGE_DEVICE_PORT", "0") or 0)
DEFAULT_TIMEOUT = float(os.getenv("WEIGHBRIDGE_TIMEOUT", "5"))
DEFAULT_COMMAND = os.getenv("WEIGHBRIDGE_READ_COMMAND", "RW\r\n")


FLOAT_PATTERN = re.compile(r"[-+]?\d*\.?\d+")


def _read_weight_from_device(
    device_ip: str,
    device_port: int,
    command: str,
    timeout: float,
) -> str:
    if not device_ip or not device_port:
        raise ValueError("Device IP/port not configured")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.settimeout(timeout)
        client.connect((device_ip, device_port))
        client.sendall(command.encode("ascii", errors="ignore"))
        data = client.recv(1024)

    return data.decode("ascii", errors="ignore").strip()


def _extract_weight(payload: str) -> float:
    match = FLOAT_PATTERN.search(payload)
    if not match:
        raise ValueError("No numeric weight found in response")
    return float(match.group(0))


@APP.get("/health")
def health():
    return {"status": "ok"}


@APP.get("/read_weight")
def read_weight(
    device_ip: Optional[str] = None,
    device_port: Optional[int] = None,
    command: Optional[str] = None,
    timeout: Optional[float] = None,
    mock: Optional[int] = 0,
):
    if mock:
        return {"weight": 0.0, "uom": "t", "raw": "MOCK"}

    ip = device_ip or DEFAULT_DEVICE_IP
    port = device_port or DEFAULT_DEVICE_PORT
    cmd = command or DEFAULT_COMMAND
    to = timeout or DEFAULT_TIMEOUT

    try:
        raw = _read_weight_from_device(ip, port, cmd, to)
        weight = _extract_weight(raw)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {"weight": weight, "uom": "t", "raw": raw}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(APP, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
