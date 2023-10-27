// Retrieve some data passed to the script by django template
const dataset = document.currentScript.dataset;

(async function initMap() {
  const { StreetViewService } = await google.maps.importLibrary("streetView");
  const svService = new StreetViewService();

  // If we have already seen the evaluation unit, get the latest user defined view
  const latestViewData = JSON.parse(
    document.getElementById("latest_view_data_value").textContent
  );

  let panoRequest, evalUnitCoord;
  // Latest view data includes a panorama ID and marker coords
  if (latestViewData) {
    evalUnitCoord = {
      lat: latestViewData["marker_lat"],
      lng: latestViewData["marker_lng"],
    };
    panoRequest = {
      pano: latestViewData["sv_pano"],
    };
  }
  // No previously saved view data
  // we will search for the best panorama
  else {

    evalUnitCoord = JSON.parse(document.getElementById("eval_unit_coords").textContent);

    if (!evalUnitCoord)
      console.debug('No eval unit coords found')
    
    panoRequest = {
      location: evalUnitCoord,
      preference: google.maps.StreetViewPreference.NEAREST,
      radius: 25,
      source: google.maps.StreetViewSource.OUTDOOR,
    };
  }

  findPanorama(svService, latestViewData, panoRequest, evalUnitCoord);
})();


/**
 * Take an array of available panoramas and their dates
 * and return a list of <option> elements for a drop-down,
 * with the date closest to targetDate selected.
 */
function generateTimeTravelOptions(panoArray, targetDate) {
  const options = [];

  // Convert the selected date string in YYYY-mm format to a Date
  const dateSplit = targetDate.split("-");
  const selectedPanoDate = new Date(
    dateSplit[0],
    parseInt(dateSplit[1]) - 1,
    1
  );

  let minDiff = Infinity;
  let closestPanoEl, closestPanoDate;

  // Assuming the objects have only 2 keys: "pano" and the variably-named date key
  const dateKey = Object.keys(panoArray[0]).filter((e) => {
    return e !== "pano";
  })[0];

  // Iterate through the available times in reverse
  // order so the most recent date appears at the top
  panoArray.reverse().forEach((el) => {
    let option = document.createElement("option");
    option.value = option.id = el["pano"];

    const date = el[dateKey];
    if (!date) {
      console.error("Could not get date from element: ", el);
      return;
    }
    // User visible text of the dropdown option
    option.innerText = date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
    });
    // Keep track of the smallest absolute difference between
    // the selected date and the avaiable dates
    let diff = Math.abs(selectedPanoDate - date);

    if (diff < minDiff) {
      minDiff = diff;
      closestPanoEl = option;
      closestPanoDate = `${date.toISOString().split("T")[0].substring(0, 7)}`;
    }
    options.push(option);
  });

  // Set the minimum difference element to selected
  closestPanoEl.selected = true;

  return {
    options,
    closestPanoId: closestPanoEl.value,
    closestPanoDate: closestPanoDate,
  };
}

/**
 * Register a drag and drop listener on the pegman
 * We can't just document.querySelector() it easily because
 * we need to wait for it to have been instantiated first
 */
function attachEventsToPegman(mutationList, _) {
  for (const mutation of mutationList) {
    if (
      mutation.target.getAttribute("src") ===
      "https://maps.gstatic.com/mapfiles/transparent.png"
    ) {
      // Without this, we easily get hundreds of listeners attached
      if (mutation.target.getAttribute("listenersSet")) return;

      console.debug("Attaching events on pegman");
      // Save a reference if needed later
      window.pegman = mutation.target;

      // Add event listeners to the element
      mutation.target.addEventListener("mousedown", () => {
        window.pegmanDropped = false;
        window.pegmanMousedown = true;
      });
      mutation.target.addEventListener("mouseup", () => {
        if (window.pegmanMousedown) {
          console.debug('pegman dropped');
          window.pegmanMousedown = false;
          window.pegmanDropped = true;
        }
      });
      mutation.target.setAttribute("listenersSet", "true");
    }
  }
}

/**
 * Use this to print all the mutations for debugging etc.
 */
function printMutationsCallback(mutationList, _) {
  for (const mutation of mutationList) {
    console.debug(mutation);
  }
}

function sleep(time) {
  return new Promise((resolve) => setTimeout(resolve, time));
}

