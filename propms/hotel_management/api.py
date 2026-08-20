# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe import _
from datetime import date, datetime, timedelta

from propms.hotel_management.availability import get_available_rooms, rooms_overlap
from propms.hotel_management.rate_engine import calculate_rate, find_best_rate_plan


@frappe.whitelist()
def check_room_availability(room_type, check_in_date, check_out_date):
	"""Find available rooms for a date range, excluding booked rooms.

	Args:
		room_type: Room Type docname
		check_in_date: string (YYYY-MM-DD)
		check_out_date: string (YYYY-MM-DD)

	Returns:
		List of available Room dicts with details
	"""
	if isinstance(check_in_date, str):
		check_in_date = date.fromisoformat(check_in_date)
	if isinstance(check_out_date, str):
		check_out_date = date.fromisoformat(check_out_date)

	if check_out_date <= check_in_date:
		frappe.throw(_("Check-out date must be after check-in date"))

	available_room_names = get_available_rooms(room_type, check_in_date, check_out_date)

	rooms = []
	for room_name in available_room_names:
		room = frappe.db.get_value(
			"Room",
			room_name,
			["name", "room_number", "property", "floor", "wing", "status", "housekeeping_status"],
			as_dict=True,
		)
		if room:
			rooms.append(room)

	return rooms


@frappe.whitelist()
def get_availability_calendar(property_name, start_date, end_date):
	"""Return room vs date grid for calendar view.

	Args:
		property_name: Property docname
		start_date: string (YYYY-MM-DD)
		end_date: string (YYYY-MM-DD)

	Returns:
		List of dicts: [{room: "101", dates: {date1: "available/occupied/reserved"}}]
	"""
	if isinstance(start_date, str):
		start_date = date.fromisoformat(start_date)
	if isinstance(end_date, str):
		end_date = date.fromisoformat(end_date)

	if end_date <= start_date:
		frappe.throw(_("End date must be after start date"))

	rooms = frappe.get_all(
		"Room",
		filters={"property": property_name, "is_active": 1},
		fields=["name", "room_number"],
		order_by="room_number asc",
	)

	room_names = [r.name for r in rooms]

	bookings = frappe.db.sql(
		"""
		SELECT room, check_in_date, check_out_date, booking_status
		FROM `tabRoom Booking`
		WHERE room IN %(rooms)s
			AND docstatus = 1
			AND booking_status IN ('Confirmed', 'Checked-In')
			AND check_in_date < %(end_date)s
			AND check_out_date > %(start_date)s
		""",
		{"rooms": room_names, "start_date": start_date, "end_date": end_date},
		as_dict=True,
	)

	booking_map = {}
	for b in bookings:
		if b.room not in booking_map:
			booking_map[b.room] = []
		booking_map[b.room].append(b)

	grid = []
	current_date = start_date
	date_columns = []
	while current_date <= end_date:
		date_columns.append(current_date.isoformat())
		current_date += timedelta(days=1)

	for room in rooms:
		dates = {}
		for date_str in date_columns:
			d = date.fromisoformat(date_str)
			status = "available"
			for b in booking_map.get(room.name, []):
				bc_in = b.check_in_date if isinstance(b.check_in_date, date) else date.fromisoformat(b.check_in_date)
				bc_out = b.check_out_date if isinstance(b.check_out_date, date) else date.fromisoformat(b.check_out_date)
				if bc_in <= d < bc_out:
					if b.booking_status == "Checked-In":
						status = "occupied"
					elif b.booking_status == "Confirmed":
						status = "reserved"
					break
			dates[date_str] = status

		grid.append({
			"room": room.room_number,
			"room_name": room.name,
			"dates": dates,
		})

	return {"grid": grid, "dates": date_columns}


