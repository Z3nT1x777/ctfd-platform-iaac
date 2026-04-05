(function () {
  function mountQuickLink() {
    if (document.getElementById("orchestrator-ui-link")) {
      return;
    }

    const link = document.createElement("a");
    link.id = "orchestrator-ui-link";
    link.href = "/plugins/orchestrator/dashboard";
    link.textContent = "Team Dashboard";
    link.className = "btn btn-sm btn-primary";

    const onChallengesPage = window.location.pathname.startsWith("/challenges");

    if (onChallengesPage) {
      link.style.position = "fixed";
      link.style.right = "18px";
      link.style.bottom = "18px";
      link.style.background = "linear-gradient(90deg, #2d7dff, #52d0ff)";
      link.style.color = "#06192e";
      link.style.padding = "12px 16px";
      link.style.borderRadius = "999px";
      link.style.fontWeight = "700";
      link.style.textDecoration = "none";
      link.style.zIndex = "9999";
      link.style.boxShadow = "0 12px 30px rgba(0,0,0,0.28)";
      document.body.appendChild(link);
      return;
    }

    const navBar = document.querySelector("nav .navbar-nav") || document.querySelector(".navbar-nav") || document.querySelector("nav ul") || document.querySelector("header ul");
    if (navBar) {
      const item = document.createElement("li");
      item.className = "nav-item";
      link.classList.add("nav-link");
      link.style.marginLeft = "8px";
      link.style.marginTop = "2px";
      item.appendChild(link);
      navBar.appendChild(item);
      return;
    }

    link.style.position = "fixed";
    link.style.right = "16px";
    link.style.bottom = "16px";
    link.style.background = "#0f172a";
    link.style.color = "#fff";
    link.style.padding = "10px 14px";
    link.style.borderRadius = "999px";
    link.style.fontWeight = "600";
    link.style.textDecoration = "none";
    link.style.zIndex = "9999";
    link.style.boxShadow = "0 8px 20px rgba(0,0,0,0.25)";

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
