var svUploaded = false;
var satUploaded = false;

function getLatestViewData() {
  // Get the latest view data from streetview
  const sv_pov = sv.getPov();
  const m_marker_pos = m_marker.getPosition();

  return {
    sv_pano: sv.getPano(),
    sv_heading: sv_pov.heading,
    sv_pitch: sv_pov.pitch,
    sv_zoom: sv_pov.zoom,
    marker_lat: m_marker_pos.lat(),
    marker_lng: m_marker_pos.lng(),
  };
}

// Tried to replace with the faster https://github.com/tsayen/dom-to-image
// but failed due to this error https://github.com/tsayen/dom-to-image/issues/205
// Since Google Maps loads the stylesheet, I can't add crossorigin="anonymous" to it.
async function screenshot(element_id) {
  return html2canvas(document.getElementById(element_id), {
    useCORS: true,
    logging: false, // set true for debug,
    ignoreElements: (el) => {
      // The following hides unwanted controls, copyrights, pins etc. on the maps and streetview canvases
      let condition =
        el.classList.contains("gmnoprint") ||
        el.classList.contains("gm-style-cc") ||
        el.id === "gmimap1" ||
        el.tagName === "BUTTON" ||
        el.classList.contains("gm-iv-address") ||
        el.getAttribute("title") === "Open this area in Google Maps (opens a new window)" ||
        el.id === "sv-top-right-controls-container" ||
        el.id === "unit-info" ||
        // Lot polygon corner markers
        (el.nodeName === "CANVAS" && el.getAttribute("width") === "32" && el.getAttribute("height") === "36");

      // Additionally remove the red pin for the streetview (but keep it for satellite)
      if (element_id === "streetview") {
        return (condition ||=
          el.getAttribute("src") === "https://maps.gstatic.com/mapfiles/api-3/images/spotlight-poi3_hdpi.png" ||
          el.getAttribute("src") === "https://maps.gstatic.com/mapfiles/api-3/images/spotlight-poi3.png");
      } else {
        return (condition ||= el.getAttribute("style") === "position: absolute; left: 0px; top: 0px; z-index: 1;");
      }
    },
  }).then((canvas) => {
    // // Uncomment for testing - appends the images to the page
    // // Hacky way to check if DEBUG is on
    // if (console.debug.toString() !== "function() {}") {
    //   document.body.style.overflowY = "scroll";
    //   document.body.style.height = "100%";
    //   document.getElementById("test-screenshots-container").appendChild(canvas);
    // }

    // Convert the image to a dataURL for uploading to the backend
    return canvas.toDataURL("image/jpeg");
  });
}

async function screenshotStreetview() {
  const sv_pov = sv.getPov();
  const panoData = sv.getLocation();

  // Screenshot the streetview and gather metadata
  const imgData = {
    sv: await screenshot("streetview"),
    lat: panoData.latLng.lat(),
    lng: panoData.latLng.lng(),
    pano_date: window.lastPanoDate,
    sv_pano: panoData.pano,
    sv_heading: sv_pov.heading,
    sv_pitch: sv_pov.pitch,
    sv_zoom: sv_pov.zoom,
    survey_slug: JSON.parse(document.getElementById("survey_slug").textContent),
  };
  return imgData;
}

async function screenshotSatellite() {
  const satData = {
    sat: await screenshot("satellite"),
    center_lat: map.center.lat(),
    center_lng: map.center.lng(),
    map_url: map.mapUrl,
    zoom: map.zoom,
    tilt: map.tilt,
    map_type: map.mapTypeId,
    survey_slug: JSON.parse(document.getElementById("survey_slug").textContent),
  };
  return satData;
}

/**
 * Screenshot and upload the streetview. Called when the screenshot button is clicked.
 */
async function screenshotStreetviewAndUpload(displayToast = true) {
  // Screenshot the streetview
  const imgData = await screenshotStreetview();

  // Get the upload url from the page and POST the data
  const url = document.getElementById("upload_url").getAttribute("data-url");

  console.debug(`Screnshotting streetview and uploading to ${url}`);

  fetch(url, {
    method: "POST",
    mode: "same-origin",
    cache: "no-cache",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken"), // So django accepts the request
    },
    body: JSON.stringify(imgData),
  }).then((resp) => {
    console.debug(resp);
    if (resp.status === 200) {
      svUploaded = true;
      if (displayToast) toasts["screenshot-toast"].show();
    }
  });
}

