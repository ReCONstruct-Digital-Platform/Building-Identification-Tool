function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
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

document.addEventListener('DOMContentLoaded', () => {

  $('#builder').queryBuilder({
    filters: [
      {
        id: '1',
        field: 'my field',
        label: 'my label',
        type: 'string',
        input: 'text',
      },
      {
        id: '2',
        field: 'my second field',
        label: 'my second label',
        type: 'integer',
        input: 'number',
      }
    ]
  });

  document.getElementById("submitQueryButton").addEventListener("click", (e) => {

    e.preventDefault();

    const rules = $('#builder').queryBuilder('getRules', {get_flags: true});

    console.log(rules);

    // Upload new satellite image
    fetch('query', {
        method: "POST",
        mode: "same-origin",
        cache: "no-cache",
        credentials: "same-origin",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie('csrftoken'), // So django accepts the request
        },
        body: JSON.stringify({ 'query': rules })
    }).then((resp) => {
        if (resp.status === 200) {
            console.debug('Query uploaded');
        }
        else {
            console.debug(`ERROR running query ${resp}`);
        }
    });



  })
})


