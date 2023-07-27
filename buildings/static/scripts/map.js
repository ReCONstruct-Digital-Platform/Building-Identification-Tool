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
    text_input.setAttribute("class", "new-material-input ms-2");
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
    if(element.value === "new-material")
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
        if(element.value === "new-material")
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


function getLatestViewData() {
    sv_pano = sv.getPano();
    sv_pov = sv.getPov();
    m_marker_pos = m_marker.getPosition();
    
    var latest_view_data = {}
    // Add extra data to the form
    latest_view_data['sv_pano'] = sv_pano;
    latest_view_data['sv_heading'] = sv_pov.heading;
    latest_view_data['sv_pitch'] = sv_pov.pitch;
    latest_view_data['sv_zoom'] = sv_pov.zoom;
    latest_view_data['marker_lat'] = m_marker_pos.lat();
    latest_view_data['marker_lng'] = m_marker_pos.lng();

    return latest_view_data;
}


async function screenshot(element_id) {
    return html2canvas(
        document.querySelector(`#${element_id}`), {
            useCORS: true,
            logging: false,
            ignoreElements: (el) => {
                // The following hides unwanted controls, copyrights, pins etc. on the maps and streetview canvases
                return el.classList.contains("gmnoprint") || el.classList.contains("gm-style-cc") 
                || el.id === 'gmimap1' || el.tagName === 'BUTTON' || el.classList.contains("gm-iv-address")
                || el.getAttribute('src') === 'https://maps.gstatic.com/mapfiles/api-3/images/spotlight-poi3_hdpi.png'
                || el.getAttribute('src') === 'https://maps.gstatic.com/mapfiles/api-3/images/spotlight-poi3.png'
            },
        }
    ).then(canvas => {
        // For testing - appends the images to the web page
        // document.body.appendChild(canvas);
        // Convert the image to a dataURL for uploading to the backend
        return canvas.toDataURL('image/png');
    })
}

async function screenshotEvent(event) {
    event.preventDefault();
        
    // If the satellite tab is inactive, it is not rendered
    // We need it to be rendered to take a screenshot,
    // so we temporarily render it in an invisible element.
    let satelliteScreenshot;
    const activeTab = $('#nav-tab button.active'); 
    if ( activeTab.attr('id') !== 'nav-satellite-tab') {
        const parent = $('#satmap').parent();
        const width = parent.width();
        const height = parent.height();
        
        $('#satmap').appendTo(document.body);
        $('#satmap').width(width).height(height);
        $('#satmap').addClass('offscreen');

        satelliteScreenshot = await screenshot('satmap');
        $('#satmap').removeClass('offscreen');
        $('#satmap').appendTo(parent);
    } else {
        satelliteScreenshot = await screenshot('satmap');
    }

    const imgData = {
        streetview: await screenshot('streetview'),
        satellite: satelliteScreenshot,
    }

    const url = $("#upload_url").attr("data-url");
    console.log(imgData);
    
    // async call
    fetch(url, {
        method: "POST", // *GET, POST, PUT, DELETE, etc.
        mode: "same-origin", // no-cors, *cors, same-origin
        cache: "no-cache", // *default, no-cache, reload, force-cache, only-if-cached
        credentials: "same-origin", // include, *same-origin, omit
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie('csrftoken'),
        },
        body: JSON.stringify(imgData), // body data type must match "Content-Type" header
      });
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

    $('#btn-no-building').click((e) => {
        e.preventDefault();
        
        const form = document.getElementById('building-submition-form');

        const no_building_input = document.createElement("input");
        no_building_input.setAttribute("type", "hidden");
        no_building_input.setAttribute("name", "no_building");
        no_building_input.setAttribute("value", "no_building");
        form.appendChild(no_building_input);
        try {
            const latest_view_data = getLatestViewData();
            document.querySelector('#latest_view_data').value = JSON.stringify(latest_view_data);
        }
        catch (error) {
            console.error(error);
        } 
        finally {
            form.submit();
        }
    })


    // Check if streetview container was resized previously
    // If not set its size to 50%, if yes use the saved settings
    const sv_container = $('.streetview-container');

    var sv_saved_width = localStorage.getItem("sv_saved_width");

    if (sv_saved_width === null){
        sv_container.css("width", '50%');
    } else {
        sv_container.css("width", sv_saved_width);
    }

    var dragging = false;

    $('#dragbar').mousedown(function(e) {
        e.preventDefault();
        dragging = true;
        
        $(document).mousemove(function(ex) {
            sv_container.css("width", ex.pageX +2);
            localStorage.setItem("sv_saved_width", ex.pageX +2);
        });
    });

    $(document).mouseup(function(e){
    if (dragging) 
    {
        $(document).unbind('mousemove');
        dragging = false;
    }
    });

    // Screenshot functionality
    $('#btn-screenshot').click(screenshotEvent);

    $('#building-submition-form').one('submit', (e) => {
        e.preventDefault();
        try {
            const latest_view_data = getLatestViewData();
            document.querySelector('#latest_view_data').value = JSON.stringify(latest_view_data);
        } 
        catch (error) {
            console.error(error);
        } 
        finally {
            console.log('building submission form submitting');
            // Go on to the normal processing
            // $('building-submission-form').submit();
        }

    })

    // $('#building-submition-form').on('submit', (e) => {
    //     e.preventDefault();
    //     console.log('preventing submission');
    //     return false;
    // })

    // When user submits form, upload both current streetview and sat views
    // then continue with default behaviour
    $('#btn-submit-vote').click(async (e) => {

        console.log('btn-submit-vote clicked');

        e.preventDefault();
        form = $('#building-submission-form')[0];
        
        if (!form.checkValidity()) {
            // Create the temporary button, click and remove it
            var tmpSubmit = document.createElement('button')
            form.appendChild(tmpSubmit)
            tmpSubmit.click()
            form.removeChild(tmpSubmit)
        }
        // Form is valid
        else {
            console.log('btn-submit-vote clicked - screenshotting');
            await screenshotEvent(e);
            $('#btn-screenshot').trigger('click');
            // const imgData = {
            //     streetview: await screenshot('streetview'),
            //     satellite: await screenshot('satmap'),
            // }
        
            // const url = $("#upload_url").attr("data-url");
            // console.log(imgData);
            
            // // async call
            // fetch(url, {
            //     method: "POST", // *GET, POST, PUT, DELETE, etc.
            //     mode: "same-origin", // no-cors, *cors, same-origin
            //     cache: "no-cache", // *default, no-cache, reload, force-cache, only-if-cached
            //     credentials: "same-origin", // include, *same-origin, omit
            //     headers: {
            //       "Content-Type": "application/json",
            //       "X-CSRFToken": getCookie('csrftoken'),
            //     },
            //     body: JSON.stringify(imgData), // body data type must match "Content-Type" header
            //   });
            console.log('btn-submit-vote clicked - form submitting');
            // Finally submit the form
            form.submit();
        }

    })
    
});

