const datasetQueryBuilderId = "#query-builder-dataset";
const surveyQueryBuilderId = "#query-builder-surveys";

function getDatasetFilterRules() {
  return document.querySelector(datasetQueryBuilderId).childElementCount
    ? $(datasetQueryBuilderId).queryBuilder("getRules", {
        get_flags: true,
        skip_empty: true,
      })
    : null;
}
function getSurveysFilterRules() {
  return document.querySelector(surveyQueryBuilderId).childElementCount
    ? $(surveyQueryBuilderId).queryBuilder("getRules", {
        get_flags: true,
        skip_empty: true,
      })
    : null;
}

// Filters code
document.addEventListener("DOMContentLoaded", () => {
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
        rules: {
          condition: "AND",
          rules: [
            {
              id: "const_year",
              field: "const_year",
              type: "date",
              input: "text",
              operator: "between",
              value: [1950, 2000],
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
        rules: {
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

  document
    .getElementById("submitQueryButton")
    // .addEventListener("htmx:configRequest", (e) => {
    //   console.log(e);
    // })
    .addEventListener("click", (e) => {
      e.preventDefault();

      const datasetRules = document.querySelector(datasetQueryBuilderId).childElementCount
        ? $(datasetQueryBuilderId).queryBuilder("getRules", {
            get_flags: true,
            skip_empty: true,
          })
        : null;

      const surveyRules = document.querySelector(surveyQueryBuilderId).childElementCount
        ? $(surveyQueryBuilderId).queryBuilder("getRules", {
            get_flags: true,
            skip_empty: true,
          })
        : null;

      if (datasetRules === null && surveyRules === null) return;

      console.log(datasetRules);
      console.log(surveyRules);

      return;

      htmx
        .ajax("POST", "", {
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken"), // So django accepts the request
          },
          values: { dataset_query: datasetRules, surveys_query: surveyRules },
        })
        .then(() => {
          // this code will be executed after the 'htmx:afterOnLoad' event,
          // and before the 'htmx:xhr:loadend' event
          console.log("Content inserted successfully!");
        });

      fetch("", {
        method: "POST",
        mode: "same-origin",
        cache: "no-cache",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"), // So django accepts the request
        },
        body: JSON.stringify({
          dataset_query: datasetRules,
          surveys_query: surveyRules,
        }),
      }).then((resp) => {
        if (resp.status === 200) {
          console.debug("Query uploaded");
        } else {
          console.debug(`ERROR running query ${resp}`);
        }
      });
    });
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
