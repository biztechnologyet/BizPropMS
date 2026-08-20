# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
import unittest
from datetime import date, timedelta


class TestRoomType(unittest.TestCase):
	def setUp(self):
		if not frappe.db.exists("Room Type", "Test Suite"):
			frappe.get_doc({
				"doctype": "Room Type",
				"room_type_name": "Test Suite",
				"bed_type": "King",
				"room_size_sqm": 45,
				"base_rate_per_night": 5000,
				"max_adults": 2,
				"max_children": 1,
				"is_active": 1,
			}).insert(ignore_permissions=True)

	def test_room_type_creation(self):
		rt = frappe.get_doc("Room Type", "Test Suite")
		self.assertEqual(rt.base_rate_per_night, 5000)
		self.assertEqual(rt.bed_type, "King")
		self.assertTrue(rt.is_active)


class TestGuestProfile(unittest.TestCase):
	def setUp(self):
		if not frappe.db.exists("Guest Profile", {"guest_name": "Test Guest HM"}):
			frappe.get_doc({
				"doctype": "Guest Profile",
				"guest_name": "Test Guest HM",
				"guest_type": "Individual",
				"phone": "+251911000000",
				"id_type": "Passport",
				"id_number": "TEST12345",
			}).insert(ignore_permissions=True)

	def test_guest_creation(self):
		guest = frappe.get_all(
			"Guest Profile",
			filters={"guest_name": "Test Guest HM"},
			fields=["name", "guest_name", "phone"],
			limit=1,
		)
		self.assertTrue(guest)
		self.assertEqual(guest[0].guest_name, "Test Guest HM")


class TestRoom(unittest.TestCase):
	def setUp(self):
		if not frappe.db.exists("Room", "T-999"):
			properties = frappe.get_all("Property", limit=1, pluck="name")
			property_name = properties[0] if properties else None
			frappe.get_doc({
				"doctype": "Room",
				"room_number": "T-999",
				"property": property_name,
				"room_type": "Test Suite",
				"status": "Available",
				"housekeeping_status": "Clean",
				"is_active": 1,
			}).insert(ignore_permissions=True)

	def test_room_exists(self):
		room = frappe.db.exists("Room", "T-999")
		self.assertTrue(room)

	def test_room_status(self):
		status = frappe.db.get_value("Room", "T-999", "status")
		self.assertEqual(status, "Available")


class TestAvailability(unittest.TestCase):
	def setUp(self):
		self.room_type = "Test Suite"

	def test_available_rooms_returns_list(self):
		from propms.hotel_management.availability import get_available_rooms
		today = date.today()
		tomorrow = today + timedelta(days=1)
		result = get_available_rooms(self.room_type, today, tomorrow)
		self.assertIsInstance(result, list)

	def test_overlap_detection(self):
		from propms.hotel_management.availability import rooms_overlap
		result = rooms_overlap("T-999", date.today(), date.today() + timedelta(days=1))
		self.assertFalse(result)


class TestRateEngine(unittest.TestCase):
	def setUp(self):
		self.room_type = "Test Suite"

	def test_calculate_rate_basic(self):
		from propms.hotel_management.rate_engine import calculate_rate
		today = date.today()
		checkout = today + timedelta(days=3)
		result = calculate_rate(self.room_type, today, checkout)
		self.assertEqual(result["nights"], 3)
		self.assertEqual(result["rate_per_night"], 5000)
		self.assertEqual(result["total_amount"], 15000)
		self.assertIsNone(result["plan_applied"])

	def test_calculate_rate_invalid_dates(self):
		from propms.hotel_management.rate_engine import calculate_rate
		today = date.today()
		with self.assertRaises(frappe.ValidationError):
			calculate_rate(self.room_type, today, today)

	def test_find_best_rate_plan_no_plans(self):
		from propms.hotel_management.rate_engine import find_best_rate_plan
		today = date.today()
		result = find_best_rate_plan(self.room_type, today, today + timedelta(days=1))
		self.assertIsNone(result)


class TestNightAudit(unittest.TestCase):
	def test_night_audit_runs(self):
		from propms.hotel_management.night_audit import execute_night_audit
		result = execute_night_audit()
		self.assertIn("auto_checkouts", result)
		self.assertIn("room_charges_generated", result)
		self.assertIn("rooms_released", result)
		self.assertIn("housekeeping_tasks_created", result)
		self.assertIn("errors", result)
