"use strict";
window.WorkspacePanels = (() => {
  const collapsed = { left: false, right: false };
  for (const side of Object.keys(collapsed)) {
    try {
      collapsed[side] =
        localStorage.getItem(`simjecture-${side}-collapsed`) === "true";
    } catch {}
  }
  function apply() {
    for (const side of Object.keys(collapsed)) {
      document.documentElement.toggleAttribute(
        `data-${side}-collapsed`,
        collapsed[side],
      );
      const button = document.getElementById(`${side}-sidebar-toggle`);
      if (button) {
        button.textContent = `${collapsed[side] ? "Show" : "Hide"} ${side} sidebar`;
        button.setAttribute("aria-expanded", String(!collapsed[side]));
      }
    }
  }
  function set(side, value) {
    collapsed[side] = value;
    try {
      localStorage.setItem(`simjecture-${side}-collapsed`, String(value));
    } catch {}
    apply();
  }
  apply();
  document.addEventListener("DOMContentLoaded", () => {
    for (const side of Object.keys(collapsed))
      document.getElementById(`${side}-sidebar-toggle`).onclick = () =>
        set(side, !collapsed[side]);
    apply();
  });
  return { set };
})();
