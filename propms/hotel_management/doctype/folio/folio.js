// Copyright (c) 2024, Biz Technology Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on('Folio', {
	refresh: function(frm) {

	}
});

frappe.ui.form.on('Folio Item', {
	amount: function(frm) {
		frm.call('calculate_totals');
	}
});
