/* Offering admin: prepopulate "رمز الاختصاص" (code) from the selected
 * التخصص (Specialty). Specialty.__str__() is "CODE — Name", and the
 * autocomplete widget (select2) exposes exactly that string as the
 * selected option's label — so we just read the part before the dash.
 *
 * django.jQuery is set by admin/js/jquery.init.js, which is normally
 * ordered before this file — but it isn't guaranteed to have *run* yet
 * the instant this file is parsed. So we don't grab it eagerly at the
 * top; we look it up lazily on load and retry briefly if needed.
 */
(function () {
  "use strict";

  function extractCode(label) {
    if (!label) return "";
    return String(label).split("—")[0].trim();
  }

  var attempts = 0;

  function init() {
    var $ = window.django && window.django.jQuery;
    if (!$) {
      attempts += 1;
      if (attempts < 50) {
        window.setTimeout(init, 100); // keep retrying for ~5s
      }
      return;
    }

    var $specialty = $("#id_specialty");
    var $code = $("#id_code");
    if (!$specialty.length || !$code.length) {
      return;
    }

    // User picks/changes a specialty via the autocomplete dropdown.
    $specialty.on("select2:select", function (e) {
      var label = e.params && e.params.data ? e.params.data.text : "";
      var code = extractCode(label);
      if (code) {
        $code.val(code);
      }
    });
  }

  if (document.readyState === "complete") {
    init();
  } else {
    window.addEventListener("load", init);
  }
})();