@frappe.whitelist()
def get_room_status_board(property_name=None):
	"""Return room status board data for front desk.

	Args:
		property_name: Optional Property docname to filter

	Returns:
		List of dicts with room_number, status, housekeeping_status, current_guest, booking_status
	"""
	filters = {"is_active": 1}
	if property_name:
		filters["property"] = property_name

	rooms = frappe.get_all(
		"Room",
		filters=filters,
		fields=[
			"name", "room_number", "property", "room_type",
			"status", "housekeeping_status", "current_guest", "current_booking",
		],
		order_by="room_number asc",
	)

	result = []
	for room in rooms:
		booking_status = None
		if room.current_booking:
			booking_status = frappe.db.get_value(
				"Room Booking", room.current_booking, "booking_status"
			)

		guest_name = None
		if room.current_guest:
			guest_name = frappe.db.get_value("Guest Profile", room.current_guest, "guest_name")

		result.append({
			"room_number": room.room_number,
			"room_name": room.name,
			"property": room.property,
			"room_type": room.room_type,
			"status": room.status,
			"housekeeping_status": room.housekeeping_status,
			"current_guest": room.current_guest,
			"guest_name": guest_name,
			"booking_name": room.current_booking,
			"booking_status": booking_status,
		})

	return result


@frappe.whitelist()
def check_in_guest(booking_name, room_name=None):
	"""Check in guest: create folio, assign room, update statuses.

	Args:
		booking_name: Room Booking docname
		room_name: Optional specific room to assign

	Returns:
		Dict with folio_name, room_name
	"""
	booking = frappe.get_doc("Room Booking", booking_name)

	if booking.booking_status != "Confirmed":
		frappe.throw(
			_("Booking {0} must be Confirmed to check in. Current status: {1}").format(
				booking_name, booking.booking_status
			)
		)

	today = date.today()
	check_in_date = booking.check_in_date
	if isinstance(check_in_date, str):
		check_in_date = date.fromisoformat(check_in_date)

	if today < check_in_date:
		frappe.throw(_("Cannot check in before the check-in date {0}").format(check_in_date))

	assigned_room = room_name

	if not assigned_room:
		available = get_available_rooms(
			booking.room_type, booking.check_in_date, booking.check_out_date
		)
		if not available:
			frappe.throw(_("No available rooms of type {0} for this date range").format(booking.room_type))
		assigned_room = available[0]

	room = frappe.get_doc("Room", assigned_room)

	if room.room_type != booking.room_type:
		frappe.throw(
			_("Room {0} is type {1}, but booking requires {2}").format(
				assigned_room, room.room_type, booking.room_type
			)
		)

	if room.status == "OutOfOrder" or room.status == "UnderMaintenance":
		frappe.throw(_("Room {0} is out of order or under maintenance").format(assigned_room))

	if rooms_overlap(assigned_room, booking.check_in_date, booking.check_out_date):
		existing = frappe.db.sql(
			"""
			SELECT name FROM `tabRoom Booking`
			WHERE room = %s AND docstatus = 1
				AND booking_status IN ('Confirmed', 'Checked-In')
				AND check_in_date < %s AND check_out_date > %s
				AND name != %s
			""",
			(assigned_room, booking.check_out_date, booking.check_in_date, booking_name),
		)
		if existing:
			frappe.throw(_("Room {0} already has an overlapping booking {1}").format(assigned_room, existing[0][0]))

	room_needs_cleaning = room.housekeeping_status == "Dirty"

	folio = frappe.get_doc({
		"doctype": "Folio",
		"guest": booking.guest,
		"booking": booking.name,
		"room": assigned_room,
		"status": "Open",
		"payment_status": "Unpaid",
		"total_charges": 0,
		"total_payments": 0,
		"balance": 0,
	})
	folio.insert(ignore_permissions=True)

	nights = (booking.check_out_date - booking.check_in_date).days
	if nights <= 0:
		nights = 1

	folio.append("folio_items", {
		"item_type": "Room Charge",
		"description": "Room {0} - {1} night(s)".format(assigned_room, nights),
		"quantity": nights,
		"rate": booking.rate_per_night,
		"amount": booking.rate_per_night * nights,
		"date": today,
		"added_by": frappe.session.user,
	})
	folio.total_charges = booking.rate_per_night * nights
	folio.balance = folio.total_charges
	folio.save(ignore_permissions=True)

	frappe.db.set_value("Room", assigned_room, {
		"status": "Occupied",
		"current_guest": booking.guest,
		"current_booking": booking.name,
	})

	frappe.db.set_value("Room Booking", booking_name, {
		"booking_status": "Checked-In",
		"room": assigned_room,
		"actual_check_in": datetime.now(),
		"checked_in_by": frappe.session.user,
	})

	if room_needs_cleaning:
		_create_housekeeping_task(assigned_room, "Stay Over", today)

	frappe.db.commit()

	return {
		"folio_name": folio.name,
		"room_name": assigned_room,
	}


