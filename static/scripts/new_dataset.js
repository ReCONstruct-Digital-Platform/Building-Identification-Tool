const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB
const EXCEL_FILE_TYPES = [
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "application/vnd.ms-excel",
];
const CSV_FILE_TYPE = "text/csv";

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

// Function to update all dropdown constraints
function updateAllDropdownConstraints() {
  const addressColumnSelect = document.querySelector('select[name="address_column"]');
  const zipColumnSelect = document.querySelector('select[name="zip_column"]');
  const stateColumnSelect = document.querySelector('select[name="state_column"]');

  // Get all column select elements
  const allSelects = [addressColumnSelect, stateColumnSelect, zipColumnSelect];

  // Update constraints for each select
  allSelects.forEach((select) => {
    const otherSelects = allSelects.filter((s) => s !== select);
    updateAvailableOptions(select, otherSelects);
  });
}

function setUpDatasetUploadForm() {
  const csvFileInput = document.querySelector('input[name="csv_file"]');
  const csvFileInputErrors = document.getElementById("csv_file_errors");
  const columnSelection = document.getElementById("column-selection");
  const addressColumnSelect = document.querySelector('select[name="address_column"]');
  const zipColumnSelect = document.querySelector('select[name="zip_column"]');
  const stateColumnSelect = document.querySelector('select[name="state_column"]');
  const addressColumnError = document.getElementById("address_column_errors");
  const stateColumnError = document.getElementById("state_column_errors");
  const zipColumnError = document.getElementById("zip_column_errors");

  const newDatasetForm = document.getElementById("new-dataset-form");

  // Function to validate CSV column selections
  function validateCsvColumns() {
    let isValid = true;

    // Clear all previous errors
    clearInputError(addressColumnSelect, addressColumnError);
    clearInputError(stateColumnSelect, stateColumnError);
    clearInputError(zipColumnSelect, zipColumnError);

    // Validate address column (required)
    if (!addressColumnSelect.value) {
      isValid = markInputError(addressColumnSelect, addressColumnError, "Address column is required");
    }

    // State column is required
    if (!stateColumnSelect.value) {
      isValid = markInputError(stateColumnSelect, stateColumnError, "State column is required");
    }

    // ZIP column is required
    if (!zipColumnSelect.value) {
      isValid = markInputError(zipColumnSelect, zipColumnError, "ZIP code column is required");
    }

    // Check for duplicate column selections
    if (
      addressColumnSelect.value &&
      (addressColumnSelect.value === stateColumnSelect.value || addressColumnSelect.value === zipColumnSelect.value)
    ) {
      isValid = markInputError(addressColumnSelect, addressColumnError, "Each column must be unique");
    }

    if (stateColumnSelect.value && stateColumnSelect.value === zipColumnSelect.value) {
      isValid = markInputError(stateColumnSelect, stateColumnError, "Each column must be unique");
      isValid = markInputError(zipColumnSelect, zipColumnError, "Each column must be unique");
    }

    return isValid;
  }

  // Handle CSV file upload and column detection
  csvFileInput.addEventListener("change", function (e) {
    if (this.files && this.files[0]) {
      const file = this.files[0];

      console.log(file);
      console.log(file.size);

      //Validate file size
      if (file.size > MAX_FILE_SIZE) {
        csvFileInputErrors.textContent =
          "File size exceeds 5MB. Please upload a smaller file or contact us for a custom request.";
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

          // Continue with parsing CSV header for column selection
          const reader = new FileReader();
          reader.onerror = function (e) {
            csvFileInputErrors.textContent = "Error reading file. Please try again.";
          };
          reader.onload = function (e) {
            const content = e.target.result;
            const firstLine = content.split("\n")[0];
            const columns = firstLine.split(",").map((col) => col.trim());

            // Populate all column selection dropdowns
            addressColumnSelect.innerHTML = "";
            zipColumnSelect.innerHTML = "";
            stateColumnSelect.innerHTML = "";

            // Add default empty option for all fields
            addressColumnSelect.innerHTML = '<option value="">-- Select Address Column --</option>';
            zipColumnSelect.innerHTML = '<option value="">-- Select ZIP Column --</option>';
            stateColumnSelect.innerHTML = '<option value="">-- Select State Column --</option>';

            // Add column options to all selects
            columns.forEach((column) => {
              // For address column
              const addrOption = document.createElement("option");
              addrOption.value = column;
              addrOption.textContent = column;
              addressColumnSelect.appendChild(addrOption);

              // For ZIP column
              const zipOption = document.createElement("option");
              zipOption.value = column;
              zipOption.textContent = column;
              zipColumnSelect.appendChild(zipOption);

              // For state column
              const stateOption = document.createElement("option");
              stateOption.value = column;
              stateOption.textContent = column;
              stateColumnSelect.appendChild(stateOption);
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

              // Auto-select state column
              if ((lowerColumn === "state" || lowerColumn.includes("state")) && !stateSelected) {
                stateSelected = column;
              }

              // Auto-select ZIP column (look for common patterns in ZIP columns)
              if (
                (lowerColumn === "zip" ||
                  lowerColumn.includes("zip") ||
                  lowerColumn === "postal" ||
                  lowerColumn.includes("postal code")) &&
                !zipSelected
              ) {
                zipSelected = column;
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
  });

  stateColumnSelect.addEventListener("change", function () {
    clearInputError(stateColumnSelect, stateColumnError);
    updateAllDropdownConstraints();
  });

  zipColumnSelect.addEventListener("change", function () {
    clearInputError(zipColumnSelect, zipColumnError);
    updateAllDropdownConstraints();
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
