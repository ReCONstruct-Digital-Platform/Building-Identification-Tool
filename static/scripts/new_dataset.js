const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const MAX_EXCEL_SIZE_READABLE = "10MB";
const EXCEL_FILE_TYPES = [
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "application/vnd.ms-excel",
];
const CSV_FILE_TYPE = "text/csv";

// Data types for unmapped columns
const COLUMN_DATA_TYPES = [
  { value: "string", label: "String" },
  { value: "number", label: "Number" },
  { value: "boolean", label: "Boolean" },
  { value: "date", label: "Date" },
];

// Form validation state
const formState = {
  hasValidFile: false,
  hasRequiredColumns: false,
};

// Function to add error styling to an input
function markInputError(input, errorElement, message) {
  input.classList.add("border-red-500", "focus:border-red-500", "focus:ring-red-500");
  errorElement.textContent = message;
}

// Function to remove error styling from an input
function clearInputError(input, errorElement) {
  input.classList.remove("border-red-500", "focus:border-red-500", "focus:ring-red-500");
  errorElement.textContent = "";
}

// Function to update available options in all dropdowns
function updateAvailableOptions(changedSelect, otherSelects) {
  // Collect all currently selected values from all dropdowns
  const selectedValues = new Set();

  // Add the value from the changed dropdown if it's not empty
  if (changedSelect.value) {
    selectedValues.add(changedSelect.value);
  }

  // Add values from other dropdowns if they're not empty
  otherSelects.forEach((select) => {
    if (select.value) {
      selectedValues.add(select.value);
    }
  });

  // Now update each of the other dropdowns
  otherSelects.forEach((select) => {
    // Remember the current value
    const currentValue = select.value;

    // For each option in this dropdown
    Array.from(select.options).forEach((option) => {
      // Skip the empty option
      if (!option.value) return;

      // If this option is in the selected values set and it's not the current value of this dropdown
      if (selectedValues.has(option.value) && option.value !== currentValue) {
        option.disabled = true;
      } else {
        option.disabled = false;
      }
    });
  });
}

// Function to count rows in a CSV file
function countCsvRows(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = function (e) {
      const content = e.target.result;
      // Split by newline and count non-empty rows (minus header)
      const rows = content.split("\n").filter((row) => row.trim() !== "");

      // Create a hidden input to store the row count
      const rowCountInput = document.getElementById("csv_row_count") || document.createElement("input");
      rowCountInput.type = "hidden";
      rowCountInput.id = "csv_row_count";
      rowCountInput.name = "csv_row_count";
      rowCountInput.value = rows.length > 0 ? rows.length - 1 : 0; // Subtract 1 for header

      // Add to the form if it doesn't already exist
      const form = document.getElementById("new-dataset-form");
      if (!document.getElementById("csv_row_count")) {
        form.appendChild(rowCountInput);
      }

      resolve({
        totalRows: rows.length,
        dataRows: rows.length > 0 ? rows.length - 1 : 0, // Excluding header row
        isEmpty: rows.length <= 1, // Empty if only header or less
      });
    };

    reader.onerror = function () {
      reject(new Error("Error reading file"));
    };

    reader.readAsText(file);
  });
}

