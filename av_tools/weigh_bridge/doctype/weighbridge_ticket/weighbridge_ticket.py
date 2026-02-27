# Copyright (c) 2026, Av Tools and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


ALLOWED_REFERENCE_DOCTYPES = {
    "Sales Invoice",
    "Delivery Note",
    "Sales Order",
    "Purchase Order",
    "Purchase Invoice",
    "Purchase Receipt",
}


def _build_qty_map(rows):
    qty_map = {}
    for row in (rows or []):
        item_code = (row.get("item_code") or "").strip()
        if not item_code:
            continue
        qty_map[item_code] = qty_map.get(item_code, 0) + flt(row.get("qty"))
    return qty_map


class WeighbridgeTicket(Document):
    def validate(self):
        self.validate_items_against_reference()

    def validate_items_against_reference(self):
        # Reference is optional. Only validate against source document when provided.
        if not self.document_reference:
            return

        if not self.document_type:
            frappe.throw("Document Type is required when Document Reference is set.")

        if self.document_type not in ALLOWED_REFERENCE_DOCTYPES:
            frappe.throw(f"Unsupported document type: {self.document_type}")

        reference_doc = frappe.get_doc(self.document_type, self.document_reference)

        if reference_doc.meta.is_submittable and reference_doc.docstatus != 1:
            frappe.throw(f"{self.document_type} must be submitted.")

        reference_qty = _build_qty_map(reference_doc.get("items"))
        ticket_qty = _build_qty_map(self.get("items"))

        extra_items = sorted([item for item in ticket_qty if item not in reference_qty])
        if extra_items:
            frappe.throw(
                "Items not found in {0} {1}: {2}".format(
                    self.document_type, self.document_reference, ", ".join(extra_items)
                )
            )

        qty_over = []
        for item_code, qty in ticket_qty.items():
            allowed_qty = flt(reference_qty.get(item_code))
            if flt(qty) > allowed_qty:
                qty_over.append(
                    "{0} ({1} > {2})".format(item_code, flt(qty), flt(allowed_qty))
                )

        if qty_over:
            frappe.throw(
                "Ticket qty exceeds {0} {1}: {2}".format(
                    self.document_type, self.document_reference, ", ".join(qty_over)
                )
            )
