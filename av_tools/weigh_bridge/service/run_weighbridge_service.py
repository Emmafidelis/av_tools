import os
import re
import socket
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import serial


APP = FastAPI(title="Weighbridge Service", version="0.1.0")

allowed_origins = [
    origin.strip()
    for origin in os.getenv("WEIGHBRIDGE_ALLOWED_ORIGINS", "*").split(",")
    if origin.strip()
]

APP.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins or ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULT_DEVICE_IP = os.getenv("WEIGHBRIDGE_DEVICE_IP", "")
DEFAULT_DEVICE_PORT = int(os.getenv("WEIGHBRIDGE_DEVICE_PORT", "0") or 0)
DEFAULT_TIMEOUT = float(os.getenv("WEIGHBRIDGE_TIMEOUT", "5"))
DEFAULT_COMMAND = os.getenv("WEIGHBRIDGE_READ_COMMAND", "RW\r\n")


FLOAT_PATTERN = re.compile(r"[-+]?\d*\.?\d+")


class ReadWeightRequest(BaseModel):
    connection_type: Optional[str] = None
    serial_port: Optional[str] = None
    baud_rate: Optional[int] = None
    parity: Optional[str] = None
    data_bits: Optional[int] = None
    stop_bits: Optional[int] = None
    device_ip: Optional[str] = None
    device_port: Optional[int] = None
    command: Optional[str] = None
    timeout: Optional[float] = None
    mock: Optional[int] = 0


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


def _read_weight_from_serial(
    serial_port: str,
    baud_rate: int,
    parity: str,
    data_bits: int,
    stop_bits: int,
    command: str,
    timeout: float,
) -> str:
    if not serial_port:
        raise ValueError("Serial port not configured")

    parity_map = {
        "none": serial.PARITY_NONE,
        "even": serial.PARITY_EVEN,
        "odd": serial.PARITY_ODD,
    }
    stop_bits_map = {
        1: serial.STOPBITS_ONE,
        2: serial.STOPBITS_TWO,
    }
    data_bits_map = {
        7: serial.SEVENBITS,
        8: serial.EIGHTBITS,
    }

    parity_value = parity_map.get((parity or "none").strip().lower(), serial.PARITY_NONE)
    stop_bits_value = stop_bits_map.get(stop_bits or 1, serial.STOPBITS_ONE)
    data_bits_value = data_bits_map.get(data_bits or 8, serial.EIGHTBITS)

    with serial.Serial(
        port=serial_port,
        baudrate=baud_rate or 9600,
        bytesize=data_bits_value,
        parity=parity_value,
        stopbits=stop_bits_value,
        timeout=timeout,
    ) as ser:
        ser.reset_input_buffer()
        ser.write(command.encode("ascii", errors="ignore"))
        data = ser.readline()
        if not data:
            data = ser.read(1024)

    return data.decode("ascii", errors="ignore").strip()


def _extract_weight(payload: str) -> float:
    match = FLOAT_PATTERN.search(payload)
    if not match:
        raise ValueError("No numeric weight found in response")
    return float(match.group(0))


def _handle_read_weight(
    connection_type: Optional[str],
    serial_port: Optional[str],
    baud_rate: Optional[int],
    parity: Optional[str],
    data_bits: Optional[int],
    stop_bits: Optional[int],
    device_ip: Optional[str],
    device_port: Optional[int],
    command: Optional[str],
    timeout: Optional[float],
    mock: Optional[int],
):
    if mock:
        return {"weight": 0.0, "uom": "t", "raw": "MOCK"}

    cmd = command or DEFAULT_COMMAND
    to = timeout or DEFAULT_TIMEOUT

    try:
        if (connection_type or "").strip().lower() == "serial" or serial_port:
            raw = _read_weight_from_serial(
                serial_port=serial_port or "",
                baud_rate=baud_rate or 9600,
                parity=parity or "None",
                data_bits=data_bits or 8,
                stop_bits=stop_bits or 1,
                command=cmd,
                timeout=to,
            )
        else:
            ip = device_ip or DEFAULT_DEVICE_IP
            port = device_port or DEFAULT_DEVICE_PORT
            raw = _read_weight_from_device(ip, port, cmd, to)
        weight = _extract_weight(raw)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {"weight": weight, "uom": "t", "raw": raw}


@APP.get("/health")
def health():
    return {"status": "ok"}


@APP.get("/read_weight")
def read_weight(
    connection_type: Optional[str] = None,
    serial_port: Optional[str] = None,
    baud_rate: Optional[int] = None,
    parity: Optional[str] = None,
    data_bits: Optional[int] = None,
    stop_bits: Optional[int] = None,
    device_ip: Optional[str] = None,
    device_port: Optional[int] = None,
    command: Optional[str] = None,
    timeout: Optional[float] = None,
    mock: Optional[int] = 0,
):
    return _handle_read_weight(
        connection_type,
        serial_port,
        baud_rate,
        parity,
        data_bits,
        stop_bits,
        device_ip,
        device_port,
        command,
        timeout,
        mock,
    )


@APP.post("/read_weight")
def read_weight_post(payload: ReadWeightRequest):
    return _handle_read_weight(
        payload.connection_type,
        payload.serial_port,
        payload.baud_rate,
        payload.parity,
        payload.data_bits,
        payload.stop_bits,
        payload.device_ip,
        payload.device_port,
        payload.command,
        payload.timeout,
        payload.mock,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(APP, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
