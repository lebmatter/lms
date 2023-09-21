const existingMessages = [];
frappe.ready(() => {
    let awayStartTime;

    if (exam["submission_status"] === "Started") {
        $(window).blur(function () {
            if (exam.restrict_tab_changes === 1) {
                awayStartTime = new Date();
                examAlert(
                    "Tab change detected",
                    "Multiple tab changes will result in exam termination!",
                );
            }
        });
    }


    $("#examAlert").on("hidden.bs.modal", function () {
        if (awayStartTime) {
            const currentTime = new Date();
            const timeAwayInMilliseconds = currentTime - awayStartTime;
            const timeAwayInMinutes = Math.floor(timeAwayInMilliseconds / (1000 * 60));
            const timeAwayInSeconds = Math.floor((timeAwayInMilliseconds % (1000 * 60)) / 1000);

            console.log(currentTime, awayStartTime);
            console.log(timeAwayInMinutes, timeAwayInSeconds);
            tabChangeStr = `Tab changed for ${timeAwayInMinutes}:${timeAwayInSeconds}s`;
            awayStartTime = null;
            frappe.call({
                method: "lms.lms.doctype.lms_exam_submission.lms_exam_submission.post_exam_message",
                type: "POST",
                args: {
                    'exam_submission': exam["exam_submission"],
                    'message': tabChangeStr,
                    'type_of_message': 'Warning',
                },
                callback: (data) => {
                    console.log(data);
                },
            });
        }
    });

    setInterval(updateMessages, 2000);
});

const examAlert = (alertTitle, alertText) => {
    $('#alertTitle').text(alertTitle);
    $('#alertText').text(alertText);
    $('#examAlert').modal('show');
}

function timeAgo(timestamp) {
    const currentTime = new Date();
    const providedTime = new Date(timestamp);
    const timeDifference = currentTime - providedTime;
    const minutesDifference = Math.floor(timeDifference / (1000 * 60));

    if (minutesDifference < 1) {
        return 'Just now';
    } else if (minutesDifference === 1) {
        return '1 minute ago';
    } else if (minutesDifference < 60) {
        return minutesDifference + ' minutes ago';
    } else if (minutesDifference < 120) {
        return '1 hour ago';
    } else if (minutesDifference < 1440) {
        return Math.floor(minutesDifference / 60) + ' hours ago';
    } else if (minutesDifference < 2880) {
        return '1 day ago';
    } else {
        return Math.floor(minutesDifference / 1440) + ' days ago';
    }
}

const addChatBubble = (timestamp, message, messageType) => {
    var chatContainer = $('#messages');
    var chatTimestamp = $('<div class="chat-timestamp">' + timestamp + '</div>');
    var msgWithPill = message;
    if (messageType === "Warning") {
        msgWithPill = '<span class="badge badge-pill badge-warning">Warning</span> ' + message
    } else if (messageType === "Critical") {
        msgWithPill = '<span class="badge badge-pill badge-danger">Critical</span> ' + message
    }
    var chatBubble = $('<div class="chat-bubble chat-left"><p>' + msgWithPill + '</p></div>');
    var chatWrapper = $('<div class="messages"></div>');

    chatWrapper.prepend(chatTimestamp);
    chatWrapper.prepend(chatBubble);
    chatContainer.prepend(chatWrapper);
}

const updateMessages = () => {
    frappe.call({
        method: "lms.lms.doctype.lms_exam_submission.lms_exam_submission.exam_messages",
        args: {
            'exam_submission': exam["exam_submission"],
        },
        callback: (data) => {
            msgData = data.message["messages"];
            $("#msgCount").text(msgData.length);

            // Check if any new messages exist
            const newMessages = msgData.filter(
                message => !existingMessages.includes(message.message_text)
            );

            // Add new messages to the existing messages array
            existingMessages.push(...newMessages.map(message => message.message_text));


            // loop through msgs and add alerts
            // Add new messages as alerts to the Bootstrap div
            newMessages.forEach(message => {
                convertedTime = timeAgo(message.creation);
                addChatBubble(convertedTime, message.message_text, message.message_type)
            });

        },
    });
};
