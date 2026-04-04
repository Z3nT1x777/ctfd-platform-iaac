(function () {
  function mountQuickLink() {
    if (document.getElementById("orchestrator-ui-link")) {
      return;
    }

    const link = document.createElement("a");
    link.id = "orchestrator-ui-link";
    link.href = "/plugins/orchestrator/ui";
    link.textContent = "Instance Control";
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
})();
