const existingMessages = [];

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
        return '<span class="text-primary font-italic">Just now</span>';
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

// check if the last video is before 30 seconds
function videoDisconnected(lastVideoURL) {
    var url = new URL(lastVideoURL);
    var filenameWithExtension = url.pathname.split("/").pop();
    var filename = filenameWithExtension.split(".")[0];

    var currentTimestamp = Math.floor(Date.now() / 1000);
    var differenceInSeconds = Math.floor(currentTimestamp - filename);
    if (differenceInSeconds >= 30) {
        return true;
    } else {
        return false;
    }

}

const addChatBubble = (exam_submission, timestamp, message, messageType) => {
    var chatContainer = $('#messages');
    if ($('#messages').attr("data-examid") === exam_submission) {
        var chatTimestamp = $('<div class="chat-timestamp"><small>' + timestamp + '</small></div>');
        var msgWithPill = message;
        if (messageType === "Warning") {
            msgWithPill = '<span class="badge badge-pill badge-warning">Warning</span> ' + message
        } else if (messageType === "Critical") {
            msgWithPill = '<span class="badge badge-pill badge-danger">Critical</span> ' + message
        }
        var chatBubble = $('<div class="chat-bubble chat-left"><small>' + msgWithPill + '</small></div>');
        var chatWrapper = $('<div class="messages"></div>');

        chatWrapper.append(chatTimestamp);
        chatWrapper.append(chatBubble);
        chatContainer.append(chatWrapper);
        chatContainer.scrollTop(chatContainer.prop("scrollHeight"));
    }
}

const updateMessages = (exam_submission) => {
    frappe.call({
        method: "lms.lms.doctype.lms_exam_submission.lms_exam_submission.exam_messages",
        args: {
            'exam_submission': exam_submission,
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
                addChatBubble(exam_submission, convertedTime, message.message_text, message.message_type)
            });

        },
    });
};
