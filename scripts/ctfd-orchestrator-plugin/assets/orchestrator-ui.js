(function () {
  function applyFloatingButtonStyle(link, bottomOffset) {
    link.style.position = "fixed";
    link.style.right = "18px";
    link.style.bottom = bottomOffset;
    link.style.zIndex = "9999";
    link.style.textDecoration = "none";
    link.style.borderRadius = "999px";
    link.style.boxShadow = "0 12px 30px rgba(0,0,0,0.18)";
  }

  function mountQuickLink() {
    if (document.getElementById("orchestrator-ui-link")) {
      return;
    }

    const link = document.createElement("a");
    link.id = "orchestrator-ui-link";
    link.href = "/plugins/orchestrator/dashboard";
    link.textContent = "Team Dashboard";
    link.className = "btn btn-primary btn-sm";

    const onChallengesPage = window.location.pathname.startsWith("/challenges");

    if (onChallengesPage) {
      applyFloatingButtonStyle(link, "18px");
      document.body.appendChild(link);
      return;
    }

    const navBar = document.querySelector("nav .navbar-nav") || document.querySelector(".navbar-nav") || document.querySelector("nav ul") || document.querySelector("header ul");
    if (navBar) {
      const item = document.createElement("li");
      item.className = "nav-item";
      link.classList.add("nav-link");
      item.appendChild(link);
      navBar.appendChild(item);
      return;
    }

    applyFloatingButtonStyle(link, "16px");

    document.body.appendChild(link);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mountQuickLink);
  } else {
    mountQuickLink();
  }

  const observer = new MutationObserver(() => {
    mountQuickLink();
  });

  if (document.body) {
    observer.observe(document.body, { childList: true, subtree: true });
  }
})();
