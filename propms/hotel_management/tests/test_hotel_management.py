import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import today, add_days, getdate, nowdate


class TestRoomType(IntegrationTestCase):
    def test_create_room_type(self):
        rt = frappe.get_doc({
            "doctype": "Room Type",
            "room_type_name": "Test Deluxe",
            "base_rate_per_night": 2500,
            "max_adults": 2,
            "max_children": 1,
            "bed_type": "Double",
            "is_active": 1
        }).insert(ignore_permissions=True)
        self.assertEqual(rt.name, "Test Deluxe")
        self.assertEqual(rt.base_rate_per_night, 2500)
        self.assertEqual(rt.is_active, 1)
        frappe.delete_doc("Room Type", rt.name, force=True)

    def test_room_type_defaults(self):
        rt = frappe.get_doc({
            "doctype": "Room Type",
            "room_type_name": "Test Standard",
            "base_rate_per_night": 1500,
            "bed_type": "Single"
        }).insert(ignore_permissions=True)
        self.assertEqual(rt.max_adults, 2)
        self.assertEqual(rt.max_children, 1)
        frappe.delete_doc("Room Type", rt.name, force=True)


class TestRoom(IntegrationTestCase):
    def setUp(self):
        self.rt = frappe.get_doc({
            "doctype": "Room Type",
            "room_type_name": "Test RoomType",
            "base_rate_per_night": 2000,
            "bed_type": "Double"
        }).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.delete_doc("Room Type", self.rt.name, force=True)

    def test_create_room(self):
        room = frappe.get_doc({
            "doctype": "Room",
            "room_number": "T101",
            "room_type": self.rt.name,
            "floor": 1,
            "status": "Available",
            "housekeeping_status": "Clean"
        }).insert(ignore_permissions=True)
        self.assertEqual(room.status, "Available")
        self.assertEqual(room.housekeeping_status, "Clean")
        frappe.delete_doc("Room", room.name, force=True)


class TestGuestProfile(IntegrationTestCase):
    def test_create_guest(self):
        guest = frappe.get_doc({
            "doctype": "Guest Profile",
            "guest_name": "Test Guest Alpha",
            "guest_type": "Individual",
            "id_type": "Passport",
            "id_number": "TEST123",
            "phone": "+251911000001",
            "nationality": "Ethiopia"
        }).insert(ignore_permissions=True)
        self.assertTrue(guest.name.startswith("GST-"))
        frappe.delete_doc("Guest Profile", guest.name, force=True)


class TestRoomBooking(IntegrationTestCase):
    def setUp(self):
        self.rt = frappe.get_doc({
            "doctype": "Room Type",
            "room_type_name": "Test Booking RT",
            "base_rate_per_night": 3000,
            "bed_type": "Queen"
        }).insert(ignore_permissions=True)
        self.guest = frappe.get_doc({
            "doctype": "Guest Profile",
            "guest_name": "Test Booking Guest",
            "guest_type": "Individual",
            "id_type": "Passport",
            "id_number": "BG001",
            "phone": "+251911000002"
        }).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.delete_doc("Guest Profile", self.guest.name, force=True)
        frappe.delete_doc("Room Type", self.rt.name, force=True)

    def test_create_booking(self):
        booking = frappe.get_doc({
            "doctype": "Room Booking",
            "guest": self.guest.name,
            "room_type": self.rt.name,
            "check_in_date": add_days(today(), 1),
            "check_out_date": add_days(today(), 3),
            "adults": 2,
            "rate_per_night": 3000,
            "currency": "ETB",
            "source": "Walk-in"
        }).insert(ignore_permissions=True)
        self.assertEqual(booking.nights, 2)
        self.assertEqual(booking.total_amount, 6000)
        self.assertEqual(booking.booking_status, "Draft")
        frappe.delete_doc("Room Booking", booking.name, force=True)

    def test_submittable(self):
        booking = frappe.get_doc({
            "doctype": "Room Booking",
            "guest": self.guest.name,
            "room_type": self.rt.name,
            "check_in_date": add_days(today(), 5),
            "check_out_date": add_days(today(), 6),
            "adults": 1,
            "rate_per_night": 3000,
            "currency": "ETB",
            "source": "Phone"
        }).insert(ignore_permissions=True)
        self.assertEqual(booking.docstatus, 0)
        booking.submit()
        self.assertEqual(booking.docstatus, 1)
        booking.cancel()
        self.assertEqual(booking.docstatus, 2)
        frappe.delete_doc("Room Booking", booking.name, force=True)


