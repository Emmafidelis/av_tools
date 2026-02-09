# Weighbridge Service

Small HTTP service that reads weight from the weighbridge indicator over TCP and exposes it to Frappe.

## Files
- `run_weighbridge_service.py`
- `requirements.txt`

## Install (Windows / Linux)
From this folder:

```bash
python -m venv venv
```

Windows:
```bash
venv\Scripts\activate
pip install -r requirements.txt
```

Linux/macOS:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

## Configure
Set environment variables (optional):
- `WEIGHBRIDGE_DEVICE_IP` (e.g. `192.168.1.50`)
- `WEIGHBRIDGE_DEVICE_PORT` (e.g. `10001`)
- `WEIGHBRIDGE_READ_COMMAND` (default `RW\r\n`)
- `WEIGHBRIDGE_TIMEOUT` (default `5` seconds)
- `PORT` (default `8000`)

Example (Windows PowerShell):
```powershell
$env:WEIGHBRIDGE_DEVICE_IP="192.168.1.50"
$env:WEIGHBRIDGE_DEVICE_PORT="10001"
$env:WEIGHBRIDGE_READ_COMMAND="RW`r`n"
```

Example (Linux/macOS):
```bash
export WEIGHBRIDGE_DEVICE_IP=192.168.1.50
export WEIGHBRIDGE_DEVICE_PORT=10001
export WEIGHBRIDGE_READ_COMMAND=$'RW\r\n'
```

## Run
```bash
python run_weighbridge_service.py
```

Service URLs:
- `GET /health`
- `GET /read_weight`

Test:
```bash
curl http://localhost:8000/health
curl "http://localhost:8000/read_weight?mock=1"
```

If `/health` works but `/read_weight` fails, the service is running and the issue is the scale connection or protocol.
