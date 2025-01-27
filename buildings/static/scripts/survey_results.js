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

function setUpModal() {
  console.debug("Running setup modal");
  const modalBackdrop = document.getElementById("modal-backdrop");
  const columnConfigModal = document.getElementById("col-config-modal");
  const showColumnConfigButton = document.getElementById("show-col-config");
  const columnConfigModalCloseButton = document.getElementById("close-modal");
  // When the user clicks on the button, open the modal
  showColumnConfigButton.addEventListener("click", (e) => {
    e.preventDefault();
    columnConfigModal.classList.remove("hidden");
    modalBackdrop.classList.remove("hidden");
    columnConfigModal.classList.add("block");
    modalBackdrop.classList.add("block");
  });

  // When the user clicks on <span> (x), close the modal
  columnConfigModalCloseButton.addEventListener("click", (e) => {
    e.preventDefault();
    columnConfigModal.classList.add("hidden");
    modalBackdrop.classList.add("hidden");
    columnConfigModal.classList.remove("block");
    modalBackdrop.classList.remove("block");
  });

  // When the user clicks anywhere outside of the modal, close it
  window.addEventListener("click", (e) => {
    if (e.target === columnConfigModal) {
      columnConfigModal.classList.add("hidden");
      modalBackdrop.classList.add("hidden");
      columnConfigModal.classList.remove("block");
      modalBackdrop.classList.remove("block");
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  setUpColumnConfig();
  setUpModal();

  document.addEventListener("htmx:afterRequest", (e) => {
    setUpColumnConfig();
    setUpModal();
  });

  const urlParams = new URLSearchParams(window.location.search);
  const urlDatasetQuery = JSON.parse(b64DecodeUnicode(urlParams.get("dataset_query")));
  const urlSurveyQuery = JSON.parse(b64DecodeUnicode(urlParams.get("survey_query")));
  console.debug(urlDatasetQuery);
  console.debug(urlSurveyQuery);

  const qb_dataset_filters = JSON.parse(document.getElementById("qb_dataset_filters").textContent);
  const qb_surveys_filters = JSON.parse(document.getElementById("qb_surveys_filters").textContent);

  console.log(qb_dataset_filters);
  console.log(qb_surveys_filters);

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

// Table Code
const sortConfig = { colId: null, direction: "asc" };

document.addEventListener("DOMContentLoaded", () => {
  const columns = document.getElementById("columns").textContent;
  console.debug(columns);

  const header = document.getElementById("tableHeader");

  // Drag and drop functionality
  header.addEventListener("dragstart", (e) => {
    let dragTarget = e.target;
    console.debug("drag target:", dragTarget);

    if (e.target.tagName !== "TH") {
      // Since we have children elements inside the th, we need to get the closest th element
      dragTarget = e.target.closest("th");
      console.debug("updated drag target to closest TH:", dragTarget);
    }

    draggedColumnIndex = Array.from(header.children[0].children).indexOf(dragTarget);
    console.debug("dragged column index:", draggedColumnIndex);
  });

  header.addEventListener("dragover", (e) => {
    e.preventDefault();
  });

  header.addEventListener("drop", (e) => {
    e.preventDefault();
    let dropTarget = e.target;
    console.debug("drop target:", dropTarget);
    if (e.target.tagName !== "TH") {
      // Since we have children elements inside the th, we need to get the closest th element
      dropTarget = e.target.closest("th");
      console.debug("updated drop target:", dropTarget);
    }
    const dropTargetIndex = Array.from(header.children[0].children).indexOf(dropTarget);
    console.debug("drop target index:", dropTargetIndex);

    if (draggedColumnIndex !== dropTargetIndex) {
      const rows = document.querySelectorAll("table tr");
      rows.forEach((row) => {
        const cells = Array.from(row.children);
        // If we drag from a lower index to a higher index with insertBefore,
        // the dragged column will be 1 position too far left. I.e. drag col 0 -> 1,
        // col 0 will be inserted before col 1, but it should be inserted after col 1.
        draggedColumnIndex < dropTargetIndex
          ? row.insertBefore(cells[draggedColumnIndex], cells[dropTargetIndex].nextSibling)
          : row.insertBefore(cells[draggedColumnIndex], cells[dropTargetIndex]);
      });
    }

    draggedColumnIndex = null;
  });

  // Attach the sortTable function to each header cell
  Array.from(header.children[0].children).forEach((th, index) => {
    th.addEventListener("click", () => {
      sortColumn(th.id, index);
    });
  });

  let draggedColumnIndex = null;

  // Column toggle functionality
  document.querySelectorAll(".column-toggle").forEach(function (checkbox) {
    checkbox.addEventListener("change", function () {
      const column = this.dataset.columnKey;
      const columnIndex = Array.from(header.children[0].children).indexOf(document.getElementById(column));
      const cells = document.querySelectorAll(`table tr > *:nth-child(${+columnIndex + 1})`);
      cells.forEach((cell) => cell.classList.toggle("hidden", !this.checked));
    });
  });

  // Sorting functionality
  function sortColumn(sortedColumnId, columnIndex) {
    // Sort key will be null the first time we click on a column
    // If equal, we're clicking on the same column a second time so we toggle the direction
    if (sortConfig.colId === sortedColumnId) {
      sortConfig.direction = sortConfig.direction === "asc" ? "desc" : "asc";
    } else {
      sortConfig.colId = sortedColumnId;
      sortConfig.direction = "asc";
    }
    console.debug("applying sortconfig:", sortConfig);
    sortTableData(columnIndex);
    updateSortIcons();
  }

  function sortTableData(columnIndex) {
    const table = document.getElementById("tableBody");
    const rows = Array.from(table.querySelectorAll("tr"));
    const sortedRows = rows.sort((a, b) => {
      const aText = a.querySelector(`td:nth-child(${columnIndex + 1})`).textContent.trim();
      const bText = b.querySelector(`td:nth-child(${columnIndex + 1})`).textContent.trim();
      if (aText < bText) return sortConfig.direction === "asc" ? -1 : 1;
      if (aText > bText) return sortConfig.direction === "asc" ? 1 : -1;
      return 0;
    });
    sortedRows.forEach((row) => table.appendChild(row));
  }

  function updateSortIcons() {
    const headers = document.querySelectorAll("#tableHeader th");
    headers.forEach((header) => {
      const sortIcon = header.querySelector(".sort-icon");
      if (sortConfig.colId === header.id) {
        sortIcon.innerHTML =
          sortConfig.direction === "asc"
            ? '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7"></path></svg>'
            : '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>';
      } else {
        sortIcon.innerHTML = "";
      }
    });
  }
});
