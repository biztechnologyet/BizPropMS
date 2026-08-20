# -*- coding: utf-8 -*-
# Copyright (c) 2024, Biz Technology Solutions and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document


class RoomBooking(Document):
    def validate(self):
        self.calculate_nights()
        self.calculate_totals()

    def calculate_nights(self):
        if self.check_in_date and self.check_out_date:
            from frappe.utils import date_diff
            self.nights = max(date_diff(self.check_out_date, self.check_in_date), 1)

    def calculate_totals(self):
        if self.nights and self.rate_per_night:
            self.total_amount = self.nights * self.rate_per_night
            if self.discount_percent:
                self.net_amount = self.total_amount - (self.total_amount * self.discount_percent / 100)
            else:
                self.net_amount = self.total_amount

    def on_submit(self):
        self.booking_status = "Confirmed"

    def on_cancel(self):
        self.booking_status = "Cancelled"
