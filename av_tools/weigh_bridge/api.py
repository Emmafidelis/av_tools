import frappe
import requests


def _get_settings():
    settings = frappe.get_single("Weighbridge Settings")
    if not settings.enabled:
        frappe.throw("Weighbridge Settings is disabled.")
    if not settings.gateway_url:
        frappe.throw("Gateway URL is required in Weighbridge Settings.")
    return settings


@frappe.whitelist()
def read_weight(mode=None):
    settings = _get_settings()
    payload = {
        "device_ip": settings.device_ip,
        "device_port": settings.device_port,
        "command": settings.command_read_weight,
        "timeout": settings.timeout_seconds,
    }

    url = settings.gateway_url.rstrip("/") + "/read_weight"
    try:
        response = requests.post(url, json=payload, timeout=settings.timeout_seconds or 5)
        response.raise_for_status()
    except requests.RequestException as exc:
        frappe.throw(f"Failed to read weight: {exc}")

    data = response.json()
    return {
        "weight": data.get("weight"),
        "uom": data.get("uom"),
        "raw": data.get("raw"),
        "mode": mode,
    }


@frappe.whitelist()
def get_gateway_payload():
    settings = _get_settings()
    return {
        "gateway_url": settings.gateway_url,
        "payload": {
            "connection_type": settings.connection_type,
            "serial_port": settings.serial_port,
            "baud_rate": settings.baud_rate,
            "parity": settings.parity,
            "data_bits": settings.data_bits,
            "stop_bits": settings.stop_bits,
            "device_ip": settings.device_ip,
            "device_port": settings.device_port,
            "command": settings.command_read_weight,
            "timeout": settings.timeout_seconds,
        },
    }
