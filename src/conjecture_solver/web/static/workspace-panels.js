"use strict";
window.WorkspacePanels = (() => {
  const $ = (id) => document.getElementById(id);
  const collapsed = { left: false, right: false };
  const sizes = { left: 224, right: 320 };
  const clamp = (n, min, max) => Math.min(max, Math.max(min, n));
  const store = (key, value) => {
    try {
      localStorage.setItem(key, String(value));
    } catch {}
  };
  for (const side of Object.keys(collapsed)) {
    try {
      collapsed[side] =
        localStorage.getItem(`simjecture-${side}-collapsed`) === "true";
      const saved = Number(localStorage.getItem(`simjecture-${side}-width`));
      if (Number.isFinite(saved) && saved >= 160 && saved <= 800)
        sizes[side] = saved;
    } catch {}
  }
  function positionTab() {
    const inspector = $("research-inspector");
    if (
      inspector &&
      !collapsed.right &&
      inspector.getBoundingClientRect().width
    )
      document.documentElement.style.setProperty(
        "--inspector-edge",
        `${inspector.getBoundingClientRect().left}px`,
      );
  }
  function apply() {
    document.documentElement.style.setProperty(
      "--navigation-width",
      `${sizes.left}px`,
    );
    for (const side of Object.keys(collapsed)) {
      document.documentElement.toggleAttribute(
        `data-${side}-collapsed`,
        collapsed[side],
      );
      const button = $(`${side}-sidebar-toggle`);
      if (button) {
        const label = `${collapsed[side] ? "Expand" : "Collapse"} ${side} sidebar`;
        button.setAttribute("aria-label", label);
        button.setAttribute("aria-expanded", String(!collapsed[side]));
        button.title = `${label} · drag to resize`;
        button.querySelector("span").textContent =
          (side === "left") === collapsed[side] ? "›" : "‹";
      }
    }
    const handle = $("left-sidebar-resizer");
    if (handle) {
      handle.setAttribute("aria-valuemin", "0");
      handle.setAttribute("aria-valuemax", "380");
      handle.setAttribute(
        "aria-valuenow",
        collapsed.left ? "0" : String(Math.round(sizes.left)),
      );
    }
    requestAnimationFrame(positionTab);
  }
  function resize() {
    const split = $("research-layout");
    if (
      !split ||
      !split.getBoundingClientRect().width ||
      split.orientation === "vertical"
    )
      return;
    if (!collapsed.right)
      split.positionInPixels = clamp(
        sizes.right,
        220,
        split.getBoundingClientRect().width * 0.65,
      );
    requestAnimationFrame(positionTab);
  }
  function set(side, value) {
    const changed = collapsed[side] !== value;
    collapsed[side] = value;
    store(`simjecture-${side}-collapsed`, value);
    apply();
    if (side === "right" && !value && changed) resize();
  }
  function dragSize(side, x) {
    const width =
      side === "left"
        ? x
        : $("research-layout").getBoundingClientRect().right - x;
    if (width < 56) {
      set(side, true);
      return;
    }
    set(side, false);
    sizes[side] = clamp(
      width,
      side === "left" ? 176 : 220,
      side === "left" ? 380 : 800,
    );
    store(`simjecture-${side}-width`, sizes[side]);
    apply();
    if (side === "right") resize();
  }
  function draggable(element, side, clickable) {
    let suppressClick = false;
    element.addEventListener("pointerdown", (event) => {
      if (event.button !== 0) return;
      event.preventDefault();
      const origin = event.clientX;
      let moved = false;
      const move = (e) => {
        if (!moved && Math.abs(e.clientX - origin) < 5) return;
        moved = true;
        document.documentElement.classList.add("resizing-panels");
        dragSize(side, e.clientX);
      };
      const finish = () => {
        window.removeEventListener("pointermove", move);
        window.removeEventListener("pointerup", finish);
        window.removeEventListener("pointercancel", finish);
        document.documentElement.classList.remove("resizing-panels");
        suppressClick = moved;
        setTimeout(() => {
          suppressClick = false;
        }, 0);
      };
      window.addEventListener("pointermove", move);
      window.addEventListener("pointerup", finish);
      window.addEventListener("pointercancel", finish);
    });
    if (clickable)
      element.onclick = () => {
        if (!suppressClick) set(side, !collapsed[side]);
      };
  }
  apply();
  document.addEventListener("DOMContentLoaded", () => {
    for (const side of Object.keys(collapsed))
      draggable($(`${side}-sidebar-toggle`), side, true);
    const handle = $("left-sidebar-resizer");
    draggable(handle, "left", false);
    handle.ondblclick = () => set("left", true);
    handle.onkeydown = (e) => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End", "Enter"].includes(e.key))
        return;
      e.preventDefault();
      if (e.key === "Home" || e.key === "Enter") {
        set("left", true);
        $("left-sidebar-toggle").focus();
      } else
        dragSize(
          "left",
          e.key === "End"
            ? 224
            : sizes.left + (e.key === "ArrowLeft" ? -24 : 24),
        );
    };
    customElements.whenDefined("wa-split-panel").then(() => {
      const split = $("research-layout");
      let initialized = false;
      new ResizeObserver(() => {
        if (
          !initialized &&
          split.getBoundingClientRect().width &&
          split.orientation !== "vertical"
        ) {
          initialized = true;
          requestAnimationFrame(resize);
        }
        positionTab();
      }).observe(split);
      new ResizeObserver(positionTab).observe($("research-inspector"));
      split.addEventListener("wa-reposition", () => {
        if (
          !initialized ||
          collapsed.right ||
          split.orientation === "vertical" ||
          !split.getBoundingClientRect().width
        )
          return;
        const width =
          (split.position / 100) * split.getBoundingClientRect().width;
        if (width < 56) set("right", true);
        else if (width >= 220 && width <= 800) {
          sizes.right = width;
          store("simjecture-right-width", width);
        }
        requestAnimationFrame(positionTab);
      });
    });
    window.addEventListener("resize", positionTab);
    apply();
  });
  return { set, resize };
})();
