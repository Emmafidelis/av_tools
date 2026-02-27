import frappe


def _get_settings():
    settings = frappe.get_single("Weighbridge Settings")
    if not settings.enabled:
        frappe.throw("Weighbridge Settings is disabled.")
    if not settings.read_weight_url:
        frappe.throw("Read Weight URL is required in Weighbridge Settings.")
    return settings


@frappe.whitelist()
def read_weight(mode=None):
    settings = _get_settings()
    return {
        "read_weight_url": settings.read_weight_url,
        "mode": mode,
    }


@frappe.whitelist()
def get_gateway_payload():
    settings = _get_settings()
    return {
        "read_weight_url": settings.read_weight_url,
        "timeout_seconds": settings.timeout_seconds,
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
