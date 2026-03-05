(function () {
  "use strict";

  var root = document.getElementById("asistent-root");
  if (!root) return;

  var STORAGE_POS_DESKTOP = "asistent_bubble_pos_desktop";
  var STORAGE_POS_MOBILE = "asistent_bubble_pos_mobile";
  var TOOLTIP_DELAY_MS = 3000;
  var TOOLTIP_VISIBLE_MS = 10000;
  var PULSE_SOFT_DURATION_MS_MIN = 10000;
  var PULSE_SOFT_DURATION_MS_MAX = 15000;
  var BUBBLE_SIZE = 54;

  var bubbleWrap = root.querySelector("#asistent-bubble-wrap");
  var fab = root.querySelector("#asistent-fab");
  var tooltipWrap = root.querySelector("#asistent-bubble-tooltip-wrap");
  var overlay = root.querySelector("#asistent-overlay");
  var backdrop = root.querySelector("#asistent-backdrop");
  var panel = root.querySelector("#asistent-panel");
  var closeBtn = root.querySelector("#asistent-close");
  var tabButtons = root.querySelectorAll(".asistent-tab");
  var tabPanels = root.querySelectorAll(".asistent-tab-panel");
  var tabsNav = root.querySelector(".asistent-tabs");

  var guideTitle = root.querySelector("#asistent-guide-title");
  var guideIntro = root.querySelector("#asistent-guide-intro");
  var guideBullets = root.querySelector("#asistent-guide-bullets");
  var tipBlock = root.querySelector("#asistent-tip-block");
  var tipText = root.querySelector("#asistent-tip-text");

  var faqSearch = root.querySelector("#asistent-faq-search");
  var faqList = root.querySelector("#asistent-faq-list");
  var faqChat = root.querySelector("#asistent-faq-chat");
  var faqMessages = root.querySelector("#asistent-faq-messages");
  var faqBack = root.querySelector("#asistent-faq-back");

  var notificationsBlock = root.querySelector("#asistent-notifications-block");
  var msgBadge = root.querySelector("#asistent-bubble-msg-badge");
  var tooltipTasksEl = root.querySelector("#asistent-tooltip-tasks");
  var astaziTab = root.querySelector("#asistent-tab-astazi");
  var astaziMessages = root.querySelector("#asistent-astazi-messages");
  var colaborariTab = root.querySelector("#asistent-tab-colaborari");
  var colaborariLoading = root.querySelector("#asistent-colaborari-loading");

  var csrfToken = root.getAttribute("data-csrf") || "";
  var todayTasks = [];
  var baseUrl = root.getAttribute("data-base-url") || "";
  var pageId = root.getAttribute("data-page-id") || "generic";

  /** Single source of truth: true = panel visible and bubble hidden, false = panel closed and bubble visible. NEVER persisted. */
  var isAssistantOpen = false;

  /** Hard reset: force assistant closed. No memory of open state between pages. */
  function ensurePanelClosed() {
    isAssistantOpen = false;
    if (root) root.classList.remove("asistent-open");
    if (overlay) {
      overlay.classList.remove("is-open");
      overlay.setAttribute("aria-hidden", "true");
      overlay.style.display = "none";
    }
    if (panel) panel.style.display = "none";
    if (bubbleWrap) bubbleWrap.style.display = "";
    document.body.classList.remove("asistent-panel-open");
  }

  function isMobile() {
    return typeof window !== "undefined" && window.innerWidth < 768;
  }

  function storageKeyPos() {
    return isMobile() ? STORAGE_POS_MOBILE : STORAGE_POS_DESKTOP;
  }

  function apiUrl(path) {
    return baseUrl + "/assistant" + path;
  }

  function headers() {
    var h = { "Content-Type": "application/json", "Accept": "application/json" };
    if (csrfToken) h["X-CSRFToken"] = csrfToken;
    return h;
  }

  function escapeHtml(s) {
    if (!s) return "";
    var div = document.createElement("div");
    div.textContent = s;
    return div.innerHTML;
  }

  // --- Position: load, save, clamp ---
  function getBubbleSize() {
    if (!bubbleWrap) return BUBBLE_SIZE;
    var rect = bubbleWrap.getBoundingClientRect();
    return Math.max(rect.width, rect.height, 50);
  }

  var DRAG_THRESHOLD_PX = 6;

  function loadPosition() {
    if (!bubbleWrap) return;
    var size = getBubbleSize();
    var defaultLeft = window.innerWidth - size - 24;
    var defaultTop = window.innerHeight - size - 24;
    try {
      var key = storageKeyPos();
      var raw = localStorage.getItem(key);
      if (raw) {
        var pos = JSON.parse(raw);
        if (typeof pos.left !== "undefined" && typeof pos.top !== "undefined") {
          bubbleWrap.style.left = pos.left + "px";
          bubbleWrap.style.top = pos.top + "px";
          bubbleWrap.style.right = "auto";
          bubbleWrap.style.bottom = "auto";
          clampPosition();
          return;
        }
        if (typeof pos.x !== "undefined" && typeof pos.y !== "undefined") {
          bubbleWrap.style.left = (window.innerWidth - pos.x - size) + "px";
          bubbleWrap.style.top = (window.innerHeight - pos.y - size) + "px";
          bubbleWrap.style.right = "auto";
          bubbleWrap.style.bottom = "auto";
          clampPosition();
          return;
        }
      }
    } catch (e) {}
    bubbleWrap.style.left = defaultLeft + "px";
    bubbleWrap.style.top = defaultTop + "px";
    bubbleWrap.style.right = "auto";
    bubbleWrap.style.bottom = "auto";
  }

  function clampPosition() {
    if (!bubbleWrap) return;
    var size = getBubbleSize();
    var r = bubbleWrap.getBoundingClientRect();
    var left = r.left;
    var top = r.top;
    left = Math.max(0, Math.min(window.innerWidth - size, left));
    top = Math.max(0, Math.min(window.innerHeight - size, top));
    bubbleWrap.style.left = left + "px";
    bubbleWrap.style.top = top + "px";
    bubbleWrap.style.right = "auto";
    bubbleWrap.style.bottom = "auto";
  }

  function savePosition() {
    if (!bubbleWrap) return;
    var r = bubbleWrap.getBoundingClientRect();
    try {
      localStorage.setItem(storageKeyPos(), JSON.stringify({ left: r.left, top: r.top }));
    } catch (e) {}
  }

  // --- Draggable: pointer events, offset-based (bubble stays under finger/cursor) ---
  var dragging = false;
  var startX, startY, offsetX, offsetY, pointerId = null;
  var openedByPointer = false;
  var upHandled = false;
  var pointerDownOnBubble = false;

  function onPointerDown(e) {
    upHandled = false;
    if (e.target.closest(".asistent-overlay") || e.target.closest(".asistent-bubble-tooltip-wrap")) return;
    pointerDownOnBubble = true;
    var r = bubbleWrap.getBoundingClientRect();
    var clientX = e.clientX != null ? e.clientX : (e.touches && e.touches[0] ? e.touches[0].clientX : 0);
    var clientY = e.clientY != null ? e.clientY : (e.touches && e.touches[0] ? e.touches[0].clientY : 0);
    startX = clientX;
    startY = clientY;
    offsetX = clientX - r.left;
    offsetY = clientY - r.top;
    pointerId = e.pointerId != null ? e.pointerId : undefined;
    dragging = false;
    if (fab && typeof fab.setPointerCapture === "function" && e.pointerId != null) {
      try { fab.setPointerCapture(e.pointerId); } catch (err) {}
    }
    e.preventDefault();
  }

  function onPointerMove(e) {
    var clientX = e.clientX != null ? e.clientX : (e.touches && e.touches[0] ? e.touches[0].clientX : startX);
    var clientY = e.clientY != null ? e.clientY : (e.touches && e.touches[0] ? e.touches[0].clientY : startY);
    if (!dragging && (offsetX == null || offsetY == null)) return;
    if (!dragging) {
      var dx = clientX - startX;
      var dy = clientY - startY;
      if (dx * dx + dy * dy > DRAG_THRESHOLD_PX * DRAG_THRESHOLD_PX) {
        dragging = true;
        bubbleWrap.classList.add("asistent-dragging");
        document.body.classList.add("asistent-dragging-bubble");
      }
    }
    if (dragging) {
      var size = getBubbleSize();
      var newLeft = clientX - offsetX;
      var newTop = clientY - offsetY;
      newLeft = Math.max(0, Math.min(window.innerWidth - size, newLeft));
      newTop = Math.max(0, Math.min(window.innerHeight - size, newTop));
      bubbleWrap.style.left = newLeft + "px";
      bubbleWrap.style.top = newTop + "px";
      bubbleWrap.style.right = "auto";
      bubbleWrap.style.bottom = "auto";
      e.preventDefault();
    }
  }

  function onPointerUp(e) {
    if (upHandled) return;
    upHandled = true;
    if (dragging) {
      savePosition();
      bubbleWrap.classList.remove("asistent-dragging");
      document.body.classList.remove("asistent-dragging-bubble");
      dragging = false;
      if (fab && typeof fab.releasePointerCapture === "function" && pointerId != null) {
        try { fab.releasePointerCapture(pointerId); } catch (err) {}
      }
    } else if (pointerDownOnBubble) {
      bubbleTappedBefore3s = true;
      clearTooltipTimers();
      openedByPointer = true;
      openPanel(e);
      if (fab && typeof fab.releasePointerCapture === "function" && pointerId != null) {
        try { fab.releasePointerCapture(pointerId); } catch (err) {}
      }
    }
    pointerDownOnBubble = false;
    pointerId = null;
    offsetX = null;
    offsetY = null;
  }

  function onPointerCancel(e) {
    upHandled = true;
    pointerDownOnBubble = false;
    if (dragging) {
      bubbleWrap.classList.remove("asistent-dragging");
      document.body.classList.remove("asistent-dragging-bubble");
      savePosition();
    }
    dragging = false;
    pointerId = null;
    offsetX = null;
    offsetY = null;
    if (fab && typeof fab.releasePointerCapture === "function" && e.pointerId != null) {
      try { fab.releasePointerCapture(e.pointerId); } catch (err) {}
    }
  }

  if (fab) {
    fab.addEventListener("pointerdown", onPointerDown, { passive: false });
    fab.addEventListener("touchstart", onPointerDown, { passive: false });
    fab.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      if (dragging) return;
      if (e.defaultPrevented) return;
      if (openedByPointer) {
        openedByPointer = false;
        return;
      }
      openPanel(e);
    }, true);
  }
  document.addEventListener("pointermove", onPointerMove, { passive: false });
  document.addEventListener("pointerup", onPointerUp, { passive: false });
  document.addEventListener("pointercancel", onPointerCancel, { passive: false });
  document.addEventListener("touchmove", onPointerMove, { passive: false });
  document.addEventListener("touchend", onPointerUp, { passive: false });
  document.addEventListener("touchcancel", onPointerCancel, { passive: false });

  window.addEventListener("resize", clampPosition);
  window.addEventListener("orientationchange", function () {
    setTimeout(clampPosition, 100);
  });

  // --- Pulse: tooltip + pulse-soft (idle) ---
  var tooltipTimer = null;
  var pulseSoftTimer = null;
  var bubbleTappedBefore3s = false;

  function clearTooltipTimers() {
    if (tooltipTimer) { clearTimeout(tooltipTimer); tooltipTimer = null; }
    if (pulseSoftTimer) { clearTimeout(pulseSoftTimer); pulseSoftTimer = null; }
  }

  function setPulseSoft() {
    if (!fab) return;
    fab.classList.remove("pulse-heartbeat", "has-due");
    fab.classList.add("pulse-soft");
  }

  function setPulseNone() {
    if (!fab) return;
    fab.classList.remove("pulse-heartbeat", "pulse-soft", "has-due");
  }

  function setPulseHeartbeat() {
    if (!fab) return;
    fab.classList.remove("pulse-soft");
    fab.classList.add("pulse-heartbeat", "has-due");
  }

  function updateHasUnread(hasUnread) {
    if (!fab) return;
    if (hasUnread) {
      clearTooltipTimers();
      hideTooltip();
      setPulseHeartbeat();
    } else {
      fab.classList.remove("has-due");
      if (!fab.classList.contains("pulse-soft")) fab.classList.remove("pulse-heartbeat");
    }
  }

  var tooltipShownThisLoad = false;

  function showTooltip() {
    if (!tooltipWrap || tooltipShownThisLoad) return;
    tooltipShownThisLoad = true;
    if (tooltipTasksEl) {
      if (todayTasks.length > 0) {
        tooltipTasksEl.innerHTML = "<a href=\"" + (baseUrl ? baseUrl + "/todo" : "/todo") + "\">Vezi ce ai de făcut astăzi</a>";
        tooltipTasksEl.style.display = "block";
        tooltipWrap.classList.add("has-tasks");
      } else {
        tooltipTasksEl.innerHTML = "";
        tooltipTasksEl.style.display = "none";
        tooltipWrap.classList.remove("has-tasks");
      }
    }
    tooltipWrap.hidden = false;
    tooltipWrap.classList.add("is-visible");
    tooltipWrap.setAttribute("aria-hidden", "false");
  }

  function hideTooltip() {
    if (!tooltipWrap) return;
    tooltipWrap.classList.remove("is-visible", "has-tasks");
    tooltipWrap.setAttribute("aria-hidden", "true");
    if (tooltipTasksEl) { tooltipTasksEl.innerHTML = ""; tooltipTasksEl.style.display = "none"; }
    setTimeout(function () {
      if (tooltipWrap && !tooltipWrap.classList.contains("is-visible")) {
        tooltipWrap.hidden = true;
      }
    }, 300);
  }

  function scheduleTooltipAndPulse() {
    if (bubbleTappedBefore3s) return;
    clearTooltipTimers();
    if (hasUnreadNotifications) {
      setPulseHeartbeat();
      return;
    }
    tooltipTimer = setTimeout(function () {
      tooltipTimer = null;
      if (bubbleTappedBefore3s || isAssistantOpen || hasUnreadNotifications) return;
      showTooltip();
      setPulseSoft();
      tooltipTimer = setTimeout(function () {
        tooltipTimer = null;
        hideTooltip();
        var dur = PULSE_SOFT_DURATION_MS_MIN + Math.random() * (PULSE_SOFT_DURATION_MS_MAX - PULSE_SOFT_DURATION_MS_MIN);
        pulseSoftTimer = setTimeout(function () {
          pulseSoftTimer = null;
          if (!hasUnreadNotifications) setPulseNone();
        }, dur);
      }, TOOLTIP_VISIBLE_MS);
    }, TOOLTIP_DELAY_MS);
  }

  var hasUnreadNotifications = false;
  var hasUnreadAnnouncements = false;
  var hasUnreadCollaborations = false;
  var waPhone = root.getAttribute("data-wa-phone") || "40764381795";

  function showMsgBadge(show, text) {
    if (!msgBadge) return;
    msgBadge.hidden = !show;
    if (text) msgBadge.textContent = text;
  }

  function showMessageOnlyPanel() {
    if (tabsNav) tabsNav.style.display = "none";
    tabPanels.forEach(function (p) { p.style.display = "none"; p.hidden = true; });
    if (notificationsBlock) {
      notificationsBlock.hidden = false;
      notificationsBlock.style.display = "";
    }
  }

  function showNormalPanel() {
    if (tabsNav) tabsNav.style.display = "";
    tabButtons.forEach(function (b) { b.classList.remove("active"); b.setAttribute("aria-selected", "false"); });
    tabPanels.forEach(function (p) { p.classList.remove("active"); p.hidden = true; p.style.display = ""; });
    var ghidBtn = root.querySelector(".asistent-tab[data-tab=\"ghid\"]");
    var ghidPanel = root.querySelector("#panel-ghid");
    if (ghidBtn) { ghidBtn.classList.add("active"); ghidBtn.setAttribute("aria-selected", "true"); }
    if (ghidPanel) { ghidPanel.classList.add("active"); ghidPanel.hidden = false; }
    if (notificationsBlock) { notificationsBlock.hidden = true; notificationsBlock.innerHTML = ""; }
    loadGuide();
  }

  // --- Notificări (anunțuri admin + expirare trial/paid) ---
  function loadNotifications() {
    if (!notificationsBlock) return;
    fetch(apiUrl("/notifications"), { headers: headers() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok) return;
        hasUnreadNotifications = !!data.has_unread;
        hasUnreadAnnouncements = !!data.has_unread_announcements;
        hasUnreadCollaborations = !!data.has_unread_collaborations;
        var hasUnreadTasks = !!data.has_unread_tasks;
        updateHasUnread(hasUnreadNotifications);
        if (hasUnreadCollaborations) {
          // Verifică dacă există potriviri cu clienți
          var hasClientMatches = data.has_client_matches || false;
          showMsgBadge(true, hasClientMatches ? "Ai o potrivire cu un client" : "Ai o posibilă colaborare");
        } else if (hasUnreadTasks) {
          showMsgBadge(true, "Ai task-uri pentru astăzi");
        } else {
          showMsgBadge(hasUnreadAnnouncements, "Ai primit un mesaj");
        }
        var html = "";
        if (data.expiry_reminder && data.expiry_reminder.show) {
          var waNum = (waPhone || "").replace(/\D/g, "") || "40764381795";
          html += "<div class=\"asistent-notif-card asistent-notif-expiry\"><p>" + escapeHtml(data.expiry_reminder.message) + "</p><div class=\"asistent-notif-actions\"><button type=\"button\" class=\"asistent-btn asistent-btn-primary asistent-notif-ok\" data-action=\"dismiss-expiry\">OK</button><a href=\"https://wa.me/" + waNum + "?text=" + encodeURIComponent("Salut, vreau să prelungesc abonamentul/trial.") + "\" target=\"_blank\" rel=\"noopener\" class=\"asistent-btn\">Contactează suport</a></div></div>";
        }
        if (data.today_tasks && data.today_tasks.length) {
          html += "<div class=\"asistent-notif-card asistent-notif-tasks\"><p><strong>📋 Task-uri pentru astăzi (" + data.today_tasks.length + ")</strong></p><ul style=\"margin:12px 0;padding-left:20px;\">";
          data.today_tasks.forEach(function (task) {
            var taskHtml = "<li style=\"margin:8px 0;\"><strong>" + escapeHtml(task.title) + "</strong>";
            if (task.description) {
              taskHtml += "<br><span style=\"color:var(--muted);font-size:13px;\">" + escapeHtml(task.description) + "</span>";
            }
            if (task.due_time) {
              taskHtml += " <span style=\"color:var(--muted);\">⏰ " + escapeHtml(task.due_time) + "</span>";
            }
            taskHtml += "<br><a href=\"" + escapeHtml(task.completion_url) + "\" class=\"asistent-btn asistent-btn-primary\" style=\"margin-top:4px;display:inline-block;text-decoration:none;\">✅ Bifează</a></li>";
            html += taskHtml;
          });
          html += "</ul></div>";
        }
        if (data.announcements && data.announcements.length) {
          data.announcements.forEach(function (a) {
            html += "<div class=\"asistent-notif-card\" data-announcement-id=\"" + a.id + "\"><p>" + escapeHtml(a.message).replace(/\n/g, "<br>") + "</p><button type=\"button\" class=\"asistent-btn asistent-btn-primary asistent-notif-read\" data-id=\"" + a.id + "\">Am citit</button></div>";
          });
        }
        if (html) {
          notificationsBlock.innerHTML = html;
          notificationsBlock.hidden = false;
          showMessageOnlyPanel();
          notificationsBlock.querySelectorAll(".asistent-notif-read").forEach(function (btn) {
            btn.addEventListener("click", function () {
              var id = this.getAttribute("data-id");
              fetch(apiUrl("/announcements/" + id + "/read"), { method: "POST", headers: headers() })
                .then(function () {
                  var card = notificationsBlock.querySelector("[data-announcement-id=\"" + id + "\"]");
                  if (card) card.remove();
                  var stillHas = !!notificationsBlock.querySelector(".asistent-notif-card");
                  hasUnreadNotifications = stillHas;
                  hasUnreadAnnouncements = !!notificationsBlock.querySelector("[data-announcement-id]");
                  updateHasUnread(stillHas);
                  showMsgBadge(hasUnreadAnnouncements, "Ai primit un mesaj");
                  if (!stillHas) {
                    notificationsBlock.hidden = true;
                    notificationsBlock.innerHTML = "";
                    showNormalPanel();
                  }
                });
            });
          });
          notificationsBlock.querySelectorAll(".asistent-notif-ok[data-action=\"dismiss-expiry\"]").forEach(function (btn) {
            btn.addEventListener("click", function () {
              fetch(apiUrl("/expiry-reminder/dismiss"), { method: "POST", headers: headers() })
                .then(function () {
                  var card = notificationsBlock.querySelector(".asistent-notif-expiry");
                  if (card) card.remove();
                  var stillHas = !!notificationsBlock.querySelector(".asistent-notif-card");
                  hasUnreadNotifications = stillHas;
                  hasUnreadAnnouncements = !!notificationsBlock.querySelector("[data-announcement-id]");
                  var hasUnreadTasks = !!notificationsBlock.querySelector(".asistent-notif-tasks");
                  updateHasUnread(stillHas);
                  if (hasUnreadTasks) {
                    showMsgBadge(true, "Ai task-uri pentru astăzi");
                  } else {
                    showMsgBadge(hasUnreadAnnouncements, "Ai primit un mesaj");
                  }
                  if (!stillHas) {
                    notificationsBlock.hidden = true;
                    notificationsBlock.innerHTML = "";
                    showNormalPanel();
                  }
                });
            });
          });
          // Reîncarcă notificările după ce un task este bifat (prin link)
          notificationsBlock.querySelectorAll(".asistent-notif-tasks a").forEach(function (link) {
            link.addEventListener("click", function () {
              setTimeout(function () {
                loadNotifications();
              }, 1000);
            });
          });
        } else {
          notificationsBlock.hidden = true;
          notificationsBlock.innerHTML = "";
          showNormalPanel();
        }
      })
      .catch(function () {});
  }

  // --- Panel open/close ---
  function openPanel(ev) {
    if (isAssistantOpen === true) return;
    if (dragging) return;
    if (ev && ev.defaultPrevented) return;
    bubbleTappedBefore3s = true;
    clearTooltipTimers();
    isAssistantOpen = true;
    if (root) root.classList.add("asistent-open");
    if (overlay) {
      overlay.style.display = "";
      overlay.setAttribute("aria-hidden", "false");
      overlay.classList.add("is-open");
    }
    if (panel) panel.style.display = "";
    if (bubbleWrap) bubbleWrap.style.display = "none";
    document.body.classList.add("asistent-panel-open");
    hideTooltip();
    setPulseNone();
    fetchTodayTasks().then(function () { renderAstaziChat(); });
    loadNotifications();
  }

  function closePanel() {
    if (!isAssistantOpen) return;
    isAssistantOpen = false;
    if (root) root.classList.remove("asistent-open");
    if (overlay) {
      overlay.setAttribute("aria-hidden", "true");
      overlay.classList.remove("is-open");
      overlay.style.display = "none";
    }
    if (panel) panel.style.display = "none";
    if (bubbleWrap) bubbleWrap.style.display = "";
    document.body.classList.remove("asistent-panel-open");
  }

  if (closeBtn) closeBtn.addEventListener("click", closePanel);

  window.addEventListener("popstate", function () {});
  window.addEventListener("pageshow", function (e) {
    if (e.persisted) ensurePanelClosed();
  });

  // --- Tabs ---
  tabButtons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      var tab = this.getAttribute("data-tab");
      tabButtons.forEach(function (b) { b.classList.remove("active"); b.setAttribute("aria-selected", "false"); });
      tabPanels.forEach(function (p) {
        p.classList.remove("active");
        p.hidden = true;
      });
      this.classList.add("active");
      this.setAttribute("aria-selected", "true");
      var panelEl = root.querySelector("#panel-" + tab);
      if (panelEl) {
        panelEl.classList.add("active");
        panelEl.hidden = false;
      }
      if (tab === "intreaba") loadFaqList(faqSearch ? faqSearch.value.trim() : "");
      if (tab === "colaborari") loadCollaborations();
    });
  });

  function loadCollaborations() {
    var colaborariMessages = root.querySelector("#asistent-colaborari-messages");
    if (!colaborariMessages) return;
    if (colaborariLoading) colaborariLoading.hidden = false;
    colaborariMessages.innerHTML = "";
    fetch(apiUrl("/collaborations"), { headers: headers() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (colaborariLoading) colaborariLoading.hidden = true;
        if (!data.ok || !data.items) {
          colaborariMessages.innerHTML = "<div class=\"asistent-colaborari-msg asistent-colaborari-msg-bot\">Nu s-au putut încărca.</div>";
          return;
        }
        if (data.items.length === 0) {
          colaborariMessages.innerHTML = "<div class=\"asistent-colaborari-msg asistent-colaborari-msg-bot\">Nu ai posibile colaborări momentan. Cererile și anunțurile tale vor fi potrivite automat cu oferte și cereri ale altor agenți.</div>";
          return;
        }
        var html = "";
        data.items.forEach(function (group) {
          var myType = group.type;
          var myLabel = escapeHtml(group.my_item.label);
          var myUrl = escapeHtml(group.my_item.url);
          var matches = group.matches || [];
          var matchWord = matches.length === 1 ? "următorul" : "următoarele";
          var matchType = myType === "request" ? "anunț" : "cerere";
          var matchTypePlural = myType === "request" ? "anunțuri" : "cereri";
          var matchTypeLabel = matches.length === 1 ? matchType : matchTypePlural;
          var myTypeLabel = myType === "request" ? "Cererea ta" : "Anunțul tău";
          html += "<div class=\"asistent-colaborari-msg asistent-colaborari-msg-bot\">";
          html += myTypeLabel + " <a href=\"" + myUrl + "\" class=\"asistent-colaborari-link-inline\" target=\"_blank\" rel=\"noopener\">" + myLabel + "</a> se potrivește cu " + matchWord + " " + matchTypeLabel + ":";
          html += "</div>";
          matches.forEach(function (match) {
            var matchLabel = escapeHtml(match.label);
            var matchUrl = escapeHtml(match.url);
            html += "<div class=\"asistent-colaborari-msg asistent-colaborari-msg-bot asistent-colaborari-match\">";
            html += "<a href=\"" + matchUrl + "\" class=\"asistent-colaborari-match-link\" target=\"_blank\" rel=\"noopener\">" + matchLabel + "</a>";
            html += "</div>";
          });
        });
        colaborariMessages.innerHTML = html;
        if (colaborariMessages.scrollHeight > colaborariMessages.clientHeight) {
          colaborariMessages.scrollTop = colaborariMessages.scrollHeight;
        }
        if (data.unread_count > 0) {
          fetch(apiUrl("/collaborations/seen"), { method: "POST", headers: headers() })
            .then(function () {
              hasUnreadCollaborations = false;
              hasUnreadNotifications = hasUnreadAnnouncements || false;
              updateHasUnread(hasUnreadNotifications);
              showMsgBadge(hasUnreadAnnouncements, "Ai primit un mesaj");
            });
        }
      })
      .catch(function () {
        if (colaborariLoading) colaborariLoading.hidden = true;
        var colaborariMessages = root.querySelector("#asistent-colaborari-messages");
        if (colaborariMessages) colaborariMessages.innerHTML = "<div class=\"asistent-colaborari-msg asistent-colaborari-msg-bot\">Eroare la încărcare.</div>";
      });
  }

  function renderAstaziChat() {
    if (!astaziTab || !astaziMessages) return;
    var todoUrl = baseUrl ? baseUrl + "/todo" : "/todo";
    if (todayTasks.length === 0) {
      astaziTab.hidden = true;
      astaziMessages.innerHTML = "";
      return;
    }
    astaziTab.hidden = false;
    var html = "";
    html += "<div class=\"asistent-astazi-msg asistent-astazi-msg-bot\">Astăzi ai de făcut:</div>";
    todayTasks.forEach(function (t) {
      var title = escapeHtml(t.title || "Task");
      var href = t.id ? (todoUrl + "/" + t.id + "/edit") : todoUrl;
      html += "<div class=\"asistent-astazi-msg asistent-astazi-msg-bot\"><a href=\"" + href + "\" class=\"asistent-astazi-task-link\">" + title + "</a></div>";
    });
    astaziMessages.innerHTML = html;
  }

  // --- Guide ---
  function loadGuide() {
    if (!guideTitle) return;
    guideTitle.textContent = "Se încarcă…";
    if (guideIntro) guideIntro.textContent = "";
    if (guideBullets) guideBullets.innerHTML = "";
    if (tipBlock) tipBlock.style.display = "none";
    renderAstaziChat();

    fetch(apiUrl("/context?page_id=" + encodeURIComponent(pageId)), { headers: headers() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok) return;
        if (guideTitle) guideTitle.textContent = data.title || "Ești aici";
        if (guideIntro) guideIntro.textContent = data.intro || "";
        if (guideBullets && data.bullets && data.bullets.length) {
          guideBullets.innerHTML = data.bullets.map(function (b) { return "<li>" + escapeHtml(b) + "</li>"; }).join("");
        }
        if (tipBlock && tipText && data.tip) {
          tipText.textContent = data.tip;
          tipBlock.style.display = "block";
        } else if (tipBlock) tipBlock.style.display = "none";
        renderAstaziChat();
      })
      .catch(function () {
        if (guideTitle) guideTitle.textContent = "Ești aici";
        if (guideIntro) guideIntro.textContent = "Poți explora meniul și modulele.";
        renderAstaziChat();
      });
  }

  // --- FAQ ---
  function loadFaqList(q) {
    if (!faqList) return;
    faqList.innerHTML = "";
    faqList.hidden = false;
    if (faqChat) faqChat.hidden = true;

    var url = q ? apiUrl("/faq/search?q=" + encodeURIComponent(q)) : apiUrl("/faq");
    fetch(url, { headers: headers() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok || !data.items || !data.items.length) {
          faqList.innerHTML = "<p class=\"asistent-muted\">Nicio întrebare găsită.</p>";
          return;
        }
        data.items.forEach(function (item) {
          var btn = document.createElement("button");
          btn.type = "button";
          btn.className = "asistent-faq-item";
          btn.textContent = item.q;
          btn.addEventListener("click", function () { showFaqAnswer(item); });
          faqList.appendChild(btn);
        });
      });
  }

  function scrollToFaqAnswer(botMsgEl) {
    if (!botMsgEl) return;
    setTimeout(function () {
      botMsgEl.scrollIntoView({ behavior: "smooth", block: "end" });
    }, 150);
  }

  function showFaqAnswer(item) {
    if (!faqMessages || !faqList || !faqChat) return;
    faqList.hidden = true;
    faqChat.hidden = false;
    faqMessages.innerHTML = "";

    var userMsg = document.createElement("div");
    userMsg.className = "asistent-msg user";
    userMsg.textContent = item.q;
    faqMessages.appendChild(userMsg);

    var botMsg = document.createElement("div");
    botMsg.className = "asistent-msg bot";
    var a = item.a || "";
    var html = a.split(/\n\n+/).map(function (block) {
      return "<p>" + block.split(/\n/).map(function (line) { return escapeHtml(line).trim(); }).filter(Boolean).join("</p><p>") + "</p>";
    }).join("");
    botMsg.innerHTML = html || "<p></p>";
    faqMessages.appendChild(botMsg);

    var tags = (item.tags || "").toLowerCase();
    var qLower = (item.q || "").toLowerCase();
    var isPriceOrContact = tags.indexOf("pret") !== -1 || tags.indexOf("plati") !== -1 || tags.indexOf("abonament") !== -1 || tags.indexOf("suport") !== -1 || tags.indexOf("whatsapp") !== -1 || qLower.indexOf("preț") !== -1 || qLower.indexOf("pret") !== -1 || qLower.indexOf("activ") !== -1 || qLower.indexOf("contact") !== -1;
    if (isPriceOrContact) {
      var waNum = (waPhone || "").replace(/\D/g, "") || "40764381795";
      var waText = encodeURIComponent("Salut! Doresc să activez abonamentul / am întrebări despre prețuri.");
      var waBtn = document.createElement("a");
      waBtn.href = "https://wa.me/" + waNum + "?text=" + waText;
      waBtn.target = "_blank";
      waBtn.rel = "noopener";
      waBtn.className = "asistent-wa-btn";
      waBtn.textContent = "Contactează pe WhatsApp";
      botMsg.appendChild(waBtn);
    }

    scrollToFaqAnswer(botMsg);
  }

  if (faqBack) faqBack.addEventListener("click", function () {
    if (faqChat) faqChat.hidden = true;
    if (faqList) faqList.hidden = false;
    loadFaqList(faqSearch ? faqSearch.value.trim() : "");
  });

  if (faqSearch) {
    faqSearch.addEventListener("input", function () { loadFaqList(this.value.trim()); });
    faqSearch.addEventListener("search", function () { loadFaqList(this.value.trim()); });
  }

  // --- Init ---
  ensurePanelClosed();
  loadPosition();
  function fetchTodayTasks() {
    return fetch(apiUrl("/today-tasks"), { headers: headers() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.ok && Array.isArray(data.tasks)) todayTasks = data.tasks;
      })
      .catch(function () {});
  }

  function fetchNotificationsInit() {
    fetchTodayTasks();
    fetch(apiUrl("/notifications"), { headers: headers() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.ok) {
          hasUnreadNotifications = !!data.has_unread;
          hasUnreadAnnouncements = !!data.has_unread_announcements;
          hasUnreadCollaborations = !!(data.has_unread_collaborations);
          updateHasUnread(hasUnreadNotifications);
          if (data.has_unread_collaborations) {
            // Verifică dacă există potriviri cu clienți
            var hasClientMatches = data.has_client_matches || false;
            showMsgBadge(true, hasClientMatches ? "Ai o potrivire cu un client" : "Ai o posibilă colaborare");
          } else {
            showMsgBadge(hasUnreadAnnouncements, "Ai primit un mesaj");
          }
        }
        if (!hasUnreadNotifications) scheduleTooltipAndPulse();
      })
      .catch(function () { scheduleTooltipAndPulse(); });
  }
  fetchNotificationsInit();

  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "visible") fetchNotificationsInit();
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", ensurePanelClosed);
  } else {
    ensurePanelClosed();
  }
})();
