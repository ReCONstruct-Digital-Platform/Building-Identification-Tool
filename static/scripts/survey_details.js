const datasetQueryBuilderId = "#query-builder-dataset";
const surveyQueryBuilderId = "#query-builder-surveys";

function getCurrentQuery() {
  return {
    ...getOrderByConfig(),
    ...getColumnConfigs("user_bldg_cols", "draggable-list"),
    ...getColumnConfigs("user_survey_cols", "draggable-list-survey"),
    ...getQueryBuilderQuery(datasetQueryBuilderId, "dataset_query"),
    ...getQueryBuilderQuery(surveyQueryBuilderId, "survey_query"),
  };
}

function getOrderByConfig() {
  const field = document.getElementById("order-by-field").value;
  const dir = document.querySelector('input[name="order-by-dir"]:checked').value;
  if (!(field === "address" && dir === "asc")) {
    return {
      field: field,
      dir: dir,
    };
  }
}

function getQueryBuilderQuery(queryBuilderId, returnKey) {
  // If querybuilder has no children, it doesn't exist
  if (!document.querySelector(queryBuilderId) || !document.querySelector(queryBuilderId).childElementCount) return null;

  const rules = $(queryBuilderId).queryBuilder("getRules", {
    get_flags: true,
    skip_empty: true,
  });

  // Rule can exist be be empty
  if (!rules.rules.length) return null;
  var query = {};
  query[returnKey] = b64EncodeUnicode(JSON.stringify(rules));
  return query;
}

function getColumnConfigs(userColumnConfigId, listId) {
  const userColumnConfig = JSON.parse(document.getElementById(userColumnConfigId).textContent);

  const list = document.getElementById(listId);

  const currentColumnConfig = Array.from(list.querySelectorAll("label"))
    .map((e) => (e.children[0].checked ? { id: e.children[0].id, label: e.innerText.trim() } : null))
    .filter((x) => x);

  if (JSON.stringify(currentColumnConfig) !== JSON.stringify(userColumnConfig)) {
    // If the current col config is different from the user config originally sent
    // by server - send it back to server to be saved. Otherwise, don't include it.
    let r = {};
    r[userColumnConfigId] = b64EncodeUnicode(JSON.stringify(currentColumnConfig));
    return r;
  }
}

function setUpDraggableList(draggableListId, defaultValues) {
  const draggableList = document.getElementById(draggableListId);
  const resetButton = draggableList.parentElement.getElementsByClassName("reset-button")[0];
  const selectAllButton = draggableList.parentElement.getElementsByClassName("select-all-button")[0];

  //   console.debug(resetButton);
  //   console.debug(selectAllButton);

  resetButton.addEventListener("click", (e) => {
    e.preventDefault();

    const listItems = draggableList.querySelectorAll("li");
    const labels = draggableList.querySelectorAll("label");

    const currentListValues = Array.from(labels)
      .map((e) => (e.children[0].checked ? { id: e.children[0].id, label: e.innerText.trim() } : null))
      .filter((x) => x);

    if (JSON.stringify(currentListValues) !== JSON.stringify(defaultValues)) {
      const firstElem = listItems[0];
      // delete all items
      draggableList.innerHTML = "";

      // recreate default items
      defaultValues.forEach((e, i) => {
        const newLi = firstElem.cloneNode(true);
        newLi.children[0].innerHTML = `
          <input type="checkbox" id="${e.id}" class="mr-4 h-5 w-5 text-teal-500 focus:ring-2 focus:ring-teal-300" checked>${e.label}`;
        draggableList.appendChild(newLi);
      });
    }
  });

  var selectAll = false;

  selectAllButton.addEventListener("click", (e) => {
    e.preventDefault();
    const labels = draggableList.querySelectorAll("label");

    Array.from(labels).forEach((e) => {
      e.children[0].checked = selectAll;
    });
    selectAll = !selectAll;
    selectAllButton.innerText = selectAll ? "Select all" : "Unselect all";
  });

  let draggedItem = null;
  draggableList.addEventListener("dragstart", (e) => {
    draggedItem = e.target;
    draggedItem.classList.remove("shadow-sm");
    draggedItem.classList.add("shadow-lg");
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", null);
  });

  draggableList.addEventListener("dragend", (e) => {
    draggedItem.classList.remove("shadow-lg");
    draggedItem.classList.add("shadow-sm");
    draggedItem = null;
  });

  draggableList.addEventListener("dragover", (e) => {
    e.preventDefault();
    const afterElement = getDragAfterElement(draggableList, e.clientY);
    if (afterElement == null) {
      draggableList.appendChild(draggedItem);
    } else {
      draggableList.insertBefore(draggedItem, afterElement);
    }
  });

  const getDragAfterElement = (container, y) => {
    const draggableElements = [...container.querySelectorAll("li")];

    return draggableElements.reduce(
      (closest, child) => {
        const box = child.getBoundingClientRect();
        const offset = y - box.top - box.height / 2;
        if (offset < 0 && offset > closest.offset) {
          return {
            offset: offset,
            element: child,
          };
        } else {
          return closest;
        }
      },
      {
        offset: Number.NEGATIVE_INFINITY,
      }
    ).element;
  };
}