// Function to get all mapped column values
function getAllMappedColumns() {
  const mappedColumns = new Set();

  // Required fields
  const externalIdColumnSelect = document.querySelector('select[name="external_id"]');
  const addressColumnSelect = document.querySelector('select[name="address_column"]');
  const zipColumnSelect = document.querySelector('select[name="zip_column"]');
  const stateColumnSelect = document.querySelector('select[name="state_column"]');

  // Add values if they exist
  if (externalIdColumnSelect && externalIdColumnSelect.value) mappedColumns.add(externalIdColumnSelect.value);
  if (addressColumnSelect && addressColumnSelect.value) mappedColumns.add(addressColumnSelect.value);
  if (zipColumnSelect && zipColumnSelect.value) mappedColumns.add(zipColumnSelect.value);
  if (stateColumnSelect && stateColumnSelect.value) mappedColumns.add(stateColumnSelect.value);

  // Coordinate fields
  const latColumnSelect = document.querySelector('select[name="lat_column"]');
  const lngColumnSelect = document.querySelector('select[name="lng_column"]');

  if (document.getElementById("coordinates_selection").classList.contains("hidden") === false) {
    if (latColumnSelect && latColumnSelect.value) mappedColumns.add(latColumnSelect.value);
    if (lngColumnSelect && lngColumnSelect.value) mappedColumns.add(lngColumnSelect.value);
  }

  // Building details fields
  // Street components
  const streetNameColumnSelect = document.querySelector('select[name="street_name_column"]');
  const streetNumColumnSelect = document.querySelector('select[name="street_num_column"]');

  // Location fields
  const muniColumnSelect = document.querySelector('select[name="muni_column"]');
  const submuniColumnSelect = document.querySelector('select[name="submuni_column"]');

  // Building characteristics
  const constYearColumnSelect = document.querySelector('select[name="const_year_column"]');
  const numFloorsColumnSelect = document.querySelector('select[name="num_floors_column"]');
  const floorAreaColumnSelect = document.querySelector('select[name="floor_area_column"]');

  if (streetNameColumnSelect && streetNameColumnSelect.value) mappedColumns.add(streetNameColumnSelect.value);
  if (streetNumColumnSelect && streetNumColumnSelect.value) mappedColumns.add(streetNumColumnSelect.value);
  if (muniColumnSelect && muniColumnSelect.value) mappedColumns.add(muniColumnSelect.value);
  if (submuniColumnSelect && submuniColumnSelect.value) mappedColumns.add(submuniColumnSelect.value);
  if (constYearColumnSelect && constYearColumnSelect.value) mappedColumns.add(constYearColumnSelect.value);
  if (numFloorsColumnSelect && numFloorsColumnSelect.value) mappedColumns.add(numFloorsColumnSelect.value);
  if (floorAreaColumnSelect && floorAreaColumnSelect.value) mappedColumns.add(floorAreaColumnSelect.value);

  return mappedColumns;
}

// Function to update unmapped columns section
function updateUnmappedColumnsSection(allColumns) {
  const mappedColumns = getAllMappedColumns();
  const unmappedColumns = allColumns.filter((column) => !mappedColumns.has(column));
  const unmappedColumnsSection = document.getElementById("unmapped_columns_section");
  const unmappedColumnsList = document.getElementById("unmapped_columns_list");

  // Clear previous content
  unmappedColumnsList.innerHTML = "";

  // If there are unmapped columns, show the section and add the columns
  if (unmappedColumns.length > 0) {
    unmappedColumnsSection.classList.remove("hidden");

    // Create a hidden input to store the unmapped columns data
    let unmappedColumnsInput = document.querySelector('input[name="unmapped_columns"]');
    if (!unmappedColumnsInput) {
      unmappedColumnsInput = document.createElement("input");
      unmappedColumnsInput.type = "hidden";
      unmappedColumnsInput.name = "unmapped_columns";
      document.getElementById("new-dataset-form").appendChild(unmappedColumnsInput);
    }

    // Create UI for each unmapped column
    unmappedColumns.forEach((column) => {
      const columnDiv = document.createElement("div");
      columnDiv.className = "flex items-center space-x-4";

      // Column name
      const columnNameDiv = document.createElement("div");
      columnNameDiv.className = "w-1/3";
      columnNameDiv.textContent = column;

      // Data type selector
      const dataTypeDiv = document.createElement("div");
      dataTypeDiv.className = "w-2/3";

      const dataTypeSelect = document.createElement("select");
      dataTypeSelect.className =
        "mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md";
      dataTypeSelect.dataset.column = column;
      dataTypeSelect.addEventListener("change", updateUnmappedColumnsData);

      // Add default option
      const defaultOption = document.createElement("option");
      defaultOption.value = "";
      defaultOption.textContent = "-- Select Data Type --";
      dataTypeSelect.appendChild(defaultOption);

      // Add data type options
      COLUMN_DATA_TYPES.forEach((type) => {
        const option = document.createElement("option");
        option.value = type.value;
        option.textContent = type.label;
        dataTypeSelect.appendChild(option);
      });

      // Default to string type
      dataTypeSelect.value = "string";

      dataTypeDiv.appendChild(dataTypeSelect);

      // Add to column div
      columnDiv.appendChild(columnNameDiv);
      columnDiv.appendChild(dataTypeDiv);

      // Add to list
      unmappedColumnsList.appendChild(columnDiv);
    });

    // Initialize unmapped columns data
    updateUnmappedColumnsData();
  } else {
    unmappedColumnsSection.classList.add("hidden");
  }
}

// Function to update the hidden unmapped columns data input
function updateUnmappedColumnsData() {
  const unmappedColumnsData = {};
  const dataTypeSelects = document.querySelectorAll("#unmapped_columns_list select");

  dataTypeSelects.forEach((select) => {
    const column = select.dataset.column;
    const dataType = select.value;
    if (column && dataType) {
      unmappedColumnsData[column] = dataType;
    }
  });

  // Update the hidden input
  const unmappedColumnsInput = document.querySelector('input[name="unmapped_columns"]');
  if (unmappedColumnsInput) {
    unmappedColumnsInput.value = JSON.stringify(unmappedColumnsData);
  }
}