function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}



// for question 3
// prompts user's inputs when selecting "number of storeys", disable the button when selecting "unsure",
$(function() {
  $('#Q3_1').on("click", function() {
      document.getElementById("I3").disabled = false;
      document.getElementById("I3").required = true;
  });
  $('#U3').on("click", function() {
      document.getElementById("I3").disabled = true;
      document.getElementById("I3").value = "";
  });
});

// for questions that have checkboxes as inputs, make sure at least one checkbox is selected
// loops through the checkboxes with given name to check if at least one is checked.
// if so, remove the required attribute from all of them
function deRequire(questionNum) {
  el = document.getElementsByName(questionNum);
  var atLeastOneChecked = false;
  for (i = 0; i < el.length; i++) {
    if (el[i].checked === true) {
      atLeastOneChecked = true;
    }
  }
  if (atLeastOneChecked) {
    for (i = 0; i < el.length; i++) {
      el[i].required = false;
    }
  } else {
    for (i = 0; i < el.length; i++) {
      el[i].required = true;
    }
  }
}

// for questions other than question 3, which require text as user's inputs
// prompt users to enter inputs or disable/clear inputs accordingly
function deDisabled(questionNum) {
    var substring = questionNum.slice(0, -1)
    if (document.getElementById(questionNum).checked) {
      document.getElementById(substring).disabled = false;
      document.getElementById(substring).required = true;
    }
    else {
      document.getElementById(substring).disabled = true;
      document.getElementById(substring).required = false;
      document.getElementById(substring).value = "";
    }
}

// dynamically control the scroll bar of the survey horizontally and vertically
// use the width/height of device, minus the width/height of streetview, gives the width/height of scrolling div
// the min width of survey is set to 500px, making sure that words wouldn't squeeze together.
// since DOMSubtreeModified is deprecated, use MutationObserver
// https://stackoverflow.com/questions/41971140/implementing-mutationobserver-in-place-of-domsubtreemodified
$(document).ready(function() {
    $('#streetview').each(function() {
      var sel = this;

      new MutationObserver(function() {
        var dynHeight = $('#streetview').height();
        var navTabheight = $('#nav-tab').height();
        var textHeight = dynHeight - navTabheight ;
        var dynWidth =  $('#streetview').width();
        var screenWidth = screen.width;
        changeWidth = screenWidth - dynWidth ;

        if (parseFloat(changeWidth) < 500)
            changeWidth = "500px";

        window.onload = (function () {
            document.getElementById("scroll").style.height = textHeight + "px";
        })();
        }).observe(sel, {childList: true, subtree: true});
    });
});
