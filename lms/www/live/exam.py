from datetime import datetime
import frappe
from frappe import _
from frappe.utils.data import markdown

from lms.lms.doctype.lms_exam_submission.lms_exam_submission import \
	get_submitted_questions
from lms.lms.utils import (
	redirect_to_exams_list
)
from lms.overrides.user import get_candidate_exams

# ACTIVE_EXAM_CODE_CACHE = "ACTIVEEXAMCODECACHE"

def get_context(context):
	context.no_cache = 1

	if frappe.session.user == "Guest":
		raise frappe.PermissionError(_("Please login to access this page."))

	sched_exams = get_candidate_exams(frappe.session.user)
	context.upcoming_exams = sched_exams["upcoming"]
	context.ongoing_exams = sched_exams["ongoing"]
	context.page_context = {}

	if sched_exams["ongoing"]:
		context.alert = {}
		set_live_exam_context(context, sched_exams["ongoing"][0])
	elif sched_exams["upcoming"] and not sched_exams["ongoing"]:
		context.exam = {}
		context.alert = {
			"title": "You have an upcoming exam.",
			"text": "{} exam starts at {}".format(
				sched_exams["upcoming"][0]["exam"],
				sched_exams["upcoming"][0]["schedule_start_time"]
		)}
	else:
		context.exam = {}
		context.alert = {
			"title": "No exams scheduled.",
			"text": "You do not have any live or upcoming exams."
		}
def set_live_exam_context(context, ongoing_exam):
	exam = frappe.db.get_value(
		"LMS Exam", ongoing_exam["exam"], ["name","title"], as_dict=True
	)
	instructions = frappe.db.get_value(
		"LMS Exam Schedule", ongoing_exam["exam_schedule"], "instructions"
	)
	for key, value in ongoing_exam.items():
		exam[key] = value

	exam["instructions"] = markdown(instructions)
	exam["last_question"] = ""

	attempted = get_submitted_questions(ongoing_exam["candidate_exam"])
	# return the last question requested in this exam, if applicable
	if attempted:
		exam["last_question"] = attempted[-1]["exam_question"]
	context.exam = exam

	context.metatags = {
		"title": exam.title,
		"image": exam.image,
		"description": exam.short_introduction,
		"keywords": exam.title,
		"og:type": "website",
	}