function setUpColumnConfig() {
  const defaultBuildingCols = JSON.parse(document.getElementById("default_bldg_cols").textContent);
  const defaultSurveyCols = JSON.parse(document.getElementById("default_survey_cols").textContent);
  setUpDraggableList("draggable-list", defaultBuildingCols);
  setUpDraggableList("draggable-list-survey", defaultSurveyCols);
}

function setUpQueryBuilders() {
  const dataset_rules = JSON.parse(document.getElementById("dataset_filter_rules").textContent);
  const survey_rules = JSON.parse(document.getElementById("survey_filter_rules").textContent);
  const dataset_filters = JSON.parse(document.getElementById("qb_dataset_filters").textContent);
  const surveys_filter = JSON.parse(document.getElementById("qb_surveys_filters").textContent);

  console.debug("dataset_rules", dataset_rules);
  console.debug("dataset_filters", dataset_filters);
  console.debug("survey_rules", survey_rules);
  console.debug("surveys_filter", surveys_filter);

  // Fix for Bootstrap Datepicker
  $(datasetQueryBuilderId).on("afterUpdateRuleValue.queryBuilder", function (e, rule) {
    if (rule.filter.plugin === "datepicker") {
      rule.$el.find(".rule-value-container input").datepicker("update");
    }
  });

  if (dataset_rules) {
    $(datasetQueryBuilderId).queryBuilder({
      optgroups: {
        core: {
          en: "Core",
        },
        attributes: {
          en: "Attributes",
        },
      },
      operators: [
        "equal",
        "not_equal",
        "less",
        "less_or_equal",
        "greater",
        "greater_or_equal",
        "between",
        "not_between",
        "begins_with",
        "not_begins_with",
        "contains",
        "not_contains",
        "ends_with",
        "not_ends_with",
        "is_null",
        "is_not_null",
        "in",
        "not_in",
      ],
      rules: dataset_rules,
      filters: dataset_filters,
      valid: true,
      allow_empty: true,
    });
  }
  if (survey_rules) {
    $(surveyQueryBuilderId).queryBuilder({
      optgroups: surveys_filter["optgroups"],
      operators: [
        "equal",
        "not_equal",
        "less",
        "less_or_equal",
        "greater",
        "greater_or_equal",
        "between",
        "not_between",
        "begins_with",
        "not_begins_with",
        "contains",
        "not_contains",
        "ends_with",
        "not_ends_with",
        "is_null",
        "is_not_null",
        "in",
        "not_in",
      ],
      filters: surveys_filter["filters"],
      rules: survey_rules,
      allow_empty: true,
    });
  }
}

function formDataToObject(formData) {
  var object = {};
  formData.forEach((value, key) => {
    // Reflect.has in favor of: object.hasOwnProperty(key)
    if (!Reflect.has(object, key)) {
      object[key] = value;
      return;
    }
    if (!Array.isArray(object[key])) {
      object[key] = [object[key]];
    }
    object[key].push(value);
  });
  return object;
}

