import frappe
from frappe.utils import flt


def validate_weighbridge_ticket(doc, method=None):
    ticket_name = doc.get("weighbridge_ticket")
    if not ticket_name:
        return

    ticket = frappe.get_doc("Weighbridge Ticket", ticket_name)
    if ticket.docstatus != 1:
        frappe.throw("Weighbridge Ticket must be submitted.")

    ticket_items = {row.item_code: row for row in ticket.items}
    doc_items = [row for row in (doc.get("items") or []) if row.item_code]

    extra_items = [row.item_code for row in doc_items if row.item_code not in ticket_items]
    if extra_items:
        frappe.throw(
            "Items not in Weighbridge Ticket: {0}".format(", ".join(extra_items))
        )

    over_limit = []
    for row in doc_items:
        ticket_qty = flt(ticket_items[row.item_code].qty or 0)
        if flt(row.qty or 0) > ticket_qty:
            over_limit.append(
                "{0} ({1} > {2})".format(row.item_code, row.qty or 0, ticket_qty)
            )
    if over_limit:
        frappe.throw(
            "Qty exceeds Weighbridge Ticket: {0}".format(", ".join(over_limit))
        )
