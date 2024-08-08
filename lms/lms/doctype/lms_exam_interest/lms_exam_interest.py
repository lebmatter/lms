# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

def create_website_user(full_name, email):
    # Check if the user already exists
    if frappe.db.exists("User", email):
        return email

    # Split full name into first name and last name
    name_parts = full_name.split()
    first_name = name_parts[0]
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
    
    # Create a new user
    user = frappe.get_doc({
        "doctype": "User",
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "enabled": 1,
        "user_type": "Website User"
    })
    
    # Add roles (adjust as needed)
    user.add_roles("LMS Exam Candidate")
    # Save the user
    user.insert(ignore_permissions=True)
    return email

class LMSExamInterest(Document):
	
	def before_insert(self):
		# check if the same entry exists
		if frappe.db.exists({
			"doctype": "LMS Exam Interest",
			"email": self.email,
			"exam_schedule": self.exam_schedule
		}):
			self.is_duplicate = True

		useremail = create_website_user(self.full_name, self.email)
		self.user = useremail
	
	def after_insert(self):
		if not frappe.db.exists({"doctype": "LMS Exam Submission", "candidate": self.email, "exam_schedule": self.exam_schedule}):
			new_submission = frappe.get_doc(
				{"doctype": "LMS Exam Submission", "candidate": self.email, "exam_schedule": self.exam_schedule}
			)
			new_submission.insert(ignore_permissions=True)
			frappe.db.commit()