// Web Awesome 3.14.0, locally vendored. No CDN or build server at runtime.
import "./vendor/webawesome-3.14.0/components/split-panel/split-panel.js";
import "./vendor/webawesome-3.14.0/components/tab-group/tab-group.js";
import "./vendor/webawesome-3.14.0/components/tab/tab.js";
import "./vendor/webawesome-3.14.0/components/tab-panel/tab-panel.js";
import "./vendor/webawesome-3.14.0/components/spinner/spinner.js";
import "./vendor/webawesome-3.14.0/components/drawer/drawer.js";

// A mouse wheel should reveal clipped inspector tabs as well as a trackpad.
customElements.whenDefined("wa-tab-group").then(async () => {
  const inspector = document.getElementById("inspector-tabs");
  if (!inspector) return;
  await inspector.updateComplete;
  const nav = inspector.nav;
  nav.addEventListener("wheel", event => {
    if (event.ctrlKey || nav.scrollWidth <= nav.clientWidth) return;
    const delta = Math.abs(event.deltaX) > Math.abs(event.deltaY) ? event.deltaX : event.deltaY;
    const before = nav.scrollLeft;
    nav.scrollLeft += delta;
    if (nav.scrollLeft !== before) event.preventDefault();
  }, { passive: false });
});
