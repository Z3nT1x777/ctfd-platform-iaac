(function () {
  var LINK_ID = "orchestrator-nav-link";
  var HREF = "/plugins/orchestrator/dashboard";

  var ICON =
    '<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" fill="currentColor" ' +
    'viewBox="0 0 16 16" style="vertical-align:-1px" aria-hidden="true">' +
    '<path d="M0 1a1 1 0 0 1 1-1h5a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1H1a1 1 0 0 1-1-1V1z' +
    'M9 0a1 1 0 0 0-1 1v7a1 1 0 0 0 1 1h5a1 1 0 0 0 1-1V1a1 1 0 0 0-1-1z' +
    'M0 9a1 1 0 0 1 1-1h5a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1H1a1 1 0 0 1-1-1z' +
    'M10 11a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1h-4a1 1 0 0 1-1-1z"/>' +
    "</svg>";

  function makeLink() {
    var a = document.createElement("a");
    a.id = LINK_ID;
    a.href = HREF;
    return a;
  }

  function tryNavbar() {
    if (document.getElementById(LINK_ID)) return true;

    // CTFd Bootstrap navbar — try both nav lists, pick rightmost visible one
    var lists = document.querySelectorAll("ul.navbar-nav");
    var target = null;
    for (var i = lists.length - 1; i >= 0; i--) {
      if (lists[i].offsetParent !== null) { // visible
        target = lists[i];
        break;
      }
    }

    if (!target) return false;

    var a = makeLink();
    a.className = "nav-link";
    a.innerHTML = ICON + " Dashboard";

    var li = document.createElement("li");
    li.className = "nav-item";
    li.appendChild(a);
    target.appendChild(li);
    return true;
  }

  function mountFallback() {
    if (document.getElementById(LINK_ID)) return;
    var a = makeLink();
    a.innerHTML = ICON + " Dashboard";
    a.style.cssText = [
      "position:fixed", "top:12px", "right:16px", "z-index:9999",
      "background:rgba(15,26,42,0.92)", "color:#e6edf7",
      "border:1px solid #2a3548", "border-radius:8px",
      "padding:6px 12px", "font-size:0.85rem", "font-weight:600",
      "text-decoration:none", "display:flex", "align-items:center", "gap:5px",
      "backdrop-filter:blur(6px)", "box-shadow:0 4px 16px rgba(0,0,0,0.3)"
    ].join(";");
    document.body.appendChild(a);
  }

  function mount() {
    if (!tryNavbar()) mountFallback();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      mount();
      // retry once after CTFd JS may have rewritten the nav
      setTimeout(function () {
        if (!document.getElementById(LINK_ID)) mount();
      }, 400);
    });
  } else {
    mount();
    setTimeout(function () {
      if (!document.getElementById(LINK_ID)) mount();
    }, 400);
  }
})();
