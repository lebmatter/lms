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

	def before_save(self):
		self.total_marks, self.evaluation_pending, self.result_status = evaluation_values(
			self.exam, self.submitted_answers
		)
		self.assign_proctor()

	def assign_proctor(self):
		"""
		Assign a proctor keeping round robin
		"""
		sched = frappe.get_doc("LMS Exam Schedule")
		pcount = {
			ex.examiner: ex.proctor_count for ex in sched.examiners if ex.can_proctor
		}
		
		# Determine the examiner with the least number of assignments
		next_examiner = min(pcount, key=pcount.get)
		self.assigned_proctor = next_examiner
	


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

def get_current_qs(exam_submission):
	"""
	Current qs: last qs attempted
	Next qs: next valid qs
	"""
	all_attempted = frappe.db.get_all(
		"Exam Result",
		filters={"parent": exam_submission, "evaluation_status": ("!=", "Not Attempted")},
		fields=["exam_question", "seq_no"],
		order_by="seq_no asc"
	)
	if all_attempted:
		attempted_qs = all_attempted[-1]["exam_question"]
		qs_no = all_attempted[-1]["seq_no"]
		
		return attempted_qs, qs_no
	else:
		return None, None


def evaluation_values(exam, submitted_answers):
	# add marks and evalualtion oending count is applicable
	total_marks = 0
	eval_pending = 0
	for ans in submitted_answers:
		if ans.is_correct:
			total_marks += ans.mark
		if ans.evaluation_status == "Pending":
			eval_pending += 1
	# check result status
	exam_total_mark, pass_perc = frappe.db.get_value(
		"LMS Exam", exam, ["total_marks", "pass_percentage"]
	)
	pass_mark = (exam_total_mark * pass_perc)/100
	if total_marks >= pass_mark:
		result_status = "Passed"
	elif eval_pending == 0:
		result_status = "Failed"
	else:
		result_status = "NA"
	
	return total_marks, eval_pending, result_status

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

	doc.status = "Submitted"
	doc.save(ignore_permissions=True)

	# return result details
	exam = frappe.db.get_value(
		"LMS Exam", doc.exam,
		["show_result", "question_type"],
		as_dict=True
	)
	if exam["question_type"] == "Choices" \
		and exam["show_result"] == "After Exam Submission":
		return {"show_result": 1}
	
	return {"show_result": 0}

@frappe.whitelist()
def get_question(exam_submission=None, qsno=1):
	"""
	Single function to fetch a new question or a submitted one.
	"""
	assert exam_submission
	qs_no = int(qsno)
	doc = frappe.get_doc("LMS Exam Submission", exam_submission)
	can_process_question(doc)
	# check if the requested question is valid
	if qs_no > frappe.db.get_value("LMS Exam", doc.exam, "total_questions"):
		frappe.throw("Invalid question no. {} requested.".format(qs_no))
	# check if the previous question is answered. else throw err
	if qs_no > 1:
		previous_qs_status = frappe.db.get_value(
			"Exam Result",
			{"parent": exam_submission, "seq_no": qs_no-1 },
			"evaluation_status"
		)
		if previous_qs_status == "Not Attempted":
			frappe.throw("Previous question not attempted.")

	try:
		# get the qs with seq no
		qs_name = frappe.db.get_value(
				"Exam Result",
				{"parent": exam_submission, "seq_no": qs_no },
				"exam_question"
		)
	except frappe.DoesNotExistError:
		frappe.throw("Invalid question requested.")
	else:
		question_doc = frappe.get_doc("LMS Exam Question", qs_name)


	answer_doc = frappe.db.get_value(
		"Exam Result", "{}-{}".format(exam_submission, qs_name),
		["marked_for_later", "answer", "seq_no"], as_dict=True
	)

	res = {
		"question": question_doc.question,
		"qs_no": answer_doc["seq_no"],
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
		
	return {"qs_name": qs_name, "qs_no": result_doc.seq_no}


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
	



