"use strict";
window.WorkspaceTheme = (() => {
  const system = matchMedia("(prefers-color-scheme: dark)");
  let choice;
  try {
    choice = localStorage.getItem("simjecture-theme");
  } catch {}
  function apply(theme) {
    document.documentElement.dataset.theme = theme;
    document.documentElement.classList.toggle("wa-dark", theme === "dark");
    document.documentElement.classList.toggle("wa-light", theme === "light");
    window.dispatchEvent(new Event("workspace-theme"));
  }
  function set(theme) {
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