async function screenshotSatelliteAndUpload(displayToast = true) {
  const satData = await screenshotSatellite();

  const uploadURL = document.getElementById("upload_url").getAttribute("data-url");

  // Upload new satellite image
  fetch(uploadURL, {
    method: "POST",
    mode: "same-origin",
    cache: "no-cache",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken"),
    },
    body: JSON.stringify(satData),
  }).then((resp) => {
    if (resp.status === 200) {
      console.debug("Satellite img uploaded successfully");
      satUploaded = true;
      if (displayToast) toasts["screenshot-toast-sat"].show();
    } else {
      console.debug(`Problem uploading screenshot ${resp}`);
    }
  });
}

/**
 * Grab the last seen satellite image from the page and upload it to the backend.
 * This is called if no satellite images were uploaded when the user submits the form
 */
async function uploadStoredSatelliteImage() {
  // Already JSON strigified
  const satData = localStorage.getItem("sat_data");
  const uploadURL = document.getElementById("upload_url").getAttribute("data-url");

  // Upload new satellite image
  fetch(uploadURL, {
    method: "POST",
    mode: "same-origin",
    cache: "no-cache",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken"),
    },
    body: satData,
  }).then((resp) => {
    if (resp.status === 200) {
      console.debug("Satellite img uploaded successfully");
      satUploaded = true;
    } else {
      console.debug(`Problem uploading screenshot ${resp}`);
    }
  });
}

function setUpDragBar() {
  const dragbar = document.getElementById("dragbar");
  const left = document.getElementById("streetview-container");

  // Check if streetview container was previously resized by the user
  // If not set its size to a default of 50%, otherwise use saved settings
  const saved = localStorage.getItem("savedWidth");

  if (saved) {
    left.style.width = saved;
  } else {
    left.style.width = "50%";
  }

  // Calculate the new width, set the left panel's width and save in local storage
  const resizeOnDrag = (e) => {
    document.selection ? document.selection.empty() : window.getSelection().removeAllRanges();
    const newWidth = e.pageX - dragbar.offsetWidth / 2 + "px";
    left.style.width = newWidth;
    localStorage.setItem("savedWidth", newWidth);
  };

  dragbar.addEventListener("mousedown", () => {
    document.addEventListener("mousemove", resizeOnDrag);
  });

  dragbar.addEventListener("mouseup", () => {
    document.removeEventListener("mousemove", resizeOnDrag);
  });

  document.addEventListener("mouseup", () => {
    document.removeEventListener("mousemove", resizeOnDrag);
  });
}

function setUpButtons() {
  // Screenshot functionality
  const buttonScreenshotStreetview = document.getElementById("btn-screenshot-sv");
  buttonScreenshotStreetview.addEventListener("click", (e) => {
    screenshotStreetviewAndUpload();
  });
  window.addEventListener(
    "keyup",
    async (e) => {
      if (e.code === "Space") {
        console.debug(`spacebar pressed. Target: ${e.target}`);
        if (e.target.nodeName !== "INPUT") {
          await screenshotStreetviewAndUpload();
        }
      }
    },
    false
  );

  const buttonScreenshotSatellite = document.getElementById("btn-screenshot-sat");
  buttonScreenshotSatellite.addEventListener("click", (e) => {
    screenshotSatelliteAndUpload();
  });

  const flagProblemButton = document.getElementById("btn-problem-flag");
  console.debug("Attaching click handler to flag button", flagProblemButton);
  flagProblemButton.addEventListener("click", (e) => {
    e.preventDefault();
    console.debug("Problem flagged");

    const form = document.getElementById("building-submission-form");

    const problemFlagInput = document.createElement("input");
    problemFlagInput.setAttribute("type", "hidden");
    problemFlagInput.setAttribute("name", "problem_flag");
    problemFlagInput.setAttribute("value", "problem_flag");
    form.appendChild(problemFlagInput);
    try {
      const latestViewData = getLatestViewData();
      document.getElementById("latest_view_data").value = JSON.stringify(latestViewData);
    } catch (error) {
      console.error(error);
    } finally {
      form.submit();
    }
  });

  // When user submits form, upload both current streetview and sat views
  // then continue with default behaviour
  document.getElementById("btn-submit-vote").addEventListener("click", async (e) => {
    e.preventDefault();

    const form = document.getElementById("building-submission-form");

    // Check form inputs are valid
    if (!form.checkValidity()) {
      // Create the temporary button, click and remove it
      // This makes the validation comments appear on screen
      const tmpSubmit = document.createElement("button");
      form.appendChild(tmpSubmit);
      tmpSubmit.click();
      form.removeChild(tmpSubmit);
    } else {
      // Check if the user previously screenshotted a streetview
      // If not, we'll save the current streetview now
      if (!svUploaded) {
        console.log("No SV screenshots taken by user, will take one now.");
        await screenshotStreetviewAndUpload(false);
      }
      // Same thing for satellite
      if (!satUploaded) {
        console.log("No Satellite screenshots taken by user, will take one now.");
        await uploadStoredSatelliteImage();
      }
      // Set the latest view data in the form
      document.getElementById("latest_view_data").value = JSON.stringify(getLatestViewData());
      console.debug("Submitting form with latest view data", document.getElementById("latest_view_data").value);
      form.submit();
    }
  });
}

