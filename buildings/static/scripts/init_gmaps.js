// Retrieve some data passed to the script by django template
var data = document.currentScript.dataset;


function timeTravel(panoId) {
  window.sv.setPano(panoId);
}


/* 
* Get the date key.
* Assumptions:
* - All elements of the array have the same keys
* - The date key immediately follows the panorama ID key
* In practice, always observed 2 keys per element
* and both 'Qm' and 'yp' as date keys. No idea if there are others.
*/
function getPanoDateKey(panoArray) {
  return Object.keys(panoArray[0]).filter((e) => {return e !== 'pano'})[0];
}


/*
* Take an array of available panoramas and their dates
* and return a list of <option> elements for a drop-down
*/
function generateOptionsAndReturnClosestPano(panoArray, selectedDate) {
  const options = [];
  const dateSplit = selectedDate.split('-');

  const selectedPanoDate = new Date(dateSplit[0], parseInt(dateSplit[1]) - 1, 1);

  let minDiff = Infinity;
  let minDiffElem;

  const dateKey = getPanoDateKey(panoArray);

  panoArray.reverse().forEach((el, _) => {
    
    let option = document.createElement('option');
    option.value = option.id = el['pano'];
    
    const date = el[dateKey];
    option.innerText = date.toLocaleDateString('en-US', { year:"numeric", month:"long"});
    
    if (!date) {
      console.debug('Could not get date from element: ', el);
    }
    
    // Keep track of the smallest absolute difference between dates
    let diff = Math.abs(selectedPanoDate - date);

    if (diff < minDiff) {
      minDiff = diff;
      minDiffElem = option;
    }
    options.push(option);
  });

  // Set the minimum difference element to selected
  minDiffElem.selected = true;

  return {
    options: options,
    closestPanoByDate: minDiffElem.value,
  }
}



/*
* Function to hide certain things on the streetview as they get loaded in
* You can console.debug() all the mutations first to know which ones to select.
*
* Also find the Pegman and register a drag and drop listener 
*/
function mutationObserverCallback(mutationList, _) {
  for (const mutation of mutationList) {
    if (
      mutation.target.getAttribute('title') === "Open this area in Google Maps (opens a new window)" 
    ) {
        mutation.target.style.display = "none";
    }
    else if (mutation.target.getAttribute('src') === 'https://maps.gstatic.com/mapfiles/transparent.png')
    {
      // Save a reference if needed later
      window.pegman = mutation.target;

      // Add event listeners to the element
      mutation.target.addEventListener('mousedown', (e) => {
        window.pegmanDropped = false;
        window.pegmanMousedown = true;
      });
      mutation.target.addEventListener('mouseup', (e) => {
        if (window.pegmanMousedown) {
          window.pegmanMousedown = false;
          window.pegmanDropped = true;
        }
      });
    }
  }
};

function printMutationsCallback(mutationList, _) {
  for (const mutation of mutationList) {
    console.debug(mutation)
  }
};

function sleep(time) {
  return new Promise((resolve) => setTimeout(resolve, time));
}


