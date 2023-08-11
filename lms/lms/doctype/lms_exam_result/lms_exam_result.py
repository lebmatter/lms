# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class LMSExamResult(Document):
	
	def autoname(self):
		if not self.name:
			assert self.exam_submission, self.exam_question
			self.name = "{}-{}".format(self.exam_submission, self.exam_question)
