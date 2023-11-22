from datetime import datetime
import frappe
from frappe import _
from lms.lms.doctype.lms_exam_submission.lms_exam_submission import proctor_list

def get_context(context):
	"""
	Get the active exams the logged-in user proctoring
	"""
	context.no_cache = 1

	if frappe.session.user == "Guest":
		raise frappe.PermissionError(_("Please login to access this page."))

	context.page_context = {}
	context.submissions = proctor_list()
	context.video_chunk_length = frappe.db.get_single_value(
		"LMS Settings", "video_chunk_length"
	)

