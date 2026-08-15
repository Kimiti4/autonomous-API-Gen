/* Governance Console — minimal enhancement JS.
   Mutations are server-rendered POST forms; the CSRF token is embedded in
   each form. This file only adds the header fallback for JS-driven flows
   and confirms state-changing submits. */
(function () {
  "use strict";
  var meta = document.querySelector('meta[name="csrf-token"]');
  var token = meta ? meta.getAttribute("content") : "";
  if (token) {
    document.addEventListener("submit", function (event) {
      var form = event.target;
      if (form.method && form.method.toLowerCase() === "post" && !form.querySelector('input[name="csrf_token"]')) {
        var input = document.createElement("input");
        input.type = "hidden";
        input.name = "csrf_token";
        input.value = token;
        form.appendChild(input);
      }
    });
  }
})();
