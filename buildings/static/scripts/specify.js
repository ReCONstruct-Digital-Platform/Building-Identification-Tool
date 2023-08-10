function turnOffSpecify(id) {
  document.getElementById(id).disabled = true;
  document.getElementById(id).value = "";
}

function turnOnSpecify(id) {
  document.getElementById(id).required = true;
  document.getElementById(id).disabled = false;
}

