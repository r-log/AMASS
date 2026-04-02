/**
 * Offline banner - shows when offline, hides when online.
 * Displays pending queue count when available.
 */
(function () {
  if (typeof document === "undefined") return;

  const banner = document.createElement("div");
  banner.id = "offline-banner";
  banner.setAttribute(
    "style",
    "display:none;position:fixed;top:0;left:0;right:0;z-index:1100;" +
      "background:linear-gradient(90deg,#f59e0b,#ef4444);color:#fff;" +
      "padding:10px 20px;font-size:14px;font-weight:600;text-align:center;" +
      "box-shadow:0 2px 10px rgba(0,0,0,0.3);"
  );
  banner.textContent = "You are offline. Requests will sync when connected.";

  function updateBanner() {
    const online = navigator.onLine;
    if (online) {
      banner.style.display = "none";
      return;
    }
    banner.style.display = "block";
    if (window.offlineQueue && typeof window.offlineQueue.getQueuedCount === "function") {
      window.offlineQueue.getQueuedCount().then((n) => {
        if (n > 0) {
          banner.textContent =
            "You are offline. " + n + " request(s) waiting to sync when connected.";
        } else {
          banner.textContent = "You are offline. Requests will sync when connected.";
        }
      });
    } else {
      banner.textContent = "You are offline. Requests will sync when connected.";
    }
  }

  function init() {
    document.body.appendChild(banner);
    updateBanner();
    window.addEventListener("online", updateBanner);
    window.addEventListener("offline", updateBanner);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
