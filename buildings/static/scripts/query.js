function getCookie(name) {
  var cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    var cookies = document.cookie.split(";");
    for (var i = 0; i < cookies.length; i++) {
      var cookie = jQuery.trim(cookies[i]);
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

document.addEventListener("DOMContentLoaded", () => {
  const filters = JSON.parse(
    document.getElementById("querybuilder_filters").textContent
  );

  // Fix for Bootstrap Datepicker
  $("#query-builder").on(
    "afterUpdateRuleValue.queryBuilder",
    function (e, rule) {
      if (rule.filter.plugin === "datepicker") {
        rule.$el.find(".rule-value-container input").datepicker("update");
      }
    }
  );

  $("#query-builder").queryBuilder({
    optgroups: {
      core: {
        en: "Core",
      },
      attributes: {
        en: "Attributes",
      },
    },
    operators: [
      "equal",
      "not_equal",
      "less",
      "less_or_equal",
      "greater",
      "greater_or_equal",
      "between",
      "not_between",
      "begins_with",
      "not_begins_with",
      "contains",
      "not_contains",
      "ends_with",
      "not_ends_with",
      "is_null",
      "is_not_null",
      "in",
      "not_in",
    ],
    filters: filters,
    rules: {
      condition: "AND",
      rules: [
        {
          id: "const_year",
          field: "const_year",
          type: "date",
          input: "text",
          operator: "between",
          value: [1950, 2000],
        },
        {
          condition: "OR",
          rules: [
            {
              id: "num_floors",
              field: "num_floors",
              type: "integer",
              input: "number",
              operator: "greater",
              value: 1,
              validation: { min: 0 },
            },
            {
              id: "attrs__phys_link",
              field: "attrs__phys_link",
              type: "string",
              input: "text",
              operator: "in",
              value: ["semi-detached", "row house"],
            },
          ],
        },
      ],
      valid: true,
    },
  });

  document
    .getElementById("submitQueryButton")
    .addEventListener("click", (e) => {
      e.preventDefault();

      const rules = $("#query-builder").queryBuilder("getRules", {
        get_flags: true,
      });

      if (rules === null) return;

      console.log(rules);

      // Upload new satellite image
      fetch("shq-hlms", {
        method: "POST",
        mode: "same-origin",
        cache: "no-cache",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"), // So django accepts the request
        },
        body: JSON.stringify({ query: rules }),
      }).then((resp) => {
        if (resp.status === 200) {
          console.debug("Query uploaded");
        } else {
          console.debug(`ERROR running query ${resp}`);
        }
      });
    });
});
