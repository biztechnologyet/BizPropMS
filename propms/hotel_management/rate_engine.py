# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe import _
from datetime import date


def calculate_rate(room_type, check_in_date, check_out_date, rate_plan=None):
	"""Calculate total rate for a stay. Apply rate plan if provided.

	Args:
		room_type: Name of the Room Type doc
		check_in_date: date object or string
		check_out_date: date object or string
	_rate_plan: Optional Rate Plan docname

	Returns:
		Dict with rate_per_night, total_amount, nights, plan_applied
	"""
	if isinstance(check_in_date, str):
		check_in_date = date.fromisoformat(check_in_date)
	if isinstance(check_out_date, str):
		check_out_date = date.fromisoformat(check_out_date)

	nights = (check_out_date - check_in_date).days
	if nights <= 0:
		frappe.throw(_("Stay must be at least 1 night"))

	base_rate = frappe.db.get_value("Room Type", room_type, "base_rate_per_night")
	if not base_rate:
		frappe.throw(_("Base rate not set for room type {0}").format(room_type))

	rate_per_night = base_rate
	plan_applied = None

	if rate_plan:
		plan_doc = frappe.get_doc("Rate Plan", rate_plan)
		plan_applied = plan_doc.plan_name

		if plan_doc.rate_type == "Fixed":
			rate_per_night = plan_doc.rate_value
		elif plan_doc.rate_type == "Percentage":
			rate_per_night = base_rate * (1 + plan_doc.rate_value / 100)

	total_amount = rate_per_night * nights

	return {
		"rate_per_night": rate_per_night,
		"total_amount": total_amount,
		"nights": nights,
		"plan_applied": plan_applied,
	}


def find_best_rate_plan(room_type, check_in_date, check_out_date):
	"""Find the best (highest priority) active rate plan for room type + dates.

	Args:
		room_type: Name of the Room Type doc
		check_in_date: date object or string
		check_out_date: date object or string

	Returns:
		Rate Plan name or None
	"""
	if isinstance(check_in_date, str):
		check_in_date = date.fromisoformat(check_in_date)
	if isinstance(check_out_date, str):
		check_out_date = date.fromisoformat(check_out_date)

	nights = (check_out_date - check_in_date).days

	plan = frappe.db.sql(
		"""
		SELECT name FROM `tabRate Plan`
		WHERE room_type = %s
			AND is_active = 1
			AND valid_from <= %s
			AND valid_to >= %s
			AND (min_stay_nights IS NULL OR min_stay_nights <= %s)
			AND (max_stay_nights IS NULL OR max_stay_nights >= %s)
		ORDER BY priority DESC
		LIMIT 1
		""",
		(room_type, check_in_date, check_out_date, nights, nights),
		as_dict=True,
	)

	return plan[0].name if plan else None
