# -*- coding: utf-8 -*-
# Copyright (c) 2024, Biz Technology Solutions and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document


class Folio(Document):
    def validate(self):
        self.calculate_totals()

    def calculate_totals(self):
        total_charges = 0
        total_payments = 0
        for item in self.get("folio_items", []):
            if item.item_type in ("Room Charge", "F&B", "Service", "Misc"):
                total_charges += item.amount or 0
            elif item.item_type == "Payment":
                total_payments += item.amount or 0
            elif item.item_type == "Discount":
                total_charges -= abs(item.amount or 0)
            elif item.item_type == "Refund":
                total_payments -= abs(item.amount or 0)
        self.total_charges = total_charges
        self.total_payments = total_payments
        self.balance = total_charges - total_payments
        if self.balance <= 0:
            self.payment_status = "Paid"
        elif self.total_payments > 0:
            self.payment_status = "Partial"
        else:
            self.payment_status = "Unpaid"

    def on_submit(self):
        self.status = "Open"

    def on_cancel(self):
        self.status = "Closed"
