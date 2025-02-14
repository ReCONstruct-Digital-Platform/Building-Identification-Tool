const datasetQueryBuilderId = "#query-builder-dataset";
const surveyQueryBuilderId = "#query-builder-surveys";

function getCurrentQuery() {
  return {
    ...getSelectedDataset(),
    ...getOrderByConfig(),
    ...getColumnConfigs("user_bldg_cols", "draggable-list"),
    ...getColumnConfigs("user_survey_cols", "draggable-list-survey"),
    ...getQueryBuilderQuery(datasetQueryBuilderId, "dataset_query"),
    ...getQueryBuilderQuery(surveyQueryBuilderId, "survey_query"),
  };
}

function getSelectedDataset() {
  return {
    ds: document.getElementById("source-dataset-select").value,
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
  if (!document.querySelector(queryBuilderId).childElementCount) return null;

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

function fillInQueryBuildersFromUrlParams() {
  const urlParams = new URLSearchParams(window.location.search);
  const urlDatasetQuery = JSON.parse(b64DecodeUnicode(urlParams.get("dataset_query")));
  const urlSurveyQuery = JSON.parse(b64DecodeUnicode(urlParams.get("survey_query")));
  urlDatasetQuery && document.getElementById("add-dataset-filter").dispatchEvent(new Event("click"));
  if (urlSurveyQuery) {
    console.debug("got survey query from URL");
    document.getElementById("add-surveys-filter").dispatchEvent(new Event("click"));
  }
}

function setUpQueryBuilders() {
  const qb_dataset_filters = JSON.parse(document.getElementById("qb_dataset_filters").textContent);
  const qb_surveys_filters = JSON.parse(document.getElementById("qb_surveys_filters").textContent);

  console.debug(qb_dataset_filters);
  console.debug(qb_surveys_filters);

  // Fully reset the QBs
  if (document.querySelector(datasetQueryBuilderId).childElementCount > 0) {
    document.querySelector(datasetQueryBuilderId).innerHTML = "";
    $(datasetQueryBuilderId).queryBuilder("destroy");
  }

  if (document.querySelector(surveyQueryBuilderId).childElementCount > 0) {
    document.querySelector(surveyQueryBuilderId).innerHTML = "";
    $(surveyQueryBuilderId).queryBuilder("destroy");
  }

  // Fix for Bootstrap Datepicker
  $(datasetQueryBuilderId).on("afterUpdateRuleValue.queryBuilder", function (e, rule) {
    if (rule.filter.plugin === "datepicker") {
      rule.$el.find(".rule-value-container input").datepicker("update");
    }
  });

  document.getElementById("add-dataset-filter").addEventListener("click", (e) => {
    e.preventDefault();
    const urlParams = new URLSearchParams(window.location.search);
    const urlDatasetQuery = JSON.parse(b64DecodeUnicode(urlParams.get("dataset_query")));
    if (document.querySelector(datasetQueryBuilderId).childElementCount > 0) {
      $(datasetQueryBuilderId).queryBuilder("destroy");
      e.target.textContent = "Add dataset filter";
      e.target.classList.remove("bg-red-600", "hover:bg-red-500", "focus-visible:outline-red-600");
      e.target.classList.add("bg-blue-600", "hover:bg-blue-500", "focus-visible:outline-blue-700");
      return;
    } else {
      e.target.textContent = "Remove dataset filter";
      e.target.classList.remove("bg-blue-600", "hover:bg-blue-500", "focus-visible:outline-blue-700");
      e.target.classList.add("bg-red-600", "hover:bg-red-500", "focus-visible:outline-red-600");

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
        filters: qb_dataset_filters,
        rules: urlDatasetQuery ?? {
          condition: "AND",
          rules: [
            {
              id: "muni",
              field: "muni",
              type: "text",
              input: "text",
              operator: "contains",
              value: "Mont",
            },
          ],
        },
        valid: true,
        allow_empty: true,
      });
    }
  });

  document.getElementById("add-surveys-filter").addEventListener("click", (e) => {
    e.preventDefault();
    const urlParams = new URLSearchParams(window.location.search);
    const urlSurveyQuery = JSON.parse(b64DecodeUnicode(urlParams.get("survey_query")));

    if (document.querySelector(surveyQueryBuilderId).childElementCount > 0) {
      $(surveyQueryBuilderId).queryBuilder("destroy");
      e.target.textContent = "Add survey filter";
      e.target.classList.remove("bg-red-600", "hover:bg-red-500", "focus-visible:outline-red-600");
      e.target.classList.add("bg-blue-600", "hover:bg-blue-500", "focus-visible:outline-blue-700");
      return;
    } else {
      e.target.textContent = "Remove survey filter";
      e.target.classList.remove("bg-blue-600", "hover:bg-blue-500", "focus-visible:outline-blue-700");
      e.target.classList.add("bg-red-600", "hover:bg-red-500", "focus-visible:outline-red-600");
      $(surveyQueryBuilderId).queryBuilder({
        optgroups: qb_surveys_filters["optgroups"],
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
        filters: qb_surveys_filters["filters"],
        rules: urlSurveyQuery,
        allow_empty: true,
      });
    }
  });
}

function setUpNextStepButton() {
  const button = document.getElementById("next-step-button");
  const modalOpenButton = document.getElementById("show-confirm-creation");

  button.addEventListener("click", (e) => {
    e.preventDefault();
    const form = document.getElementById("survey-creation-form");
    if (!form.checkValidity()) {
      // Create the temporary button, click and remove it
      // This makes the validation comments appear on screen
      const tmpSubmit = document.createElement("button");
      form.appendChild(tmpSubmit);
      tmpSubmit.click();
      form.removeChild(tmpSubmit);
      return;
    }
    // Else open modal by sending a click to the hidden modal open button
    modalOpenButton.dispatchEvent(new Event("click"));
  });
}

function setUpConfirmButton() {
  const button = document.getElementById("confirm-survey-creation");

  button.addEventListener("click", (e) => {
    e.preventDefault();

    const surveyName = document.getElementById("survey-name").value;
    console.debug(surveyName);

    const body = JSON.stringify({
      survey_name: surveyName,
      ...getCurrentQuery(),
    });

    console.debug(body);

    fetch("", {
      method: "POST",
      mode: "same-origin",
      cache: "no-cache",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: body,
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

const classesTabActive = [
  "text-black",
  "underline",
  "underline-offset-[15px]",
  "decoration-gray-900",
  "decoration-[3px]",
];
const inactiveClasses = ["text-gray-900"];

document.addEventListener("DOMContentLoaded", () => {
  setUpQueryBuilders();
  fillInQueryBuildersFromUrlParams();
  setUpColumnConfig();
  setUpModals();
  setUpNextStepButton();
  setUpConfirmButton();
  setUpCollapsibles();
  setUpTabGroups("tabs-survey", classesTabActive, inactiveClasses);
});

document.addEventListener("htmx:afterRequest", (e) => {
  console.debug("HMTX after request", e);
  setUpColumnConfig();
  setUpModals();
  setUpSpecifyClickLabel();
});
