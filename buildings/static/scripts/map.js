function getLatestViewData() {
    // Get the latest view data from streetview
    const sv_pano = sv.getPano();
    const sv_pov = sv.getPov();
    const m_marker_pos = m_marker.getPosition();
    
    return {
        'sv_pano': sv_pano,
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
            logging: false, // set true for debug
            ignoreElements: (el) => {
                // The following hides unwanted controls, copyrights, pins etc. on the maps and streetview canvases
                return el.classList.contains("gmnoprint") || el.classList.contains("gm-style-cc") 
                || el.id === 'gmimap1' || el.tagName === 'BUTTON' || el.classList.contains("gm-iv-address")
                || el.getAttribute('src') === 'https://maps.gstatic.com/mapfiles/api-3/images/spotlight-poi3_hdpi.png'
                || el.getAttribute('src') === 'https://maps.gstatic.com/mapfiles/api-3/images/spotlight-poi3.png'
            },
        }
    ).then(canvas => {
        // For testing - appends the images to the page
        // document.body.appendChild(canvas);
        // Convert the image to a dataURL for uploading to the backend
        return canvas.toDataURL('image/png');
    })
}


async function screenshotAndUpload(event) {
    event.preventDefault();
    // Attempt to get the satellite screenshot from this element
    let satelliteDataUrl = $("#sat_data").attr("data-url");
    
    // If not found, screenshot it now
    if (!satelliteDataUrl) {
        console.log('Need to screenshot satellite');
        satelliteDataUrl = await screenshot('satmap');
    }
    // Screenshot the streetview as well
    const imgData = {
        streetview: await screenshot('streetview'),
        satellite: satelliteDataUrl,
    }

    // Get the upload url from the page and POST the data
    const url = $("#upload_url").attr("data-url");

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
      });
}


function setUpDraggableMidBar() {
    // Check if streetview container was previously resized by the user
    // If not set its size to a default of 50%, otherwise use saved settings
    const sv_container = $('#streetview-container');
    const sv_saved_width = localStorage.getItem("sv_saved_width");

    if (sv_saved_width){
        sv_container.css("width", sv_saved_width);
    } else {
        sv_container.css("width", '50%');
    }

    let dragging = false;

    $('#dragbar').mousedown(function(e) {
        e.preventDefault();
        dragging = true;
        
        $(document).mousemove(function(ex) {
            sv_container.css("width", ex.pageX +2);
            localStorage.setItem("sv_saved_width", ex.pageX +2);
        });
    });

    // $('#dragbar').mouseup((e) => {
    //     localStorage.setItem("sv_saved_width", e.pageX + 2);
    // });

    $(document).mouseup(() => {
        if (dragging) {
            $(document).unbind('mousemove');
            dragging = false;
        }
    });
}

function setupDragBar2() {
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

$(document).ready(function() {

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

    // setUpDraggableMidBar();
    setupDragBar2();
    setUpScrollHeight();

    // The hide.bs.tab event fires when the tab is to be hidden
    $('#nav-satellite-tab').on('hide.bs.tab', async (e) => {
        // We save a screenshot of its current version to upload later
        console.log('screenshoting satellite');
        const dataUrl = await screenshot('satmap');
        $('#sat_data').attr('data-url', dataUrl);
    });

    // Screenshot functionality
    $('#btn-screenshot').click(screenshotAndUpload);

    // When user submits form, upload both current streetview and sat views
    // then continue with default behaviour
    $('#btn-submit-vote').click(async (e) => {
        e.preventDefault();
        form = $('#building-submission-form')[0];
        
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
            // screenshot the streetview
            await screenshotAndUpload(e);
            // Set the latest view data
            $('#latest_view_data').val(JSON.stringify(getLatestViewData()));
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


// dynamically control the scroll bar of the survey horizontally and vertically
// use the width/height of device, minus the width/height of streetview, gives the width/height of scrolling div
// the min width of survey is set to 500px, making sure that words wouldn't squeeze together.
// since DOMSubtreeModified is deprecated, use MutationObserver
// https://stackoverflow.com/questions/41971140/implementing-mutationobserver-in-place-of-domsubtreemodified

// $(document).ready(
function setUpScrollHeight() {
    
    const targetNode = document.getElementById('streetview');

    const observer = new MutationObserver(() => {
        var svHeight = $('#streetview').height();
        var tabHeight = $('#nav-tab').height();
        var textHeight = svHeight - tabHeight ;

        console.log(`sv height: ${svHeight}\nnavtab height: ${tabHeight}\ntextHeight: ${textHeight}`);
        console.log()

        // var dynWidth =  $('#streetview').width();
        // changeWidth = screen.width - dynWidth;
        
        // if (parseFloat(changeWidth) < 500) {
        //     changeWidth = "500";
        // }
        
        // console.log(`changeWidth: ${changeWidth}`)

        document.getElementById("scroll").style.height = textHeight + "px";

    })

    observer.observe(targetNode, {childList: true, subtree: true});

}

