// Retrieve some data passed to the script by django template
var data = document.currentScript.dataset;


function timeTravel(panoId) {
  window.sv.setPano(panoId);
}

/*
* Take an array of available panoramas and their dates
* and return a list of <option> elements for a drop-down
*/
function generateSelectOptions(panoArray, selectedDate) {
  const options = [];
  const dateSplit = selectedDate.split('-');

  const selectedPanoDate = 
    new Date(Date.UTC(dateSplit[0], dateSplit[1], 1))
      .toLocaleDateString('en-US', { year:"numeric", month:"long"});
  
  /* 
  * Get the date key.
  * Assumptions:
  * - All elements of the array have the same keys
  * - The date key immediately follows the panorama ID key
  * In practice, always observed 2 keys per element
  * and both 'Qm' and 'yp' as date keys. No idea if there are others.
  */
  const dateKey = Object.keys(panoArray[0]).filter((e) => {return e !== 'pano'})[0];

  panoArray.reverse().forEach((el, i) => {
    
    let option = document.createElement('option');
    option.value = el['pano'];
    
    const date = new Date(el[dateKey]).toLocaleDateString('en-US', { year:"numeric", month:"long"});
    option.innerText = date;
    
    if (!date) {
      console.log('Could not get date from element: ', el);
    }
    
    // Match the dates as strings
    // I couldn't find how to declare a Date as UTC easily
    // Format is 'full-month year'
    if (date === selectedPanoDate) {
      option.selected = true;
    }
    options.push(option);
  });
  return options;
}


/*
* Function to hide certain things on the streetview as they get loaded in
* You can console.log() all the mutations first to know which ones to select.
*/
function mutationCallbackHideGoogleLogo(mutationList, _) {
  for (const mutation of mutationList) {
    if (
      mutation.target.getAttribute('title') === "Open this area in Google Maps (opens a new window)" 
    ) {
        mutation.target.style.display = "none";
    }
  }
};


function findPanorama(svService, latestViewData, panoRequest, evalUnitCoord) {
  console.log(`Searching for panorama: ${JSON.stringify(panoRequest)}`);

  // Send a request to the panorama service
  svService.getPanorama(panoRequest, function(panoData, status) 
  {
    if (status === google.maps.StreetViewStatus.OK) 
    {
      console.log(`Status ${status}: panorama found.`);

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
        mapTypeId: 'satellite',
        zoom: 18,
        controlSize: 25,
        fullscreenControl: false,
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
      
      // Set the time travel select visible only once the streetview is loaded
      // Otherwise it shows on the side of the screen before ending in the right place
      google.maps.event.addListenerOnce(map, 'idle', () => {
        const options = generateSelectOptions(panoData.time, panoData.imageDate);
        document.getElementById('time-travel-select').append(...options);
        document.getElementById('time-travel-container').style.display = 'flex';
      });

      
      // Register a mutation observer to filter out elements
      const observer = new MutationObserver(mutationCallbackHideGoogleLogo);
      const config = { attributes: true, childList: true, subtree: true };
      observer.observe(document.getElementById('streetview'), config);
      observer.observe(document.getElementById('satmap'), config);


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
      //Handle other statuses here
      if (radius > 200) {
        console.log(`Status ${status}: Could not find panorama within ${radius}m! Giving up.`);
        elem = document.createElement('div');
        elem.innerText = "Could not find Panorama for location";
        document.getElementById("streetview").appendChild(elem);
        return;
      }
      else {
        console.log(`Status ${status}: could not find panorama within ${radius}m, trying ${radius+50}m.`)
        panoRequest.radius += 50;
        return findPanorama(svService, latestViewData, panoRequest, evalUnitCoord);
      }
    }
    // Else we were doing an ID search - switch to radius search
    else {
      console.log(`Could not find panorama id ${panoRequest.pano}. Switching to radius search.`);
      // Making a radius search request
      panoRequest = {
        location: evalUnitCoord,
        preference: google.maps.StreetViewPreference.BEST,
        radius: 50,
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
  const latestViewData = JSON.parse(document.getElementById('latest_view_data').textContent);

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
      preference: google.maps.StreetViewPreference.BEST,
      radius: 50,
      source: google.maps.StreetViewSource.OUTDOOR
    };
  }

  findPanorama(svService, latestViewData, panoRequest, evalUnitCoord);
}



window.initMaps = initMaps;

// Note that we set the above function as callback
const gmapsURL = `https://maps.googleapis.com/maps/api/js?key=${data.gmapsApiKey}&libraries=geometry&callback=initMaps&v=weekly`;

// Create the script tag, set the appropriate attributes
var script = document.createElement('script');
script.src = gmapsURL;
// Append the 'script' element to 'head'
document.head.appendChild(script);
