// Copyright (c) 2024, Biz Technology Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on('Folio Item', {
	refresh: function(frm) {

	},

	quantity: function(frm, cdt, cdn) {
		calculate_amount(frm, cdt, cdn);
	},

	rate: function(frm, cdt, cdn) {
		calculate_amount(frm, cdt, cdn);
	}
});

function calculate_amount(frm, cdt, cdn) {
	var row = locals[cdt][cdn];
	if (row.quantity && row.rate) {
		frappe.model.set_value(cdt, cdn, 'amount', row.quantity * row.rate);
	}
}
