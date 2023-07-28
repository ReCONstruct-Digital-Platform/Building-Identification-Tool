function deRequire(questionNum) {
  el = document.getElementsByName(questionNum);
  var atLeastOneChecked = false;
  for (i = 0; i < el.length; i++) {
    if (el[i].checked === true) {
      atLeastOneChecked = true;
    }
  }
  if (atLeastOneChecked) {
    for (i = 0; i < el.length; i++) {
      el[i].required = false;
    }
  } else {
    for (i = 0; i < el.length; i++) {
      el[i].required = true;
    }
  }
}

function deDisabled(questionNum) {
  var substring = questionNum.slice(0, -1)
  // If checkbox is checked, activate the associated entry field
  // set it to required.
  if (document.getElementById(questionNum).checked) {
    document.getElementById(substring).disabled = false;
    document.getElementById(substring).required = true;
  }
  // If the checkbox is not checked, disabled the associated entry 
  // field, set it to not required and reset its value.
  else {
    document.getElementById(substring).disabled = true;
    document.getElementById(substring).required = false;
    document.getElementById(substring).value = "";
  }
}
