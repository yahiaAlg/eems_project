/* Offering admin: prepopulate "رمز الاختصاص" (code) from the selected
 * التخصص (Specialty). Specialty.__str__() is "CODE — Name", and the
 * autocomplete widget (select2) exposes exactly that string as the
 * selected option's label — so we just read the part before the dash.
 */
(function ($) {
  "use strict";

  function extractCode(label) {
    if (!label) return "";
    return $.trim(String(label).split("—")[0]);
  }

  $(function () {
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
  });
})(django.jQuery);
