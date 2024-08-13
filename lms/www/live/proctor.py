from datetime import datetime
import frappe
from frappe import _

def get_context(context):
	"""
	Get the active exams the logged-in user proctoring
	"""
	context.no_cache = 1

	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login"
		raise frappe.Redirect

	context.page_context = {}
	proctor_list = frappe.get_all("LMS Exam Submission", filters={
		"assigned_proctor": frappe.session.user,
	}, fields=["name", "candidate_name", "status"])
	tracker = "{}:tracker"
	live_submissions = [
		p for p in proctor_list if frappe.cache().get(tracker.format(p["name"]))
	]

	context.submissions = live_submissions
	context.pending_candidates = len(proctor_list) - len(live_submissions)
	context.video_chunk_length = frappe.db.get_single_value(
		"LMS Settings", "video_chunk_length"
	)