// Function to update all dropdown constraints
function updateAllDropdownConstraints() {
  const externalIdColumnSelect = document.querySelector('select[name="external_id"]');
  const addressColumnSelect = document.querySelector('select[name="address_column"]');
  const zipColumnSelect = document.querySelector('select[name="zip_column"]');
  const stateColumnSelect = document.querySelector('select[name="state_column"]');
  const latColumnSelect = document.querySelector('select[name="lat_column"]');
  const lngColumnSelect = document.querySelector('select[name="lng_column"]');

  // Street components
  const streetNameColumnSelect = document.querySelector('select[name="street_name_column"]');
  const streetNumColumnSelect = document.querySelector('select[name="street_num_column"]');

  // Location fields
  const muniColumnSelect = document.querySelector('select[name="muni_column"]');
  const submuniColumnSelect = document.querySelector('select[name="submuni_column"]');

  // Building characteristics
  const constYearColumnSelect = document.querySelector('select[name="const_year_column"]');
  const numFloorsColumnSelect = document.querySelector('select[name="num_floors_column"]');
  const floorAreaColumnSelect = document.querySelector('select[name="floor_area_column"]');

  // Get all column select elements
  const allSelects = [
    externalIdColumnSelect,
    addressColumnSelect,
    stateColumnSelect,
    zipColumnSelect,
    streetNameColumnSelect,
    streetNumColumnSelect,
    muniColumnSelect,
    submuniColumnSelect,
    constYearColumnSelect,
    numFloorsColumnSelect,
    floorAreaColumnSelect,
  ];

  // Add coordinate selects if they're visible
  if (document.getElementById("coordinates_selection").classList.contains("hidden") === false) {
    allSelects.push(latColumnSelect, lngColumnSelect);
  }

  // Update constraints for each select
  allSelects.forEach((select) => {
    if (select) {
      // Make sure the select exists
      const otherSelects = allSelects.filter((s) => s !== select);
      updateAvailableOptions(select, otherSelects);
    }
  });

  // Get all columns from the first select (they all have the same options)
  const allColumns = [];
  if (addressColumnSelect) {
    Array.from(addressColumnSelect.options).forEach((option) => {
      if (option.value) {
        allColumns.push(option.value);
      }
    });
  }

  // Update unmapped columns section
  updateUnmappedColumnsSection(allColumns);
}