@frappe.whitelist()
def check_out_guest(booking_name):
	"""Check out guest: finalize charges, release room.

	Args:
		booking_name: Room Booking docname

	Returns:
		Dict with summary
	"""
	booking = frappe.get_doc("Room Booking", booking_name)

	if booking.booking_status != "Checked-In":
		frappe.throw(
			_("Booking {0} is not Checked-In. Current status: {1}").format(
				booking_name, booking.booking_status
			)
		)

	frappe.db.set_value("Room Booking", booking_name, {
		"booking_status": "Checked-Out",
		"actual_check_out": datetime.now(),
		"checked_out_by": frappe.session.user,
	})

	room_name = booking.room
	if room_name:
		frappe.db.set_value("Room", room_name, {
			"status": "Dirty",
			"housekeeping_status": "Dirty",
			"current_guest": None,
			"current_booking": None,
		})

		_create_housekeeping_task(room_name, "Checkout Clean", date.today())

	frappe.db.commit()

	return {
		"booking_name": booking_name,
		"room_name": room_name,
		"status": "Checked-Out",
	}


@frappe.whitelist()
def add_folio_charge(folio_name, item_type, description, rate, quantity=1, charge_date=None):
	"""Add a charge line item to an open folio.

	Args:
		folio_name: Folio docname
		item_type: One of Room Charge/F&B/Service/Misc/Discount/Refund/Payment
		description: Description of the charge
		rate: Rate per unit
		quantity: Number of units (default 1)
		charge_date: Date string (default today)

	Returns:
		Updated Folio dict
	"""
	folio = frappe.get_doc("Folio", folio_name)

	if folio.status != "Open":
		frappe.throw(_("Folio {0} is not Open. Current status: {1}").format(folio_name, folio.status))

	item_date = charge_date if charge_date else date.today()

	amount = rate * quantity

	folio.append("folio_items", {
		"item_type": item_type,
		"description": description,
		"quantity": quantity,
		"rate": rate,
		"amount": amount,
		"date": item_date,
		"added_by": frappe.session.user,
	})

	_recalculate_folio_totals(folio)
	folio.save(ignore_permissions=True)

	frappe.db.commit()

	return {
		"name": folio.name,
		"total_charges": folio.total_charges,
		"total_payments": folio.total_payments,
		"balance": folio.balance,
		"payment_status": folio.payment_status,
	}


@frappe.whitelist()
def process_folio_payment(folio_name, amount, payment_method=None):
	"""Process payment against a folio.

	Args:
		folio_name: Folio docname
		amount: Payment amount
		payment_method: Optional payment method description

	Returns:
		Updated Folio dict
	"""
	folio = frappe.get_doc("Folio", folio_name)

	if folio.status != "Open":
		frappe.throw(_("Folio {0} is not Open. Current status: {1}").format(folio_name, folio.status))

	if amount <= 0:
		frappe.throw(_("Payment amount must be greater than zero"))

	description = "Payment"
	if payment_method:
		description = "Payment - {0}".format(payment_method)

	folio.append("folio_items", {
		"item_type": "Payment",
		"description": description,
		"quantity": 1,
		"rate": amount,
		"amount": amount,
		"date": date.today(),
		"added_by": frappe.session.user,
	})

	_recalculate_folio_totals(folio)
	folio.save(ignore_permissions=True)

	frappe.db.commit()

	return {
		"name": folio.name,
		"total_charges": folio.total_charges,
		"total_payments": folio.total_payments,
		"balance": folio.balance,
		"payment_status": folio.payment_status,
	}


