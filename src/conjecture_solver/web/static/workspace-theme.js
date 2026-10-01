"use strict";
window.WorkspaceTheme = (() => {
  const system = matchMedia("(prefers-color-scheme: dark)");
  let choice;
  try {
    choice = localStorage.getItem("simjecture-theme");
    if (!["dark", "light"].includes(choice)) choice = null;
  } catch {}
  function apply(theme) {
    document.documentElement.dataset.theme = theme;
    document.documentElement.classList.toggle("wa-dark", theme === "dark");
    document.documentElement.classList.toggle("wa-light", theme === "light");
    window.dispatchEvent(new Event("workspace-theme"));
  }
  function set(theme) {
    if (!["dark", "light"].includes(theme)) return;
    choice = theme;
    try {
      localStorage.setItem("simjecture-theme", theme);
    } catch {}
    apply(theme);
  }
  apply(
    ["dark", "light"].includes(choice)
      ? choice
      : system.matches
        ? "dark"
        : "light",
  );
  system.addEventListener("change", () => {
    if (!choice) apply(system.matches ? "dark" : "light");
  });
  return { set };
})();

// Move keyboard focus without replacing a conversation's hash-based route.
document.addEventListener("DOMContentLoaded", () => {
  document.querySelector(".skip-link")?.addEventListener("click", (event) => {
    event.preventDefault();
    document.getElementById("main-content")?.focus();
  });
});
