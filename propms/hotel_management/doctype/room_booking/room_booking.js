// Copyright (c) 2024, Biz Technology Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on('Room Booking', {
	refresh: function(frm) {

	},

	check_in_date: function(frm) {
		calculate_nights(frm);
	},

	check_out_date: function(frm) {
		calculate_nights(frm);
	},

	rate_per_night: function(frm) {
		calculate_totals(frm);
	},

	discount_percent: function(frm) {
		calculate_totals(frm);
	},

	nights: function(frm) {
		calculate_totals(frm);
	}
});

function calculate_nights(frm) {
	if (frm.doc.check_in_date && frm.doc.check_out_date) {
		var diff = frappe.datetime.get_diff(frm.doc.check_out_date, frm.doc.check_in_date);
		frm.set_value('nights', Math.max(diff, 1));
		calculate_totals(frm);
	}
}

function calculate_totals(frm) {
	if (frm.doc.nights && frm.doc.rate_per_night) {
		var total = frm.doc.nights * frm.doc.rate_per_night;
		frm.set_value('total_amount', total);
		if (frm.doc.discount_percent) {
			frm.set_value('net_amount', total - (total * frm.doc.discount_percent / 100));
		} else {
			frm.set_value('net_amount', total);
		}
	}
}
