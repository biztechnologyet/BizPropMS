# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe import _
from datetime import date, timedelta


def execute_night_audit():
	"""Nightly audit job - runs at midnight via scheduler.

	Returns:
		Summary dict with counts of actions taken
	"""
	frappe.logger().info("Night Audit: Starting execution")

	results = {
		"auto_checkouts": 0,
		"room_charges_generated": 0,
		"rooms_released": 0,
		"housekeeping_tasks_created": 0,
		"errors": [],
	}

	try:
		results["auto_checkouts"] = auto_checkout_overdue()
	except Exception as e:
		results["errors"].append("Auto-checkout error: {0}".format(str(e)))
		frappe.logger().error("Night Audit - Auto-checkout error: {0}".format(str(e)))

	try:
		results["room_charges_generated"] = generate_room_charges()
	except Exception as e:
		results["errors"].append("Room charges error: {0}".format(str(e)))
		frappe.logger().error("Night Audit - Room charges error: {0}".format(str(e)))

	try:
		results["rooms_released"] = release_checked_out_rooms()
	except Exception as e:
		results["errors"].append("Room release error: {0}".format(str(e)))
		frappe.logger().error("Night Audit - Room release error: {0}".format(str(e)))

	try:
		results["housekeeping_tasks_created"] = create_housekeeping_tasks()
	except Exception as e:
		results["errors"].append("Housekeeping task error: {0}".format(str(e)))
		frappe.logger().error("Night Audit - Housekeeping task error: {0}".format(str(e)))

	frappe.db.commit()

	frappe.logger().info("Night Audit: Completed - {0}".format(results))

	return results


def auto_checkout_overdue():
	"""Check out bookings where check_out_date <= today and status is still Checked-In.

	Returns:
		Count of auto-checkouts performed
	"""
	today = date.today()

	overdue_bookings = frappe.get_all(
		"Room Booking",
		filters={
			"booking_status": "Checked-In",
			"check_out_date": ["<=", today],
			"docstatus": 1,
		},
		fields=["name", "room", "guest"],
	)

	count = 0
	for booking in overdue_bookings:
		try:
			frappe.db.set_value("Room Booking", booking.name, {
				"booking_status": "Checked-Out",
				"actual_check_out": frappe.utils.now_datetime(),
				"checked_out_by": "Administrator",
			})

			if booking.room:
				frappe.db.set_value("Room", booking.room, {
					"status": "Dirty",
					"housekeeping_status": "Dirty",
					"current_guest": None,
					"current_booking": None,
				})

			count += 1
			frappe.logger().info("Night Audit: Auto-checked out booking {0}".format(booking.name))
		except Exception as e:
			frappe.logger().error(
				"Night Audit: Failed to auto-checkout booking {0}: {1}".format(booking.name, str(e))
			)

	return count


def generate_room_charges():
	"""Create room charge folio items for all occupied rooms.

	Generates a daily room charge for each Checked-In booking that does not
	yet have a room charge folio item for today.

	Returns:
		Count of charges generated
	"""
	today = date.today()

	checked_in_bookings = frappe.get_all(
		"Room Booking",
		filters={
			"booking_status": "Checked-In",
			"docstatus": 1,
		},
		fields=["name", "room", "rate_per_night", "check_in_date", "check_out_date"],
	)

	count = 0
	for booking in checked_in_bookings:
		check_out = booking.check_out_date
		if isinstance(check_out, str):
			check_out = date.fromisoformat(check_out)

		if today >= check_out:
			continue

		existing = frappe.db.exists(
			"Folio Item",
			{
				"parenttype": "Folio",
				"parentfield": "folio_items",
				"item_type": "Room Charge",
				"date": today,
			},
		)

		folio_name = frappe.db.get_value(
			"Folio",
			{"booking": booking.name, "status": "Open"},
			"name",
		)

		if not folio_name:
			continue

		already_charged = frappe.db.sql(
			"""
			SELECT name FROM `tabFolio Item`
			WHERE parent = %s AND item_type = 'Room Charge' AND date = %s
			""",
			(folio_name, today),
		)
		if already_charged:
			continue

		try:
			folio = frappe.get_doc("Folio", folio_name)

			folio.append("folio_items", {
				"item_type": "Room Charge",
				"description": "Room {0} - Night".format(booking.room),
				"quantity": 1,
				"rate": booking.rate_per_night,
				"amount": booking.rate_per_night,
				"date": today,
				"added_by": "Administrator",
			})

			total_charges = 0
			total_payments = 0
			for item in folio.folio_items:
				if item.item_type == "Payment":
					total_payments += item.amount
				else:
					total_charges += item.amount

			balance = total_charges - total_payments
			payment_status = "Paid" if balance <= 0 and total_charges > 0 else (
				"Partial" if total_payments > 0 else "Unpaid"
			)

			folio.total_charges = total_charges
			folio.total_payments = total_payments
			folio.balance = balance
			folio.payment_status = payment_status
			folio.save(ignore_permissions=True)

			count += 1
			frappe.logger().info(
				"Night Audit: Generated room charge for booking {0}".format(booking.name)
			)
		except Exception as e:
			frappe.logger().error(
				"Night Audit: Failed to generate charge for booking {0}: {1}".format(
					booking.name, str(e)
				)
			)

	return count


def release_checked_out_rooms():
	"""Set Checked-Out rooms to Dirty status.

	Returns:
		Count of rooms released
	"""
	rooms = frappe.get_all(
		"Room",
		filters={"status": "Occupied"},
		fields=["name", "current_booking"],
	)

	count = 0
	for room in rooms:
		if room.current_booking:
			booking_status = frappe.db.get_value(
				"Room Booking", room.current_booking, "booking_status"
			)
			if booking_status == "Checked-Out":
				frappe.db.set_value("Room", room.name, {
					"status": "Dirty",
					"housekeeping_status": "Dirty",
					"current_guest": None,
					"current_booking": None,
				})
				count += 1
				frappe.logger().info("Night Audit: Released room {0}".format(room.name))

	return count


def create_housekeeping_tasks():
	"""Create housekeeping tasks for rooms that need cleaning.

	Creates tasks for rooms with Dirty housekeeping status that do not
	already have a pending or in-progress task for today.

	Returns:
		Count of tasks created
	"""
	today = date.today()

	dirty_rooms = frappe.get_all(
		"Room",
		filters={
			"housekeeping_status": "Dirty",
			"is_active": 1,
		},
		fields=["name", "status"],
	)

	count = 0
	for room in dirty_rooms:
		existing_task = frappe.db.exists(
			"Housekeeping Task",
			{
				"room": room.name,
				"status": ["in", ["Pending", "In Progress"]],
				"scheduled_date": today,
			},
		)
		if existing_task:
			continue

		task_type = "Checkout Clean" if room.status == "Dirty" else "Stay Over"

		try:
			task = frappe.get_doc({
				"doctype": "Housekeeping Task",
				"room": room.name,
				"task_type": task_type,
				"status": "Pending",
				"priority": "High" if room.status == "Dirty" else "Medium",
				"scheduled_date": today,
				"notes": "Auto-generated by Night Audit",
			})
			task.insert(ignore_permissions=True)
			count += 1
			frappe.logger().info("Night Audit: Created housekeeping task for room {0}".format(room.name))
		except Exception as e:
			frappe.logger().error(
				"Night Audit: Failed to create task for room {0}: {1}".format(room.name, str(e))
			)

	return count
