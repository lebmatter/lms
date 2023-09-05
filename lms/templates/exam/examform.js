function storeObjectInLocalStorage(key, object) {
    const objectString = JSON.stringify(object);
    localStorage.setItem(key, objectString);
}

function getObjectFromLocalStorage(key) {
    const objectString = localStorage.getItem(key);
    if (objectString) {
        return JSON.parse(objectString);
    }
    else {
        examAlert("Invalid data in browser local storage.")
    }
}

function clearKeyFromLocalStorage(key) {
    localStorage.removeItem(key);
}

// Function to update the countdown timer
function updateTimer() {
    var remainingTime = new Date(exam.end_time) - new Date().getTime();
    if (remainingTime <= 0) {
        // Display "0m 0s" when time is up
        document.getElementById("timer").innerHTML = "00:00";
        examAlert("Exam ended", "Your exam is submitted.");
        return; // Stop the timer from updating further
    }
    // Calculate minutes and seconds
    var minutes = Math.floor((remainingTime % (1000 * 60 * 60)) / (1000 * 60));
    var seconds = Math.floor((remainingTime % (1000 * 60)) / 1000);
    // Display the countdown timer
    document.getElementById("timer").innerHTML = minutes + ":" + seconds;

    // Update the timer every second
    setTimeout(updateTimer, 1000);
}


/*
Exam data will be stored in localStorage in following keys
exam, exanOverview, currentQuestion
*/

const examOverviewKey = "examOverView";
const currentQuestionKey = "currentQuestion";

const answrdCheck = `
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-check" viewBox="0 0 16 16">
        <path d="M10.97 4.97a.75.75 0 0 1 1.07 1.05l-3.99 4.99a.75.75 0 0 1-1.08.02L4.324 8.384a.75.75 0 1 1 1.06-1.06l2.094 2.093 3.473-4.425a.267.267 0 0 1 .02-.022z"/>
      </svg>
    `;
const answrLater = `
<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-clock-history" viewBox="0 0 16 16">
  <path d="M8.515 1.019A7 7 0 0 0 8 1V0a8 8 0 0 1 .589.022l-.074.997zm2.004.45a7.003 7.003 0 0 0-.985-.299l.219-.976c.383.086.76.2 1.126.342l-.36.933zm1.37.71a7.01 7.01 0 0 0-.439-.27l.493-.87a8.025 8.025 0 0 1 .979.654l-.615.789a6.996 6.996 0 0 0-.418-.302zm1.834 1.79a6.99 6.99 0 0 0-.653-.796l.724-.69c.27.285.52.59.747.91l-.818.576zm.744 1.352a7.08 7.08 0 0 0-.214-.468l.893-.45a7.976 7.976 0 0 1 .45 1.088l-.95.313a7.023 7.023 0 0 0-.179-.483zm.53 2.507a6.991 6.991 0 0 0-.1-1.025l.985-.17c.067.386.106.778.116 1.17l-1 .025zm-.131 1.538c.033-.17.06-.339.081-.51l.993.123a7.957 7.957 0 0 1-.23 1.155l-.964-.267c.046-.165.086-.332.12-.501zm-.952 2.379c.184-.29.346-.594.486-.908l.914.405c-.16.36-.345.706-.555 1.038l-.845-.535zm-.964 1.205c.122-.122.239-.248.35-.378l.758.653a8.073 8.073 0 0 1-.401.432l-.707-.707z"/>
  <path d="M8 1a7 7 0 1 0 4.95 11.95l.707.707A8.001 8.001 0 1 1 8 0v1z"/>
  <path d="M7.5 3a.5.5 0 0 1 .5.5v5.21l3.248 1.856a.5.5 0 0 1-.496.868l-3.5-2A.5.5 0 0 1 7 9V3.5a.5.5 0 0 1 .5-.5z"/>
</svg>
`;

