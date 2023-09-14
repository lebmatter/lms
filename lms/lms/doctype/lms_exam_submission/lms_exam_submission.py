# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import random
import json
import random
from datetime import datetime, timedelta

import frappe
from frappe.model.document import Document
from frappe.utils import now


class LMSExamSubmission(Document):

	def can_start_exam(self):
		scheduled_start = frappe.db.get_value(
		"LMS Exam Schedule", self.exam_schedule, "start_date_time"
		)
		if self.exam_started_time:
			frappe.throw("Exam already started at {}".format(self.exam_started_time))

		start_time = datetime.strptime(now(), '%Y-%m-%d %H:%M:%S.%f')
		if start_time < scheduled_start:
			frappe.throw("This exam can be started only after {}".format(scheduled_start))

		return start_time

	def exam_ended(self):
		"""
		End time is schedule start time + duration + additional time given
		returns True, end_time if exam has ended
		"""
		scheduled_start, duration = frappe.db.get_value(
		"LMS Exam Schedule", self.exam_schedule, ["start_date_time", "duration"]
		)
		end_time = scheduled_start + timedelta(minutes=duration) + \
			timedelta(minutes=self.additional_time_given)
		
		current_time = datetime.strptime(now(), '%Y-%m-%d %H:%M:%S.%f')

		if current_time >= end_time:
			return True, end_time
		
		return False, end_time	

	def get_messages(self):
		"""
		Get messages as dict
		"""
		res = []
		for msg in self.messages:
			res.append({
				"creation": msg.creation.isoformat(),
				"message_text": msg.message,
				"message_type":msg.type_of_message
			})

		# sort by datetime
		res = sorted(res, key=lambda x: x['creation'])
		
		return res

def can_process_question(doc, member=None):
	"""
	validatior function to run before getting or updating a question
	"""
	if doc.status == "Submitted":
		frappe.throw("Exam is already submitted!")
	elif doc.status == "Started":
		# check if the exam is ended, if so, submit the exam
		exam_ended, end_time = doc.exam_ended()
		if exam_ended:
			doc.status = "Submitted"
			doc.save(ignore_permissions=True)
			frappe.throw("This exam has ended at {}".format(end_time))
	else:
		frappe.throw("Invalid exam.")
	if doc.candidate != (member or frappe.session.user):
		frappe.throw("Invalid exam requested.")


def get_submitted_questions(exam_submission, fields=["exam_question"]):
	all_submitted = frappe.db.get_all(
		"Exam Result",
		filters={"parent": exam_submission},
		fields=fields,
		order_by="creation asc"
	)

	return all_submitted

@frappe.whitelist()
def start_exam(exam_submission=None):
	"""
	Get questions and store order in cache
	"""
	assert exam_submission
	doc = frappe.get_doc("LMS Exam Submission", exam_submission)
	if doc.status == "Started":
		return True

	if frappe.session.user != doc.candidate:
		raise PermissionError("Incorrect exam for the user.")

	start_time = doc.can_start_exam()
	doc.exam_started_time = start_time
	doc.status = "Started"
	doc.save(ignore_permissions=True)

	return True


@frappe.whitelist()
def end_exam(exam_submission=None):
	"""
	Submit Candidate exam
	"""
	assert exam_submission
	doc = frappe.get_doc("LMS Exam Submission", exam_submission)
	if doc.status == "Submitted":
		frappe.throw("Exam is sbumitted already.")
	if doc.status != "Started":
		frappe.throw("Exam is not in started state.")
	
	doc.status = "Submitted"
	doc.save(ignore_permissions=True)

def pick_new_question(exam_schedule, exclude=[], get_random=False):
	"""
	Get question list,
	check if to get random qs or not
	exclude is the list of questions that is 
	"""
	all_qs = frappe.get_all(
		"Exam Schedule Question",
		filters={"parent": exam_schedule},
		fields=["exam_question"],
		order_by="creation desc"
	)
	all_qs_list = [q["exam_question"] for q in all_qs]
	if get_random:
		random.shuffle(all_qs_list)
	
	assigned_qs = None
	for qs in all_qs_list:
		if qs in exclude:
			continue
		else:
			assigned_qs = qs
			break
	
	assert assigned_qs
	return assigned_qs


def validate_and_get_question(exam_submission, question=None, member=None):
	"""
	validations:
	> check exam belongs to signed in user
	"""
	doc = frappe.get_doc("LMS Exam Submission", exam_submission)
	can_process_question(doc)

	schedule_doc = frappe.get_doc(
		"LMS Exam Schedule", doc.exam_schedule, ignore_permissions=True
	)
	submitted = get_submitted_questions(exam_submission)
	submitted_questions = [s["exam_question"] for s in submitted]

	question_number = 0
	question_doc = None
	answer_doc = None
	if not question:
		# check if the user reached max no. of questions
		if len(submitted_questions) >= schedule_doc.total_questions:
			frappe.throw("No more questions in the exam.")
		# new qs no
		question_number = len(submitted_questions) + 1
		question = pick_new_question(
			schedule_doc.name,
			exclude=submitted_questions,
			get_random=schedule_doc.randomize_questions
		)
		# create a new answer doc
		doc.append('submitted_answers',{
			"exam_submission": exam_submission,
			"exam_question": question,
			"question": frappe.db.get_value("LMS Exam Question", question, "question")
		})
		doc.save(ignore_permissions=True)

	else:
		# make sure that question belongs to the exam submission
		try:
			question_number = submitted_questions.index(question) + 1
		except ValueError:
			frappe.throw("Invalid question requested.")
		else:
			answer_doc = frappe.get_doc(
				"Exam Result", "{}-{}".format(exam_submission, question)
			)

	try:
		question_doc = frappe.get_doc("LMS Exam Question", question)
	except frappe.DoesNotExistError:
		frappe.throw("Invalid question requested.")


	return question_number, question_doc, answer_doc

