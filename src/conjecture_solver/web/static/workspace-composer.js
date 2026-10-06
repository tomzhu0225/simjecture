"use strict";
window.WorkspaceComposer = (() => {
  const editors = new Map();
  function mount(form, input, controls, scope) {
    form.classList.add("prompt-composer");
    if (form.querySelector(".composer-attach")) form.classList.add("has-attachments");
    const toolbar = form.querySelector(".composer-bottom, .start-bottom");
    const picker = form.querySelector(`#${scope}-agent-picker`);
    const summary = picker.querySelector(".agent-picker-summary");
    const popup = document.createElement("div");
    popup.className = "agent-picker-popup";
    popup.id = `${scope}-agent-popup`;
    popup.setAttribute("popover", "auto");
    popup.setAttribute("role", "dialog");
    popup.setAttribute("aria-label", "Agent and model settings");
    picker.setAttribute("popovertarget", popup.id);
    picker.setAttribute("aria-controls", popup.id);
    controls.before(picker);
    popup.append(controls);
    toolbar.append(popup);
    function positionPopup() {
      const box = picker.getBoundingClientRect();
      const width = Math.min(320, window.innerWidth - 24);
      popup.style.width = `${width}px`;
      popup.style.left = `${Math.max(12, Math.min(box.right - width, window.innerWidth - width - 12))}px`;
      popup.style.top = "auto";
      popup.style.bottom = `${Math.max(12, window.innerHeight - box.top + 10)}px`;
      popup.style.maxHeight = `${Math.max(120, box.top - 22)}px`;
    }
    picker.addEventListener("click", positionPopup);
    popup.addEventListener("toggle", event => {
      picker.setAttribute("aria-expanded", String(event.newState === "open"));
      if (event.newState === "open") positionPopup();
    });
    const expand = document.createElement("button");
    expand.type = "button";
    expand.className = "composer-expand";
    expand.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 4h6v6M20 4l-7 7M10 20H4v-6M4 20l7-7"/></svg>';
    expand.setAttribute("aria-label", "Expand message editor");
    expand.setAttribute("aria-expanded", "false");
    expand.hidden = true;
    form.append(expand);
    let expanded = false;
    let frame = 0;
    function fit() {
      if (!form.getBoundingClientRect().width) return;
      if (!input.value) expanded = false;
      const style = getComputedStyle(form);
      const attach = form.querySelector(".composer-attach");
      const available = form.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight)
        - toolbar.getBoundingClientRect().width - parseFloat(style.columnGap)
        - (attach ? attach.getBoundingClientRect().width + parseFloat(style.columnGap) : 0);
      // Use the compact width even when the draft is already expanded. This
      // avoids flipping between two layouts on successive renders.
      input.style.width = `${Math.max(40, available)}px`;
      input.style.height = "0px";
      const line = parseFloat(getComputedStyle(input).lineHeight) || 24;
      const multiline = !!input.value && (input.scrollHeight > line + 3 || input.value.includes("\n"));
      input.style.width = "";
      form.classList.toggle("is-multiline", multiline || expanded);
      form.classList.toggle("is-expanded", expanded);
      input.style.height = "0px";
      // A wrapped placeholder is not a draft. Keep an empty editor on one
      // line, matching its initial CSS layout on narrow screens.
      const content = input.value ? input.scrollHeight : line;
      const limit = expanded ? Math.min(window.innerHeight * .56, 560) : Math.min(window.innerHeight * .3, 220);
      input.style.height = `${Math.max(line, expanded ? limit : Math.min(content, limit))}px`;
      input.style.overflowY = content > limit ? "auto" : "hidden";
      expand.hidden = content <= line * 5 && !expanded;
      expand.setAttribute("aria-label", expanded ? "Collapse message editor" : "Expand message editor");
      expand.title = expanded ? "Collapse message editor" : "Expand message editor";
      expand.setAttribute("aria-expanded", String(expanded));
      form.classList.toggle("has-editor-expand", !expand.hidden);
    }
    function update() {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(fit);
    }
    expand.onclick = () => { expanded = !expanded; fit(); input.focus(); };
    input.addEventListener("input", update);
    input.addEventListener("keydown", event => {
      if (event.key === "Escape" && expanded) { expanded = false; update(); }
    });
    // Observe width only. Height changes from fitting must not trigger a loop.
    let width = 0;
    new ResizeObserver(entries => {
      const next = entries[0].contentRect.width;
      if (next !== width) { width = next; update(); }
    }).observe(form);
    window.addEventListener("resize", () => { update(); if (popup.matches(":popover-open")) positionPopup(); });
    editors.set(input.id, { update, fit, picker, popup, summary, controls });
    update();
    refresh(scope);
  }
  function refresh(scope) {
    const editor = editors.get(scope === "home" ? "first-request" : "chat-input");
    if (!editor) return;
    const selects = editor.controls.querySelectorAll("select");
    const backend = selects[0], model = selects[1];
    const custom = editor.controls.querySelector('input[placeholder="Exact model ID"]');
    const name = model?.value === "__custom__" ? custom?.value : model?.selectedOptions[0]?.textContent;
    editor.picker.disabled = !backend?.options.length;
    editor.summary.textContent = editor.picker.disabled ? "Loading agent…" : name || backend?.value || "Choose agent";
    editor.picker.title = `${backend?.value || "Agent"} · ${name || "Choose model"}`;
    editor.update();
  }
  function open(scope) {
    const editor = editors.get(scope === "home" ? "first-request" : "chat-input");
    if (!editor) return;
    if (!editor.popup.matches(":popover-open")) editor.picker.click();
  }
  function update(id) { editors.get(id)?.update(); }
  return { mount, refresh, open, update };
})();