async function findPanorama(svService, latestViewData, panoRequest, evalUnitCoord) {
  const { Map } = await google.maps.importLibrary("maps");
  const { event } = await google.maps.importLibrary("core");
  const { Marker } = await google.maps.importLibrary("marker");
  const { spherical } = await google.maps.importLibrary("geometry");
  const { StreetViewStatus, StreetViewPanorama } = await google.maps.importLibrary("streetView");

  // Send a request to the panorama service
  svService.getPanorama(panoRequest, (data, status) => {
    if (status === StreetViewStatus.OK) {

      if (panoRequest.radius) {
        console.debug(`Status ${status}: panorama found within ${panoRequest.radius}m`);
      }
      else {
        console.debug(`Status ${status}: panorama ${panoRequest.pano} found`);
      }

      let heading;
      let zoom = pitch = 0;

      if (latestViewData) {
        heading = latestViewData["sv_heading"];
        zoom = latestViewData["sv_zoom"];
        pitch = latestViewData["sv_pitch"];
      } else {
        heading = spherical.computeHeading(data.location.latLng, evalUnitCoord);
      }

      const sv = new StreetViewPanorama(
        document.getElementById("streetview"),
        {
          position: evalUnitCoord,
          center: evalUnitCoord,
          zoom: zoom,
          pov: {
            heading: heading,
            pitch: pitch,
          },
          imageDateControl: true,
          fullscreenControl: false,
          motionTracking: false,
          motionTrackingControl: false,
        }
      );
      sv.setPano(data.location.pano);
      
      const map = new Map(document.getElementById("satellite"), {
        center: evalUnitCoord,
        mapTypeId: "hybrid",
        zoom: 18,
        controlSize: 25,
        fullscreenControl: false,
        mapTypeControl: false,
      });
      map.setStreetView(sv);


      // init markers
      const sv_marker = new Marker({
        position: evalUnitCoord,
        map: sv,
        draggable: true,
      });
      const m_marker = new Marker({
        position: evalUnitCoord,
        map: map,
        draggable: true,
      });

      // Set ondrag event listeners for both markers
      // Dragging any of them will instantly update the other
      sv_marker.addListener("drag", () => {
        m_marker.setPosition(sv_marker.getPosition());
      });
      m_marker.addListener("drag", () => {
        sv_marker.setPosition(m_marker.getPosition());
      });


      // Export all of these to be able to access them from other scripts
      window.sv = sv;
      window.map = map;
      window.sv_marker = sv_marker;
      window.m_marker = m_marker;
      window.lastPanoDate = data.imageDate;
      window.lastPanoId = data.location.pano;
      
      // Generate the initial time travel dropdown
      const { options } = generateTimeTravelOptions(data.time, data.imageDate);
      // Set the time travel select visible only once the streetview is loaded
      // Otherwise it shows on the side of the screen before ending in the right place
      document.getElementById("time-travel-select").append(...options);
      document.getElementById("time-travel-container").style.display = "flex";

      // Register a mutation observer to attach events to the pegman
      const observer = new MutationObserver(attachEventsToPegman);
      const config = { attributes: true, subtree: true };
      observer.observe(document.getElementById("satellite"), config);

      // Custom event launched when pegman is dropped and we need a manual pano set
      sv.addListener("pano_change_needed", () => {
        sleep(0).then(() => {
          sv.setPano(window.shouldBePano);
          console.debug(`Changed pano to ${window.shouldBePano}`);
        });
      });

      sv.addListener("pano_changed", () => {
        console.debug("pano_changed");

        const newPanoId = sv.getPano();

        // Detect when we need to change the panorama after a pegman drop
        if (window.panoChangeNeeded) {
          window.panoChangeNeeded = false;
          console.debug(`Starting change to ${window.shouldBePano}`);
          // trigger custom event
          return event.trigger(sv, "pano_change_needed");
        }
        // Skip duplicate events
        if (window.lastPanoId === newPanoId) {
          console.debug(`Extra event on ${window.lastPanoId}, returning!`);
          return;
        }
        // Get more info on the pano from StreetViewService
        svService.getPanorama({ pano: newPanoId }, (data, status) => {
          if (status === StreetViewStatus.OK) {
            console.debug(`New pano: ${newPanoId} - (${data.imageDate})`);
            console.debug(`Last pano: ${window.lastPanoId} - (${window.lastPanoDate})`);

            // If the pegman was just dropped and the new panorama's date is not equal
            // to the last panorama's date, we manually change the panorama to the
            // one closest in time to the pre-pegman drop date.
            if (window.pegmanDropped && data.imageDate !== window.lastPanoDate)
            {
              window.pegmanDropped = false;
              console.debug("Pegman dropped and new pano date not equal to last.");

              // Get the ID of the panorama closest in time to the last date
              const { closestPanoId, closestPanoDate } = generateTimeTravelOptions(data.time, window.lastPanoDate);
              console.debug(`Will change to closest pano ${closestPanoId} (${closestPanoDate})`);

              // Set this variable so we know we need to change the pano
              window.panoChangeNeeded = true;
              window.shouldBePano = closestPanoId;
              return;
            }
            console.debug(`Generating dropdown options for new pano`);

            const { options } = generateTimeTravelOptions(
              data.time,
              data.imageDate
            );
            document.getElementById("time-travel-select")
                    .replaceChildren(...options);

            // save the current pano date for next time
            window.lastPanoDate = data.imageDate;
            window.lastPanoId = newPanoId;
          }
        });
      });


    }
    // Check if we were doing a radius search
    else if (panoRequest.radius) {
      var radius = panoRequest.radius;

      if (radius >= 100) {
        console.debug(
          `Status ${status}: Could not find panorama within ${radius}m! Giving up.`
        );
        elem = document.createElement("div");
        elem.innerText = `Could not find panorama within ${radius}m.`;
        document.getElementById("streetview").appendChild(elem);
      } else {
        panoRequest.radius += 25;
        console.debug(
          `Status ${status}: could not find panorama within ${radius}m, trying ${panoRequest.radius}m.`
        );

        return findPanorama(
          svService,
          latestViewData,
          panoRequest,
          evalUnitCoord
        );
      }
    }
    // Else we were doing an ID search - switch to radius search
    else {
      console.debug(`Could not find pano ${panoRequest.pano}. Switching to radius search.`);
      
      // Making a radius search request
      panoRequest = {
        location: evalUnitCoord,
        preference: google.maps.StreetViewPreference.NEAREST,
        radius: 25,
        source: google.maps.StreetViewSource.OUTDOOR,
      };
      return findPanorama(
        svService,
        latestViewData,
        panoRequest,
        evalUnitCoord
      );
    }
  });
}