function allInputsEmpty() {
  let allEmpty = true;
  document.querySelectorAll("input").forEach((input) => {
    if ((input.type === "radio" || input.type === "checkbox") && input.checked) return (allEmpty = false);
    if ((input.type === "number" || input.type === "text") && input.value !== "") return (allEmpty = false);
  });
  return allEmpty;
}

/**
 * Set up an event listener to take a screenshot of the satellite view
 * and save it in localstorage when the tab is hidden.
 */
function screenshotSatelliteOnTabHide() {
  // The tab:hide event fires when a tab is to be hidden
  document.getElementById("nav-satellite-tab").addEventListener("tab:hide", async () => {
    // If satellite already uploaded, do not take a screenshot
    if (satUploaded) return;

    console.debug("Hiding satellite tab, and no previous uploaded, storing screenshot in localstorage");
    const satImageData = await screenshotSatellite();
    localStorage.setItem("sat_data", JSON.stringify(satImageData));
  });
}

/**
 * We have to set heights dynamically bc the streetview get loaded at runtime.
 * Setting height = 100% did not work.
 * Otherwise, it will have a height of 0. We don't set an absolute height from the
 * start to accomodate any screen height.
 */
function setStreetviewAndMapContainerHeight() {
  const container = document.getElementById("streetview-and-map-container");
  const windowHeight = window.innerHeight;
  // Leave some space for navbar, tabs and some padding at the bottom
  const navbarHeight = document.getElementById("navbar").offsetHeight;
  const leftTopRow = document.getElementById("left-top-row").offsetHeight;

  // const topRowHeight = document.getElementById("survey-top-row").offsetHeight;
  const topRowHeight = 0;

  // Leave some space at the bottom
  const padding = getComputedStyle(document.getElementById("survey-page-container")).paddingLeft.replace("px", "");
  const containerHeight = windowHeight - navbarHeight - topRowHeight - padding;

  console.debug(
    `Setting container height to ${windowHeight} - ${navbarHeight} - ${padding} - ${topRowHeight} = ${containerHeight}px`
  );
  container.style.height = containerHeight + "px";

  const streetViewHeight = containerHeight - leftTopRow;
  document.getElementById("streetview").style.height = streetViewHeight + "px";
  document.getElementById("nav-survey").style.height = streetViewHeight + "px";
}

function renderSelectedFields(currentListValues) {
  // take current col config
  // use it to re-render the info box

  const allValues = JSON.parse(document.getElementById("bldg_cols_and_values").textContent);

  const infoBox = document.getElementById("bldg-cols-display");
  infoBox.innerHTML = "";

  if (currentListValues.length <= 10) {
    infoBox.classList.remove("grid-cols-2");
    infoBox.classList.add("grid-cols-1");
  } else {
    infoBox.classList.add("grid-cols-2");
    infoBox.classList.remove("grid-cols-1");
  }

  // iterate through current selected fields and recreate the infobox using template and values
  currentListValues.forEach((field) => {
    const node = document.createElement("div");
    node.id = `${field.id}-field`;
    node.classList.add("flex", "gap-2");
    node.innerHTML = `<div class="font-semibold">${field.label}:</div>${allValues[field.id]}`;
    // console.debug(node);
    infoBox.appendChild(node);
  });
}

