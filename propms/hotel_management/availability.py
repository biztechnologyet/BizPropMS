# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe import _
from datetime import date, timedelta


def get_available_rooms(room_type, check_in_date, check_out_date, property_name=None):
	"""Return list of available rooms for given type and date range.

	Args:
		room_type: Name of the Room Type doc
		check_in_date: date object or string
		check_out_date: date object or string
		property_name: Optional Property name to filter rooms

	Returns:
		List of Room docname strings that are available
	"""
	if isinstance(check_in_date, str):
		check_in_date = date.fromisoformat(check_in_date)
	if isinstance(check_out_date, str):
		check_out_date = date.fromisoformat(check_out_date)

	if check_out_date <= check_in_date:
		frappe.throw(_("Check-out date must be after check-in date"))

	filters = {
		"room_type": room_type,
		"is_active": 1,
		"status": ["not in", ["OutOfOrder", "UnderMaintenance"]],
	}
	if property_name:
		filters["property"] = property_name

	all_rooms = frappe.get_all("Room", filters=filters, pluck="name")

	available = []
	for room_name in all_rooms:
		if not rooms_overlap(room_name, check_in_date, check_out_date):
			available.append(room_name)

	return available


def rooms_overlap(room_name, check_in, check_out):
	"""Check if a room has overlapping Confirmed or Checked-In bookings.

	Args:
		room_name: Room docname (room_number)
		check_in: date object
		check_out: date object

	Returns:
		True if there is an overlapping booking, False otherwise
	"""
	overlapping = frappe.db.sql(
		"""
		SELECT name FROM `tabRoom Booking`
		WHERE room = %s
			AND docstatus = 1
			AND booking_status IN ('Confirmed', 'Checked-In')
			AND check_in_date < %s
			AND check_out_date > %s
		""",
		(room_name, check_out, check_in),
	)

	return bool(overlapping)
