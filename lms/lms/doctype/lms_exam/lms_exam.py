# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import random
import frappe
from frappe.model.document import Document

from ...utils import generate_slug, validate_image

class LMSExam(Document):

	def validate(self):
		self.validate_video_link()
		self.validate_status()
		self.image = validate_image(self.image)

	def validate_video_link(self):
		if self.video_link and "/" in self.video_link:
			self.video_link = self.video_link.split("/")[-1]

	def validate_status(self):
		if self.published:
			self.status = "Approved"


	def autoname(self):
		if not self.name:
			title = self.title
			if self.title == "New Exam":
				title = self.title + str(random.randint(0, 99))
			self.name = generate_slug(title, "LMS Exam")

	def __repr__(self):
		return f"<Exam#{self.name}>"


@frappe.whitelist(allow_guest=True)
def search_exam(text):
	exams = frappe.get_all(
		"LMS Exam",
		filters={"published": True},
		or_filters={
			"title": ["like", f"%{text}%"],
			"tags": ["like", f"%{text}%"],
			"short_introduction": ["like", f"%{text}%"],
			"description": ["like", f"%{text}%"],
		},
		fields=["name", "title"],
	)
	return exams

