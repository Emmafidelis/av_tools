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

    ticket_qty_by_item = _get_qty_by_item(ticket.get("items"))
    doc_qty_by_item = _get_qty_by_item(doc.get("items"))

    extra_items = sorted([item for item in doc_qty_by_item if item not in ticket_qty_by_item])
    if extra_items:
        frappe.throw(f"Items not in Weighbridge Ticket: {', '.join(extra_items)}")

    over_limit = []
    for item_code, qty in doc_qty_by_item.items():
        ticket_qty = flt(ticket_qty_by_item.get(item_code))
        if flt(qty) > ticket_qty:
            over_limit.append(f"{item_code} ({flt(qty)} > {ticket_qty})")

    if over_limit:
        frappe.throw(f"Qty exceeds Weighbridge Ticket: {', '.join(over_limit)}")
