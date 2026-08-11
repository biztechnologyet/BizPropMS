// Copyright (c) 2016, Biz Technology Solutions and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Utility Invoices"] = {
	"filters": [
		{
			"fieldname":"year",
			"label": __("Year"),
			"fieldtype": "Link",
			"options": "Fiscal Year"
		}
	]
};
