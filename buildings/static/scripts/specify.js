function turnOffSpecify(id) {
  console.debug('turning off specify')
  document.getElementById(id).disabled = true;
  document.getElementById(id).required = false;
  document.getElementById(id).value = "";
}

function turnOnSpecify(id) {
  document.getElementById(id).required = true;
  document.getElementById(id).disabled = false;
}

// UX improvement: automatically check the radio/checkbox when user clicks 
// on a specify input field or label. And unselect when label clicked again.
// TODO: This code is kinda ugly, probably a cleaner way to make this work
document.addEventListener("DOMContentLoaded", () => {
  // Catch the click on the parent
  // https://stackoverflow.com/questions/3100319/event-on-a-disabled-input#answer-32925830 
  $("input[id$='_specify_value']").parent().click((e) => {

    let parent = $(e.target);

    // Label is not at the same level in DOM, need to tweak the parent
    if (parent.get(0).nodeName === 'LABEL') {
      parent = parent.parent();
    } 

    const specify_check = parent.find("input[id$='_specify']");
    const specify_input_field = parent.find("input[id$='_specify_value']");
    const element_type = specify_check.attr('type');

    if (element_type === 'radio') {
      // If radio, unselect all other radios (since they are mutually exclusive)
      parent.parent().find('input').each(() => {
        $(this).prop("checked", false);
      })
      // and mark this radio as checked, with its input field required
      // Note: radios are not unselected when we click on the label again
      // since we need at least one value and that's the default behaviour
      specify_check.prop('checked', true);
      specify_input_field.prop('required', true);
      specify_input_field.prop('disabled', false);
      specify_input_field.focus();
    } 
    else if (element_type === 'checkbox') {
      // Checkboxes are not mutually exclusive, so here we don't uncheck the others
      // Even though in our case we do require at least one answer, you can still 
      // return to a state of no checkbox selected after selecting one. 

      // Prevent the event from bubbling to the multi_checkbox_required.js functions
      e.preventDefault();
      
      // Handle the event based on the current state of the checkbox
      // If it was checked, we are unselecting the field, so uncheck 
      // the checkbox, make the input disabled and delete its value
      if (specify_check.prop('checked')) {
        specify_check.prop('checked', false);
        specify_input_field.attr('required', false);
        specify_input_field.prop('value', '');
        specify_input_field.prop('disabled', true);
      } else {
        // Else we are selecting it, so activate the input field
        specify_check.prop('checked', true);
        specify_input_field.prop('required', true);
        specify_input_field.prop('disabled', false);
        specify_input_field.focus();
      }
      // Manually call this multi_checkbox_required.js to set 
      // the other checkboxes required or not as necessary
      markCheckboxesNotRequired(specify_check.attr('name'));
    }
  });
});