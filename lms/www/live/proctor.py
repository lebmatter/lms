from datetime import datetime
import frappe
from frappe import _

def get_context(context):
	"""
	Get the active exams the logged-in user proctoring
	"""
	context.no_cache = 1

	if frappe.session.user == "Guest":
		raise frappe.PermissionError(_("Please login to access this page."))

	context.page_context = {}
	proctor_list = frappe.get_all("LMS Exam Submission", filters={
		"assigned_proctor": frappe.session.user,
		"status": "Started"
	}, fields=["name", "candidate_name"])
	tracker = "{}:tracker"
	live_submissions = [
		p for p in proctor_list if frappe.cache().get(tracker.format(p["name"]))
	]

	context.submissions = live_submissions
	context.video_chunk_length = frappe.db.get_single_value(
		"LMS Settings", "video_chunk_length"
	)

