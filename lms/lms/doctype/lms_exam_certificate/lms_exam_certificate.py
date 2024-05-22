# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import os
import tempfile
import frappe
from frappe.model.document import Document
from frappe.utils.pdf import get_pdf


class LMSExamCertificate(Document):
    def after_insert(self):
        self.send_email()

    def can_send_certificate(self):
        has_certification = frappe.db.get_value("LMS Exam", self.exam, "enable_certification")
        assert has_certification, "Exam does not have certification enabled."
        # assert result status
        result_status = frappe.db.get_value("LMS Exam Submission", self.exam_submission, "result_status")
        assert result_status == "Passed", "Exam is not passed. Can't send certificate."

        existing_certs = frappe.get_all("LMS Exam Certificate", filters={"exam_submission": self.exam_submission})
        assert len(existing_certs) == 0, "Cannot create duplicate certificates for same exam."

    def send_email(self):
        self.can_send_certificate()


        cert_template = frappe.db.get_value("LMS Exam", self.exam, "certificate_template")
        cert_template_text = frappe.db.get_value("LMS Exam Certificate Template", cert_template, "template")
        # Render certificate content
        context = {
            "name": self.member_name,
            "score": frappe.db.get_value("LMS Exam Submission", self.exam_submission, "total_marks"),
        }
        cert_content = frappe.render_template(cert_template_text, context)

        # Generate PDF
        pdf_content = get_pdf(cert_content)

        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
            temp_pdf.write(pdf_content)
            temp_pdf_path = temp_pdf.name

        # Retrieve the email template document
        email_template = frappe.get_doc("Email Template", "Exam Certificate Issue")

        # Render the subject and message
        subject = frappe.render_template(email_template.subject, context)
        message = frappe.render_template(email_template.response, context)

        member_email = frappe.db.get_value("User", self.member, "email")

        # Read the PDF content from the temporary file
        with open(temp_pdf_path, 'rb') as pdf_file:
            pdf_attachment = pdf_file.read()

        try:
            # Send the email
            frappe.sendmail(
                recipients=[member_email],
                subject=subject,
                message=message,
                attachments=[{
                    'fname': 'certificate.pdf',
                    'fcontent': pdf_attachment
                }]
            )
        finally:
            # Delete the temporary file
            os.remove(temp_pdf_path)
