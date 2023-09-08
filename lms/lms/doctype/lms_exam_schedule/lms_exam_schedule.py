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
		
		validate_weightage_table(self.questions)

		if not self.pass_percentage:
			frappe.throw("Please enter a valid pass percentage")
		
		if self.pass_percentage > 100.0:
			frappe.throw("Pass percentage should not be more than 100")


	def before_submit(self):
		self.total_marks, self.total_questions = update_questions_for_schedule(
			self.name, self.questions
		)


def validate_weightage_table(cat_weightage):
	for cat in cat_weightage:
		if not cat.mark_per_question or not cat.no_of_questions:
			frappe.throw("No. of Qs & Marks per Qs columns for {} category should be more than 0.".format(
				cat.question_category
			))
		
		# check if selected no. of questions are available in question bank
		get_random_questions(
			cat.question_category, cat.mark_per_question, cat.no_of_questions
		)


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


def update_questions_for_schedule(exam_schedule, cat_weightage):
	"""
	Function to update assigned questions
	> Validate if required no. of questions
	> Delete existing questions
	> Add questions

	returns: total marks, no of marks
	"""
	validate_weightage_table(cat_weightage)
	existing_questions = frappe.get_all(
		"Exam Schedule Question", {"exam_schedule": exam_schedule}
	)
	for qs in existing_questions:
		frappe.delete_doc("Exam Schedule Question", qs["name"])
	
	question_type = frappe.db.get_value(
		"LMS Exam Schedule", exam_schedule, "question_type"
	)
	
	total_qs = 0
	total_marks = 0
	for cat in cat_weightage:
		questions = get_random_questions(
			cat.question_category, cat.mark_per_question,
			cat.no_of_questions, question_type
		)
		for qs in questions:
			doc = frappe.get_doc({
					"doctype": "Exam Schedule Question",
					"exam_schedule": exam_schedule,
					"question": qs["name"],
					"mark": cat.mark_per_question,
					"category": cat.question_category
			})
			doc.insert()
			total_marks += cat.mark_per_question
			total_qs += 1
	
	return	total_marks, total_qs




