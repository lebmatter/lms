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

/*
Exam data will be stored in localStorage in following keys
exam, exanOverview, currentQuestion
*/

const examOverviewKey = "examOverView";
const currentQuestionKey = "currentQuestion";

frappe.ready(() => {
    clearKeyFromLocalStorage(examOverviewKey);
    clearKeyFromLocalStorage(currentQuestionKey);

    updateOverviewMap();

    // check if exam is already started
    if (exam["last_question"]) {
        $("#start-banner").addClass("hide");
        $("#quiz-form").removeClass("hide");
        // on first load, show the last question loaded
        getQuestion(exam["last_question"]);
    } else {
        $("#quiz-title").text(exam["title"]);
        $("#quiz-btn").text("Start exam");
        $("#quiz-message").hide();
    }

    $("#startExam").click((e) => {
        e.preventDefault();
        startExam();
    });

    $("#nextQs").click((e) => {
        e.preventDefault();
        // submit the current answer, then load next one
        submitAnswer();
        var currentQuestion = getObjectFromLocalStorage(currentQuestionKey);
        var examOverview = getObjectFromLocalStorage(examOverviewKey);
        // if the question is already loaded, get it or get new
        var nextQs = currentQuestion["no"] + 1;
        if (examOverview.submitted[nextQs] === undefined) {
            getQuestion('');
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

        $("#quiz-title").text(exam["title"]);
        $("#quiz-btn").hide();
        $("#quiz-message").text(
            "You can review the answers till the allowed time."
        );
        $("#quiz-message").show();


    });

});


function startExam() {
    frappe.call({
        method: "lms.lms.doctype.lms_exam_submission.lms_exam_submission.start_exam",
        args: {
            'exam_submission': exam["candidate_exam"],
        },
        callback: (data) => {
            getQuestion('');
        },
    });
};

function updateOverviewMap() {
    frappe.call({
        method: "lms.lms.doctype.lms_exam_submission.lms_exam_submission.exam_overview",
        args: {
            "exam_submission": exam.candidate_exam,
        },
        success: (data) => {
            storeObjectInLocalStorage(examOverviewKey, data.message);
            document.getElementById("answered").innerHTML = data.message.total_answered;
            document.getElementById("notattempted").innerHTML = data.message.total_not_attempted;
            document.getElementById("markedforlater").innerHTML = data.message.total_marked_for_later;
            $("#question-length").text(data.message.total_questions);

            // populate buttons
            // Loop to generate 10 buttons and pill labels
            $("#button-grid").html('');
            for (let i = 1; i <= data.message.total_questions; i++) {
                btnStatus = "btn-secondary";
                // create a new button
                const button = $("<button></button>");
                if (data.message.submitted[i] === undefined) {
                    btnStatus = "btn-secondary";
                } else if (data.message.submitted[i].marked_for_later) {
                    btnStatus = "btn-warning";
                } else if (data.message.submitted[i].answer) {
                    btnStatus = "btn-info";
                }

                button.addClass("exam-map-btn btn btn " + btnStatus + " m-1 btn-sm");
                button.text(i);
                button.attr("id", "button-" + i);
                if (i <= data.message.submitted.length) {
                    button.prop("disabled", true);
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


function getQuestion(question) {
    // clearAllQuestions();
    // const cachedQuestion = localStorage.getItem(`${exam["candidate_exam"]}question_${qsNo}`);

    // if (cachedQuestion) {
    //     // The question is already in the cache, use it
    //     displayQuestion(JSON.parse(cachedQuestion));
    // } else {
    frappe.call({
        method: "lms.lms.doctype.lms_exam_submission.lms_exam_submission.get_question",
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

    if (answer === '') {
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
                'markdflater': $("#markedForLater").prop('checked') ? 1 : 0,
            },
            callback: (data) => {
                console.log("submitted answer.")
            },
        });
    }
};