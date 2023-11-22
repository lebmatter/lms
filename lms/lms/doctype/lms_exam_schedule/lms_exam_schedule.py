# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt
from datetime import timedelta, datetime
from dateutil.parser import parse
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
		
		# validate examiner list
		self.validate_examiner_list()
		self.assign_examiners()

	def validate_examiner_list(self):
		"""
		get all the other exams which falls in the current exam's timeframe
		make sure that there is no conflicting proctor.
		Conflicting evaluator is fine, since they are not time bound.
		"""
		if not self.examiners:
			return
		
		exam_start = parse(self.start_date_time)
		end_time = exam_start + timedelta(minutes=self.duration)
		other_exams = frappe.get_all(
			"LMS Exam Schedule",
			filters=[["start_date_time", ">=", exam_start]],
			fields=["name", "duration", "start_date_time"], 
		)

		for exam2 in other_exams:
			examiners1 = [ex.examiner for ex in self.examiners]
			exam2_end = exam2["start_date_time"] + timedelta(minutes=exam2["duration"])
			if check_overlap(exam_start, end_time, exam2["start_date_time"], exam2_end):
				examiners2 = frappe.db.get_all(
					"Examiner",
					filters={"parent": "resulttest", "can_proctor": 1},
					fields=["examiner"]
				)
				examiners2 = [ex.examiner for ex in examiners2]
				# check if any examiner in the 2nd list
				overlap = set(examiners1).intersection(set(examiners2))
				if overlap:
					frappe.throw(
						"Can't add {} as proctor(s). Overlap found with schedule {}".format(
							overlap, exam2["name"]
						))
			

	def assign_examiners(self):
		"""
		Fn should be called on before_save
		This will overwrite all submissions
		"""
		assignments_proctor = {}
		assignments_evaluator = {}
		proctors = [ex.examiner for ex in self.examiners if ex.can_proctor]
		evaluators = [ex.examiner for ex in self.examiners if ex.can_evaluate]
		candidates = frappe.get_all(
			"LMS Exam Submission",
			filters={
				"exam_schedule": self.name
		}, fields=["name", "assigned_proctor", "assigned_evaluator"],
		order_by="name")
		candidate_list = [c_["name"] for c_ in candidates]

		# Iterate over candidates and assign each to an examiner
		for i, candidate in enumerate(candidate_list):
			# Cycle through procots
			proctor = proctors[i % len(proctors)]
			if proctor not in assignments_proctor:
				assignments_proctor[proctor] = []
			assignments_proctor[proctor].append(candidate)

			# Cycle through evaluators
			evaluator = evaluators[i % len(evaluators)]
			if evaluator not in assignments_evaluator:
				assignments_evaluator[evaluator] = []
			assignments_evaluator[evaluator].append(candidate)

		for examiner_, submissions_ in assignments_proctor.items():
			# update submission
			for sub_ in submissions_:
				existing_user = frappe.db.get_value(
					"LMS Exam Submission", sub_, "assigned_proctor"
				)
				if examiner_ != existing_user:
					frappe.db.set_value(
						"LMS Exam Submission", sub_, "assigned_proctor", examiner_
					)
		for examiner_, submissions_ in assignments_evaluator.items():
			# update submission
			for sub_ in submissions_:
				existing_user = frappe.db.get_value(
					"LMS Exam Submission", sub_, "assigned_evaluator"
				)
				if examiner_ != existing_user:
					frappe.db.set_value(
						"LMS Exam Submission", sub_, "assigned_evaluator", examiner_
					)
		# update current schedule
		for doc in self.examiners:
			if doc.examiner in assignments_proctor:
				doc.proctoring_count = len(assignments_proctor[doc.examiner])
			if doc.examiner in assignments_evaluator:
				doc.evaluation_count = len(assignments_evaluator[doc.examiner])


def check_overlap(start_time1, end_time1, start_time2, end_time2):
    assert isinstance(start_time1, datetime), "start_time1 must be a datetime object"
    assert isinstance(end_time1, datetime), "end_time1 must be a datetime object"
    assert isinstance(start_time2, datetime), "start_time2 must be a datetime object"
    assert isinstance(end_time2, datetime), "end_time2 must be a datetime object"

    # Check if Period 1 starts before Period 2 ends AND Period 1 ends after Period 2 starts
    return start_time1 < end_time2 and end_time1 > start_time2
