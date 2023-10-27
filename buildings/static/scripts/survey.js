function setUpSurveyNavigation() {
    // Set-up the on-page back button
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
}

function getLatestViewData() {
    // Get the latest view data from streetview
    const sv_pov = sv.getPov();
    const m_marker_pos = m_marker.getPosition();
    
    return {
        'sv_pano': sv.getPano(),
        'sv_heading': sv_pov.heading,
        'sv_pitch': sv_pov.pitch,
        'sv_zoom': sv_pov.zoom,
        'marker_lat': m_marker_pos.lat(),
        'marker_lng': m_marker_pos.lng(),
    }
}

// Tried to replace with the faster https://github.com/tsayen/dom-to-image 
// but failed due to this error https://github.com/tsayen/dom-to-image/issues/205
// Since google maps loads the stylesheet, I can't add crossorigin="anonymous" to it.
async function screenshot(element_id) {
    return html2canvas(
        document.getElementById(element_id), {
            useCORS: true,
            logging: false, // set true for debug,
            ignoreElements: (el) => {
                // The following hides unwanted controls, copyrights, pins etc. on the maps and streetview canvases
                let condition = el.classList.contains("gmnoprint") || el.classList.contains("gm-style-cc") 
                || el.id === 'gmimap1' || el.tagName === 'BUTTON' || el.classList.contains("gm-iv-address")
                || el.getAttribute('title') === "Open this area in Google Maps (opens a new window)"
                || el.id === 'time-travel-container';

                // Addtionally remove the red pin for the streetview (but keep it for satellite)
                if (element_id === 'streetview') {
                    return condition 
                        ||= el.getAttribute('src') === 'https://maps.gstatic.com/mapfiles/api-3/images/spotlight-poi3_hdpi.png'
                        || el.getAttribute('src') === 'https://maps.gstatic.com/mapfiles/api-3/images/spotlight-poi3.png';
                }
                else {
                    return condition ||= el.getAttribute('style') === "position: absolute; left: 0px; top: 0px; z-index: 1;";
                }
            },
        }
    ).then(canvas => {
        // // Uncomment for testing - appends the images to the page
        // document.body.style.overflowY = 'scroll';
        // document.body.style.height = '100%';
        // document.getElementById('test-screenshots-container').appendChild(canvas);

        // Convert the image to a dataURL for uploading to the backend
        return canvas.toDataURL('image/png');
    })
}


/**
* Screenshot the streetview. Called when the screenshot button is clicked.
*/
async function screenshotStreetview(event) {
    event.preventDefault();

    const toastElement = document.getElementById('screenshot-toast');
    const toastBootstrap = bootstrap.Toast.getOrCreateInstance(toastElement); 
    
    // Screenshot the streetview as well
    const imgData = {
        streetview: await screenshot('streetview'),
    }

    // Get the upload url from the page and POST the data
    const url = document.getElementById("upload_url").getAttribute("data-url");

    fetch(url, {
        method: "POST",
        mode: "same-origin", 
        cache: "no-cache", 
        credentials: "same-origin", 
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie('csrftoken'), // So django accepts the request
        },
        body: JSON.stringify(imgData), 
    }).then((resp) => {
        if (resp.status === 200) {
            document.getElementById('sv_uploaded').setAttribute('data-uploaded', 'true');
            toastBootstrap.show();
        }
    });
}


function setUpDragBar() {
    const dragbar = document.getElementById('dragbar');
    const left = document.getElementById('streetview-container');

    // Check if streetview container was previously resized by the user
    // If not set its size to a default of 50%, otherwise use saved settings
    const saved = localStorage.getItem("savedWidth");

    if (saved){
        left.style.width = saved;
    } else {
        left.style.width = '50%';
    }
    
    // Calculate the new width, set the left panel's width and save in local storage
    const resizeOnDrag = (e) => {
        document.selection ? document.selection.empty() : window.getSelection().removeAllRanges();
        const newWidth = (e.pageX - dragbar.offsetWidth / 2) + 'px'
        left.style.width = newWidth;
        localStorage.setItem("savedWidth", newWidth);
    }
      
    dragbar.addEventListener('mousedown', () => {
        document.addEventListener('mousemove', resizeOnDrag);
    });
    
    dragbar.addEventListener('mouseup', () => {
        document.removeEventListener('mousemove', resizeOnDrag);
    });

    document.addEventListener('mouseup', () => {
        document.removeEventListener('mousemove', resizeOnDrag);
    });
}

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

/** 
* This function dynamically sets the height of the right panel (satellite view and survey)
*/
function setUpScrollHeightObserver() {
    const svElement = document.getElementById('streetview');
    const tabElement = document.getElementById('nav-tab');

    const observer = new MutationObserver(() => {
        const svHeight = svElement.offsetHeight;
        const tabHeight = tabElement.offsetHeight;
        const textHeight = svHeight - tabHeight ;
        document.getElementById("tab-content-container").style.height = textHeight + "px";
    })
    observer.observe(svElement, {childList: true, subtree: true});
}