function findPanorama(svService, latestViewData, panoRequest, evalUnitCoord) {
  // Send a request to the panorama service
  svService.getPanorama(panoRequest, function(panoData, status) 
  {
    if (status === google.maps.StreetViewStatus.OK) 
    {
      if (panoRequest.radius) {
        console.debug(`Status ${status}: panorama found within ${panoRequest.radius}m`);
      } else{
        console.debug(`Status ${status}: panorama ${panoRequest.pano} found`);
      }
      let heading, zoom, pitch;
      
      if (latestViewData) {
        heading = latestViewData['sv_heading'];
        zoom = latestViewData['sv_zoom'];
        pitch = latestViewData['sv_pitch'];
      } else {
        heading = google.maps.geometry.spherical.computeHeading(panoData.location.latLng, evalUnitCoord);
        zoom = 0;
        pitch = 0;
      }

      const sv = new google.maps.StreetViewPanorama(
        document.getElementById('streetview'),
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
        });
      
      const sv_marker = new google.maps.Marker({
        position: evalUnitCoord,
        map: sv,
        title: "Building",
        draggable: true,
      });

      // Setting the panorama after the marker has been defined,
      // otherwise the marker does not show for some reason!
      // https://stackoverflow.com/questions/23498921/google-street-view-with-custom-panorama-and-markers
      sv.setPano(panoData.location.pano);
      
      const map = new google.maps.Map(document.getElementById("satmap"), {
        center: evalUnitCoord,
        mapTypeId: 'hybrid',
        zoom: 18,
        controlSize: 25,
        fullscreenControl: false,
        mapTypeControl: false,
      });
      
      const m_marker = new google.maps.Marker({
        position: evalUnitCoord,
        map: map,
        draggable: true,
      });

      map.setStreetView(sv);

      // Export all of these to be able to access them from other scripts
      window.sv = sv;
      window.map = map;
      window.sv_marker = sv_marker;
      window.m_marker = m_marker;
      window.lastSVImageDate = panoData.imageDate;
      window.lastPanoChanged = panoData.location.pano;

      // Set the time travel select visible only once the streetview is loaded
      // Otherwise it shows on the side of the screen before ending in the right place
      const {options} = generateOptionsAndReturnClosestPano(panoData.time, panoData.imageDate);
      document.getElementById('time-travel-select').append(...options);

      google.maps.event.addListenerOnce(map, 'idle', () => {
        document.getElementById('time-travel-container').style.display = 'flex';
      });

      
      // Register a mutation observer to remove the Goog logo from streetview/satmap
      // (It showed up a bit in the screenshots) - could also remove it in html2canvas
      const observer = new MutationObserver(mutationObserverCallback);
      const config = {attributes: true, childList: true, subtree: true };
      observer.observe(document.getElementById('streetview'), config);
      observer.observe(document.getElementById('satmap'), config);
      
      // Custom event launched when pegman is dropped and we need a manual pano set
      sv.addListener('manual_pano_set', () => {
        sleep(0).then(() => {
          console.debug(`detected manual pano set needed to ${window.shouldBePano}`);
          sv.setPano(window.shouldBePano);
        })
      });

      // 
      sv.addListener('pano_changed', () => {
        console.debug('pano_changed');
        let panoId = sv.getPano();
      
        if (window.doingManualPanoSet) {
          window.doingManualPanoSet = false;
          console.debug(`Manual set extra event on ${window.lastPanoChanged}, triggering manual_pano_set event!`);
          // trigger custom event
          return google.maps.event.trigger(sv, 'manual_pano_set');
        }
        // Skip duplicate events
        if (window.lastPanoChanged === panoId ) {
          console.debug(`Extra event on ${window.lastPanoChanged}, returning!`)
          return;
        }
        
        // Get more info on the pano from StreetViewService
        svService.getPanorama({pano: panoId}, function(panoData, status) 
        {
          if (status === google.maps.StreetViewStatus.OK) {
            console.debug(`Current pano: ${window.lastPanoChanged} - (${window.lastSVImageDate})`)
            console.debug(`Pano changed to: ${panoId} - (${panoData.imageDate})`);
            
            if (panoData.imageDate !== window.lastSVImageDate) {
              if (window.pegmanDropped) {
                window.pegmanDropped = false;
                console.debug("Pegman dropped and new pano date not equal to last.")
                // Need to manually set
                var {options, closestPanoByDate} = generateOptionsAndReturnClosestPano(panoData.time, window.lastSVImageDate);
                console.debug(`should be pano ${closestPanoByDate}`);
                window.doingManualPanoSet = true;
                window.shouldBePano = closestPanoByDate;
              }
            }
            console.debug(`Generating options for new pano ${panoData.imageDate}`);
            var {options} = generateOptionsAndReturnClosestPano(panoData.time, panoData.imageDate);
            document.getElementById('time-travel-select').replaceChildren(...options);
            // save the current image date for next time
            window.lastSVImageDate = panoData.imageDate;
            console.debug(`Setting last pano to ${panoId}`);
            window.lastPanoChanged = panoId;
          }
        });
      });

      // Set ondrag event listeners for both markers
      // Dragging any of them will instantly update the other
      sv_marker.addListener("drag", ()=> {
        m_marker.setPosition(sv_marker.getPosition());
      });
      m_marker.addListener("drag", ()=> {
        sv_marker.setPosition(m_marker.getPosition());
      });

      return;
    }
    // Check if we were doing a radius search 
    else if (panoRequest.radius) {
      
      var radius = panoRequest.radius

      if (radius >= 200) {
        console.debug(`Status ${status}: Could not find panorama within ${radius}m! Giving up.`);
        elem = document.createElement('div');
        elem.innerText = `Could not find panorama within ${radius}m.`;
        document.getElementById("streetview").appendChild(elem);
        return;
      }
      else {
        if (panoRequest.radius < 100) {
          panoRequest.radius += 25;
        }
        else {
          panoRequest.radius += 50;
        }
        console.debug(`Status ${status}: could not find panorama within ${radius}m, trying ${panoRequest.radius}m.`);

        return findPanorama(svService, latestViewData, panoRequest, evalUnitCoord);
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
        source: google.maps.StreetViewSource.OUTDOOR
      };
      return findPanorama(svService, latestViewData, panoRequest, evalUnitCoord);
    }
  });
}

function initMaps() {

  let panoRequest,
      evalUnitCoord;
  
  const svService = new google.maps.StreetViewService();

  // If we have already seen the evaluation unit, get the latest user defined view
  const latestViewData = JSON.parse(document.getElementById('latest_view_data_value').textContent);

  // Latest view data includes a panorama ID and marker coords
  if (latestViewData) {
    evalUnitCoord = {
      lat: latestViewData['marker_lat'],
      lng: latestViewData['marker_lng']
    };

    panoRequest = {
      pano: latestViewData['sv_pano']
    };
  }
  // No previously saved view data
  // we will search for the best panorama
  else {
    evalUnitCoord = { 
      lat: parseFloat(data.evalUnitLat),
      lng: parseFloat(data.evalUnitLng),
    };

    panoRequest = {
      location: evalUnitCoord,
      preference: google.maps.StreetViewPreference.NEAREST,
      radius: 25,
      source: google.maps.StreetViewSource.OUTDOOR
    };
  }

  findPanorama(svService, latestViewData, panoRequest, evalUnitCoord);
}



window.initMaps = initMaps;

// Note that we set the above function as callback
const gmapsURL = `https://maps.googleapis.com/maps/api/js?key=${data.gmapsApiKey}&libraries=geometry&callback=initMaps&v=3.53`;

// Create the script tag, set the appropriate attributes
var script = document.createElement('script');
script.src = gmapsURL;
// Append the 'script' element to 'head'
document.head.appendChild(script);
