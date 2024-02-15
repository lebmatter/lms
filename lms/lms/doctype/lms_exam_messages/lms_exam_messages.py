# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class LMSExamMessages(Document):
	
	def after_insert(self):
		# trigger webocket msg to proctor and candidate
		chat_message = {
				"creation": self.timestamp.isoformat(),
				"exam_submission": self.exam_submission,
				"message": self.message,
				"type_of_message": self.type_of_message
		}
		frappe.publish_realtime(
			event='newcandidatemsg',
			message=chat_message,
			user=frappe.db.get_value(
				"LMS Exam Submission", self.exam_submission, "candidate"
		))

		# if there is an assigned proctor, send a msg
		proctor = frappe.db.get_value(
				"LMS Exam Submission", self.exam_submission, "assigned_proctor"
		)
		if proctor:
			frappe.publish_realtime(
				event='newproctormsg',
				message=chat_message,
				user=proctor
			)
