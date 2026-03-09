# Copyright (c) 2026, Aakvatech and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import cint, flt, getdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	_validate_filters(filters)

	columns = _get_columns()
	rows = _get_rows(filters)
	data, totals = _build_data(rows)
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
			"label": "Payment Type",
			"fieldname": "payment_type",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": "Date",
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"label": "Client Name",
			"fieldname": "customer_name",
			"fieldtype": "Data",
			"width": 240,
		},
		{
			"label": "Record No",
			"fieldname": "record_no",
			"fieldtype": "Int",
			"width": 90,
		},
		{
			"label": "Invoice Type",
			"fieldname": "invoice_type",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": "Invoice No",
			"fieldname": "invoice",
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"width": 170,
		},
		{
			"label": "Cheque No",
			"fieldname": "cheque_no",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": "Receipt No",
			"fieldname": "receipt_no",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": "Amount",
			"fieldname": "amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 140,
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
	invoice_type_expr = "case when ifnull(si.outstanding_amount, 0) > 0 then 'Credit' else 'Cash' end"
	payment_type_expr = f"coalesce(nullif(sip.mode_of_payment, ''), {invoice_type_expr})"

	conditions = [
		"si.docstatus = 1",
		"ifnull(si.is_return, 0) = 0",
		"si.posting_date between %(from_date)s and %(to_date)s",
	]
	values = {
		"from_date": filters.from_date,
		"to_date": filters.to_date,
	}

	if filters.get("company"):
		conditions.append("si.company = %(company)s")
		values["company"] = filters.company

	if filters.get("customer"):
		conditions.append("si.customer = %(customer)s")
		values["customer"] = filters.customer

	if filters.get("invoice_type"):
		conditions.append(f"{invoice_type_expr} = %(invoice_type)s")
		values["invoice_type"] = filters.invoice_type

	if filters.get("payment_type"):
		conditions.append(f"{payment_type_expr} = %(payment_type)s")
		values["payment_type"] = filters.payment_type

	if cint(filters.get("only_weighbridge")):
		conditions.append("ifnull(si.weighbridge_ticket, '') != ''")

	condition_sql = " and ".join(conditions)

	return frappe.db.sql(
		f"""
		select
			si.name as invoice,
			si.posting_date,
			si.customer_name,
			si.currency,
			{invoice_type_expr} as invoice_type,
			{payment_type_expr} as payment_type,
			ifnull(sip.reference_no, '') as cheque_no,
			si.name as receipt_no,
			si.grand_total as amount
		from `tabSales Invoice` si
		left join (
			select parent, min(idx) as idx
			from `tabSales Invoice Payment`
			group by parent
		) sipx
			on sipx.parent = si.name
		left join `tabSales Invoice Payment` sip
			on sip.parent = sipx.parent and sip.idx = sipx.idx
		where {condition_sql}
		order by {payment_type_expr}, si.posting_date, si.name
		""",
		values=values,
		as_dict=True,
	)


def _build_data(rows):
	data = []
	totals = {"amount": 0.0}

	for i, row in enumerate(rows, start=1):
		amount = flt(row.amount)
		data.append(
			{
				"payment_type": row.payment_type,
				"posting_date": row.posting_date,
				"customer_name": row.customer_name,
				"record_no": i,
				"invoice_type": row.invoice_type,
				"invoice": row.invoice,
				"cheque_no": row.cheque_no,
				"receipt_no": row.receipt_no,
				"amount": amount,
				"currency": row.currency,
			}
		)
		totals["amount"] += amount

	return data, totals


def _get_report_summary(totals, rows, filters):
	if not rows:
		return []

	currency = rows[0].get("currency")
	if not currency and filters.get("company"):
		currency = frappe.db.get_value("Company", filters.company, "default_currency")

	return [
		{
			"value": len(rows),
			"indicator": "Blue",
			"label": "Invoices",
			"datatype": "Int",
		},
		{
			"value": totals["amount"],
			"indicator": "Green",
			"label": "Total Amount",
			"datatype": "Currency",
			"currency": currency,
		},
	]
