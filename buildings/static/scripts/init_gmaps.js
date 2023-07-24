var map;
var sv;
var m_marker;
var sv_marker;

var panoRequest;
var building_coord;


function initMaps() {
  const svService = new google.maps.StreetViewService();

  // If we have already seen the building, get the latest user defined view
  const building_latest_view_data = JSON.parse(document.getElementById('building_latest_view_data').textContent);

  if (building_latest_view_data) {
    panoRequest = {
      pano: building_latest_view_data['sv_pano']
    };

    building_coord = {
      lat: building_latest_view_data['marker_lat'],
      lng: building_latest_view_data['marker_lng']
    };
  }
  // No previously saved view data
  // we will search for the best panorama
  else {
    building_coord = {
      lat: parseFloat("{{ building.lat }}"),
      lng: parseFloat("{{ building.lon }}")
    };

    panoRequest = {
      location: building_coord,
      preference: google.maps.StreetViewPreference.BEST,
      radius: 50,
      source: google.maps.StreetViewSource.OUTDOOR
    };
  }

  function findPanoramaByRadius(panoRequest, building_coord) {

    console.log(`Searching using radius`);

    svService.getPanorama(panoRequest, function(panoData, status) {
      if (status === google.maps.StreetViewStatus.OK) {

        console.log("Found Panorama")
        // Calculate the correct direction the camera must face
        // based on the panorama default location and the building location
        const heading = google.maps.geometry.spherical.computeHeading(panoData.location.latLng, building_coord);

        sv = new google.maps.StreetViewPanorama(
          document.getElementById('streetview'),
          {
              position: building_coord,
              center: building_coord,
              zoom: 0,
              pov: {
                heading: heading,
                pitch: 0,
              },
          });

          sv_marker = new google.maps.Marker({
            position: building_coord,
            map: sv,
            title: "Building",
            draggable: true,
          });

          sv_marker.addListener("dragend", ()=> {
            m_marker.setPosition(sv_marker.getPosition());
          })

          // Setting the panorama after the marker has been defined,
          // otherwise the marker does not show for some reason!
          // https://stackoverflow.com/questions/23498921/google-street-view-with-custom-panorama-and-markers
          sv.setPano(panoData.location.pano);
          window.sv = sv;

          map = new google.maps.Map(document.getElementById("satmap"), {
            center: building_coord,
            mapTypeId: 'satellite',
            zoom: 18,
            // streetViewControl: false,
            rotateControl: false,
            controlSize: 25,
          });

          m_marker = new google.maps.Marker({
            position: building_coord,
            map: map,
            draggable: true,
          });

          map.setStreetView(sv);
          window.map = map;

          // Listen to the marker being dragged and update the one on the streetview to match
          m_marker.addListener("dragend", ()=> {
            sv_marker.setPosition(m_marker.getPosition());
          })
      }
      else {
        var radius = panoRequest.radius
        //Handle other statuses here
        if (radius > 200) {
          console.log(`Could not find a street view within ${radius}m of building! Giving up.`);
          elem = document.createElement('div');
          elem.innerText = "Could not find Panorama for location";
          document.getElementById("streetview").appendChild(elem);
          return false;
        }
        else {
          console.log(`Could not find street view within ${radius}m, trying again within ${radius+50}m.`)
          panoRequest.radius = panoRequest.radius + 50;
          findPanoramaByRadius(panoRequest, building_coord);
        }
      }
    });
    }

  function findPanoramaById(panoRequest, building_coord) {
    console.log(`Searching for panorama using Id: ${panoRequest.pano}`);

    svService.getPanorama(panoRequest, function(panoData, status) {
      if (status === google.maps.StreetViewStatus.OK) {

        const heading = building_latest_view_data['sv_heading'];
        const zoom = building_latest_view_data['sv_zoom'];
        const pitch = building_latest_view_data['sv_pitch'];

        sv = new google.maps.StreetViewPanorama(
          document.getElementById('streetview'),
          {
              position: building_coord,
              center: building_coord,
              zoom: zoom,
              pov: {
                heading: heading,
                pitch: pitch,
              },
          });

          sv_marker = new google.maps.Marker({
            position: building_coord,
            map: sv,
            title: "Building",
            draggable: true,
          });

          sv_marker.addListener("dragend", ()=> {
            m_marker.setPosition(sv_marker.getPosition());
          })

          // Setting the panorama after the marker has been defined,
          // otherwise the marker does not show for some reason!
          // https://stackoverflow.com/questions/23498921/google-street-view-with-custom-panorama-and-markers
          sv.setPano(panoData.location.pano);
          window.sv = sv;

          map = new google.maps.Map(document.getElementById("satmap"), {
            center: building_coord,
            mapTypeId: 'satellite',
            zoom: 18,
            // streetViewControl: false,
            rotateControl: false,
            controlSize: 25,
          });

          m_marker = new google.maps.Marker({
            position: building_coord,
            map: map,
            draggable: true,
          });

          map.setStreetView(sv);
          window.map = map;

          // Listen to the marker being dragged and update the one on the streetview to match
          m_marker.addListener("dragend", ()=> {
            sv_marker.setPosition(m_marker.getPosition());
          })
      }
      else {
        console.log(`Could not find panorama id ${panoRequest.pano}. Searching using radius`);
        // Making a radius search request
        panoRequest = {
          location: building_coord,
          preference: google.maps.StreetViewPreference.BEST,
          radius: 50,
          source: google.maps.StreetViewSource.OUTDOOR
        };
        return findPanoramaByRadius(panoRequest, building_coord);
      }
    });
  }

  if (building_latest_view_data)
    findPanoramaById(panoRequest, building_coord);
    else
    findPanoramaByRadius(panoRequest, building_coord);
}

window.initMaps = initMaps;