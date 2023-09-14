# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import random
import pytz
from datetime import timedelta

import frappe

from frappe.utils import now
from frappe.model.document import Document


class LMSExamSchedule(Document):

	# TODO add validation for start time and end time
	# start time should be greater than now
	# end time >= start + duration

	def validate(self):
		if self.duration <= 0:
			frappe.thow("Duration should be greater than 0.")
		
		self.validate_weightage_table()

		if not self.pass_percentage:
			frappe.throw("Please enter a valid pass percentage")
		
		if self.pass_percentage > 100.0:
			frappe.throw("Pass percentage should not be more than 100")
		
		if self.question_type != "Choices" and not self.examiners:
			frappe.throw(
				"Exam with Question type:{} needs evaluation. Add examiner list.".format(
					self.question_type
			))

	
	def before_save(self):
		if self.question_type != "Choices":
			self.evaluation_required = 1
		# TODO update question list only if the picked list is changed
		self.total_marks, self.total_questions = self.update_questions_for_schedule()


	def validate_weightage_table(self):
		for cat in self.questions:
			if not cat.mark_per_question or not cat.no_of_questions:
				frappe.throw("No. of Qs & Marks per Qs columns for {} category should be more than 0.".format(
					cat.question_category
				))

			# check if selected no. of questions are available in question bank
			get_random_questions(
				cat.question_category, cat.mark_per_question, cat.no_of_questions,
				self.question_type
			)

	def update_questions_for_schedule(self):
		"""
		Function to update assigned questions
		> Validate if required no. of questions
		> Delete existing questions
		> Add questions

		returns: total marks, no of marks
		"""
		self.validate_weightage_table()

		self.questions = []
		
		total_qs = 0
		total_marks = 0
		for cat in self.select_questions:
			questions = get_random_questions(
				cat.question_category, cat.mark_per_question,
				cat.no_of_questions, self.question_type
			)
			for qs in questions:
				self.questions.append({
						"doctype": "Exam Schedule Question",
						"exam_schedule": self.name,
						"question": qs["name"],
						"mark": cat.mark_per_question,
						"category": cat.question_category
				})
				total_marks += cat.mark_per_question
				total_qs += 1
		
		return	total_marks, total_qs


def get_random_questions(category, mark_per_qs, no_of_qs, question_type):
	if question_type == "Mixed":
		cat_qs = frappe.get_all(
				"LMS Exam Question",
				{"category": category, "mark": mark_per_qs},
		)
	else:
		cat_qs = frappe.get_all(
				"LMS Exam Question",
				{"category": category, "mark": mark_per_qs, "type": question_type},
		)
	try:
		return random.sample(cat_qs, no_of_qs)
	except ValueError:
			frappe.throw(
				"Insufficient no. of {} mark questions in {} category. Available: {}".format(
				mark_per_qs, category, len(cat_qs)
			))
