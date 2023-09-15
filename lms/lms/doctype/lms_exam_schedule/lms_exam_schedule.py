# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe

from frappe.utils import now
from frappe.model.document import Document


class LMSExamSchedule(Document):

	def before_save(self):
		question_type = frappe.db.get_value("LMS Exam", self.exam, "question_type")

		if question_type != "Choices" and not self.examiners:
			frappe.msgprint(
				"Warning: Exam with question type:{} needs evaluation. Add examiner list.".format(
					self.question_type
			))