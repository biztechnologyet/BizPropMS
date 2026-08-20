import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import today, add_days


class TestPropertyCreation(IntegrationTestCase):
    def test_create_property(self):
        prop = frappe.get_doc({
            "doctype": "Property",
            "property_name": "Test Property Alpha",
            "status": "Available",
            "property_for": "Rent"
        }).insert(ignore_permissions=True)
        self.assertTrue(prop.name)
        self.assertEqual(prop.status, "Available")
        frappe.delete_doc("Property", prop.name, force=True)


class TestUnitType(IntegrationTestCase):
    def test_create_unit_type(self):
        ut = frappe.get_doc({
            "doctype": "Unit Type",
            "unit_type_name": "Test 2BR Apartment",
            "description": "Two bedroom apartment"
        }).insert(ignore_permissions=True)
        self.assertTrue(ut.name)
        frappe.delete_doc("Unit Type", ut.name, force=True)


class TestGuardShift(IntegrationTestCase):
    def test_create_guard_shift(self):
        gs = frappe.get_doc({
            "doctype": "Guard Shift",
            "guard_shift_name": "Test Night Shift",
            "shift_time_from": "22:00:00",
            "shift_time_to": "06:00:00"
        }).insert(ignore_permissions=True)
        self.assertTrue(gs.name)
        frappe.delete_doc("Guard Shift", gs.name, force=True)


class TestMeter(IntegrationTestCase):
    def test_create_meter(self):
        m = frappe.get_doc({
            "doctype": "Meter",
            "meter_name": "Test Meter 001",
            "meter_type": "Electric"
        }).insert(ignore_permissions=True)
        self.assertTrue(m.name)
        frappe.delete_doc("Meter", m.name, force=True)


class TestKeySet(IntegrationTestCase):
    def test_create_key_set(self):
        ks = frappe.get_doc({
            "doctype": "Key Set",
            "key_set_name": "Test Key Set 001",
            "status": "In"
        }).insert(ignore_permissions=True)
        self.assertTrue(ks.name)
        frappe.delete_doc("Key Set", ks.name, force=True)


class TestInsurance(IntegrationTestCase):
    def test_create_insurance(self):
        ins = frappe.get_doc({
            "doctype": "Insurance",
            "insurance_name": "Test Policy",
            "insurance_type": "Property"
        }).insert(ignore_permissions=True)
        self.assertTrue(ins.name)
        frappe.delete_doc("Insurance", ins.name, force=True)


class TestOutsourcingCategory(IntegrationTestCase):
    def test_create_category(self):
        cat = frappe.get_doc({
            "doctype": "Outsourcing Category",
            "outsourcing_category_name": "Test Cleaning Service"
        }).insert(ignore_permissions=True)
        self.assertTrue(cat.name)
        frappe.delete_doc("Outsourcing Category", cat.name, force=True)


class TestPropertyManagementSettings(IntegrationTestCase):
    def test_settings_exist(self):
        settings = frappe.get_single_doc("Property Management Settings")
        self.assertTrue(settings.name)
