import re

import frappe
import requests


def _get_settings():
    settings = frappe.get_single("Weighbridge Settings")
    if not settings.enabled:
        frappe.throw("Weighbridge Settings is disabled.")
    if not settings.gateway_url and not settings.read_weight_url:
        frappe.throw(
            "Gateway URL or Read Weight URL is required in Weighbridge Settings."
        )
    return settings


@frappe.whitelist()
def read_weight(mode=None):
    settings = _get_settings()
    if settings.read_weight_url:
        try:
            response = requests.get(
                settings.read_weight_url, timeout=settings.timeout_seconds or 5
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            frappe.throw(f"Failed to read weight: {exc}")

        match = re.search(r"<id>ValPoids</id><value>\\s*([^<]+)</value>", response.text)
        if not match:
            frappe.throw("ValPoids not found in response.")

        raw_value = match.group(1).strip()
        number_match = re.search(r"[-+]?\\d*\\.?\\d+", raw_value)
        if not number_match:
            frappe.throw("No numeric weight found in response.")

        return {
            "weight": float(number_match.group(0)),
            "uom": settings.unit_of_measure,
            "raw": raw_value,
            "mode": mode,
        }

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
        "read_weight_url": settings.read_weight_url,
        "payload": {
            "device_ip": settings.device_ip,
            "device_port": settings.device_port,
            "command": settings.command_read_weight,
            "timeout": settings.timeout_seconds,
            "read_url": settings.read_weight_url,
        },
    }


@frappe.whitelist()
def get_ticket_items(ticket, doctype=None):
    if not ticket:
        frappe.throw("Weighbridge Ticket is required.")

    doc = frappe.get_doc("Weighbridge Ticket", ticket)
    if doc.docstatus != 1:
        frappe.throw("Weighbridge Ticket must be submitted.")

    if doctype and doc.document_type and doc.document_type != doctype:
        frappe.throw("Weighbridge Ticket document type does not match.")

    items = [
        {
            "item_code": row.item_code,
            "item_name": row.item_name,
            "qty": row.qty,
            "uom": row.uom,
        }
        for row in (doc.items or [])
    ]

    return {
        "items": items,
        "document_type": doc.document_type,
        "document_reference": doc.document_reference,
    }
