# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class ExamResult(Document):
	
	def autoname(self):
		self.name = "{}-{}".format(self.parent, self.exam_question)

	def before_save(self):
		"""
		Validate if appilicable before save
		"""
		# evaluate
		question_type, mark = frappe.db.get_value(
			"LMS Exam Question", self.exam_question, ["question_type", "mark"]
		)
		if question_type == "Choices" and self.answer:
			answered_options = [ans for ans in self.answer.split(",")]
			correct_options = frappe.db.get_value(
				"LMS Exam Question", self.exam_question,
				[
					"is_correct_1",
					"is_correct_2",
					"is_correct_3",
					"is_correct_4"
				],
				as_dict=True
			)
			correct_options = [cans.aplit("is_correct_")[1] for cans in correct_options]
			if sorted(answered_options) == sorted(correct_options):
				self.is_correct = 1
				self.evaluation_status = "Auto"
				self.mark = mark