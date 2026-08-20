# -*- coding: utf-8 -*-
# Copyright (c) 2024, Biz Technology Solutions and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document


class FolioItem(Document):
    def validate(self):
        if not self.amount and self.quantity and self.rate:
            self.amount = self.quantity * self.rate
