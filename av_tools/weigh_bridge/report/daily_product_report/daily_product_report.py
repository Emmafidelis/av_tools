# Copyright (c) 2026, Aakvatech and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.utils import flt, getdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	_validate_filters(filters)

	columns = _get_columns()
	rows = _get_rows(filters)
	data, totals = _build_rows(rows)
	report_summary = _get_report_summary(totals, rows, filters)

	return columns, data, None, None, report_summary


def _validate_filters(filters):
	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw("From Date and To Date are required.")

	if getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw("From Date cannot be after To Date.")


def _get_columns():
	return [
		{
			"label": "Ticket",
			"fieldname": "ticket",
			"fieldtype": "Link",
			"options": "Weighbridge Ticket",
			"width": 160,
		},
		{
			"label": "Date",
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"label": "Invoice",
			"fieldname": "invoice",
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"width": 170,
		},
		{
			"label": "Client",
			"fieldname": "customer_name",
			"fieldtype": "Data",
			"width": 220,
		},
		{
			"label": "Product",
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 150,
		},
		{
			"label": "Description",
			"fieldname": "description",
			"fieldtype": "Data",
			"width": 240,
		},
		{
			"label": "Qty",
			"fieldname": "qty",
			"fieldtype": "Float",
			"precision": 3,
			"width": 100,
		},
		{
			"label": "Value",
			"fieldname": "value",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"label": "VAT",
			"fieldname": "vat",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"label": "Total",
			"fieldname": "total",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 130,
		},
		{
			"label": "Currency",
			"fieldname": "currency",
			"fieldtype": "Data",
			"hidden": 1,
			"width": 0,
		},
	]


def _get_rows(filters):
	conditions = ["si.docstatus = 1", "ifnull(si.is_return, 0) = 0"]
	values = {
		"from_date": filters.from_date,
		"to_date": filters.to_date,
	}

	conditions.append("si.posting_date between %(from_date)s and %(to_date)s")

	if filters.get("company"):
		conditions.append("si.company = %(company)s")
		values["company"] = filters.company

	if filters.get("customer"):
		conditions.append("si.customer = %(customer)s")
		values["customer"] = filters.customer

	if filters.get("item_code"):
		conditions.append("sii.item_code = %(item_code)s")
		values["item_code"] = filters.item_code

	condition_sql = " and ".join(conditions)

	return frappe.db.sql(
		f"""
		select
			si.name as invoice,
			si.posting_date,
			si.customer,
			si.customer_name,
			si.company,
			si.currency,
			si.weighbridge_ticket as ticket,
			sii.idx,
			sii.item_code,
			sii.item_name,
			sii.description,
			sii.uom,
			sii.qty,
			sii.amount as value,
			sii.item_tax_rate
		from `tabSales Invoice` si
		inner join `tabSales Invoice Item` sii
			on sii.parent = si.name
		where {condition_sql}
		order by si.posting_date, si.name, sii.idx
		""",
		values=values,
		as_dict=True,
	)


def _build_rows(rows):
	data = []
	totals = {"qty": 0.0, "value": 0.0, "vat": 0.0, "total": 0.0}

	for row in rows:
		row.value = flt(row.value)
		row.qty = flt(row.qty)
		vat_rate = _get_vat_rate(row.get("item_tax_rate"))
		vat = flt(row.value) * vat_rate / 100
		total = flt(row.value) + flt(vat)

		data.append(
			{
				"ticket": row.ticket,
				"posting_date": row.posting_date,
				"invoice": row.invoice,
				"customer_name": row.customer_name,
				"item_code": row.item_code,
				"description": row.description or row.item_name or row.item_code,
				"qty": row.qty,
				"value": row.value,
				"vat": vat,
				"total": total,
				"currency": row.currency,
			}
		)

		totals["qty"] += flt(row.qty)
		totals["value"] += flt(row.value)
		totals["vat"] += flt(vat)
		totals["total"] += flt(total)

	return data, totals


def _get_vat_rate(item_tax_rate):
	if not item_tax_rate:
		return 0.0

	try:
		parsed = json.loads(item_tax_rate)
	except Exception:
		return 0.0

	if not isinstance(parsed, dict):
		return 0.0

	for value in parsed.values():
		try:
			return flt(value)
		except Exception:
			continue

	return 0.0


def _get_report_summary(totals, rows, filters):
	if not rows:
		return []

	currency = rows[0].get("currency")
	if not currency and filters.get("company"):
		currency = frappe.db.get_value("Company", filters.company, "default_currency")

	return [
		{
			"value": totals["qty"],
			"indicator": "Blue",
			"label": "Total Qty",
			"datatype": "Float",
		},
		{
			"value": totals["value"],
			"indicator": "Green",
			"label": "Total Value",
			"datatype": "Currency",
			"currency": currency,
		},
		{
			"value": totals["vat"],
			"indicator": "Orange",
			"label": "Total VAT",
			"datatype": "Currency",
			"currency": currency,
		},
		{
			"value": totals["total"],
			"indicator": "Green",
			"label": "Grand Total",
			"datatype": "Currency",
			"currency": currency,
		},
	]
