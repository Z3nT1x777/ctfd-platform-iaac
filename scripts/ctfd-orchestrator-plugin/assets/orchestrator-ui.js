/* ── Dashboard pill (all pages) ─────────────────────────────────────── */
(function () {
  if (document.getElementById("orchestrator-nav-link")) return;

  var a = document.createElement("a");
  a.id = "orchestrator-nav-link";
  a.href = "/plugins/orchestrator/dashboard";
  a.innerHTML =
    '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="currentColor" ' +
    'viewBox="0 0 16 16" aria-hidden="true" style="flex-shrink:0">' +
    '<path d="M0 1a1 1 0 0 1 1-1h5a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1H1a1 1 0 0 1-1-1V1z' +
    'M9 0a1 1 0 0 0-1 1v7a1 1 0 0 0 1 1h5a1 1 0 0 0 1-1V1a1 1 0 0 0-1-1z' +
    'M0 9a1 1 0 0 1 1-1h5a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1H1a1 1 0 0 1-1-1z' +
    'M10 11a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1h-4a1 1 0 0 1-1-1z"/>' +
    "</svg>" +
    '<span style="white-space:nowrap">Dashboard</span>';

  a.style.cssText = [
    "position:fixed", "bottom:20px", "right:20px", "z-index:9999",
    "display:flex", "align-items:center", "gap:6px", "padding:8px 14px",
    "background:rgba(13,22,36,0.88)", "color:#a0b4cc",
    "border:1px solid #2a3548", "border-radius:10px",
    "font-size:0.82rem", "font-weight:600", "text-decoration:none",
    "letter-spacing:0.3px", "backdrop-filter:blur(8px)",
    "box-shadow:0 4px 20px rgba(0,0,0,0.35)",
    "transition:color .2s,border-color .2s,background .2s"
  ].join(";");

  a.addEventListener("mouseenter", function () {
    a.style.color = "#e6edf7";
    a.style.borderColor = "#4a6080";
    a.style.background = "rgba(13,22,36,0.98)";
  });
  a.addEventListener("mouseleave", function () {
    a.style.color = "#a0b4cc";
    a.style.borderColor = "#2a3548";
    a.style.background = "rgba(13,22,36,0.88)";
  });

  function mount() {
    if (document.getElementById("orchestrator-nav-link")) return;
    document.body.appendChild(a);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();

/* ── Dashboard page logic ───────────────────────────────────────────── */
(function () {
  if (!window.location.pathname.startsWith("/plugins/orchestrator/dashboard")) return;

  /* Config injected by server-side template */
  var MAX_ACTIVE = (window._CFG && window._CFG.max_active) ? window._CFG.max_active : 10;

  /* ── Helpers ── */
  function fmt(sec) {
    if (!sec || sec <= 0) return "Expired";
    var m = Math.floor(sec / 60);
    var s = sec % 60;
    return m + "m " + (s < 10 ? "0" : "") + s + "s";
  }

  function ttlClass(sec) {
    if (sec > 1800) return "b-green";
    if (sec > 600)  return "b-amber";
    return "b-red";
  }

  function ttlPct(sec) {
    return Math.min(100, Math.round(sec / 36));
  }

  function esc(s) {
    return String(s || "")
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  /* ── State ── */
  var _instances = [];
  var _ticker = null;

  function startTicker() {
    if (_ticker) clearInterval(_ticker);
    _ticker = setInterval(function () {
      var minSec = Infinity;
      var minName = "";
      for (var i = 0; i < _instances.length; i++) {
        var inst = _instances[i];
        if (!inst.ttl_remaining_sec) continue;
        inst.ttl_remaining_sec = Math.max(0, inst.ttl_remaining_sec - 1);
        var el  = document.getElementById("ttl-n-" + i);
        var bar = document.getElementById("ttl-b-" + i);
        if (el)  el.textContent = fmt(inst.ttl_remaining_sec);
        if (bar) {
          bar.style.width = ttlPct(inst.ttl_remaining_sec) + "%";
          bar.className = "ttl-bar " + ttlClass(inst.ttl_remaining_sec);
        }
        if (inst.ttl_remaining_sec > 0 && inst.ttl_remaining_sec < minSec) {
          minSec  = inst.ttl_remaining_sec;
          minName = inst.challenge_name || "";
        }
      }
      if (minSec < Infinity) {
        var mEl = document.getElementById("stat-min-ttl");
        if (mEl) mEl.textContent = fmt(minSec);
      }
    }, 1000);
  }

  /* ── Fetch helpers ── */
  function getJSON(url, cb) {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", url, true);
    xhr.setRequestHeader("Cache-Control", "no-store");
    xhr.timeout = 8000;
    xhr.onload = function () {
      if (xhr.status >= 200 && xhr.status < 300) {
        try { cb(null, JSON.parse(xhr.responseText)); }
        catch (e) { cb(e, null); }
      } else {
        cb(new Error("HTTP " + xhr.status), null);
      }
    };
    xhr.onerror   = function () { cb(new Error("network"), null); };
    xhr.ontimeout = function () { cb(new Error("timeout"), null); };
    xhr.send();
  }

  /* ── Instances ── */
  function refreshInstances() {
    getJSON("/plugins/orchestrator/instances", function (err, data) {
      var list     = document.getElementById("instances-list");
      var badge    = document.getElementById("sidebar-count");
      var quota    = document.getElementById("quota-label");
      var statR    = document.getElementById("stat-running");
      var statRSub = document.getElementById("stat-running-sub");
      var statT    = document.getElementById("stat-min-ttl");
      var statTN   = document.getElementById("stat-min-ttl-name");

      if (err || !data || !data.ok) {
        if (list) list.innerHTML = "<div class=\"empty-box\">Could not load instances. Is the orchestrator running?</div>";
        return;
      }

      _instances = data.instances || [];
      var count = _instances.length;

      if (badge) { badge.textContent = count; badge.className = count > 0 ? "nav-badge" : "nav-badge zero"; }
      if (quota)    quota.textContent = count + " / " + MAX_ACTIVE;
      if (statR)    statR.textContent = count;
      if (statRSub) statRSub.textContent = count > 0 ? "Active" : "None running";

      var active = _instances.filter(function (i) { return (i.ttl_remaining_sec || 0) > 0; });
      if (active.length) {
        var minInst = active.reduce(function (a, b) {
          return a.ttl_remaining_sec < b.ttl_remaining_sec ? a : b;
        });
        if (statT)  statT.textContent = fmt(minInst.ttl_remaining_sec);
        if (statTN) statTN.textContent = minInst.challenge_name || "—";
      } else {
        if (statT)  statT.textContent = "—";
        if (statTN) statTN.textContent = count === 0 ? "No instances" : "Expired";
      }

      if (!list) { startTicker(); return; }

      if (!_instances.length) {
        list.innerHTML = "<div class=\"empty-box\">No active instances right now. <a href=\"/challenges\">Launch a challenge \u2192</a></div>";
        startTicker();
        return;
      }

      list.innerHTML = "";
      for (var idx = 0; idx < _instances.length; idx++) {
        (function (inst, i) {
          var ref      = inst.challenge_ref || inst.challenge_name || String(inst.challenge_id || "");
          var sec      = inst.ttl_remaining_sec || 0;
          var isUp     = sec > 0;
          var conn     = inst.connection_display || inst.url || "—";
          var user     = inst.ssh_user || "—";
          var sshHref  = inst.open_href || ("/plugins/orchestrator/launch?challenge_id=" + (inst.challenge_id || ""));
          var extHref  = "/plugins/orchestrator/extend-ui?challenge_ref=" + encodeURIComponent(ref);
          var killHref = "/plugins/orchestrator/stop-ui?challenge_ref=" + encodeURIComponent(ref);
          var pts      = inst.challenge_value ? inst.challenge_value + " pts" : "";
          var cat      = inst.challenge_category || "";
          var metaParts = [cat, pts].filter(Boolean);
          if (inst.launched_by_username) metaParts.push("by " + inst.launched_by_username);

          var card = document.createElement("div");
          card.className = "inst-card";
          card.innerHTML =
            "<div class=\"inst-head\">" +
              "<div class=\"inst-icon\">\uD83D\uDD12</div>" +
              "<div>" +
                "<div class=\"inst-name\">" + esc(inst.challenge_name || "—") + "</div>" +
                "<div class=\"inst-meta\">" + esc(metaParts.join(" · ")) + "</div>" +
              "</div>" +
              "<div class=\"inst-badge " + (isUp ? "badge-up" : "badge-down") + "\">" +
                "<div class=\"badge-dot " + (isUp ? "dot-up" : "dot-down") + "\"></div>" +
                (isUp ? "UP" : "DOWN") +
              "</div>" +
            "</div>" +
            "<div class=\"inst-body\">" +
              "<div class=\"inst-col\"><div class=\"col-lbl\">Connection</div><div class=\"col-val col-conn\">" + esc(conn) + "</div></div>" +
              "<div class=\"inst-col\"><div class=\"col-lbl\">TTL remaining</div>" +
                "<div class=\"ttl-num\" id=\"ttl-n-" + i + "\">" + fmt(sec) + "</div>" +
                "<div class=\"ttl-bar-wrap\"><div class=\"ttl-bar " + ttlClass(sec) + "\" id=\"ttl-b-" + i + "\" style=\"width:" + ttlPct(sec) + "%\"></div></div>" +
              "</div>" +
              "<div class=\"inst-col\"><div class=\"col-lbl\">User</div><div class=\"user-val\">" + esc(user) + "</div></div>" +
              "<div class=\"inst-actions\">" +
                "<a class=\"act-btn btn-extend\" href=\"" + esc(extHref) + "\">+30m</a>" +
                "<a class=\"act-btn btn-ssh\" href=\"" + esc(sshHref) + "\">SSH</a>" +
                "<a class=\"act-btn btn-kill\" href=\"" + esc(killHref) + "\" onclick=\"return confirm('Kill instance?')\">Kill</a>" +
              "</div>" +
            "</div>";
          list.appendChild(card);
        })(_instances[idx], idx);
      }
      startTicker();
    });
  }

  /* ── Leaderboard ── */
  function refreshLeaderboard() {
    getJSON("/plugins/orchestrator/leaderboard/live", function (err, data) {
      var body = document.getElementById("live-activity-body");
      if (!body) return;
      if (err || !data) {
        body.innerHTML = "<tr><td colspan=\"3\" style=\"padding:9px 11px;color:var(--muted)\">Error loading</td></tr>";
        return;
      }
      var rows = data.rows || [];
      if (!rows.length) {
        body.innerHTML = "<tr><td colspan=\"3\" style=\"padding:9px 11px;color:var(--muted)\">No active instances</td></tr>";
        return;
      }
      var html = "";
      for (var i = 0; i < rows.length; i++) {
        var r = rows[i];
        html += "<tr><td>" + esc(r.team_name || r.team_id) + "</td><td>" + r.active_instances +
          "</td><td><span class=\"status-pill\"><span class=\"s-dot\"></span>active</span></td></tr>";
      }
      body.innerHTML = html;
    });
  }

  /* ── Quick Launch ── */
  function refreshQuickLaunch() {
    getJSON("/plugins/orchestrator/instances", function (err, instData) {
      var runningIds = {};
      if (!err && instData && instData.instances) {
        for (var k = 0; k < instData.instances.length; k++) {
          runningIds[instData.instances[k].challenge_id] = true;
        }
      }
      getJSON("/plugins/orchestrator/challenges", function (err2, challData) {
        var container = document.getElementById("quick-launch-list");
        if (!container) return;
        if (err2 || !challData) {
          container.innerHTML = "<div style=\"padding:11px 13px;color:var(--muted);font-size:13px\">Error loading challenges</div>";
          return;
        }
        var challenges = challData.challenges || [];
        if (!challenges.length) {
          container.innerHTML = "<div style=\"padding:11px 13px;color:var(--muted);font-size:13px\">No challenges available</div>";
          return;
        }
        var running = [];
        var offline = [];
        for (var j = 0; j < challenges.length; j++) {
          var ch = challenges[j];
          if (runningIds[ch.id]) { running.push(ch); } else { offline.push(ch); }
        }

        function qlRow(ch, isRun) {
          var pts = ch.value ? ch.value + " pts" : "";
          return "<div class=\"ql-item" + (isRun ? " running" : "") +
            "\" onclick=\"window.location='/plugins/orchestrator/launch?challenge_id=" + ch.id + "'\">" +
            "<div class=\"ql-name\">" + esc(ch.name) + "</div>" +
            "<div class=\"ql-right\">" +
              (isRun ? "<span class=\"ql-run-lbl\">Running \u25CF</span>" : "") +
              (pts    ? "<span class=\"ql-pts\">" + pts + "</span>" : "") +
            "</div></div>";
        }

        var html = "";
        for (var r = 0; r < running.length; r++) { html += qlRow(running[r], true); }

        if (offline.length) {
          var offlineRows = "";
          for (var o = 0; o < offline.length; o++) { offlineRows += qlRow(offline[o], false); }
          html += "<details class=\"ql-dropdown\">" +
            "<summary class=\"ql-dropdown-toggle\">All challenges " +
            "<span class=\"ql-count\">" + offline.length + "</span></summary>" +
            "<div class=\"ql-dropdown-body\">" + offlineRows + "</div></details>";
        }

        container.innerHTML = html;
      });
    });
  }

  /* ── Entry point ── */
  function refreshAll() {
    refreshInstances();
    refreshLeaderboard();
    refreshQuickLaunch();
  }

  window._dashRefresh = refreshAll;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", refreshAll);
  } else {
    refreshAll();
  }

  setInterval(refreshAll, 30000);
})();
