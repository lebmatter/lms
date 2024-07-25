frappe.listview_settings['LMS Exam Submission'] = {
	get_indicator: function (doc) {
		if (doc.status === "Terminated") {
			// Closed
			return [__("Terminated"), "red", "status,=,Terminated"];
		} else if (doc.status === "Submitted") {
			// Closed
			return [__("Submitted"), "green", "status,=,Submitted"];
		} else if (doc.status === "Started") {
			// Closed
			return [__("Started"), "blue", "status,=,Started"];
		}
}};