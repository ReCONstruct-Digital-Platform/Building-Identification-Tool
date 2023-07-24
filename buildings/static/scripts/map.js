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
            logging: true,
            ignoreElements: (el) => {
                // The following hides unwanted controls, copyrights, pins etc. on the maps and streetview canvases
                return el.classList.contains("gmnoprint") || el.classList.contains("gm-style-cc")
                || el.id === 'gmimap1' || el.tagName === 'BUTTON' 
                || el.getAttribute('src') === 'https://maps.gstatic.com/mapfiles/api-3/images/spotlight-poi3_hdpi.png'
                || el.getAttribute('src') === 'https://maps.gstatic.com/mapfiles/api-3/images/spotlight-poi3.png'
            },
        }
    ).then(canvas => {
        // For testing - appends the images to the web page
        document.body.appendChild(canvas);
        // Convert the image to a dataURL for uploading to the backend
        return canvas.toDataURL('image/png');
    })
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

    if (sv_saved_width == null){
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
    $('#btn-screenshot').click(async (e) => {
        e.preventDefault();
        
        const imgData = {
            streetview: await screenshot('streetview'),
            satellite: await screenshot('satmap'),
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
    });

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
            // Go on to the normal processing
            $('#building-submition-form').submit();
        }

    })

    // When user submits form, upload both current streetview and sat views
    // then continue with default behaviour
    $('#btn-submit-vote').click(async (e) => {

        e.preventDefault();
        form = $('#building-submition-form')[0];
        
        if (!form.checkValidity()) {
            // Create the temporary button, click and remove it
            var tmpSubmit = document.createElement('button')
            form.appendChild(tmpSubmit)
            tmpSubmit.click()
            form.removeChild(tmpSubmit)
        } else {
            const imgData = {
                streetview: await screenshot('streetview'),
                satellite: await screenshot('satmap'),
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
        
              $('#building-submition-form').submit();
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
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}


var change_width = parseFloat(screen.width) * 0.5;
// console.log('begin: ' + nav_tabwidth);
 //calculate the height of text bar dynamically

function SubquestionOne(){
    $("#Rowhouse").attr('required', '');
    $("#Large-multi-family").attr('required', '');
    var requiredCheckboxes = $('.subquestion1 :radio[required]');
    requiredCheckboxes.change(function(){
        if(requiredCheckboxes.is(':checked')) {
            requiredCheckboxes.removeAttr('required');
        } else {
            requiredCheckboxes.attr('required', 'required');
        }
    });
};

function SubquestionTwo(){
    $("#Community-center").attr('required', '');
    $("#Hockey-arena").attr('required', '');
    $("#Library").attr('required', '');
    $("#Sports").attr('required', '');
    $("#Unsure4").attr('required', '');
    var requiredCheck= $('.subquestion2 :radio[required]');
    requiredCheck.change(function(){
        if(requiredCheck.is(':checked')) {
            requiredCheck.removeAttr('required');
        } else {
            requiredCheck.attr('required', 'required');
        }
    });
};

$(document).ready(function() {

    // what does this do ?

    $('#streetview').bind('DOMSubtreeModified', function(){
        var dynheight = $('#streetview').height();
        //console.log('changed dynHeight: ' + dynheight);
        var nav_tabheight = $('#nav-tab').height();
        var textHeight = dynheight - nav_tabheight ;

        var dynwidth =  $('#streetview').width();
        var screenwidth = screen.width;
        change_width = screenwidth - dynwidth ;
        //console.log(change_width);
        //var nav_tabwidth = $('#nav-tab').width();
        //console.log('dynwidth: ' + nav_tabwidth);
        if (parseFloat(change_width) < 500)
            change_width = "500px";

        window.onload = (function () {
            document.getElementById("scroll").style.height = textHeight + "px";
            //
        })();
    });

  $("input[name$='Q4']").click(function() {
      var test = $(this).val();
      if (test[2] == '1') {
          // Check whether this is a top-level question, and if so,
          // hide all the subquestions (and uncheck responses)
          $('.desc').hide();
          $('input').not('[value='+test+']').removeAttr('checked');
      } else {
          // Find the ID of this question
          var parent_q = $($(this).parents('.desc')[0]).attr('id');
          var type = parent_q.substring(0,2); // Get the type, such as "in"
          var level = parent_q.substring(2);  // Get the level, such as 1
          $(".desc").each(function(elt_index, elt) {
              // Hide each question/answer with either a different type or a higher ID.
              var e_id = $(elt).attr('id');
              if(e_id.substring(0,2) != type || e_id.substring(2) > level) {
                  $(elt).hide();
                  $(elt).children('input').removeAttr('checked');
              }
          });
      }
      $("#"+test).show();
      //document.getElementById("scroll").style.width = change_width + "px";
  });
});

$(document).ready(function(){
  $("input[name$='Q5']").click(function() {
      var test = $(this).val();
      if (test[2] == '1') {
          // Check whether this is a top-level question, and if so,
          // hide all the subquestions (and uncheck responses)
          $('.desc2').hide();
          $('input').not('[value='+test+']').removeAttr('checked');
      } else {
          // Find the ID of this question
          var parent_q = $($(this).parents('.desc2')[0]).attr('id');
          var type = parent_q.substring(0,2); // Get the type, such as "in"
          var level = parent_q.substring(2);  // Get the level, such as 1
          $(".desc2").each(function(elt_index, elt) {
              // Hide each question/answer with either a different type or a higher ID.
              var e_id = $(elt).attr('id');
              if(e_id.substring(0,2) != type || e_id.substring(2) > level) {
                  $(elt).hide();
                  $(elt).children('input').removeAttr('checked');
              }
          });
      }
      $("#"+test).show();
  });
});

$(document).ready(function(){
  $("input[name$='Q7']").click(function() {
      var test = $(this).val();
      if (test[2] == '1') {
          // Check whether this is a top-level question, and if so,
          // hide all the subquestions (and uncheck responses)
          $('.desc5').hide();
          $('input').not('[value='+test+']').removeAttr('checked');
      } else {
          // Find the ID of this question
          var parent_q = $($(this).parents('.desc5')[0]).attr('id');
          var type = parent_q.substring(0,2); // Get the type, such as "in"
          var level = parent_q.substring(2);  // Get the level, such as 1
          $(".desc5").each(function(elt_index, elt) {
              // Hide each question/answer with either a different type or a higher ID.
              var e_id = $(elt).attr('id');
              if(e_id.substring(0,2) != type || e_id.substring(2) > level) {
                  $(elt).hide();
                  $(elt).children('input').removeAttr('checked');
              }
          });
      }
      $("#"+test).show();
  });
});

$(document).ready(function(){
  $("input[name$='Q14']").click(function() {
      var test = $(this).val();
      if (test[2] == '1') {
          // Check whether this is a top-level question, and if so,
          // hide all the subquestions (and uncheck responses)
          $('.desc3').hide();
          $('input').not('[value='+test+']').removeAttr('checked');
      } else {
          // Find the ID of this question
          var parent_q = $($(this).parents('.desc3')[0]).attr('id');
          var type = parent_q.substring(0,2); // Get the type, such as "in"
          var level = parent_q.substring(2);  // Get the level, such as 1
          $(".desc3").each(function(elt_index, elt) {
              // Hide each question/answer with either a different type or a higher ID.
              var e_id = $(elt).attr('id');
              if(e_id.substring(0,2) != type || e_id.substring(2) > level) {
                  $(elt).hide();
                  $(elt).children('input').removeAttr('checked');
              }
          });
      }
      $("#"+test).show();
  });
});

$(document).ready(function(){
  $("input[name$='Q18']").click(function() {
      var test = $(this).val();
      if (test[2] == '1') {
          // Check whether this is a top-level question, and if so,
          // hide all the subquestions (and uncheck responses)
          $('.desc4').hide();
          $('input').not('[value='+test+']').removeAttr('checked');
      } else {
          // Find the ID of this question
          var parent_q = $($(this).parents('.desc4')[0]).attr('id');
          var type = parent_q.substring(0,2); // Get the type, such as "in"
          var level = parent_q.substring(2);  // Get the level, such as 1
          $(".desc4").each(function(elt_index, elt) {
              // Hide each question/answer with either a different type or a higher ID.
              var e_id = $(elt).attr('id');
              if(e_id.substring(0,2) != type || e_id.substring(2) > level) {
                  $(elt).hide();
                  $(elt).children('input').removeAttr('checked');
              }
          });
      }
      $("#"+test).show();
  });
});

// after changing the answer of a main question, remove the checked answer from subquestion
function removeSub(elements) {
    for (var i = 0; i < elements.length; i++) {
        if (elements[i].type == "radio" || elements[i].type == "checkbox") {
            elements[i].checked = false;
        }
    }
}

$(document).ready(function() {
    //Q4 folding
    $("input[type='radio']").change(function(){
    //hide
    if($(this).val()=="SF1" || $(this).val()=="SD1")
    {
        $("#submit_Q4").show();
        $("#submit_Q4_1").hide();
        var elements = document.querySelectorAll("[name=Q4_2]");
        var elements2 = document.querySelectorAll("[name=Q4_1]");
        removeSub(elements);
        removeSub(elements2);
    }
    //show
    else if ($(this).val()=="MU1" )
    {
        $("#submit_Q4").hide();
        $("#submit_Q4_1").show();
        var elements = document.querySelectorAll("[name=Q4_2]");
        removeSub(elements);
    }
    else if ($(this).val()=="PU1"){
         $("#submit_Q4").hide();
         $("#submit_Q4_1").show();
         var elements = document.querySelectorAll("[name=Q4_1]");
         removeSub(elements);
    }
    else if ($(this).val()=="SC1" ||$(this).val()=="OT1"){
         $("#submit_Q4").hide();
         $("#submit_Q4_1").show();
         var elements = document.querySelectorAll("[name=Q4_1],[name=Q4_2]");
         removeSub(elements);
    }});

    //Q5 folding
    $("input[type='radio']").change(function(){
        if($(this).val()=="YE2")
        {
            $("#submit_Q5").show();
            $("#submit_Q5_1").hide();
            $("#submit_Q5_2").hide();

        }
        else if ($(this).val()=="NO1"){
            $("#submit_Q5").hide();
            $("#submit_Q5_1").show();
            $("#submit_Q5_2").show();

            var elements = document.querySelectorAll("[name=Q5_1], [name=Q5_2]");
            removeSub(elements);
        }

        else if ($(this).val()=="YE3" || $(this).val()=="YE4")
        {
            $("#submit_Q5").hide();
            $("#submit_Q5_1").show();
            $("#submit_Q5_2").show();
        }
    });

    //Q6 folding
    $("input[type='radio']").change(function(){
        if($(this).val()=="Insignificant")
        {
        $("#submit_Q6").show();
        $("#submit_Q6_1").hide();

        }
        else if ($(this).val()=="Small" || $(this).val()=="Medium" || $(this).val()=="Large" )
        {
            $("#submit_Q6").hide();
            $("#submit_Q6_1").show();
        }
    });

    //Q7 remove subquestions after changing the answer of main quesiton
    $("input[type='radio']").change(function(){
        if($(this).val()=="AC1"){
            var elements = document.querySelectorAll("[name=Q7_1]");
            removeSub(elements);
        }
    });

    //Q13 folding
    $("input[type='radio']").change(function(){
        if($(this).val()=="3")
        {
        $("#submit_Q13").show();
        $("#submit_Q13_1").hide();
        }
        else if ($(this).val()=="1" || $(this).val()=="2" || $(this).val()=="3" )
        {
            $("#submit_Q13").hide();
            $("#submit_Q13_1").show();
        }
    });

    //Q14 remove subquestions after changing the answer of main quesiton
    $("input[type='radio']").change(function(){
        const fruits = ["IS1", "LW1", "LB1", "MT1","UN1",];
        if(fruits.includes($(this).val())){
            var elements = document.querySelectorAll("[name=Q14_1]");
            removeSub(elements);
        }
    });

    //Q18 remove subquestions after changing the answer of main quesiton
    $("input[type='radio']").change(function(){
        const fruits = ["N_1"];
        if(fruits.includes($(this).val())){
            var elements = document.querySelectorAll("[name=Q18_1]");
            removeSub(elements);
        }
    });

    $(function(){
        var requiredCheckboxes = $('.browsers :checkbox[required]');
        //console.log(typeof(requiredCheckboxes));
        requiredCheckboxes.change(function(){
            if(requiredCheckboxes.is(':checked')) {
                requiredCheckboxes.removeAttr('required');
            } else {
                requiredCheckboxes.attr('required', 'required');
            }
        });
    });

    $(function(){
        var requiredCheckboxes = $('.browsers2 :checkbox[required]');
        requiredCheckboxes.change(function(){
            if(requiredCheckboxes.is(':checked')) {
                requiredCheckboxes.removeAttr('required');
            } else {
                requiredCheckboxes.attr('required', 'required');
            }
        });
    });

});
