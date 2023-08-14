function turnOffSpecify(id) {
  document.getElementById(id).disabled = true;
  document.getElementById(id).required = false;
  document.getElementById(id).value = "";
}

function turnOnSpecify(id) {
  document.getElementById(id).required = true;
  document.getElementById(id).disabled = false;
}

// Check the radio/checkbox associated with the input field  
// when the input is clicked
$(document).ready(() => {
  // Catch the click on the parent
  // https://stackoverflow.com/questions/3100319/event-on-a-disabled-input#answer-32925830 
  $("input[id$='_specify_value']").parent().click((e) => {
    const parent = $(e.target);
    const specify_input = parent.find("input[id$='_specify']");
    // If radio, unselect all other radios
    if (specify_input.attr('type') === 'radio') {
      parent.parent().find('input').each(() => {
        $(this).prop("checked", false);
      })
    }
    specify_input.prop('checked', true);
    const specify_value_input = parent.find("input[id$='_specify_value']");
    specify_value_input.attr('required', true).removeAttr('disabled');
    // Set the cursor in the input
    specify_value_input.focus();
  }
  );

});