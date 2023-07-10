# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
import pytz
from frappe.model.document import Document


class LMSExamSchedule(Document):

	def validate(self):
		self.validate_timezone()
	
	def validate_timezone(self):
		if not self.timezone:
			return

		if self.timezone not in pytz.all_timezones:
			frappe.throw(_("Invalid timezone."))


	