class TestRatePlan(IntegrationTestCase):
    def setUp(self):
        self.rt = frappe.get_doc({
            "doctype": "Room Type",
            "room_type_name": "Test Rate RT",
            "base_rate_per_night": 5000,
            "bed_type": "King"
        }).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.delete_doc("Room Type", self.rt.name, force=True)

    def test_create_rate_plan(self):
        rp = frappe.get_doc({
            "doctype": "Rate Plan",
            "plan_name": "Test Corporate Rate",
            "room_type": self.rt.name,
            "rate_type": "Percentage",
            "rate_value": -20,
            "valid_from": today(),
            "valid_to": add_days(today(), 90),
            "is_active": 1,
            "priority": 10
        }).insert(ignore_permissions=True)
        self.assertEqual(rp.plan_name, "Test Corporate Rate")
        frappe.delete_doc("Rate Plan", rp.name, force=True)


class TestFolio(IntegrationTestCase):
    def setUp(self):
        self.rt = frappe.get_doc({
            "doctype": "Room Type",
            "room_type_name": "Test Folio RT",
            "base_rate_per_night": 2000,
            "bed_type": "Double"
        }).insert(ignore_permissions=True)
        self.guest = frappe.get_doc({
            "doctype": "Guest Profile",
            "guest_name": "Test Folio Guest",
            "guest_type": "Individual",
            "id_type": "Passport",
            "id_number": "FG001",
            "phone": "+251911000003"
        }).insert(ignore_permissions=True)
        self.booking = frappe.get_doc({
            "doctype": "Room Booking",
            "guest": self.guest.name,
            "room_type": self.rt.name,
            "check_in_date": today(),
            "check_out_date": add_days(today(), 2),
            "adults": 2,
            "rate_per_night": 2000,
            "currency": "ETB",
            "source": "Walk-in"
        }).insert(ignore_permissions=True)
        self.booking.submit()

    def tearDown(self):
        frappe.db.rollback()

    def test_create_folio(self):
        folio = frappe.get_doc({
            "doctype": "Folio",
            "guest": self.guest.name,
            "booking": self.booking.name,
            "status": "Open",
            "total_charges": 0,
            "total_payments": 0,
            "balance": 0
        }).insert(ignore_permissions=True)
        self.assertEqual(folio.status, "Open")
        self.assertEqual(folio.total_charges, 0)
        self.assertEqual(folio.total_payments, 0)
        frappe.delete_doc("Folio", folio.name, force=True)


class TestHousekeepingTask(IntegrationTestCase):
    def setUp(self):
        self.rt = frappe.get_doc({
            "doctype": "Room Type",
            "room_type_name": "Test HK RT",
            "base_rate_per_night": 1000,
            "bed_type": "Single"
        }).insert(ignore_permissions=True)
        self.room = frappe.get_doc({
            "doctype": "Room",
            "room_number": "HK101",
            "room_type": self.rt.name,
            "floor": 1,
            "status": "Available",
            "housekeeping_status": "Dirty"
        }).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.delete_doc("Room", self.room.name, force=True)
        frappe.delete_doc("Room Type", self.rt.name, force=True)

    def test_create_task(self):
        task = frappe.get_doc({
            "doctype": "Housekeeping Task",
            "room": self.room.name,
            "task_type": "Checkout Clean",
            "status": "Pending",
            "priority": "High",
            "scheduled_date": today()
        }).insert(ignore_permissions=True)
        self.assertEqual(task.status, "Pending")
        self.assertEqual(task.priority, "High")
        frappe.delete_doc("Housekeeping Task", task.name, force=True)


class TestAvailabilityLogic(IntegrationTestCase):
    def test_rooms_overlap(self):
        from propms.hotel_management.availability import rooms_overlap
        result = rooms_overlap("NONEXISTENT", today(), add_days(today(), 1))
        self.assertFalse(result)
