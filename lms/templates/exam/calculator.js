frappe.ready(() => {
    updateResult(0);
});

const getCurrentResult = () => {
    const resultElement = document.getElementById('calcResult');
    return resultElement.value;
};
const updateResult = (newResult) => {
    $("#calcResult").val(newResult);
};

const appendSymbol = symbol => {
    let currentResult;
    // sanitize current result with regex
    var pattern = /^[-+*/%0-9.]*$/;
    if (pattern.test(getCurrentResult()) === true) {
        currentResult = eval(getCurrentResult());
        if (!isFinite(currentResult)) {
            $("#calcResult").val("Error");
            return
        } else {

        }

    }
    else {
        $("#calcResult").val("Error");
        return
    }
    if (symbol === '=') {
        try {
            updateResult(currentResult);
        } catch (error) {
            updateResult('Error');
        }
    } else {
        newResult = currentResult + symbol;
        updateResult(newResult);
    }
};

const appendNumber = number => {
    let currentResult = getCurrentResult();
    newResult = currentResult + number;
    updateResult(newResult);
};

const clearResult = () => {
    updateResult(0);
};