// Copyright (c) 2026, Aakvatech and contributors
// For license information, please see license.txt

frappe.query_reports["Daily Payment Report"] = {
	"filters": [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_end(),
			reqd: 1,
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "payment_type",
			label: __("Payment Type"),
			fieldtype: "Link",
			options: "Mode of Payment",
		},
		{
			fieldname: "invoice_type",
			label: __("Invoice Type"),
			fieldtype: "Select",
			options: "\nCash\nCredit",
		},
		{
			fieldname: "only_weighbridge",
			label: __("Only Weighbridge"),
			fieldtype: "Check",
			default: 1,
		},
	]
};