frappe.ready(() => {
    clearKeyFromLocalStorage(examOverviewKey);
    clearKeyFromLocalStorage(currentQuestionKey);

    updateOverviewMap();

    // check if exam is already started
    if (!exam["last_question"]) {
        $("#quiz-btn").text("Start exam");
        $("#quiz-btn").show();
        $("#quiz-message").hide();
        $("#quiz-btn").click((e) => {
            e.preventDefault();
            startExam();
        });
    } else {
        $("#start-banner").addClass("hide");
        $("#quiz-form").removeClass("hide");
        // on first load, show the last question loaded
        getQuestion(exam["last_question"]);
    }

    if (exam.submission_status === "Started") {
        // Start the countdown timer
        updateTimer();
    }

    $("#nextQs").click((e) => {
        e.preventDefault();
        // submit the current answer, then load next one
        submitAnswer();
        var currentQuestion = getObjectFromLocalStorage(currentQuestionKey);
        var examOverview = getObjectFromLocalStorage(examOverviewKey);
        // if the question is already loaded, get it or get new
        var nextQs = currentQuestion["no"] + 1;
        if (examOverview.submitted[nextQs] === undefined) {
            getQuestion("");
        } else {
            getQuestion(examOverview.submitted[nextQs].name);
        }
        updateOverviewMap();

    });

    $("#finish").click((e) => {
        e.preventDefault();
        // submit the current answer
        submitAnswer();
        updateOverviewMap();
        $("#start-banner").removeClass("hide");
        $("#quiz-form").addClass("hide");

        $("#quiz-title").html();
        $("#quiz-btn").hide();
        $("#quiz-message").text(
            "You have remaining time in the exam. You can review and revise your answers until the allocated time expires."
        );
        $("#quiz-message").show();
    });

});

function updateOverviewMap() {
    frappe.call({
        method: "lms.lms.doctype.lms_exam_submission.lms_exam_submission.exam_overview",
        args: {
            "exam_submission": exam.candidate_exam,
        },
        success: (data) => {
            storeObjectInLocalStorage(examOverviewKey, data.message);
            // document.getElementById("answered").innerHTML = data.message.total_answered;
            // document.getElementById("notattempted").innerHTML = data.message.total_not_attempted;
            document.getElementById("markedforlater").innerHTML = data.message.total_marked_for_later;
            $("#question-length").text(data.message.total_questions);

            // populate buttons
            // Loop to generate 10 buttons and pill labels
            $("#button-grid").html('');
            for (let i = 1; i <= data.message.total_questions; i++) {
                btnCls = "btn-outline-dark";
                // create a new button
                const button = $("<button disabled></button>");
                button.text(i);
                button.addClass("exam-map-btn btn " + btnCls + " m-1 btn-sm");
                button.attr("id", "button-" + i);
                if (i <= Object.keys(data.message.submitted).length) {
                    button.prop("disabled", false);
                    if (data.message.submitted[i].marked_for_later) {
                        button.html(answrLater + ' ' + i);
                    } else if (data.message.submitted[i].answer) {
                        button.html(answrdCheck + ' ' + i);
                    }
                }
                // append the button and label to the row
                // buttonRow.append(button, label);
                $("#button-grid").append(button);
                button.click((e) => {
                    getQuestion(data.message.submitted[i].name);
                });
            }
        },
    });
};

