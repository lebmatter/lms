# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt
from datetime import timedelta, datetime, date
from dateutil.parser import parse
import frappe

from frappe.utils import now
from frappe.model.document import Document


class LMSExamSchedule(Document):

	def on_trash(self):
		frappe.db.delete("LMS Exam Submission", {"exam_schedule": self.name})

	def before_save(self):
		question_type = frappe.db.get_value("LMS Exam", self.exam, "question_type")

		if question_type != "Choices" and not self.examiners:
			frappe.msgprint(
				"Warning: Exam with question type:{} needs evaluation. Add examiner list.".format(
					self.question_type
			))
		
		# validate examiner list
		self.validate_examiner_list()

		# validate cert template
		if self.certificate_template != "":
			has_certification = frappe.db.get_value("LMS Exam", self.exam, "enable_certification")
			if not has_certification:
				frappe.msgprint("Warning: Certification is not enabled in the exam.")
				self.certificate_template = ""

	
	def can_end_schedule(self):
		if self.status == "Ended":
			frappe.msgprint("Schedule is already ended!")
			return False
		
		now = datetime.now()
		end_time = self.start_date_time + timedelta(minutes=self.duration +0)
		if now < end_time:
			frappe.msgprint("Can't end the schedule before {} (end time + 5 min buffer).".format(end_time.isoformat()))
			return False
		
		return True

	def validate_examiner_list(self):
		"""
		get all the other exams which falls in the current exam's timeframe
		make sure that there is no conflicting proctor.
		Conflicting evaluator is fine, since they are not time bound.
		"""
		if not self.examiners:
			return
		
		if type(self.start_date_time) != datetime:
			exam_start = parse(self.start_date_time)
		else:
			exam_start = self.start_date_time
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
			
def check_overlap(start_time1, end_time1, start_time2, end_time2):
	assert isinstance(start_time1, datetime), "start_time1 must be a datetime object"
	assert isinstance(end_time1, datetime), "end_time1 must be a datetime object"
	assert isinstance(start_time2, datetime), "start_time2 must be a datetime object"
	assert isinstance(end_time2, datetime), "end_time2 must be a datetime object"

	# Check if Period 1 starts before Period 2 ends AND Period 1 ends after Period 2 starts
	return start_time1 < end_time2 and end_time1 > start_time2


def _submit_pending_exams(schedule_name):
	"""
	submit exams if pendding
	"""	
	submissions = frappe.get_all(
		"LMS Exam Submission", 
		filters={"exam_schedule": schedule_name},
		fields=["name", "result_status", "status", "total_marks", "exam", "candidate", "candidate_name"]
	)
	for subm in submissions:
		if subm["status"] in ["Submitted", "Terminated", "Registered"]:
			continue
		doc = frappe.get_doc("LMS Exam Submission", subm["name"])
		doc.status = "Submitted"
		doc.exam_submitted_time = datetime.now()
		doc.save(ignore_permissions=True)


def _send_certificates(schedule_name):
	"""
	send certificates if applicable
	"""
	submissions = frappe.get_all(
		"LMS Exam Submission", 
		filters={"exam_schedule": schedule_name},
		fields=["name", "result_status", "status", "total_marks", "exam", "candidate", "candidate_name"]
	)
	for subm in submissions:
		if subm["status"] != "Submitted":
			continue
		
		if subm["result_status"] != "Passed":
			continue

		try:
			frappe.get_last_doc("LMS Exam Certificate", filters={"exam_submission": subm["name"]})
		except frappe.DoesNotExistError:
			today = date.today()
			certexp = frappe.db.get_value("LMS Exam", subm["exam"], "expiry")

			new_cert = frappe.get_doc({
				"doctype":"LMS Exam Certificate",
				"exam_submission": subm["name"],
				"exam": subm["exam"],
				"member": subm["candidate"],
				"member_name": subm["candidate_name"],
				"issue_date": today
			})
			if certexp:
				certexp *= 365
				new_cert.expiry_date = today + timedelta(days=certexp)
			new_cert.insert()

@frappe.whitelist()
def end_schedule(docname):
	"""
	Check if the schedule can be ended
	Submit all unsubmitted exams
	Send certificated if applicable
	"""
	doc = frappe.get_doc("LMS Exam Schedule", docname)
	if not doc.can_end_schedule():
		return

	_submit_pending_exams(docname)
	has_certification = frappe.db.get_value("LMS Exam", doc.exam, "enable_certification")
	if has_certification:
		_send_certificates(docname)

	doc.reload()
	doc.status = 'Ended'
	doc.save()
	return "Success"