function setUpSaveSurveyButton() {
  const button = document.getElementById("save-survey-button");
  if (!button) return;

  button.addEventListener("click", (e) => {
    e.preventDefault();
    const allFormData = {};
    // Gather field data from all the forms
    document.querySelectorAll("form").forEach((form, i) => {
      if (!form.checkValidity()) {
        // Create the temporary button, click and remove it
        // This makes the validation comments appear on screen
        const tmpSubmit = document.createElement("button");
        form.appendChild(tmpSubmit);
        tmpSubmit.click();
        form.removeChild(tmpSubmit);
        return;
      }
      // Get the field type from the associated select
      const fieldType = form.parentNode.querySelector("select").value;
      const fieldNum = i + 1;
      const fieldFormData = new FormData(form);
      const fieldFormJSON = formDataToObject(fieldFormData);
      fieldFormJSON["field_type"] = fieldType;
      fieldFormJSON["field_num"] = fieldNum;
      delete fieldFormJSON["csrfmiddlewaretoken"];
      allFormData[form.id] = fieldFormJSON;
    });

    console.debug("submitted form data", allFormData);

    fetch("", {
      method: "POST",
      mode: "same-origin",
      cache: "no-cache",
      credentials: "same-origin",
      headers: {
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify(allFormData),
    })
      .then((res) => {
        if (res.status != 200) {
          throw new Error("Error creating survey");
        }
        document.getElementById("save-survey-success").classList.remove("hidden");
        document.getElementById("save-survey-success").classList.add("block");

        setTimeout(() => {
          document.getElementById("save-survey-success").classList.remove("block");
          document.getElementById("save-survey-success").classList.add("hidden");
        }, 5000);

        return res.text();
      })
      // The response is the last saved time
      .then((text) => {
        document.getElementById("last-saved-time").innerHTML = text;
      })
      .catch((error) => {
        console.error("Error creating survey", error);
        document.getElementById("save-survey-error").classList.remove("hidden");
        document.getElementById("save-survey-error").classList.add("block");

        setTimeout(() => {
          document.getElementById("save-survey-error").classList.remove("block");
          document.getElementById("save-survey-error").classList.add("hidden");
        }, 5000);
      });
  });
}

function setUpConfirmSurveyActivationButton() {
  const button = document.getElementById("confirm-survey-activation");

  button.addEventListener("click", (e) => {
    e.preventDefault();

    fetch("", {
      method: "POST",
      mode: "same-origin",
      cache: "no-cache",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify({ activate_survey: true }),
      redirect: "follow",
    })
      .then((res) => {
        if (res.status != 200) {
          throw new Error("Error creating survey");
        }
        // Redirect to the next step
        if (res.redirected) window.location.href = res.url;
      })
      .catch((error) => {
        console.error("Error creating survey", error);
        document.getElementById("survey-creation-error").classList.remove("hidden");
        document.getElementById("survey-creation-error").classList.add("block");

        setTimeout(() => {
          document.getElementById("survey-creation-error").classList.remove("block");
          document.getElementById("survey-creation-error").classList.add("hidden");
        }, 5000);
      });
  });
}

function turnOffSpecify(id) {
  console.debug("turning off specify");
  document.getElementById(id).disabled = true;
  document.getElementById(id).required = false;
  document.getElementById(id).value = "";
}

function turnOnSpecify(id) {
  console.debug("turning on specify");
  document.getElementById(id).required = true;
  document.getElementById(id).disabled = false;
}

function setUpSpecifyClickLabel() {
  // Catch the click on the parent
  // https://stackoverflow.com/questions/3100319/event-on-a-disabled-input#answer-32925830
  $("input[id$='_specify_value']")
    .parent()
    .click((e) => {
      let parent = $(e.target);
      console.debug("clicked specify!");

      // Label is not at the same level in DOM, need to tweak the parent
      if (parent.get(0).nodeName === "LABEL") {
        console.debug("clicked label");
        parent = parent.parent();
      }

      const specify_check = parent.find("input[id$='_specify']");
      const specify_input_field = parent.find("input[id$='_specify_value']");
      const element_type = specify_check.attr("type");

      if (element_type === "radio") {
        // If radio, unselect all other radios (since they are mutually exclusive)
        parent
          .parent()
          .find("input")
          .each(() => {
            $(this).prop("checked", false);
          });
        // and mark this radio as checked, with its input field required
        // Note: radios are not unselected when we click on the label again
        // since we need at least one value and that's the default behaviour
        specify_check.prop("checked", true);
        specify_input_field.prop("required", true);
        specify_input_field.prop("disabled", false);
        specify_input_field.focus();
      } else if (element_type === "checkbox") {
        // Checkboxes are not mutually exclusive, so here we don't uncheck the others
        // Even though in our case we do require at least one answer, you can still
        // return to a state of no checkbox selected after selecting one.

        // Prevent the event from bubbling to the multi_checkbox_required.js functions
        e.preventDefault();

        // Handle the event based on the current state of the checkbox
        // If it was checked, we are unselecting the field, so uncheck
        // the checkbox, make the input disabled and delete its value
        if (specify_check.prop("checked")) {
          specify_check.prop("checked", false);
          specify_input_field.attr("required", false);
          specify_input_field.prop("value", "");
          specify_input_field.prop("disabled", true);
        } else {
          // Else we are selecting it, so activate the input field
          specify_check.prop("checked", true);
          specify_input_field.prop("required", true);
          specify_input_field.prop("disabled", false);
          specify_input_field.focus();
        }
        // Manually call this multi_checkbox_required.js to set
        // the other checkboxes required or not as necessary
        markCheckboxesNotRequired(specify_check.attr("name"));
      }
    });
}

function setUpDraggableOptions(fieldForm) {
  const fieldFormId = fieldForm.id;
  // Should only be 1 in each field form - loop over all if this changes
  const draggableList = fieldForm.getElementsByClassName("draggable-list")[0];
  if (!draggableList) return;
  console.debug("Setting up draggable options", draggableList);

  let draggedItem = null;
  draggableList.addEventListener("dragstart", (e) => {
    draggedItem = e.target;
    draggedItem.classList.remove("shadow-sm");
    draggedItem.classList.add("shadow-lg");
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", null);
  });

  draggableList.addEventListener("dragend", (e) => {
    draggedItem.classList.remove("shadow-lg");
    draggedItem.classList.add("shadow-sm");
    draggedItem = null;
    htmx.trigger(`#${fieldFormId}`, "change");
  });

  draggableList.addEventListener("dragover", (e) => {
    e.preventDefault();
    const afterElement = getDragAfterElement(draggableList, e.clientY);
    if (afterElement == null) {
      draggableList.appendChild(draggedItem);
    } else {
      draggableList.insertBefore(draggedItem, afterElement);
    }
  });

  const getDragAfterElement = (container, y) => {
    const draggableElements = [...container.querySelectorAll("li")];

    return draggableElements.reduce(
      (closest, child) => {
        const box = child.getBoundingClientRect();
        const offset = y - box.top - box.height / 2;
        if (offset < 0 && offset > closest.offset) {
          return {
            offset: offset,
            element: child,
          };
        } else {
          return closest;
        }
      },
      {
        offset: Number.NEGATIVE_INFINITY,
      }
    ).element;
  };
}

function setUpAddOptionButton(fieldForm) {
  const template = document.getElementById("new-option-template");
  const draggableList = fieldForm.getElementsByClassName("draggable-list")[0];

  const fieldFormId = fieldForm.id;
  // Should only be 1 in each field form - loop over all if this changes
  const addOptionButton = fieldForm.getElementsByClassName("add-option-button")[0];
  if (!addOptionButton) return;

  addOptionButton.addEventListener("click", (e) => {
    e.preventDefault();
    console.debug("Adding option");

    const optNum = draggableList.querySelectorAll("li").length + 1;
    const newOption = template.content.cloneNode(true);

    const optionInput = newOption.querySelector("input");
    optionInput.value = `Option ${optNum}`;
    optionInput.placeholder = `Option ${optNum}`;

    draggableList.appendChild(newOption);
    htmx.trigger(`#${fieldFormId}`, "change");
  });
}

function setUpDeleteOptionButtons(fieldForm) {
  const fieldFormId = fieldForm.id;
  const draggableList = fieldForm.getElementsByClassName("draggable-list")[0];
  if (!draggableList) return;

  draggableList.querySelectorAll("li").forEach((listItem) => {
    const deleteOptionButton = listItem.querySelector(".delete-option-button");
    if (!deleteOptionButton) return;
    console.debug("setting up delete option button", deleteOptionButton);

    deleteOptionButton.addEventListener("click", (e) => {
      e.preventDefault();
      listItem.remove();
      htmx.trigger(`#${fieldFormId}`, "change");
    });
  });
}

function setUpAddQuestionButton() {
  if (surveyStatus === "ACTIVE") return;
  const id = "add-question";
  const addQuestionButton = document.getElementById(id);
  const template = document.getElementById("new-field-template");
  const holder = document.getElementById("questions-holder");

  addQuestionButton.addEventListener("click", (e) => {
    console.debug("adding question", e.target);

    const qnum = fieldCounter + 1;

    const newFieldForm = template.content.cloneNode(true);
    const firstDiv = newFieldForm.querySelector("div");
    firstDiv.id = `new-field-form-${qnum}`;
    console.debug(newFieldForm);

    const typeSelect = newFieldForm.querySelector("select");
    typeSelect.id = `question-type-select-${qnum}`;
    typeSelect.setAttribute("hx-vals", `js:{field_num: ${qnum}}`);
    typeSelect.setAttribute("hx-target", `#field-form-holder-${qnum}`);

    const form = newFieldForm.querySelector("form");
    form.id = `field-form-${qnum}`;
    form.setAttribute("hx-target", `#field-form-holder-${qnum}`);
    form.setAttribute("hx-vals", `js:{field_num: ${qnum}}`);

    const formHolder = newFieldForm.querySelector(".field-form-holder");
    formHolder.id = `field-form-holder-${qnum}`;

    const renderTarget = newFieldForm.querySelector(".field-render-target");
    renderTarget.id = `field-render-target-${qnum}`;

    const deleteQuestionButton = newFieldForm.querySelector(".delete-question-button");
    deleteQuestionButton.addEventListener("click", (e) => {
      e.preventDefault();
      document.getElementById(firstDiv.id).remove();
    });

    // Enable HTMX functionality on the new node https://htmx.org/api/#process
    htmx.process(newFieldForm);
    // will append the first div, not the template itself
    holder.appendChild(newFieldForm);
    fieldCounter++;
  });
}

/**
 * Iterate through the rendered saved questions and setup interactivity (if not disabled)
 */
function setUpSavedQuestionInteractivity() {
  if (surveyStatus === "ACTIVE") return;
  const fieldFormBlocks = document.querySelectorAll(".new-field-form-and-render-block");
  fieldFormBlocks.forEach((block) => {
    const deleteQuestionButton = block.querySelector(".delete-question-button");
    deleteQuestionButton.addEventListener("click", (e) => {
      e.preventDefault();
      block.remove();
    });

    const fieldForm = block.querySelector(".field-form-holder");
    setUpDraggableOptions(fieldForm);
    setUpAddOptionButton(fieldForm);
    setUpDeleteOptionButtons(fieldForm);
  });
}

function setUpConfirmActivationButton() {
  if (surveyStatus === "ACTIVE") return;
  document.getElementById("confirm-activation-button").addEventListener("click", (e) => {
    e.preventDefault();
    const button = document.getElementById("confirm-survey-creation");
    button.click();
  });
}

const classesTabActive = [
  "text-black",
  "underline",
  "underline-offset-[15px]",
  "decoration-gray-900",
  "decoration-[3px]",
];
const inactiveClasses = ["text-gray-900"];

var fieldCounter = 0;
var surveyStatus;

document.addEventListener("DOMContentLoaded", () => {
  // htmx.logAll();

  // Initialize the counter
  fieldCounter = JSON.parse(document.getElementById("num_fields").textContent);
  surveyStatus = JSON.parse(document.getElementById("survey_status").textContent);

  setUpQueryBuilders();
  setUpColumnConfig();
  setUpModals();
  setUpSaveSurveyButton();
  setUpConfirmSurveyActivationButton();
  setUpCollapsibles();
  setUpTabGroups("tabs-survey", classesTabActive, inactiveClasses);
  setUpAddQuestionButton();
  setUpSpecifyClickLabel();
  setUpSavedQuestionInteractivity();
  setUpConfirmActivationButton();
});

document.addEventListener("htmx:afterRequest", (e) => {
  console.debug("HMTX after request", e);
  setUpColumnConfig();
  setUpModals();
  setUpSpecifyClickLabel();

  setUpDraggableOptions(e.detail.target);
  setUpAddOptionButton(e.detail.target);
  setUpDeleteOptionButtons(e.detail.target);
});
