/**
 * La încărcarea paginii, dacă există erori de validare (formular sau flash),
 * derulează automat la prima eroare și pune focus pe câmpul asociat.
 * Folosit peste tot unde există Salvează / Publică / Generează / Download etc.
 */
(function () {
  "use strict";

  function findFirstErrorElement() {
    var selectors = [
      ".err",
      ".formErr",
      ".error",
      ".invalid-feedback",
      ".flash.error"
    ];
    for (var i = 0; i < selectors.length; i++) {
      var el = document.querySelector(selectors[i]);
      if (el && el.offsetParent !== null && el.textContent && el.textContent.trim().length > 0) {
        return el;
      }
    }
    return null;
  }

  function findFocusableControl(errorEl) {
    if (!errorEl) return null;
    var parent = errorEl.parentElement;
    if (!parent) return null;
    var control = parent.querySelector("input:not([type=hidden]):not([disabled]), select, textarea");
    if (control) return control;
    if (errorEl.previousElementSibling) {
      var tag = errorEl.previousElementSibling.tagName;
      if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA") return errorEl.previousElementSibling;
    }
    var form = errorEl.closest("form");
    if (form) {
      var firstInvalid = form.querySelector("input:not([type=hidden]):not([disabled]), select, textarea");
      return firstInvalid;
    }
    return null;
  }

  function run() {
    var errorEl = findFirstErrorElement();
    if (!errorEl) return;

    var scrollMargin = 24;
    errorEl.scrollIntoView({ behavior: "smooth", block: "center", inline: "nearest" });

    var control = findFocusableControl(errorEl);
    if (control) {
      try {
        control.focus({ preventScroll: true });
        if (control.setSelectionRange && typeof control.setSelectionRange === "function" && control.value) {
          control.setSelectionRange(0, control.value.length);
        }
      } catch (e) {}
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
})();
