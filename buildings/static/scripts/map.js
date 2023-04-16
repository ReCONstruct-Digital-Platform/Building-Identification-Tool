// Global counter variable to keep track of next ID to assign
var NEXT_ROW_ID = 2;


function getDeleteRowIconInnerHTML() {
    html = `
        <a class="a-delete-row" href="#">
        <i class="x-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-x-circle" viewBox="0 0 16 16">
            <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
            <path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708z"/>
            </svg>
        </i>
        </a>
    `;
    return html
}

function addNewMaterial(element) {
    const name = element.name
    element.old_name = name;
    element.name = "";
    const el = element.parentElement;

    const text_input = document.createElement("input");
    text_input.setAttribute("class", "new-material-input ml-2");
    text_input.setAttribute("type", "text")
    text_input.setAttribute("name", name)
    text_input.setAttribute("required", "")
    text_input.setAttribute("placeholder", "Enter new material...");

    el.appendChild(text_input)
}

// Adds event listeners to a select element, to detect if 'new-material'
// is selected. If so, make a text input field appear.
function addEventListeners(element) {
    // In case the value right after creation is new material, create the text input directly
    if(element.value == "new-material")
    {
        addNewMaterial(element);
    }

    // Just in case, copied this from online but don't think it's ever used
    element.addEventListener("click", function() {
        var options = element.querySelectorAll("option");
        var count = options.length;
        if(typeof(count) === "undefined" || count < 1)
        {
            addNewMaterial(element);
        }
    });

    element.addEventListener("change", function() {
        if(element.value == "new-material")
        {
            if (!element.parentElement.querySelector('input')) {
                addNewMaterial(element);
            }
        }
        else
        {
            // When changing from selected materials, if new value is
            // not 'New Material' then check if there's an input and delete it
            if (element.parentElement.querySelector('input')) {
                element.parentElement.querySelector('input').remove();
                element.name = element.old_name;
            }
        } 
    });
}


function addDeleteRowListener(element) {
    // Configures the element to delete the given ID when clicked
    element.addEventListener("click", function() {
        const row = element.closest('tr');
        row.remove();
    });
}

function getSelectedMaterials() {
    // Return all materials currently selected in dropdowns on the page
    const material_selects = document.querySelectorAll('.material-select')

    const selected_materials = [];
    for (var i = 0; i < material_selects.length; i++) {
        material = material_selects[i];

        if (material.value === "new-material") {
            selected_materials[i] = material.parentElement.querySelector('input').value;
        }
        else {
            selected_materials[i] = material.value;
        }
    }
    return selected_materials;
}





$(document).ready(function() {

    const element = document.getElementById('prev-building-link');

    // Provide a standard href to facilitate standard browser features such as 
    //  - Hover to see link
    //  - Right click and copy link
    //  - Right click and open in new tab
    element.setAttribute('href', document.referrer);

    // We can't let the browser use the above href for navigation. If it does, 
    // the browser will think that it is a regular link, and place the current 
    // page on the browser history, so that if the user clicks "back" again,
    // it'll actually return to this page. We need to perform a native back to
    // integrate properly into the browser's history behavior
    element.onclick = function() {
        history.back();
        return false;
    }

    // Add a text input when user clicks the 'Add Note' button
    // Only add if one doesn't already exist, to avoid duplicates.
    $('#btn-add-note').click(function() {
        const note_container = document.getElementById('note-container');

        if (!note_container.hasChildNodes()) {
            
            // Create this inner container to be deleted, instead of the overall element
            const inner_container = document.createElement('div');
            inner_container.setAttribute("class", "note-inner-container")
            inner_container.setAttribute("id", "note-inner-container")
            note_container.appendChild(inner_container);

            const p = document.createElement('p');
            p.innerText = "Additonal notes about this building:"
            inner_container.appendChild(p);
            
            const input_container = document.createElement('div');
            input_container.setAttribute("class", "note-input-container")
            inner_container.appendChild(input_container);
            

            const text_input = document.createElement('textarea');
            // text_input.setAttribute("type", "text");
            text_input.setAttribute("name", "note") ;
            text_input.setAttribute("placeholder", "Enter note...");
            text_input.setAttribute("class", "mb-3");
            text_input.setAttribute("required", "");
            text_input.setAttribute("resize", "both");
            input_container.appendChild(text_input);
            
            const delete_note = document.createElement('div');
            delete_note.setAttribute("class", "delete-note-icon");
            delete_note.innerHTML = getDeleteRowIconInnerHTML();
            
            delete_note.addEventListener("click", function() {
                inner_container.remove();
            });

            input_container.appendChild(delete_note);
        }
    });


    var dragging = false;

    $('#dragbar').mousedown(function(e) {
        e.preventDefault();
        dragging = true;
        var side = $('.streetview-container');
        $(document).mousemove(function(ex) {
            side.css("width", ex.pageX +2);
        });
    });

    $(document).mouseup(function(e){
    if (dragging) 
    {
        $(document).unbind('mousemove');
        dragging = false;
    }
    });


});