// Copyright (c) 2023, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on("LMS Exam Submission", {
    refresh(frm) {
        frappe.call({
            method: "lms.lms.doctype.lms_exam_submission.lms_exam_submission.exam_video_list",
            args: {
                "exam_submission": frm.doc.name,
            },
            callback: function (r) {
                // Convert the object into an array of key-value pairs
                const videoArray = Object.entries(r.message.videos);

                // Sort the array based on Unix timestamps in ascending order
                videoArray.sort((a, b) => a[0] - b[0]);
                var videoElement = document.getElementById("candidateVideo");
                var playPauseBtn = document.getElementById('play-pause-btn');
                var previousBtn = document.getElementById('previous-btn');
                var nextBtn = document.getElementById('next-btn');
                var indexField = document.getElementById('index-field');

                var currentIndex = 0;

                function playVideo() {
                    videoElement.src = videoArray[currentIndex][1];
                    videoElement.play();
                    indexField.value = (currentIndex + 1) + '/' + videoArray.length;
                }

                playPauseBtn.addEventListener('click', function () {
                    if (videoElement.paused) {
                        videoElement.play();
                    } else {
                        videoElement.pause();
                    }
                });

                previousBtn.addEventListener('click', function () {
                    currentIndex--;
                    playVideo();
                });

                nextBtn.addEventListener('click', function () {
                    currentIndex++;
                    playVideo();
                });

                // Initial video playback
                playVideo();
            },
        });
    },
});
