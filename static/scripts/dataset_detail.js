// Dataset Detail Page JavaScript

// Function to get current query parameters for HTMX requests
function getCurrentQuery() {
  // Get the selected geocoding filter
  const geocodingFilter = document.getElementById('geocoding-filter').value;
  
  // Get the selected ordering field and direction
  const orderByField = document.getElementById('order-by-field').value;
  const orderByDir = document.querySelector('input[name="order-by-dir"]:checked').value;
  
  // Get the selected columns
  const userBldgCols = getUserBldgCols();
  
  return {
    geocoding_filter: geocodingFilter,
    field: orderByField,
    dir: orderByDir,
    user_bldg_cols: JSON.stringify(userBldgCols)
  };
}

// Function to get selected building columns
function getUserBldgCols() {
  const checkboxes = document.querySelectorAll('#draggable-list input[type="checkbox"]:checked');
  const cols = [];
  
  checkboxes.forEach(checkbox => {
    cols.push({
      id: checkbox.id,
      label: checkbox.parentElement.textContent.trim()
    });
  });
  
  return cols;
}

// Initialize the page when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
  // Set up event listeners for the geocoding filter
  const geocodingFilter = document.getElementById('geocoding-filter');
  if (geocodingFilter) {
    geocodingFilter.addEventListener('change', function() {
      document.getElementById('submitQueryButton').click();
    });
  }
  
  // Set up event listeners for ordering options
  const orderByField = document.getElementById('order-by-field');
  if (orderByField) {
    orderByField.addEventListener('change', function() {
      document.getElementById('submitQueryButton').click();
    });
  }
  
  const orderByDirRadios = document.querySelectorAll('input[name="order-by-dir"]');
  orderByDirRadios.forEach(radio => {
    radio.addEventListener('change', function() {
      document.getElementById('submitQueryButton').click();
    });
  });
  
  // Set up column configuration modal
  const columnConfigModal = document.getElementById('column_config_modal');
  const showColConfigButton = document.getElementById('show-col-config');
  
  if (showColConfigButton && columnConfigModal) {
    showColConfigButton.addEventListener('click', function() {
      // Modal handling is done by the modal component
    });
    
    // Handle reset defaults button
    const resetButtons = document.querySelectorAll('.reset-button');
    resetButtons.forEach(button => {
      button.addEventListener('click', function() {
        const defaultBldgCols = JSON.parse(document.getElementById('default_bldg_cols').textContent);
        
        // Reset checkboxes to match default columns
        const checkboxes = document.querySelectorAll('#draggable-list input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
          const isInDefault = defaultBldgCols.some(col => col.id === checkbox.id);
          checkbox.checked = isInDefault;
        });
      });
    });
    
    // Handle select/unselect all buttons
    const selectAllButtons = document.querySelectorAll('.select-all-button');
    selectAllButtons.forEach(button => {
      button.addEventListener('click', function() {
        const checkboxes = button.closest('div').querySelectorAll('input[type="checkbox"]');
        const allChecked = Array.from(checkboxes).every(cb => cb.checked);
        
        checkboxes.forEach(checkbox => {
          checkbox.checked = !allChecked;
        });
        
        // Update button text
        button.textContent = allChecked ? 'Select all' : 'Unselect all';
      });
    });
  }
  
  // Set up draggable lists for column reordering
  const draggableLists = document.querySelectorAll('#draggable-list');
  draggableLists.forEach(list => {
    setupDraggableList(list);
  });
  
  // Handle download button
  const downloadButton = document.getElementById('download');
  if (downloadButton) {
    downloadButton.addEventListener('click', function(e) {
      e.preventDefault();
      
      // Show loading icon
      document.getElementById('download-button-loading-icon').classList.remove('hidden');
      document.getElementById('download-button-icon').classList.add('hidden');
      
      // Get current query parameters
      const params = getCurrentQuery();
      
      // Add dataset ID
      const datasetId = window.location.pathname.split('/').pop();
      params.dataset_id = datasetId;
      
      // TODO: Implement download functionality
      // This would typically make an AJAX request to a server endpoint
      
      // For now, just simulate a download after a delay
      setTimeout(() => {
        // Hide loading icon
        document.getElementById('download-button-loading-icon').classList.add('hidden');
        document.getElementById('download-button-icon').classList.remove('hidden');
        
        console.log('Download requested with params:', params);
        alert('Download functionality not implemented in this demo');
      }, 1000);
    });
  }
});

// Function to set up draggable list functionality
function setupDraggableList(list) {
  let draggedItem = null;
  
  // Add event listeners to list items
  const items = list.querySelectorAll('li');
  items.forEach(item => {
    // Drag start
    item.addEventListener('dragstart', function() {
      draggedItem = item;
      setTimeout(() => {
        item.classList.add('opacity-50');
      }, 0);
    });
    
    // Drag end
    item.addEventListener('dragend', function() {
      draggedItem = null;
      item.classList.remove('opacity-50');
    });
    
    // Drag over
    item.addEventListener('dragover', function(e) {
      e.preventDefault();
    });
    
    // Drag enter
    item.addEventListener('dragenter', function(e) {
      e.preventDefault();
      if (this !== draggedItem) {
        this.classList.add('bg-gray-100');
      }
    });
    
    // Drag leave
    item.addEventListener('dragleave', function() {
      this.classList.remove('bg-gray-100');
    });
    
    // Drop
    item.addEventListener('drop', function(e) {
      e.preventDefault();
      if (this !== draggedItem) {
        const allItems = Array.from(list.querySelectorAll('li'));
        const draggedIndex = allItems.indexOf(draggedItem);
        const droppedIndex = allItems.indexOf(this);
        
        if (draggedIndex < droppedIndex) {
          this.parentNode.insertBefore(draggedItem, this.nextSibling);
        } else {
          this.parentNode.insertBefore(draggedItem, this);
        }
        
        this.classList.remove('bg-gray-100');
      }
    });
  });
}