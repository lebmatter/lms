// Copyright (c) 2023, Frappe and contributors
// For license information, please see license.txt

// frappe.ui.form.on("LMS Exam Schedule", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on('LMS Exam Schedule', {
    refresh: function(frm) {
        frm.add_custom_button(__('End Schedule'), function() {
            frappe.call({
                method: 'lms.lms.doctype.lms_exam_schedule.lms_exam_schedule.end_schedule',
                args: {
                    docname: frm.doc.name
                },
                callback: function(response) {
                    if(response.message == "Success") {
                        frappe.msgprint(__('Exam schedule is ended!'));
                        frm.reload_doc();
                    }
                }
            });
        });
    }
});