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

    def on_submit(self):
        self.update_reference_document_quantities()

    def on_cancel(self):
        self.clear_reference_document_link()

    def validate_items_against_reference(self):
        # Reference is optional. Only validate against source document when provided.
        if not self.document_reference:
            return

        if not self.document_type:
            frappe.throw("Document Type is required when Document Reference is set.")

        if self.document_type not in ALLOWED_REFERENCE_DOCTYPES:
            frappe.throw(f"Unsupported document type: {self.document_type}")

        reference_doc = frappe.get_doc(self.document_type, self.document_reference)

        if reference_doc.meta.is_submittable and reference_doc.docstatus != 0:
            frappe.throw(f"{self.document_type} must be in Draft.")

        reference_qty = _build_qty_map(reference_doc.get("items"))
        ticket_qty = _build_qty_map(self.get("items"))

        extra_items = sorted([item for item in ticket_qty if item not in reference_qty])
        if extra_items:
            frappe.throw(
                "Items not found in {0} {1}: {2}".format(
                    self.document_type, self.document_reference, ", ".join(extra_items)
                )
            )

    def update_reference_document_quantities(self):
        if not self.document_type or not self.document_reference:
            return

        if self.document_type not in ALLOWED_REFERENCE_DOCTYPES:
            frappe.throw(f"Unsupported document type: {self.document_type}")

        reference_doc = frappe.get_doc(self.document_type, self.document_reference)
        reference_doc.check_permission("write")

        if reference_doc.meta.is_submittable and reference_doc.docstatus != 0:
            frappe.throw(f"{self.document_type} must be in Draft.")

        ticket_qty = {}
        for row in (self.get("items") or []):
            item_code = (row.get("item_code") or "").strip()
            if item_code:
                ticket_qty[item_code] = flt(row.get("qty"))

        if not ticket_qty:
            frappe.throw("Please add at least one item before submitting Weighbridge Ticket.")

        reference_items = reference_doc.get("items") or []
        reference_codes = {
            (row.get("item_code") or "").strip() for row in reference_items if row.get("item_code")
        }
        missing_items = sorted([item_code for item_code in ticket_qty if item_code not in reference_codes])
        if missing_items:
            frappe.throw(
                "Items not found in {0} {1}: {2}".format(
                    self.document_type, self.document_reference, ", ".join(missing_items)
                )
            )

        for row in reference_items:
            item_code = (row.get("item_code") or "").strip()
            if item_code in ticket_qty:
                row.qty = ticket_qty[item_code]

        reference_doc.weighbridge_ticket = self.name

        reference_doc.save()

    def clear_reference_document_link(self):
        if not self.document_type or not self.document_reference:
            return

        linked_ticket = frappe.db.get_value(
            self.document_type, self.document_reference, "weighbridge_ticket"
        )
        if linked_ticket == self.name:
            frappe.db.set_value(
                self.document_type,
                self.document_reference,
                "weighbridge_ticket",
                None,
                update_modified=False,
            )