function displayQuestion(current_qs) {
    $("#quiz-form").fadeOut(300);
    let currentQuestion = {
        "exam": exam.name,
        "no": current_qs.qs_no,
        "name": current_qs.name,
        "key": exam.name + "_question_" + current_qs.qs_no,
        "multiple": current_qs.multiple,
        "type": current_qs.type,
        "question": current_qs.question,
        "description_image": current_qs.description_image,
        "option_1": current_qs.option_1,
        "option_2": current_qs.option_2,
        "option_3": current_qs.option_3,
        "option_4": current_qs.option_4,
        "option_1_image": current_qs.option_1_image,
        "option_2_image": current_qs.option_2_image,
        "option_3_image": current_qs.option_3_image,
        "option_4_image": current_qs.option_4_image,
        "answer": current_qs.answer || '',
        "marked_for_later": current_qs.marked_for_later
    }
    storeObjectInLocalStorage(currentQuestionKey, currentQuestion);
    examOverview = getObjectFromLocalStorage(examOverviewKey);

    $("#start-banner").addClass("hide");
    $("#quiz-form").removeClass("hide");
    $("#current-question").text(currentQuestion["no"])
    $('#markedForLater').prop("checked", false);

    // Set question attributes
    $('#question').attr({
        'data-name': currentQuestion["name"],
        'data-type': currentQuestion["type"],
        'data-multi': currentQuestion["multiple"]
    });
    if (currentQuestion["description_image"]) {
        $("#question-image").show();
        $("#question-image").attr("src", currentQuestion["description_image"]);
    } else {
        $("#question-image").hide();
    }

    // Set question number and instruction
    let instruction;
    if (currentQuestion["type"] == "Choices" && currentQuestion["multiple"]) {
        instruction = "Choose all answers that apply";
    } else if (currentQuestion["type"] == "Choices") {
        instruction = "Choose one answer";
    } else {
        instruction = "Enter the correct answer";
    }
    $('#question-number').text(`Question ${currentQuestion["no"]}: ${instruction}`);

    // Set question text
    $('#question-text').html('');
    $('#question-text').append(currentQuestion["question"]);

    // Populate choices or show input based on question type
    if (currentQuestion["type"] === "Choices") {
        let valuesToMatch = currentQuestion["answer"].split(','); // Extract numeric part
        $('#choices').show();
        $('#text-input').hide();

        let options = {
            "option_1": currentQuestion["option_1"],
            "option_2": currentQuestion["option_2"],
            "option_3": currentQuestion["option_3"],
            "option_4": currentQuestion["option_4"],
        }
        let choicesHtml = '';

        $.each(options, function (key, value) {
            if (value) {
                let inputType = currentQuestion["multiple"] ? 'checkbox' : 'radio';
                let explanation = current_qs[`explanation_${key}`];
                let explanationHtml = explanation ? `<small class="explanation ml-10">${explanation}</small>` : '';
                let checked = '';
                let optImg = currentQuestion[key + "_image"]
                if (valuesToMatch.includes(key.split("_")[1])) {
                    checked = "checked"
                }

                let optImgHtml = '';
                if (optImg) {
                    optImgHtml = `<div class="option-image"><img src="${optImg}" class="img-fluid" alt="" ></div>`
                }
                choicesHtml += `
                    <div class="mb-2">
                        <div class="custom-checkbox">
                            <label class="option-row">
                                <input class="option" value="${key}" type="${inputType}" name="${currentQuestion["key"]}" ${checked}>
                                <div class="option-text">${value}</div>
                            </label>
                        </div>
                        ${explanationHtml}
                        ${optImgHtml}
                    </div>`;
            }
        });
        if (currentQuestion["marked_for_later"]) {
            $('#markedForLater').prop("checked", true);
        }
        $('#examTextInput').hide();
        $('#choices').html('');
        $('#choices').append(choicesHtml);

    } else {
        $('#choices').hide();
        $('#examTextInput').show();
        $("#examTextInput").find("textarea").val(currentQuestion["answer"]);
    }
    // if this is the lastQs, change button
    if (currentQuestion["no"] === examOverview["total_questions"]) {
        $('#nextQs').hide();
        $('#finish').show();
    } else {
        $('#nextQs').show();
        $('#finish').hide();
    }

    if (exam.time) {
        $('#exam-timer').attr('data-time', exam.time);
        $('#exam-timer').show();
    } else {
        $('#exam-timer').hide();
    }
    $("#quiz-form").fadeIn(300);
};

function startExam() {
    frappe.call({
        method: "lms.lms.doctype.lms_exam_submission.lms_exam_submission.start_exam",
        type: "POST",
        args: {
            "exam_submission": exam["candidate_exam"],
        },
        callback: (data) => {
            $("#start-banner").addClass("hide");
            $("#quiz-form").removeClass("hide");
            getQuestion("");
            updateTimer();
        }
    });
};

function getQuestion(question) {
    frappe.call({
        method: "lms.lms.doctype.lms_exam_submission.lms_exam_submission.get_question",
        type: "POST",
        args: {
            "exam_submission": exam["candidate_exam"],
            "question": question,
        },
        callback: (data) => {
            displayQuestion(data.message);
            updateOverviewMap();
        }
    });
};


function submitAnswer() {
    var currentQuestion = getObjectFromLocalStorage(currentQuestionKey);
    let answer;
    var mrkForLtr = $("#markedForLater").prop('checked') ? 1 : 0;
    if (currentQuestion["type"] == "Choices") {
        let checkedValues = [];
        $("[name='" + currentQuestion["key"] + "']:checked").each(function () {
            const numericValue = $(this).val().split("_")[1];
            checkedValues.push(numericValue);
        });

        answer = checkedValues.join(",");
    } else {
        answer = $("#examTextInput").find("textarea").val();
    }

    if (answer === '' && mrkForLtr === 0) {
        examAlert(
            "No answer submitted!", "You need to enter an answer(s) or mark it for later."
        );
    } else {
        frappe.call({
            method: "lms.lms.doctype.lms_exam_submission.lms_exam_submission.submit_question_response",
            type: "POST",
            args: {
                'exam_submission': exam["candidate_exam"],
                'qs_name': currentQuestion["name"],
                'answer': answer,
                'markdflater': mrkForLtr,
            },
            callback: (data) => {
                console.log("submitted answer.")
            },
        });
    }
};