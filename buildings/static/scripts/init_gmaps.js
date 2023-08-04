// Retrieve some data passed to the script by the template
var data = document.currentScript.dataset;


function findPanorama(svService, latestViewData, panoRequest, buildingCoord) {
  console.log(`Searching for panorama: ${JSON.stringify(panoRequest)}`);

  // Send a request to the panorama service
  svService.getPanorama(panoRequest, function(panoData, status) 
  {
    if (status === google.maps.StreetViewStatus.OK) {
      console.log(`Status ${status}: panorama found.`);

      let heading, zoom, pitch;
      
      if (latestViewData) {
        heading = latestViewData['sv_heading'];
        zoom = latestViewData['sv_zoom'];
        pitch = latestViewData['sv_pitch'];
      } else {
        heading = google.maps.geometry.spherical.computeHeading(panoData.location.latLng, buildingCoord);
        zoom = 0;
        pitch = 0;
      }

      const sv = new google.maps.StreetViewPanorama(
        document.getElementById('streetview'),
        {
            position: buildingCoord,
            center: buildingCoord,
            zoom: zoom,
            pov: {
              heading: heading,
              pitch: pitch,
            },
        });

      const sv_marker = new google.maps.Marker({
        position: buildingCoord,
        map: sv,
        title: "Building",
        draggable: true,
      });

      // Setting the panorama after the marker has been defined,
      // otherwise the marker does not show for some reason!
      // https://stackoverflow.com/questions/23498921/google-street-view-with-custom-panorama-and-markers
      sv.setPano(panoData.location.pano);
      
      const map = new google.maps.Map(document.getElementById("satmap"), {
        center: buildingCoord,
        mapTypeId: 'satellite',
        zoom: 18,
        // streetViewControl: false,
        rotateControl: false,
        controlSize: 25,
      });
      
      const m_marker = new google.maps.Marker({
        position: buildingCoord,
        map: map,
        draggable: true,
      });

      map.setStreetView(sv);

      // Export all of these to be able to access them from other scripts
      window.sv = sv;
      window.map = map;
      window.sv_marker = sv_marker;
      window.m_marker = m_marker;

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
        return findPanorama(svService, latestViewData, panoRequest, buildingCoord);
      }
    }
    // Else we were doing an ID search - switch to radius search
    else {
      console.log(`Could not find panorama id ${panoRequest.pano}. Switching to radius search.`);
      // Making a radius search request
      panoRequest = {
        location: buildingCoord,
        preference: google.maps.StreetViewPreference.BEST,
        radius: 50,
        source: google.maps.StreetViewSource.OUTDOOR
      };
      return findPanorama(svService, latestViewData, panoRequest, buildingCoord);
    }
  });
}

function initMaps() {

  let panoRequest,
      buildingCoord;
  
  const svService = new google.maps.StreetViewService();

  // If we have already seen the building, get the latest user defined view
  const latestViewData = JSON.parse(document.getElementById('latest_view_data').textContent);

  // Latest view data includes a panorama ID and marker coords
  if (latestViewData) {
    buildingCoord = {
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
    buildingCoord = {
      lat: parseFloat(data.buildingLat),
      lng: parseFloat(data.buildingLon),
    };

    panoRequest = {
      location: buildingCoord,
      preference: google.maps.StreetViewPreference.BEST,
      radius: 50,
      source: google.maps.StreetViewSource.OUTDOOR
    };
  }

  return findPanorama(svService, latestViewData, panoRequest, buildingCoord);
}

window.initMaps = initMaps;

// Note that we set the above function as callback
const gmapsURL = `https://maps.googleapis.com/maps/api/js?key=${data.gmapsApiKey}&libraries=geometry&callback=initMaps&v=weekly`;

// Create the script tag, set the appropriate attributes
var script = document.createElement('script');
script.src = gmapsURL;
// Append the 'script' element to 'head'
document.head.appendChild(script);

