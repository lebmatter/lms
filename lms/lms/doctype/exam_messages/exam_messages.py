# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ExamMessages(Document):
	
	def before_save(self):
		if not self.from_user:
			self.from_user = frappe.session.user
