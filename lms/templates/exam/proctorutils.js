var videoStore = {};
var currentVideoIndex = {};
const videos = document.getElementsByClassName('video');
const toggleButton = document.getElementsByClassName("toggleButton");

function addEventListenerToClass(className, eventType, handlerFunction) {
    var elements = document.getElementsByClassName(className);

    for (var i = 0; i < elements.length; i++) {
        elements[i].addEventListener(eventType, handlerFunction);
    }
}
function togglePlay() {
    // Find the closest '.video-container' ancestor
    const videoContainer = this.closest('.video-container');

    // Within that container, find the video element
    const video = videoContainer.querySelector('video');
    if (video.paused || video.ended) {
        video.play();
    } else {
        video.pause();
    }
}

function updateToggleButton() {
    // Find the closest '.video-container' ancestor from the video
    const videoContainer = this.closest('.video-container');

    // Within that container, find the toggleButton
    const toggleButton = videoContainer.querySelector('.toggleButton');
    toggleButton.innerHTML = this.paused ? "►" : "❚ ❚";
}

function parseUnitTime(videoURL, addSeconds) {
    var url = new URL(videoURL);
    var filenameWithExtension = url.pathname.split("/").pop();
    var filename = filenameWithExtension.split(".")[0];

    var date = new Date(filename * 1000);
    var hours = String(date.getHours()).padStart(2, '0');
    var minutes = String(date.getMinutes()).padStart(2, '0');
    var seconds = String(date.getSeconds() + Math.floor(addSeconds)).padStart(2, '0');

    return hours + ':' + minutes + ':' + seconds;;

}


function handleProgress() {
    const videoContainer = this.closest('.video-container');
    let fTS = videoContainer.querySelector(".fileTimeStamp");
    let exam_submission = videoContainer.getAttribute("data-videoid");
    let islive = videoContainer.getAttribute("data-islive");

    // Within that container, find the video element
    const video = videoContainer.querySelector('video');
    // show timestamp only if current video is not live
    if (islive === "0") {
        fTS.innerText = parseUnitTime(videoStore[exam_submission][currentVideoIndex[exam_submission]], video.currentTime);
    } else {
        fTS.innerText = "";
    }
}

function scrub(e) {
    const scrubTime = (e.offsetX / progress.offsetWidth) * video.duration;
    video.currentTime = scrubTime;
}

function playVideoAtIndex(exam_submission, index) {
    currentVideoIndex[exam_submission] = index;
    var vid = document.getElementById(exam_submission);
    const videoContainer = vid.closest('.video-container');
    let liveBtn = videoContainer.querySelector(".goLive");
    let skipfwd = videoContainer.querySelector(".skipFwd");

    if (currentVideoIndex[exam_submission] < videoStore[exam_submission].length) {
        vid.src = videoStore[exam_submission][currentVideoIndex[exam_submission]];
        vid.load();
        vid.play();
    } else {
        console.log('End of playlist');
    }

    const video = videoContainer.querySelector('video');
    // if currentidx is length-1, then we are playing last video
    let disconnected = videoDisconnected(videoStore[exam_submission][videoStore[exam_submission].length - 1]);
    if (currentVideoIndex[exam_submission] == videoStore[exam_submission].length - 1) {
        skipfwd.disabled = true;
        // check if the last video is 30 sec old
        if (!video.paused) {
            if (!disconnected) {
                liveBtn.innerHTML = '<svg width="10" height="10" xmlns="http://www.w3.org/2000/svg">' +
                    '<circle cx="5" cy="5" r="5" fill="green" />' +
                    '</svg> Live';
                videoContainer.setAttribute("data-islive", "1");
            } else {
                liveBtn.innerHTML = '<svg width="10" height="10" xmlns="http://www.w3.org/2000/svg">' +
                    '<circle cx="5" cy="5" r="5" fill="red" />' +
                    '</svg> Offline';
                videoContainer.setAttribute("data-islive", "0");
            }

        }
    } else {
        skipfwd.disabled = false;
        if (!disconnected) {
            liveBtn.innerText = "Go Live";
            videoContainer.setAttribute("data-islive", "0");
        } else {
            liveBtn.innerHTML = '<svg width="10" height="10" xmlns="http://www.w3.org/2000/svg">' +
                '<circle cx="5" cy="5" r="5" fill="red" />' +
                '</svg> Disconnected';
            videoContainer.setAttribute("data-islive", "0");
        }
    }

}

function handleSliderUpdate() {
    // Find the closest '.video-container' ancestor
    const videoContainer = this.closest('.video-container');
    let exam_submission = videoContainer.getAttribute("data-videoid");
    playVideoAtIndex(exam_submission, this.value);
}

