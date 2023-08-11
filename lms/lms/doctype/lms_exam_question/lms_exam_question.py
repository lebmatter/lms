# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from lms.lms.doctype.lms_quiz.lms_quiz import validate_correct_options, \
	validate_duplicate_options, validate_possible_answer


class LMSExamQuestion(Document):

	def validate(self):
		if self.type == "Choices":
			validate_duplicate_options(self)
			validate_correct_options(self)
		else:
			validate_possible_answer(self)