@frappe.whitelist()
def settle_folio(folio_name):
	"""Settle folio: create Sales Invoice from folio charges.

	Args:
		folio_name: Folio docname

	Returns:
		Dict with invoice name
	"""
	folio = frappe.get_doc("Folio", folio_name)

	if folio.status != "Open":
		frappe.throw(_("Folio {0} is not Open. Current status: {1}").format(folio_name, folio.status))

	if folio.balance <= 0 and folio.total_charges > 0:
		frappe.throw(_("Folio {0} is already fully paid").format(folio_name))

	if folio.total_charges <= 0:
		frappe.throw(_("Folio {0} has no charges to settle").format(folio_name))

	booking = frappe.get_doc("Room Booking", folio.booking)
	customer = _get_or_create_customer(booking.guest)

	si = frappe.get_doc({
		"doctype": "Sales Invoice",
		"customer": customer,
		"posting_date": date.today(),
		"company": booking.company or frappe.defaults.get_defaults().company,
	})

	for item in folio.folio_items:
		if item.item_type == "Payment":
			continue
		if item.item_type in ("Discount", "Refund"):
			qty = -1 * abs(item.quantity)
			rate = abs(item.rate)
		else:
			qty = item.quantity
			rate = item.rate

		si.append("items", {
			"item_name": item.description,
			"description": item.description,
			"qty": qty,
			"rate": rate,
			"amount": item.amount,
		})

	if not si.items:
		frappe.throw(_("No charge items found in folio to invoice"))

	si.insert(ignore_permissions=True)
	si.submit()

	for item in folio.folio_items:
		if item.item_type != "Payment":
			frappe.db.set_value("Folio Item", item.name, "sales_invoice", si.name)

	frappe.db.set_value("Folio", folio_name, {
		"status": "Settled",
		"payment_status": "Paid",
	})

	frappe.db.commit()

	return {"sales_invoice": si.name, "folio": folio_name}


@frappe.whitelist()
def run_night_audit():
	"""Manual trigger for nightly audit.

	Returns:
		Summary dict with counts of actions taken
	"""
	from propms.hotel_management.night_audit import execute_night_audit

	return execute_night_audit()


def _recalculate_folio_totals(folio):
	"""Recalculate folio total_charges, total_payments, balance, payment_status."""
	total_charges = 0
	total_payments = 0

	for item in folio.folio_items:
		if item.item_type == "Payment":
			total_payments += item.amount
		else:
			total_charges += item.amount

	balance = total_charges - total_payments

	if balance <= 0 and total_charges > 0:
		payment_status = "Paid"
	elif total_payments > 0:
		payment_status = "Partial"
	else:
		payment_status = "Unpaid"

	folio.total_charges = total_charges
	folio.total_payments = total_payments
	folio.balance = balance
	folio.payment_status = payment_status


def _create_housekeeping_task(room_name, task_type, scheduled_date):
	"""Create a housekeeping task for a room."""
	task = frappe.get_doc({
		"doctype": "Housekeeping Task",
		"room": room_name,
		"task_type": task_type,
		"status": "Pending",
		"priority": "High" if task_type == "Checkout Clean" else "Medium",
		"scheduled_date": scheduled_date,
		"notes": "Auto-generated during {0}".format(task_type.lower()),
	})
	task.insert(ignore_permissions=True)
	return task


def _get_or_create_customer(guest_name):
	"""Get or create a Customer linked to a Guest Profile for invoicing."""
	guest = frappe.get_doc("Guest Profile", guest_name)

	existing = frappe.db.get_value(
		"Customer",
		{"custom_guest_profile": guest_name},
		"name",
	)
	if existing:
		return existing

	customer = frappe.get_doc({
		"doctype": "Customer",
		"customer_name": guest.guest_name,
		"customer_type": "Individual",
		"customer_group": frappe.db.get_single_value("Selling Settings", "customer_group")
		or "All Customer Groups",
		"territory": frappe.db.get_single_value("Selling Settings", "territory")
		or "All Territories",
	})
	customer.insert(ignore_permissions=True)
	return customer.name
