"use strict";
(() => {
  if (!document.querySelector('meta[name="simjecture-hosted"]')) return;
  const lease = crypto.randomUUID();
  let csrf = "", busy = false, leaving = false;
  async function heartbeat() {
    if (busy || leaving) return;
    busy = true;
    try {
      const response = await fetch("/api/me");
      if (!response.ok) return;
      const profile = await response.json();
      csrf = profile.csrf_token;
      await fetch("/api/session/heartbeat", {
        method: "POST", headers: {"Content-Type": "application/json", "X-CSRF-Token": csrf},
        body: JSON.stringify({lease}),
      });
    } catch {} finally {busy = false;}
  }
  window.addEventListener("pagehide", () => {
    leaving = true;
    if (csrf) navigator.sendBeacon("/api/session/leave", new Blob(
      [JSON.stringify({lease, csrf})], {type: "application/json"},
    ));
  });
  window.addEventListener("pageshow", () => {leaving = false; heartbeat();});
  document.addEventListener("visibilitychange", () => {if (!document.hidden) heartbeat();});
  setInterval(heartbeat, 20000);
  // Workspace admission may create its cookie after this script starts.
  setTimeout(heartbeat, 3000);
})();
