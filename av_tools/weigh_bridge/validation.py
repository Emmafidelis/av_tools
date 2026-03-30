import frappe
from frappe.utils import flt


def _get_qty_by_item(rows):
    qty_by_item = {}
    for row in (rows or []):
        item_code = (row.get("item_code") or "").strip()
        if not item_code:
            continue
        qty_by_item[item_code] = qty_by_item.get(item_code, 0) + flt(row.get("qty"))
    return qty_by_item


def validate_weighbridge_ticket(doc, method=None):
    ticket_name = doc.get("weighbridge_ticket")
    if not ticket_name:
        return

    ticket = frappe.get_doc("Weighbridge Ticket", ticket_name)
    if ticket.docstatus != 1:
        frappe.throw("Weighbridge Ticket must be submitted.")

    if ticket.get("target_document_type") and ticket.target_document_type != doc.doctype:
        frappe.throw("Weighbridge Ticket target document type does not match this document.")

    if (
        not doc.get("__islocal")
        and ticket.get("target_document_reference")
        and ticket.target_document_reference != doc.name
    ):
        frappe.throw("Weighbridge Ticket belongs to another document.")

    ticket_qty_by_item = _get_qty_by_item(ticket.get("items"))
    doc_qty_by_item = _get_qty_by_item(doc.get("items"))

    extra_items = sorted([item for item in doc_qty_by_item if item not in ticket_qty_by_item])
    if extra_items:
        frappe.throw(f"Items not in Weighbridge Ticket: {', '.join(extra_items)}")

    missing_items = sorted([item for item in ticket_qty_by_item if item not in doc_qty_by_item])
    if missing_items:
        frappe.throw(f"Items missing from document: {', '.join(missing_items)}")

    qty_mismatch = []
    for item_code, ticket_qty in ticket_qty_by_item.items():
        doc_qty = flt(doc_qty_by_item.get(item_code))
        ticket_qty = flt(ticket_qty)
        if abs(doc_qty - ticket_qty) > 1e-9:
            qty_mismatch.append(f"{item_code} ({doc_qty} != {ticket_qty})")

    if qty_mismatch:
        frappe.throw(f"Qty must match Weighbridge Ticket: {', '.join(qty_mismatch)}")