function setUpDraggableList(draggableListId, defaultValues) {
  const draggableList = document.getElementById(draggableListId);
  const resetButton = draggableList.parentElement.getElementsByClassName("reset-button")[0];
  const selectAllButton = draggableList.parentElement.getElementsByClassName("select-all-button")[0];

  const updateButton = document.getElementById("button-update-fields");
  const updateSettingsUrl = JSON.parse(document.getElementById("update_settings_url").textContent);

  updateButton.addEventListener("click", (e) => {
    e.preventDefault();
    console.debug("update fields");

    const labels = draggableList.querySelectorAll("label");

    const currentListValues = Array.from(labels)
      .map((e) => (e.children[0].checked ? { id: e.children[0].id, label: e.innerText.trim() } : null))
      .filter((x) => x);

    renderSelectedFields(currentListValues);

    const surveySlug = JSON.parse(document.getElementById("survey_slug").textContent);

    fetch(updateSettingsUrl, {
      method: "POST",
      mode: "same-origin",
      cache: "no-cache",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify({
        survey_slug: surveySlug,
        sur_page_bldg_cols: currentListValues,
      }),
    }).then((resp) => {
      console.debug(resp);
      if (resp.status === 200) {
        console.debug("SUCCESS");
      }
    });
  });

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
  setUpDraggableList("draggable-list", defaultBuildingCols);
}

function setUpChangeSurveySelect() {
  const select = document.getElementById("change-survey-select");
  select.addEventListener("change", (e) => {
    window.location.href = e.target.value;
  });
}

function setUpCollapsibleInfoBox() {
  const infoBox = document.getElementById("bldg-cols-display");
  const collapseButton = document.getElementById("infobox-collapse-button");
  const iconCollapse = document.getElementById("infobox-collapse-icon");
  const iconExpand = document.getElementById("infobox-expand-icon");
  const horizontalRule = document.getElementById("infobox-hr");

  const infoBoxSavedExpanded = localStorage.getItem("infobox-collapsed") !== "true";

  if (infoBoxSavedExpanded) {
    console.debug("infox saved as opened", infoBox);
    infoBox.removeAttribute("collapsed");
    infoBox.classList.remove("max-h-0");
    infoBox.classList.add("max-h-[100vh]");
    infoBox.classList.add("grid");

    iconCollapse.classList.remove("hidden");
    horizontalRule.classList.remove("hidden");
    iconExpand.classList.add("hidden");
  }

  collapseButton.addEventListener("click", (e) => {
    const isCollapsed = infoBox.classList.contains("max-h-0");
    if (isCollapsed) {
      // OPENING
      console.debug("OPENING INFOBOX", infoBox);
      infoBox.removeAttribute("collapsed");
      infoBox.classList.remove("max-h-0");
      infoBox.classList.add("max-h-[100vh]");
      infoBox.classList.add("grid");

      iconCollapse.classList.remove("hidden");
      horizontalRule.classList.remove("hidden");
      iconExpand.classList.add("hidden");

      localStorage.setItem("infobox-collapsed", false);
    } else {
      console.debug("CLOSING INFOBOX", infoBox);
      infoBox.setAttribute("collapsed", "");
      infoBox.classList.remove("max-h-[100vh]");
      infoBox.classList.remove("grid");
      infoBox.classList.add("max-h-0");

      iconExpand.classList.remove("hidden");
      iconCollapse.classList.add("hidden");
      horizontalRule.classList.add("hidden");

      localStorage.setItem("infobox-collapsed", true);
    }
  });
}

const tabsActiveClasses = ["bg-opacity-85"];
const tabsInactiveClasses = ["bg-opacity-25"];

document.addEventListener("DOMContentLoaded", function () {
  setUpCollapsibleInfoBox();
  setStreetviewAndMapContainerHeight();
  setUpTabGroups("tabs-right", tabsActiveClasses, tabsInactiveClasses);
  setUpToasts();
  setUpDragBar();
  setUpButtons();
  screenshotSatelliteOnTabHide();
  setUpModals();
  setUpChangeSurveySelect();
  setUpColumnConfig();
});

window.addEventListener("resize", (e) => {
  e.preventDefault();
  setStreetviewAndMapContainerHeight();
});
