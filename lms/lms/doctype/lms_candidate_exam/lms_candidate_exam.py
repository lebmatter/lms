# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt
import random
import json

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate

CANDIDATEQSKEY = "CANDIDATEQS:"
QSCACHEKEY = "QSCACHE"
# map of active exam and active question that user has requested
# Eg., ACTIVEEXAMS:abc123 10
ACTIVEEXAMS = "ACTIVEEXAMS:"


class LMSCandidateExam(Document):

	def cache_candidate_qs_stack(self):
		assigned_qs = frappe.get_all(
			"Exam Schedule Question", {"exam_schedule": self.exam_schedule}
		)
		is_random = frappe.db.get_value(
			"LMS Exam Schedule", self.exam_schedule, "randomize_questions"
		)
		if is_random:
			random.shuffle(assigned_qs)
		
		# store it in cache
		key = CANDIDATEQSKEY + self.candidate
		for q_ in assigned_qs:
			frappe.cache().lpush(key, q_["name"])


	def cache_all_questions(self):
		"""
		Cache all questions for this exam in frappe.cache
		"""
		all_qs = frappe.get_all(
			"Exam Schedule Question",
			filters={"exam_schedule": self.exam_schedule},
			fields=["question"]
		)
		for qs in all_qs:
			qs_doc = frappe.get_doc("LMS Exam Question", qs["name"], as_dict=True)
			frappe.cache().hset(QSCACHEKEY, json.dumps(qs_doc))


@frappe.whitelist()
def start_exam(candidate_exam):
	"""
	Get questions and store order in cache
	"""
	active_exam_key = ACTIVEEXAMS + candidate_exam
	if frappe.cache().get(active_exam_key):
		return True

	doc = frappe.get_doc("LMS Candidate Exam", candidate_exam)
	scheduled_start = frappe.db.get_value(
		"LMS Exam Schedule", doc["exam_schedule"], "start_date_time"
	)
	if nowdate() < scheduled_start:
		frappe.throw("Scheduled exam is yet to start!")

	doc.cache_candidate_qs_stack()
	# mark exam as started
	frappe.cache().set(active_exam_key, 1)

	return True


@frappe.whitelist()
def end_exam(candidate_exam):
	"""
	Submit Candidate exam
	"""
	doc = frappe.get_doc("LMS Candidate Exam", candidate_exam)
	if doc.status == 1:
		frappe.throw("Exam is sbumitted already.")
	
	doc.submit()

def validate_and_get_question(candidate_exam, qs_no):
	"""
	validations:
	> check exam belongs to signed in user
	> check if current  qs is <= max questions
	> make sure that no multi sign is turned on (frappe settings)


	Start exam if it is not already started, assert that requested qs no is 1

	Check if current_qs < submitted qs (in case of going back on exam UI)
	if len(submitted qs) >= current_qs,
		get next qs from cache
	else get from submitted list
	"""
	if not qs_no:
		frappe.throw("Question no. should not be 0.")
	
	try:
		assert type(qs_no) == int
	except AssertionError:
		frappe.throw("Question number should be an integer.")

	doc = frappe.get_doc("LMS Candidate Exam", candidate_exam)
	if doc.docstatus == 1:
		frappe.throw("Exam is already submitted!")
	# check that exam belongs to the current user
	# if doc.candidate != frappe.session.user:
	# 	frappe.throw("Exam does not belong to the logged in user.")

	# check if the user reached max no. of questions
	# This should be dealt by UI ideally
	total_questions = frappe.db.get_value(
		"LMS Exam Schedule", doc.exam_schedule, "total_questions"
	)
	if qs_no > total_questions:
		frappe.throw(
			"Invalid question no. {}! Total questions in exam is {}.".format(
			qs_no, total_questions
		))

	# check if the candidate is requesting a question they already attempted
	attempted = frappe.get_all(
		"LMS Exam Result", {"candidate_exam": candidate_exam}
	)
	try:
		assert qs_no <= len(attempted) + 1
	except AssertionError:
		frappe.throw(
			"Qs no. ({}) cannot be processed. Previous question(s) not attempted!".format(
			qs_no
		))

	qs_name = None
	# requested question is already submitted
	is_submitted = False
	if qs_no <= len(attempted):
		is_submitted = True
		qs_name = attempted[qs_no - 1]["name"]
	elif qs_no == len(attempted) + 1:
		# if current_qs = max(attempted), get next from cache
		key = CANDIDATEQSKEY + doc.candidate
		qs_name = frappe.cache().rpop(key).decode()
	else:
		frappe.throw("Question no ({}) is invalid.".format(qs_no))
	
	if not qs_name:
		frappe.throw("No valid question found.")

	doc.can_fetch_qs()

	qs_doc = {}
	cached_qs = frappe.cache().hget(QSCACHEKEY, qs_name)
	if cached_qs:
		qs_doc = json.loads(cached_qs)
	else:
		qs_doc = frappe.get_doc("LMS Exam Question", qs_name, as_dict=True)
	
	return is_submitted, qs_doc


@frappe.whitelist()
def get_question(candidate_exam, qs_no):
	is_submitted, qs_doc = validate_and_get_question(candidate_exam, qs_no)

	qs_doc["is_submitted"]	= 0
	qs_doc["marked_for_later"] = ""
	qs_doc["user_response"]	= ""
	if is_submitted:
		result_doc = frappe.db.get_value(
			"LMS Exam Result", filters={
				"candidate_exam": candidate_exam,
				"exam_question": qs_doc.name
		}, fields=["marked_for_later", "user_response"])
		qs_doc["is_submitted"]	= 1
		qs_doc["marked_for_later"] = result_doc["marked_for_later"]
		qs_doc["user_response"]	= result_doc["user_response"]

	return qs_doc


@frappe.whitelist()
def submit_question_response(candidate_exam, qs_no, user_response, marked_for_later=True):
	"""
	Submit response and add marks if applicable
	"""
	_, qs_doc = validate_and_get_question(candidate_exam, qs_no)
	result_doc = frappe.db.last_doc(
				"LMS Exam Result", filters={
					"candidate_exam": candidate_exam,
					"exam_question": qs_doc.name
				})
	if not result_doc:
		new_doc = frappe.get_doc({
			"doctype": "LMS Exam Result",
			"candidate_exam": candidate_exam,
			"exam_question": qs_doc.name,
			"marked_for_later": marked_for_later,
			"answer": user_response
		})
		new_doc.insert()
	
	# for mcqs, check correct answer
	



