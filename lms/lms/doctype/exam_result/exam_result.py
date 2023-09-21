# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

class ExamResult(Document):
	
	def autoname(self):
		self.name = "{}-{}".format(self.parent, self.exam_question)