@frappe.whitelist()
def get_question(exam_submission=None, question=None):
	"""
	Single function to fetch a new question or a submitted one.
	if question param is not passed, the function will assign a new question
	"""
	assert exam_submission
	question_number, question_doc, answer_doc = validate_and_get_question(
		exam_submission, question=question
	)

	res = {
		"question": question_doc.question,
		"qs_no": question_number,
		"name": question_doc.name,
		"type": question_doc.type,
		"description_image": question_doc.description_image,
		"option_1": question_doc.option_1,
		"option_2": question_doc.option_2,
		"option_3": question_doc.option_3,
		"option_4": question_doc.option_4,
		"option_1_image": question_doc.option_1_image,
		"option_2_image": question_doc.option_2_image,
		"option_3_image": question_doc.option_3_image,
		"option_4_image": question_doc.option_4_image,
		"multiple": question_doc.multiple,
		# submitted answer
		"marked_for_later": answer_doc.marked_for_later,
		"answer": answer_doc.answer
	}

	return res


@frappe.whitelist()
def submit_question_response(exam_submission=None, qs_name=None, answer="", markdflater=0):
	"""
	Submit response and add marks if applicable
	"""
	assert exam_submission, qs_name

	submission = frappe.get_doc("LMS Exam Submission", exam_submission)
	# check of the logged in user is same as exam submission candidate
	if frappe.session.user != submission.candidate:
		raise PermissionError("You don't have access to submit and answer.")

	can_process_question(submission)

	try:
		frappe.get_doc("LMS Exam Question", qs_name)
	except frappe.DoesNotExistError:
		frappe.throw("Question does not exist.")

	try:
		result_doc = frappe.get_doc(
			"Exam Result", "{}-{}".format(exam_submission, qs_name)
		)
	except frappe.DoesNotExistError:
		frappe.throw("Invalid question.")

	else:
		# check if there is any change in answer or flag
		if result_doc.answer != answer or \
			result_doc.marked_for_later != markdflater:
			result_doc.answer = answer
			result_doc.marked_for_later = markdflater
			result_doc.save(ignore_permissions=True)
		
	return {"qs_name": qs_name}


@frappe.whitelist()
def submit_exam(exam_submission=None):
	"""
	Submit response and add marks if applicable
	"""
	assert exam_submission

	doc = frappe.get_doc("LMS Exam Submission", exam_submission)
	# check of the logged in user is same as exam submission candidate
	if frappe.session.user != doc.candidate:
		raise PermissionError("You don't have access to this exam.")

	if doc.status == "Submitted":
		frappe.throw("Exam is already submitted!")
	elif doc.status == "Started":
		# check if the exam is ended, if so, submit the exam
		exam_ended, end_time = doc.exam_ended()
		if exam_ended:
			doc.status = "Submitted"
			doc.save(ignore_permissions=True)

	return {"status": "Submitted"}

@frappe.whitelist()
def post_exam_message(exam_submission=None, message=None, type_of_message="General"):
	"""
	Submit response and add marks if applicable
	"""
	assert exam_submission
	assert message

	# check of the logged in user is same as exam submission candidate
	if frappe.session.user != frappe.db.get_value(
		"LMS Exam Submission", exam_submission, "candidate"
	):
		raise PermissionError("You don't have access to post messages.")

	submission = frappe.get_doc("LMS Exam Submission", exam_submission)
	submission.append('messages',{
		"from_user": frappe.db.get_value(
		"LMS Exam Submission", exam_submission, "candidate"),
		"message": message,
		"type_of_message": type_of_message
	})
	submission.save(ignore_permissions=True)

	return {"status": 1}


@frappe.whitelist()
def exam_messages(exam_submission=None):
	"""
	Get messages
	"""
	assert exam_submission
	doc = frappe.get_doc("LMS Exam Submission", exam_submission)

	# check of the logged in user is same as exam submission candidate
	if frappe.session.user != doc.candidate:
		raise PermissionError("You don't have access to view messages.")

	return {"messages": doc.get_messages()}


@frappe.whitelist()
def exam_overview(exam_submission=None):
	"""
	return list of questions and its status
	"""
	assert exam_submission
	all_submitted = get_submitted_questions(
		exam_submission, fields=["marked_for_later", "exam_question", "answer"]
	)
	exam_schedule = frappe.db.get_value(
		"LMS Exam Submission", exam_submission, "exam_schedule"
	)
	total_questions = frappe.db.get_value(
		"LMS Exam Schedule", exam_schedule, "total_questions"
	)
	res = {
		"exam_submission": exam_submission,
		"submitted": {},
		"total_questions": total_questions,
		"total_answered": 0,
		"total_marked_for_later": 0,
		"total_not_attempted": 0
	}

	for idx, resitem in enumerate(all_submitted):
		res["submitted"][idx + 1] = {
			"name": resitem["exam_question"],
			"marked_for_later": resitem["marked_for_later"],
			"answer": resitem["answer"]
			}
		if resitem["marked_for_later"]:
			res["total_marked_for_later"] += 1
		else:
			res["total_answered"] += 1

	# find total non-attempted
	res["total_not_attempted"] = res["total_questions"] - \
		res["total_answered"] - res["total_marked_for_later"]

	return res
	



