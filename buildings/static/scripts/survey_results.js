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
    // scenario 1: user never changed defaults.
    let r = {};
    r[userColumnConfigId] = b64EncodeUnicode(JSON.stringify(currentColumnConfig));
    return r;
  }
}

function setUpDraggableList(draggableListId, defaultValues) {
  const draggableList = document.getElementById(draggableListId);
  const resetButton = draggableList.parentElement.getElementsByClassName("reset-button")[0];
  const selectAllButton = draggableList.parentElement.getElementsByClassName("select-all-button")[0];

  console.debug(resetButton);
  console.debug(selectAllButton);

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


document.addEventListener("DOMContentLoaded", () => {
  setUpColumnConfig();
  setUpModals();

  document.addEventListener("htmx:afterRequest", (e) => {
    setUpColumnConfig();
    setUpModals();
  });

  const urlParams = new URLSearchParams(window.location.search);
  const urlDatasetQuery = JSON.parse(b64DecodeUnicode(urlParams.get("dataset_query")));
  const urlSurveyQuery = JSON.parse(b64DecodeUnicode(urlParams.get("survey_query")));
  console.debug(urlDatasetQuery);
  console.debug(urlSurveyQuery);

  const qb_dataset_filters = JSON.parse(document.getElementById("qb_dataset_filters").textContent);
  const qb_surveys_filters = JSON.parse(document.getElementById("qb_surveys_filters").textContent);

  console.debug(qb_dataset_filters);
  console.debug(qb_surveys_filters);

  // Fix for Bootstrap Datepicker
  $(datasetQueryBuilderId).on("afterUpdateRuleValue.queryBuilder", function (e, rule) {
    if (rule.filter.plugin === "datepicker") {
      rule.$el.find(".rule-value-container input").datepicker("update");
    }
  });

  document.getElementById("add-dataset-filter").addEventListener("click", (e) => {
    e.preventDefault();

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

    if (document.querySelector(surveyQueryBuilderId).childElementCount > 0) {
      $(surveyQueryBuilderId).queryBuilder("destroy");
      e.target.textContent = "Add surveys filter";
      e.target.classList.remove("bg-red-600", "hover:bg-red-500", "focus-visible:outline-red-600");
      e.target.classList.add("bg-blue-600", "hover:bg-blue-500", "focus-visible:outline-blue-700");
      return;
    } else {
      e.target.textContent = "Remove surveys filter";
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
        // filters: survey_filters_fake,
        filters: qb_surveys_filters["filters"],
        rules: urlSurveyQuery ?? {
          condition: "AND",
          rules: [
            {
              id: "response_data__exterior_cladding",
              field: "response_data__exterior_cladding",
              input: "text",
              type: "checkbox",
              operator: "in",
              value: ["brick_masonry", "wood"],
            },
          ],
        },
        allow_empty: true,
      });
    }
  });

  urlDatasetQuery && document.getElementById("add-dataset-filter").dispatchEvent(new Event("click"));
  urlSurveyQuery && document.getElementById("add-surveys-filter").dispatchEvent(new Event("click"));
});


