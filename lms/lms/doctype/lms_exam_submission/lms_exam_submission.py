# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

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
		frappe.throw("Exam submitted!")
	elif doc.status == "Started":
		# check if the exam is ended, if so, submit the exam
		exam_ended, end_time = doc.exam_ended()
		if exam_ended:
			doc.status = "Submitted"
			doc.save(ignore_permissions=True)
			frappe.throw("This exam has ended at {}".format(end_time))
	else:
		frappe.throw("Exam is not started yet.")
	if doc.candidate != (member or frappe.session.user):
		frappe.throw("Invalid exam requested.")

def get_submitted_questions(exam_submission, fields=["exam_question"]):
	all_submitted = frappe.db.get_all(
		"Exam Result",
		filters={"parent": exam_submission, "evaluation_status": ("!=", "Not Attempted")},
		fields=fields,
		order_by="seq_no asc"
	)

	return all_submitted

@frappe.whitelist()
def start_exam(exam_submission=None):
	"""
	start exam, Get questions and store in order
	"""
	assert exam_submission
	doc = frappe.get_doc("LMS Exam Submission", exam_submission)
	if doc.status == "Started":
		return True

	if frappe.session.user != doc.candidate:
		raise PermissionError("Incorrect exam for the user.")

	start_time = doc.can_start_exam()
	doc.exam_started_time = start_time
	# get questions
	questions = frappe.get_all(
		"Schedule Exam Question", filters={"parent": doc.exam}, fields=["exam_question"]
	)
	random_questions = frappe.db.get_value("LMS Exam", doc.exam, "randomize_questions")
	if random_questions:
		random.shuffle(questions)

	doc.submitted_answers = []
	for idx, qs in enumerate(questions):
		seq_no = idx + 1
		doc.append(
			'submitted_answers',{
				"seq_no": seq_no,
				"exam_question": qs["exam_question"],
				"evaluation_status": "Not Attempted"
		})

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

	# add marks and evalualtion oending count is applicable
	total_marks = 0
	eval_pending = 0
	for ans in doc.submitted_answers:
		if ans.is_correct:
			total_marks += ans.mark
		if ans.evaluation_status == "Pending":
			eval_pending += 1

	doc.total_marks = total_marks
	doc.evaluation_pending = eval_pending
	# check result status
	exam_total_mark, pass_perc = frappe.db.get_value(
		"LMS Exam", doc.exam, ["total_marks", "pass_percentage"]
	)
	pass_mark = (exam_total_mark * pass_perc)/100
	if total_marks >= pass_mark:
		doc.result_status = "Passed"
	doc.status = "Submitted"
	doc.save(ignore_permissions=True)

@frappe.whitelist()
def get_question(exam_submission=None, question=None):
	"""
	Single function to fetch a new question or a submitted one.
	if question param is not passed, the function will assign a new question
	"""
	assert exam_submission
	doc = frappe.get_doc("LMS Exam Submission", exam_submission)
	can_process_question(doc)

	question_number = 0
	picked_qs = None
	if not question:
		allqs = frappe.get_all(
			"Exam Result",
			filters={"parent": doc.name},
			fields=["name", "exam_question", "seq_no", "evaluation_status"],
			order_by="seq_no asc"
		)
		for qs in allqs:
			if qs["evaluation_status"] == "Not Attempted":
				question_number = qs["seq_no"]
				picked_qs = qs["exam_question"]
				break
	else:
		picked_qs = question

	try:
		question_number = frappe.db.get_value(
			"Exam Result", "{}-{}".format(exam_submission, question), "seq_no"
		)
	except ValueError:
		frappe.throw("Invalid question requested.")
	else:
		picked_qs = question

	try:
		question_doc = frappe.get_doc("LMS Exam Question", picked_qs)
	except frappe.DoesNotExistError:
		frappe.throw("Invalid question requested.")


	answer_doc = frappe.db.get_value(
		"Exam Result", "{}-{}".format(exam_submission, picked_qs),
		["marked_for_later", "answer"], as_dict=True
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
		"marked_for_later": answer_doc["marked_for_later"],
		"answer": answer_doc["answer"]
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
			result_doc.evaluation_status = "Pending"
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
		frappe.throw("Exam submitted!")
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
		exam_submission, fields=["marked_for_later", "exam_question", "answer", "seq_no"]
	)
	exam_schedule = frappe.db.get_value(
		"LMS Exam Submission", exam_submission, "exam_schedule"
	)
	exam = frappe.db.get_value("LMS Exam Schedule", exam_schedule, "exam")
	total_questions = frappe.db.get_value("LMS Exam", exam, "total_questions")
	res = {
		"exam_submission": exam_submission,
		"submitted": {},
		"total_questions": total_questions,
		"total_answered": 0,
		"total_marked_for_later": 0,
		"total_not_attempted": 0
	}

	for idx, resitem in enumerate(all_submitted):
		res["submitted"][resitem["seq_no"]] = {
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
	



