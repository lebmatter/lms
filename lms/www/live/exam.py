from datetime import datetime
import frappe
from frappe import _
from frappe.utils.data import markdown

from lms.lms.doctype.lms_exam_submission.lms_exam_submission import \
	get_current_qs
from lms.lms.utils import (
	redirect_to_exams_list
)
from lms.overrides.user import get_live_exam

# ACTIVE_EXAM_CODE_CACHE = "ACTIVEEXAMCODECACHE"

def get_context(context):
	context.no_cache = 1

	if frappe.session.user == "Guest":
		raise frappe.PermissionError(_("Please login to access this page."))

	exam_details = get_live_exam(frappe.session.user)
	context.page_context = {}

	if not exam_details:
		context.exam = {}
		context.alert = {
			"title": "No exams scheduled.",
			"text": "You do not have any live or upcoming exams."
		}
	elif exam_details["submission_status"] == "Submitted":
		context.exam = {}
		context.alert = {
			"title": "Exam submitted!",
			"text": "You have already submitted your previous exam: {}.".format(
				exam_details["exam"]
			)
		}
	elif exam_details["live_status"] == "Live":
		context.alert = {}
		exam = frappe.db.get_value(
			"LMS Exam", exam_details["exam"], ["name","title", "instructions"], as_dict=True
		)
		for key, value in exam_details.items():
			exam[key] = value

		exam["instructions"] = markdown(exam["instructions"])
		exam["current_qs"] = 1
		# return the last question requested in this exam, if applicable
		if exam["submission_status"] == "Started":
			_, current_qs_no = get_current_qs(exam_details["exam_submission"]) 
			exam["current_qs"] = current_qs_no
		context.exam = exam

		context.metatags = {
			"title": exam.title,
			"image": exam.image,
			"description": exam.short_introduction,
			"keywords": exam.title,
			"og:type": "website",
		}


	elif exam_details["live_status"] == "Upcoming":
		context.exam = {}
		context.alert = {
			"title": "You have an upcoming exam.",
			"text": "{} exam starts at {}".format(
				exam_details["exam"],
				exam_details["start_time"]
		)}