function playNextVideo() {
    const videoContainer = this.closest('.video-container');
    let exam_submission = videoContainer.getAttribute("data-videoid");
    playVideoAtIndex(exam_submission, currentVideoIndex[exam_submission] + 1);

}

function playLastVideo() {
    const videoContainer = this.closest('.video-container');
    let exam_submission = videoContainer.getAttribute("data-videoid");
    let fTS = videoContainer.querySelector(".fileTimeStamp");
    fTS.innerText = "";

    playVideoAtIndex(exam_submission, videoStore[exam_submission].length - 1);

}

function playPreviousVideo() {
    const videoContainer = this.closest('.video-container');
    let exam_submission = videoContainer.getAttribute("data-videoid");
    playVideoAtIndex(exam_submission, currentVideoIndex[exam_submission] - 1);
}

function openChatModal() {
    const videoContainer = this.closest('.video-container');
    const video = videoContainer.querySelector('video');
    const modalVideo = document.getElementById('modalVideo');
    modalVideo.src = video.src;
    const videoId = videoContainer.getAttribute("data-videoid");
    $('#chatModal').attr("data-videoid", videoId)
    $('#chatModal').modal('show');
    $('#messages').attr("data-examid", videoId)
    updateMessages(videoId);
}

addEventListenerToClass("toggleButton", "click", togglePlay);
addEventListenerToClass("video", "click", togglePlay);
addEventListenerToClass("video", "play", updateToggleButton);
addEventListenerToClass("video", "pause", updateToggleButton);
addEventListenerToClass("video", "timeupdate", handleProgress);
addEventListenerToClass("video", "ended", playNextVideo);
addEventListenerToClass("goLive", "click", playLastVideo);
addEventListenerToClass("skipBack", "click", playPreviousVideo);
addEventListenerToClass("skipFwd", "click", playNextVideo);
addEventListenerToClass("menu", "click", openChatModal);



frappe.ready(() => {
    for (var i = 0; i < videos.length; i++) {
        // Check if the element is an HTML5 video
        if (videos[i].nodeName !== 'VIDEO') {
            continue; // Skip to the next iteration of the loop
        }
        let exam_submission = videos[i].getAttribute('data-videoid');
        frappe.call({
            method: "lms.lms.doctype.lms_exam_submission.lms_exam_submission.proctor_video_list",
            args: {
                "exam_submission": exam_submission,
            },
            success: (data) => {
                var vid = document.getElementById(exam_submission);
                let container = vid.closest(".video-container");
                container.classList.remove("hidden");
                // convert api response to an array of objects
                let videoList = Object.entries(data.message.videos).map(([unixtimestamp, videourl]) => {
                    return { unixtimestamp: parseInt(unixtimestamp, 10), videourl };
                });
                // sort them
                videoList.sort((a, b) => a.unixtimestamp - b.unixtimestamp);


                videoStore[exam_submission] = videoList.map(video => video.videourl);;
                playVideoAtIndex(exam_submission, videoStore[exam_submission].length - 1);
            },
        });
    }
    frappe.realtime.on('newproctorvideo', (data) => {
        videoStore[data.exam_submission].push(data.url);
    });

    frappe.realtime.on('newproctormsg', (data) => {
        convertedTime = timeAgo(data.creation);
        addChatBubble(data.exam_submission, convertedTime, data.message, data.type_of_message)
    });

    // chatModal controls
    // Handle send button click event
    $("#send-button").click(function () {
        var message = $("#message-input").val();
        sendMessage(message);
        $("#message-input").val("");
    });

    // Handle enter key press event
    $("#message-input").keypress(function (e) {
        if (e.which == 13) {
            var message = $("#message-input").val();
            sendMessage(message);
            $("#message-input").val("");
        }
    });

    $("#terminateExam").click(function () {
        let videoId = $('#chatModal').attr("data-videoid");
        var result = prompt("Do you want to terminate this candidate's exam? Confirm by typing `Terminate Exam`. This step is irreversable.");
        if (result === "Terminate Exam") {
            frappe.call({
                method: "lms.lms.doctype.lms_exam_submission.lms_exam_submission.terminate_exam",
                type: "POST",
                args: {
                    'exam_submission': videoId
                },
                callback: (data) => {
                    let confrm = confirm("Exam terminated!");
                    if (confrm) {
                        window.location.reload()
                    }
                },
            });
        } else {
            alert("Invalid input given.");
        }

    });

    // Function to send a message
    function sendMessage(message) {
        let videoId = $('#chatModal').attr("data-videoid");
        if (message.trim() !== "") {
            frappe.call({
                method: "lms.lms.doctype.lms_exam_submission.lms_exam_submission.post_exam_message",
                type: "POST",
                args: {
                    'exam_submission': videoId,
                    'message': message,
                    'type_of_message': "General",
                },
                callback: (data) => {
                    console.log(data);
                },
            });
        }
    }

});