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

/* Offering admin: pricing auto-calc between the monthly path
 * (duration_months / monthly_fee) and the daily path
 * (duration_days / daily_fee), both converging on total_fee.
 *
 * Each of the 5 fields is either "user"-owned (a value the person typed,
 * or that was already saved on the record) or "auto"-owned (a value this
 * script computed). We only ever overwrite a field that's empty or
 * auto-owned — a value the user typed by hand is never silently
 * clobbered — but unlike a plain "only fill if empty" rule, an
 * auto-owned field (e.g. total_fee, first computed from the months lane)
 * stays refreshable, so switching to fill in the days lane afterwards
 * correctly recomputes it instead of leaving it stuck on the old number.
 * It also cross-fills the other duration unit (~30 days/month) so a day
 * price is available even when only months were typed, and vice versa.
 */
(function () {
  "use strict";

  var MONTH_DAYS = 30;

  function round2(n) {
    return Math.round((n + Number.EPSILON) * 100) / 100;
  }

  function num($el) {
    var v = $el.length ? String($el.val()).trim().replace(",", ".") : "";
    if (!v) return null;
    var n = parseFloat(v);
    return isNaN(n) ? null : n;
  }

  function isEmpty($el) {
    return !$el.length || String($el.val()).trim() === "";
  }

  var attempts = 0;

  function init() {
    var $ = window.django && window.django.jQuery;
    if (!$) {
      attempts += 1;
      if (attempts < 50) {
        window.setTimeout(init, 100);
      }
      return;
    }

    var $months = $("#id_duration_months");
    var $monthlyFee = $("#id_monthly_fee");
    var $days = $("#id_duration_days");
    var $dailyFee = $("#id_daily_fee");
    var $total = $("#id_total_fee");

    if (!$months.length || !$total.length || !$days.length || !$dailyFee.length || !$monthlyFee.length) {
      return; // fields not on this page (e.g. add view before the migration ran)
    }

    var fields = {
      months: $months,
      monthlyFee: $monthlyFee,
      days: $days,
      dailyFee: $dailyFee,
      total: $total,
    };

    // Every field starts out "user"-owned: a freshly-loaded record's
    // saved values are real data, not something this script computed,
    // so they're left alone until the user (or this script) touches them.
    var owner = {
      months: "user",
      monthlyFee: "user",
      days: "user",
      dailyFee: "user",
      total: "user",
    };

    function writable(key) {
      return isEmpty(fields[key]) || owner[key] === "auto";
    }

    function setVal(key, value) {
      fields[key].val(value);
      owner[key] = "auto";
    }

    function recompute(srcKey) {
      owner[srcKey] = "user"; // whatever the person just edited is authoritative

      var months = num($months);
      var monthlyFee = num($monthlyFee);
      var days = num($days);
      var dailyFee = num($dailyFee);

      var monthsLane = months !== null && monthlyFee !== null;
      var daysLane = days !== null && dailyFee !== null;
      var srcIsDaysLane = srcKey === "days" || srcKey === "dailyFee";

      // 1) total, from whichever lane the just-edited field belongs to
      // (falling back to the other lane if only it is complete).
      // total_fee is a derived field, not data of its own — so unlike
      // monthlyFee/dailyFee it's always refreshed here, even if it
      // already held a saved/typed value, as long as the edit that
      // triggered this wasn't to total_fee itself.
      if (srcKey !== "total") {
        if (srcIsDaysLane && daysLane) {
          setVal("total", round2(days * dailyFee));
        } else if (!srcIsDaysLane && monthsLane) {
          setVal("total", round2(months * monthlyFee));
        } else if (srcIsDaysLane && monthsLane) {
          setVal("total", round2(months * monthlyFee));
        } else if (!srcIsDaysLane && daysLane) {
          setVal("total", round2(days * dailyFee));
        }
      }

      var total = num($total);

      // 2) vice versa: total + duration -> the missing unit price — but
      // only within a lane that isn't contradicted by the other lane
      // already being complete. duration_months is whole-number-only, so
      // e.g. a 15-day (half-month) course with days+dailyFee already
      // set must NOT derive monthlyFee as total / 1 month — that would
      // silently double the true daily-based rate. Leave it blank
      // instead of inventing a misleading number.
      if (total !== null && months !== null && months > 0 && writable("monthlyFee") && !daysLane) {
        setVal("monthlyFee", round2(total / months));
      }
      if (total !== null && days !== null && days > 0 && writable("dailyFee") && !monthsLane) {
        setVal("dailyFee", round2(total / days));
      }

      monthlyFee = num($monthlyFee);
      dailyFee = num($dailyFee);

      // 3) cross-fill the other duration unit (~30 days/month).
      if (months !== null && monthlyFee !== null && writable("days") && writable("dailyFee")) {
        setVal("days", months * MONTH_DAYS);
        setVal("dailyFee", round2(monthlyFee / MONTH_DAYS));
      } else if (days !== null && dailyFee !== null && writable("months") && writable("monthlyFee")) {
        setVal("months", Math.max(1, Math.round(days / MONTH_DAYS)));
        setVal("monthlyFee", round2(dailyFee * MONTH_DAYS));
      }
    }

    Object.keys(fields).forEach(function (key) {
      fields[key].on("input change", function () {
        recompute(key);
      });
    });
  }

  if (document.readyState === "complete") {
    init();
  } else {
    window.addEventListener("load", init);
  }
})();