function setUpButtons() {
    // Screenshot functionality
    const screenshotButton = document.getElementById('btn-screenshot');
    screenshotButton.addEventListener('click', (e) => {
        screenshotStreetview(e);
    });
    window.addEventListener('keyup', (e) => {
        if (e.code === 'Space') {
            console.debug('spacebar pressed');
            if (e.target.nodeName !== 'INPUT') {
                screenshotStreetview(e);
            }
        }
    }, false);


    // No building button
    document.getElementById('btn-no-building').addEventListener('click', (e) => {
        e.preventDefault();
        
        const form = document.getElementById('building-submission-form');

        const no_building_input = document.createElement("input");
        no_building_input.setAttribute("type", "hidden");
        no_building_input.setAttribute("name", "no_building");
        no_building_input.setAttribute("value", "no_building");
        form.appendChild(no_building_input);
        try {
            const latest_view_data = getLatestViewData();
            document.getElementById('latest_view_data').value = JSON.stringify(latest_view_data);
        }
        catch (error) {
            console.error(error);
        } 
        finally {
            form.submit();
        }
    })

    // When user submits form, upload both current streetview and sat views
    // then continue with default behaviour
    document.getElementById('btn-submit-vote').addEventListener('click', async (e) => {
        e.preventDefault();

        const form = document.getElementById('building-submission-form');
        
        // Check form inputs are valid
        if (!form.checkValidity()) {
            // Create the temporary button, click and remove it
            // This makes the validation comments appear on screen
            var tmpSubmit = document.createElement('button');
            form.appendChild(tmpSubmit);
            tmpSubmit.click();
            form.removeChild(tmpSubmit);
        }
        else {
            // Check if the user previously screenshotted a streetview
            // If not, we'll save the current streetview now
            const sv_uploaded = document.getElementById('sv_uploaded');
            if (sv_uploaded.getAttribute('data-uploaded') !== 'true') {
                console.log('No SV screenshots taken by user, will take one now.')
                await screenshotStreetview(e);
            }
            // Set the latest view data in the form
            const latest_view_data =  JSON.stringify(getLatestViewData());
            document.getElementById('latest_view_data').value = latest_view_data;
            form.submit();
        }
    });
}


/**
 * Handle the stored satellite image upload to the backend.
 * If the new image has not changed from the previous one, 
 * or all form fileds are empty, do not upload.
 */
function uploadSatelliteImage(target, uploadURL, oldValue) {
    const currentValue = target.getAttribute('data-url');

    if (allInputsEmpty())
        return console.debug('No input filled yet, do not screenshot satellite.')

    if (oldValue === currentValue)
        return console.debug("Satellite image hasn't changed, do not upload.")
       
    // Upload new satellite image
    fetch(uploadURL, {
        method: "POST",
        mode: "same-origin", 
        cache: "no-cache", 
        credentials: "same-origin", 
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie('csrftoken'), // So django accepts the request
        },
        body: JSON.stringify({'satellite': currentValue})
    }).then((resp) => {
        if (resp.status === 200) {
            console.debug('Satellite img uploaded successfully');
        } 
        else {
            console.debug(`Problem uploading screenshot ${resp}`);
        }
    });
}

/**
 * Called when the user switches from satellite view to the survey.
 * If the satellite view has changed since the last time this happened,
 * upload the new view to the image store.
 */
function satelliteImageMutationCallback(mutationList, _) {
    const target = document.getElementById('sat_data');
    const uploadURL = document.getElementById("upload_url").getAttribute("data-url");

    for (const mutation of mutationList) {
        uploadSatelliteImage(target, uploadURL, mutation.oldValue);
    }
}

/**
 * Check if all the survey inputs are empty.
 * Used to decide if we want to screenshot the satellite.
 */
function allInputsEmpty() {
    let allEmpty = true;
    document.querySelectorAll('input').forEach((input) => {
        if ((input.type === 'radio' || input.type === 'checkbox') && input.checked)
            return allEmpty = false;
        if ((input.type === 'number' || input.type === 'text') && input.value !== '') 
            return allEmpty = false;
    });
    return allEmpty;
}

/**
 * Setup the satellite image observer to upload new satellite views to backend
 */
function setUpSatelliteImageObserver() {
    const targetNode = document.getElementById('sat_data');
    const observer = new MutationObserver(satelliteImageMutationCallback);
    observer.observe(targetNode, {attributes: true, attributeOldValue: true});
}


/**
 * Setup an event listener to take a screenshot of the satellite view
 * and save it in a hidden element on the page.
 * A mutation observer on the storage element will handle uploading it. 
 */
function satelliteTabScreenshotOnHide() {
    // The hide.bs.tab event fires when the tab is to be hidden
    document.getElementById('nav-satellite-tab').addEventListener(
      'hide.bs.tab', async () => {
        const dataUrl = await screenshot('satellite');
        document.getElementById('sat_data').setAttribute('data-url', dataUrl);
    });
}


/**
 * Used to detect when the form is first starting to be filled
 * and trigger a satellite screenshot upload at that point.
 * This is to avoid uploading useless satellite screenshots when
 * a user is not actively filling the survey but changes tabs.
 */
function setUpInitialSurveyMutationChecker() {
    const form = document.getElementById('building-submission-form');
    const observer = new MutationObserver(async (mutationList, observer) => {
        for (const mutation of mutationList) {
            if (mutation.target.nodeName === 'INPUT') {
                if (!allInputsEmpty()) {
                    console.debug('Detected form input mutation, with some inputs filled. Trigerring upload.')
                    const target = document.getElementById('sat_data');
                    const uploadURL = document.getElementById("upload_url").getAttribute("data-url");
                    uploadSatelliteImage(target, uploadURL, "dummy old value");
                    // Only execute this observer the first time an input is changed
                    observer.disconnect();
                    // don't process any other accompagnying mutations
                    // e.g. on radio + text/number inputs
                    return;
                }
            }
        }
    });
    observer.observe(form, {subtree: true, attributes: true});
}


$(document).ready(function() {
    setUpSurveyNavigation();
    setUpDragBar();
    setUpScrollHeightObserver();
    setUpButtons();
    satelliteTabScreenshotOnHide();
    setUpSatelliteImageObserver();
    setUpInitialSurveyMutationChecker();
});
