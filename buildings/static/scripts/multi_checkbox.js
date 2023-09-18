function markCheckboxesNotRequired(name) {
  // Select all checked checkboxes
  checked = document.querySelectorAll(`input[name=${name}][type='checkbox']:checked`);
  const atLeastOneChecked = (checked.length > 0);
  // If a checkbox is checked, we can remove the required flag from all, else it needs to be there.
  all_checkboxes = document.querySelectorAll(`input[name=${name}][type='checkbox']`);
  all_checkboxes.forEach((el) => {el.required = !atLeastOneChecked});
}

function activateSpecifyEntryField(input_id) {
  // Id of the associated entry field
  const entry_field_id = `${input_id}_value`;
  // If checkbox is checked, activate the associated entry field
  // set it to required.
  if (document.getElementById(input_id).checked) {
    document.getElementById(entry_field_id).disabled = false;
    document.getElementById(entry_field_id).required = true;
  }
  // If the checkbox is not checked, disable the associated entry 
  // field, set it to not required and reset its value.
  else {
    document.getElementById(entry_field_id).disabled = true;
    document.getElementById(entry_field_id).required = false;
    document.getElementById(entry_field_id).value = "";
  }
}