function setUpDatasetUploadForm() {
  const csvFileInput = document.querySelector('input[name="csv_file"]');
  const csvFileInputErrors = document.getElementById("csv_file_errors");
  const columnSelection = document.getElementById("column-selection");
  const externalIdColumnSelect = document.querySelector('select[name="external_id"]');
  const addressColumnSelect = document.querySelector('select[name="address_column"]');
  const zipColumnSelect = document.querySelector('select[name="zip_column"]');
  const stateColumnSelect = document.querySelector('select[name="state_column"]');
  const latColumnSelect = document.querySelector('select[name="lat_column"]');
  const lngColumnSelect = document.querySelector('select[name="lng_column"]');
  const addressColumnError = document.getElementById("address_column_errors");
  const stateColumnError = document.getElementById("state_column_errors");
  const zipColumnError = document.getElementById("zip_column_errors");
  const latColumnError = document.getElementById("lat_column_errors");
  const lngColumnError = document.getElementById("lng_column_errors");
  const submitButton = document.querySelector('button[type="submit"]');

  // Street components and their errors
  const streetNameColumnSelect = document.querySelector('select[name="street_name_column"]');
  const streetNumColumnSelect = document.querySelector('select[name="street_num_column"]');
  const streetNameColumnError = document.getElementById("street_name_column_errors");
  const streetNumColumnError = document.getElementById("street_num_column_errors");

  // Location fields and their errors
  const muniColumnSelect = document.querySelector('select[name="muni_column"]');
  const submuniColumnSelect = document.querySelector('select[name="submuni_column"]');
  const muniColumnError = document.getElementById("muni_column_errors");
  const submuniColumnError = document.getElementById("submuni_column_errors");

  // Building characteristics and their errors
  const constYearColumnSelect = document.querySelector('select[name="const_year_column"]');
  const numFloorsColumnSelect = document.querySelector('select[name="num_floors_column"]');
  const floorAreaColumnSelect = document.querySelector('select[name="floor_area_column"]');
  const constYearColumnError = document.getElementById("const_year_column_errors");
  const numFloorsColumnError = document.getElementById("num_floors_column_errors");
  const floorAreaColumnError = document.getElementById("floor_area_column_errors");

  const coordinatesSelection = document.getElementById("coordinates_selection");
  const hasCoordinatesRadios = document.querySelectorAll('input[name="has_coordinates"]');
  const buildingDetailsSelection = document.getElementById("building_details_selection");
  const hasBuildingDetailsRadios = document.querySelectorAll('input[name="has_building_details"]');

  const newDatasetForm = document.getElementById("new-dataset-form");

  // Disable submit button initially
  submitButton.disabled = true;

  // Function to update submit button state
  function updateSubmitButtonState() {
    submitButton.disabled = !(formState.hasValidFile && formState.hasRequiredColumns);
  }

  // Function to validate CSV column selections
  function validateCsvColumns() {
    let isValid = true;

    // Clear all previous errors
    clearInputError(addressColumnSelect, addressColumnError);
    clearInputError(stateColumnSelect, stateColumnError);
    clearInputError(zipColumnSelect, zipColumnError);

    if (latColumnSelect && lngColumnSelect) {
      clearInputError(latColumnSelect, latColumnError);
      clearInputError(lngColumnSelect, lngColumnError);
    }

    // Check if a file has been uploaded
    if (!formState.hasValidFile) {
      isValid = false;
      csvFileInputErrors.textContent = "Please upload a valid CSV file";
    }

    // Clear building details errors
    if (streetNameColumnSelect && streetNumColumnSelect) {
      clearInputError(streetNameColumnSelect, streetNameColumnError);
      clearInputError(streetNumColumnSelect, streetNumColumnError);
      clearInputError(muniColumnSelect, muniColumnError);
      clearInputError(submuniColumnSelect, submuniColumnError);
      clearInputError(constYearColumnSelect, constYearColumnError);
      clearInputError(numFloorsColumnSelect, numFloorsColumnError);
      clearInputError(floorAreaColumnSelect, floorAreaColumnError);
    }

    // Validate address column (required)
    if (!addressColumnSelect.value) {
      isValid = false;
      markInputError(addressColumnSelect, addressColumnError, "Address column is required");
    }

    // Province column is required
    if (!stateColumnSelect.value) {
      isValid = false;
      markInputError(stateColumnSelect, stateColumnError, "Province column is required");
    }

    // Postal code column is recommended but not required
    // We'll just show a warning in the form validation

    // Check if coordinates are enabled and validate those fields
    const hasCoordinatesValue = document.querySelector('input[name="has_coordinates"]:checked')?.value;
    if (hasCoordinatesValue === "yes") {
      if (!latColumnSelect.value) {
        isValid = false;
        markInputError(latColumnSelect, latColumnError, "Latitude column is required");
      }

      if (!lngColumnSelect.value) {
        isValid = false;
        markInputError(lngColumnSelect, lngColumnError, "Longitude column is required");
      }
    }

    // TODO: not recommended to check all possible combinations
    // Check for duplicate column selections
    if (
      addressColumnSelect.value &&
      (addressColumnSelect.value === stateColumnSelect.value || addressColumnSelect.value === zipColumnSelect.value)
    ) {
      isValid = false;
      markInputError(addressColumnSelect, addressColumnError, "Each column must be unique");
    }

    if (stateColumnSelect.value && stateColumnSelect.value === zipColumnSelect.value) {
      isValid = false;
      markInputError(stateColumnSelect, stateColumnError, "Each column must be unique");
      markInputError(zipColumnSelect, zipColumnError, "Each column must be unique");
    }

    // All building details fields are optional, so no validation needed here

    // Validate unmapped columns data types
    const dataTypeSelects = document.querySelectorAll("#unmapped_columns_list select");
    dataTypeSelects.forEach((select) => {
      if (!select.value) {
        isValid = false;
        select.classList.add("border-red-500", "focus:border-red-500", "focus:ring-red-500");
        const errorElement = document.createElement("p");
        errorElement.className = "mt-2 text-sm text-red-600";
        errorElement.textContent = "Data type is required";
        select.parentNode.appendChild(errorElement);
      }
    });

    // Update form state
    formState.hasRequiredColumns = isValid;
    updateSubmitButtonState();

    return isValid;
  }

  // Handle CSV file upload and column detection
  csvFileInput.addEventListener("change", function (e) {
    // Reset form state when file changes
    formState.hasValidFile = false;
    formState.hasRequiredColumns = false;
    updateSubmitButtonState();

    // Hide column selection when file changes
    columnSelection.classList.add("hidden");

    if (this.files && this.files[0]) {
      const file = this.files[0];

      console.log(file);
      console.log(file.size);

      //Validate file size
      if (file.size > MAX_FILE_SIZE) {
        csvFileInputErrors.textContent = `File size exceeds ${MAX_EXCEL_SIZE_READABLE}. Please upload a smaller file or contact us for a custom request.`;
        return;
      }

      // Validate file type
      if (EXCEL_FILE_TYPES.includes(file.type)) {
        csvFileInputErrors.textContent = "We don't support Excel files. Please export it as a CSV file and re-upload.";
        return;
      }

      if (file.type !== CSV_FILE_TYPE) {
        csvFileInputErrors.textContent = "Invalid file type. Please upload a CSV file.";
        return;
      }

      // Count rows in the CSV file and validate
      countCsvRows(file)
        .then((result) => {
          if (result.isEmpty) {
            csvFileInputErrors.textContent =
              "The CSV file is empty or contains only headers. Please upload a file with at least one data row.";
            return;
          }

          console.log(`CSV file has ${result.dataRows} data rows (${result.totalRows} total rows)`);
          csvFileInputErrors.textContent = ""; // Clear any previous errors

          // Set valid file state
          formState.hasValidFile = true;
          updateSubmitButtonState();

          // Continue with parsing CSV header for column selection
          const reader = new FileReader();
          reader.onerror = function (e) {
            csvFileInputErrors.textContent = "Error reading file. Please try again.";
          };
          reader.onload = function (e) {
            const content = e.target.result;
            const firstLine = content.split("\n")[0];
            const columns = firstLine.split(",").map((col) => col.trim());

            // Reset building details dropdowns
            const buildingDetailSelects = [
              { select: addressColumnSelect, label: "Select Address Column" },
              { select: externalIdColumnSelect, label: "Select External ID Column" },
              { select: zipColumnSelect, label: "Select Postal Code Column" },
              { select: stateColumnSelect, label: "Select Province Column" },
              { select: latColumnSelect, label: "Select Latitude Column" },
              { select: lngColumnSelect, label: "Select Longitude Column" },
              { select: streetNameColumnSelect, label: "Select Street Name Column" },
              { select: streetNumColumnSelect, label: "Select Street Number Column" },
              { select: muniColumnSelect, label: "Select Municipality Column" },
              { select: submuniColumnSelect, label: "Select Sub-Municipality Column" },
              { select: constYearColumnSelect, label: "Select Construction Year Column" },
              { select: numFloorsColumnSelect, label: "Select Number of Floors Column" },
              { select: floorAreaColumnSelect, label: "Select Floor Area Column" },
            ];

            buildingDetailSelects.forEach((item) => {
              if (item.select) {
                item.select.innerHTML = `<option value="">${item.label}</option>`;
              }
            });

            // Add column options to all selects
            columns.forEach((column) => {
              // Add options to building details dropdowns
              const buildingDetailSelects = [
                addressColumnSelect,
                externalIdColumnSelect,
                zipColumnSelect,
                stateColumnSelect,
                latColumnSelect,
                lngColumnSelect,
                streetNameColumnSelect,
                streetNumColumnSelect,
                muniColumnSelect,
                submuniColumnSelect,
                constYearColumnSelect,
                numFloorsColumnSelect,
                floorAreaColumnSelect,
              ];

              buildingDetailSelects.forEach((select) => {
                if (select) {
                  const option = document.createElement("option");
                  option.value = column;
                  option.textContent = column;
                  select.appendChild(option);
                }
              });
            });

            // Try to auto-select appropriate columns based on common column names
            let addressSelected = null;
            let stateSelected = null;
            let zipSelected = null;

            columns.forEach((column) => {
              const lowerColumn = column.toLowerCase();

              // Auto-select address column
              if ((lowerColumn.includes("address") || lowerColumn.includes("street")) && !addressSelected) {
                addressSelected = column;
              }

              // Auto-select province column
              if (
                (lowerColumn === "state" ||
                  lowerColumn.includes("state") ||
                  lowerColumn === "province" ||
                  lowerColumn.includes("province")) &&
                !stateSelected
              ) {
                stateSelected = column;
              }

              // Auto-select postal code column (look for common patterns in postal code columns)
              if (
                (lowerColumn === "zip" ||
                  lowerColumn.includes("zip") ||
                  lowerColumn === "postal" ||
                  lowerColumn.includes("postal") ||
                  lowerColumn.includes("postal code")) &&
                !zipSelected
              ) {
                zipSelected = column;
              }

              // Auto-select lat/lng columns if they exist
              if (
                (lowerColumn === "lat" || lowerColumn.includes("latitude") || lowerColumn === "y") &&
                document.getElementById("has_coords_yes")
              ) {
                document.getElementById("has_coords_yes").checked = true;
                coordinatesSelection.classList.remove("hidden");
                latColumnSelect.value = column;
              }

              if (
                (lowerColumn === "lng" ||
                  lowerColumn === "long" ||
                  lowerColumn.includes("longitude") ||
                  lowerColumn === "x") &&
                document.getElementById("has_coords_yes")
              ) {
                document.getElementById("has_coords_yes").checked = true;
                coordinatesSelection.classList.remove("hidden");
                lngColumnSelect.value = column;
              }

              // Check for construction year
              if (
                lowerColumn.includes("year") ||
                lowerColumn.includes("built") ||
                lowerColumn.includes("construction")
              ) {
                buildingDetailsSelection.classList.remove("hidden");
                constYearColumnSelect.value = column;
              }

              // Check for number of floors
              if (lowerColumn.includes("floor") || lowerColumn.includes("storey") || lowerColumn.includes("story")) {
                buildingDetailsSelection.classList.remove("hidden");
                numFloorsColumnSelect.value = column;
              }

              // Check for floor area
              if (
                lowerColumn.includes("area") ||
                lowerColumn.includes("size") ||
                lowerColumn.includes("sqft") ||
                lowerColumn.includes("sq ft") ||
                lowerColumn.includes("square")
              ) {
                buildingDetailsSelection.classList.remove("hidden");
                floorAreaColumnSelect.value = column;
              }

              // Check for street name
              if (lowerColumn.includes("street") && lowerColumn.includes("name")) {
                buildingDetailsSelection.classList.remove("hidden");
                streetNameColumnSelect.value = column;
              }

              // Check for street number
              if ((lowerColumn.includes("street") && lowerColumn.includes("num")) || lowerColumn === "number") {
                buildingDetailsSelection.classList.remove("hidden");
                streetNumColumnSelect.value = column;
              }

              // Check for municipality
              if (
                lowerColumn.includes("city") ||
                lowerColumn.includes("town") ||
                lowerColumn === "municipality" ||
                lowerColumn.includes("muni")
              ) {
                buildingDetailsSelection.classList.remove("hidden");
                muniColumnSelect.value = column;
              }
            });

            // Apply selections if found (in order of importance)
            if (addressSelected) {
              addressColumnSelect.value = addressSelected;
            }

            if (stateSelected) {
              stateColumnSelect.value = stateSelected;
            }

            if (zipSelected) {
              zipColumnSelect.value = zipSelected;
            }

            // Update all dropdown constraints after auto-selection
            updateAllDropdownConstraints();

            // Show column selection
            columnSelection.classList.remove("hidden");

            // Validate columns after auto-selection
            validateCsvColumns();
          };
          reader.readAsText(file);
        })
        .catch((error) => {
          csvFileInputErrors.textContent = "Error processing CSV file. Please try again.";
          console.error(error);
        });
    }
  });

  // Add change event listeners to update available options and clear errors
  addressColumnSelect.addEventListener("change", function () {
    clearInputError(addressColumnSelect, addressColumnError);
    updateAllDropdownConstraints();
    validateCsvColumns();
  });

  externalIdColumnSelect.addEventListener("change", function () {
    updateAllDropdownConstraints();
    validateCsvColumns();
  });

  stateColumnSelect.addEventListener("change", function () {
    clearInputError(stateColumnSelect, stateColumnError);
    updateAllDropdownConstraints();
    validateCsvColumns();
  });

  zipColumnSelect.addEventListener("change", function () {
    clearInputError(zipColumnSelect, zipColumnError);
    updateAllDropdownConstraints();
    validateCsvColumns();
  });

  // Add event listener for unmapped columns data type changes
  document.addEventListener("change", function (e) {
    if (e.target.closest("#unmapped_columns_list select")) {
      updateUnmappedColumnsData();
      validateCsvColumns();
    }
  });

  // Add change event listeners for building detail fields
  if (streetNameColumnSelect) {
    streetNameColumnSelect.addEventListener("change", function () {
      if (streetNameColumnError) clearInputError(streetNameColumnSelect, streetNameColumnError);
      updateAllDropdownConstraints();
      validateCsvColumns();
    });
  }

  if (streetNumColumnSelect) {
    streetNumColumnSelect.addEventListener("change", function () {
      if (streetNumColumnError) clearInputError(streetNumColumnSelect, streetNumColumnError);
      updateAllDropdownConstraints();
      validateCsvColumns();
    });
  }

  if (muniColumnSelect) {
    muniColumnSelect.addEventListener("change", function () {
      if (muniColumnError) clearInputError(muniColumnSelect, muniColumnError);
      updateAllDropdownConstraints();
      validateCsvColumns();
    });
  }

  if (submuniColumnSelect) {
    submuniColumnSelect.addEventListener("change", function () {
      if (submuniColumnError) clearInputError(submuniColumnSelect, submuniColumnError);
      updateAllDropdownConstraints();
      validateCsvColumns();
    });
  }

  if (constYearColumnSelect) {
    constYearColumnSelect.addEventListener("change", function () {
      if (constYearColumnError) clearInputError(constYearColumnSelect, constYearColumnError);
      updateAllDropdownConstraints();
      validateCsvColumns();
    });
  }

  if (numFloorsColumnSelect) {
    numFloorsColumnSelect.addEventListener("change", function () {
      if (numFloorsColumnError) clearInputError(numFloorsColumnSelect, numFloorsColumnError);
      updateAllDropdownConstraints();
      validateCsvColumns();
    });
  }

  if (floorAreaColumnSelect) {
    floorAreaColumnSelect.addEventListener("change", function () {
      if (floorAreaColumnError) clearInputError(floorAreaColumnSelect, floorAreaColumnError);
      updateAllDropdownConstraints();
      validateCsvColumns();
    });
  }

  // Add event listeners for the coordinate radio buttons
  hasCoordinatesRadios.forEach((radio) => {
    radio.addEventListener("change", function () {
      console.log("Coordinates radio changed:", this.value);

      if (this.value === "True") {
        // Make sure the coordinates selection is visible
        coordinatesSelection.classList.remove("hidden");
        console.log("Showing coordinates section");

        // Populate the lat/lng dropdowns with the same options as other dropdowns
        if (addressColumnSelect && addressColumnSelect.options.length > 1) {
          // Clear existing options except the first one
          while (latColumnSelect.options.length > 1) {
            latColumnSelect.remove(1);
          }
          while (lngColumnSelect.options.length > 1) {
            lngColumnSelect.remove(1);
          }

          // Add all column options from the address dropdown
          for (let i = 1; i < addressColumnSelect.options.length; i++) {
            const option = addressColumnSelect.options[i];

            const latOption = document.createElement("option");
            latOption.value = option.value;
            latOption.textContent = option.textContent;
            latColumnSelect.appendChild(latOption);

            const lngOption = document.createElement("option");
            lngOption.value = option.value;
            lngOption.textContent = option.textContent;
            lngColumnSelect.appendChild(lngOption);
          }

          // Try to auto-select lat/lng columns based on common names
          Array.from(latColumnSelect.options).forEach((option) => {
            const lowerValue = option.value.toLowerCase();
            if (lowerValue === "lat" || lowerValue.includes("latitude") || lowerValue === "y") {
              latColumnSelect.value = option.value;
            }
          });

          Array.from(lngColumnSelect.options).forEach((option) => {
            const lowerValue = option.value.toLowerCase();
            if (
              lowerValue === "lng" ||
              lowerValue === "long" ||
              lowerValue.includes("longitude") ||
              lowerValue === "x"
            ) {
              lngColumnSelect.value = option.value;
            }
          });
        }
      } else {
        coordinatesSelection.classList.add("hidden");
        console.log("Hiding coordinates section");
      }
      // Update dropdown constraints when visibility changes
      updateAllDropdownConstraints();
      validateCsvColumns();
    });
  });

  // Add event listeners for coordinate fields
  if (latColumnSelect) {
    latColumnSelect.addEventListener("change", function () {
      if (latColumnError) clearInputError(latColumnSelect, latColumnError);
      updateAllDropdownConstraints();
      validateCsvColumns();
    });
  }

  if (lngColumnSelect) {
    lngColumnSelect.addEventListener("change", function () {
      if (lngColumnError) clearInputError(lngColumnSelect, lngColumnError);
      updateAllDropdownConstraints();
      validateCsvColumns();
    });
  }

  // Add event listeners for the building details radio buttons
  hasBuildingDetailsRadios.forEach((radio) => {
    radio.addEventListener("change", function () {
      console.log("Building details radio changed:", this.value);

      if (this.value === "yes") {
        // Make sure the building details selection is visible
        buildingDetailsSelection.classList.remove("hidden");
        console.log("Showing building details section");

        // Populate the building details dropdowns with the same options as other dropdowns
        if (addressColumnSelect && addressColumnSelect.options.length > 1) {
          const buildingDetailSelects = [
            streetNameColumnSelect,
            streetNumColumnSelect,
            muniColumnSelect,
            submuniColumnSelect,
            constYearColumnSelect,
            numFloorsColumnSelect,
            floorAreaColumnSelect,
          ];

          // Clear existing options except the first one for each select
          buildingDetailSelects.forEach((select) => {
            if (select) {
              while (select.options.length > 1) {
                select.remove(1);
              }
            }
          });

          // Add all column options from the address dropdown to each building detail dropdown
          for (let i = 1; i < addressColumnSelect.options.length; i++) {
            const option = addressColumnSelect.options[i];

            buildingDetailSelects.forEach((select) => {
              if (select) {
                const newOption = document.createElement("option");
                newOption.value = option.value;
                newOption.textContent = option.textContent;
                select.appendChild(newOption);
              }
            });
          }

          // Try to auto-select building detail columns based on common names
          if (streetNameColumnSelect) {
            Array.from(streetNameColumnSelect.options).forEach((option) => {
              const lowerValue = option.value.toLowerCase();
              if (lowerValue.includes("street") && lowerValue.includes("name")) {
                streetNameColumnSelect.value = option.value;
              }
            });
          }

          if (streetNumColumnSelect) {
            Array.from(streetNumColumnSelect.options).forEach((option) => {
              const lowerValue = option.value.toLowerCase();
              if ((lowerValue.includes("street") && lowerValue.includes("num")) || lowerValue === "number") {
                streetNumColumnSelect.value = option.value;
              }
            });
          }

          if (muniColumnSelect) {
            Array.from(muniColumnSelect.options).forEach((option) => {
              const lowerValue = option.value.toLowerCase();
              if (
                lowerValue.includes("city") ||
                lowerValue.includes("town") ||
                lowerValue === "municipality" ||
                lowerValue.includes("muni")
              ) {
                muniColumnSelect.value = option.value;
              }
            });
          }

          if (constYearColumnSelect) {
            Array.from(constYearColumnSelect.options).forEach((option) => {
              const lowerValue = option.value.toLowerCase();
              if (lowerValue.includes("year") || lowerValue.includes("built") || lowerValue.includes("construction")) {
                constYearColumnSelect.value = option.value;
              }
            });
          }

          if (numFloorsColumnSelect) {
            Array.from(numFloorsColumnSelect.options).forEach((option) => {
              const lowerValue = option.value.toLowerCase();
              if (lowerValue.includes("floor") || lowerValue.includes("storey") || lowerValue.includes("story")) {
                numFloorsColumnSelect.value = option.value;
              }
            });
          }

          if (floorAreaColumnSelect) {
            Array.from(floorAreaColumnSelect.options).forEach((option) => {
              const lowerValue = option.value.toLowerCase();
              if (
                lowerValue.includes("area") ||
                lowerValue.includes("size") ||
                lowerValue.includes("sqft") ||
                lowerValue.includes("sq ft") ||
                lowerValue.includes("square")
              ) {
                floorAreaColumnSelect.value = option.value;
              }
            });
          }
        }
      } else {
        buildingDetailsSelection.classList.add("hidden");
        console.log("Hiding building details section");
      }
      // Update dropdown constraints when visibility changes
      updateAllDropdownConstraints();
      validateCsvColumns();
    });
  });

  // Update form submission validation
  newDatasetForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    // First check if a file has been uploaded
    if (!csvFileInput.files || !csvFileInput.files[0]) {
      csvFileInputErrors.textContent = "Please upload a CSV file";
      return false;
    }

    // Check if the CSV file has data rows
    const rowCountInput = document.getElementById("csv_row_count");
    if (!rowCountInput || parseInt(rowCountInput.value) < 1) {
      csvFileInputErrors.textContent =
        "The CSV file is empty or contains only headers. Please upload a file with at least one data row.";
      return false;
    }

    // Make sure unmapped columns data is updated before submission
    updateUnmappedColumnsData();

    // Then validate column selections
    if (!validateCsvColumns()) {
      return false;
    }

    // If all validations pass, the form will submit normally
    newDatasetForm.submit();
  });
}

document.addEventListener("DOMContentLoaded", () => {
  // do stuff
  setUpDatasetUploadForm();
});
