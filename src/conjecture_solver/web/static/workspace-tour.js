"use strict";
// First-visit guided tour. It highlights one part of the workspace at a time
// and never blocks the page; replay it from the workspace menu.
window.WorkspaceTour = (() => {
  const seenKey = "simjecture-tour-seen";
  let permissions = {}, knowledgeCapabilities = {};
  function init(data) {
    permissions = data.hosting?.permissions || {};
    knowledgeCapabilities = data.knowledge_capabilities || {};
  }
  const visible = (node) => !!node && node.getClientRects().length > 0 && !node.closest("[hidden]") &&
    !(node.parentElement?.closest("details:not([open])") && node.tagName !== "SUMMARY");
  const pick = (...selectors) => selectors.map((s) => document.querySelector(s)).find(visible) || null;
  const steps = [
    {
      target: () => pick("#quick-start"),
      title: "Ask your agent anything",
      get body() {
        return "Describe a question, a puzzling result or a simulation you want to run. " +
          (permissions.change_model === false
            ? "The hosted agent and model are provided for this workspace."
            : "Choose which agent and model answers from the menu on the right.");
      },
    },
    {
      target: () => pick("#home-knowledge"),
      get title() {
        return knowledgeCapabilities.connect_folders === false
          ? "Reuse earlier conversations" : "Bring your own references";
      },
      get body() {
        return knowledgeCapabilities.connect_folders === false
          ? "Search completed replies from your conversations under Knowledge. Your agent can use them as references in this workspace."
          : "Connect folders of papers and notes under Knowledge. Your agent can search them and cite what it used.";
      },
    },
    {
      target: () => pick(".mode-cards"),
      title: "Two ways to work",
      body: "Interactive is a conversation: you steer each step. Autonomous study runs on its own within a time budget, then an independent review checks the evidence. Start in Interactive; switch to Autonomous study inside the conversation once your claim is clear.",
    },
    {
      target: () => pick("#project-list"),
      title: "Your conversations",
      body: "Each conversation keeps its own files, simulations and studies. Its live runs and outputs appear in the Workspace panel beside the chat.",
    },
    {
      // Opens the Resources group for this step and restores it afterwards.
      prepare: () => {
        const group = document.querySelector(".workspace-resources");
        if (group && !group.open) { reopen = group; group.open = true; }
      },
      available: () => visible(document.querySelector(".workspace-resources summary")),
      target: () => pick('.nav-item[data-view="tools"]'),
      get title() {
        return permissions.install_tools === false
          ? "Explore the available research tools" : "Add research tools when you need them";
      },
      get body() {
        return permissions.install_tools === false
          ? "Open Research tools to see the verified solvers available here. Your administrator manages installation and setup."
          : "Python is ready now. Install solvers such as WarpX from Research tools; setup shows its progress and you can keep working meanwhile.";
      },
    },
  ];
  let index = 0, active = [], ring = null, card = null, returnFocus = null, reopen = null;

  function markSeen() { try { localStorage.setItem(seenKey, "true"); } catch {} }
  function seen() { try { return localStorage.getItem(seenKey) === "true"; } catch { return true; } }

  function escape(event) {
    // The tour is non-modal: Escape also works after focus moves into the page.
    // Let an open modal dialog or a control handling Escape dismiss itself first.
    if (event.key === "Escape" && !event.defaultPrevented && !document.querySelector("dialog[open]")) {
      event.preventDefault();
      stop();
    }
  }

  function build() {
    ring = document.createElement("div");
    ring.className = "tour-ring";
    ring.setAttribute("aria-hidden", "true");
    card = document.createElement("section");
    card.className = "tour-card";
    card.setAttribute("role", "dialog");
    card.setAttribute("aria-modal", "false");
    card.setAttribute("aria-labelledby", "tour-title");
    card.setAttribute("aria-describedby", "tour-body");
    card.tabIndex = -1;
    card.innerHTML = `
      <p class="tour-step" id="tour-step"></p>
      <h2 id="tour-title"></h2>
      <p id="tour-body"></p>
      <div class="tour-actions">
        <button type="button" class="quiet tour-skip">Skip tour</button>
        <span class="tour-nav">
          <button type="button" class="secondary tour-back">Back</button>
          <button type="button" class="primary tour-next">Next</button>
        </span>
      </div>`;
    card.querySelector(".tour-skip").onclick = () => stop();
    card.querySelector(".tour-back").onclick = () => go(index - 1);
    card.querySelector(".tour-next").onclick = () => (index >= active.length - 1 ? stop() : go(index + 1));
    card.addEventListener("keydown", (event) => {
      if (event.key === "ArrowRight") { event.preventDefault(); card.querySelector(".tour-next").click(); }
      else if (event.key === "ArrowLeft" && index > 0) { event.preventDefault(); go(index - 1); }
    });
    document.body.append(ring, card);
    document.addEventListener("keydown", escape);
    addEventListener("resize", place);
    addEventListener("scroll", place, true);
  }

  function place() {
    if (!card) return;
    const target = active[index]?.target();
    if (!target) return stop();
    const box = target.getBoundingClientRect();
    const pad = 6;
    Object.assign(ring.style, {
      top: `${box.top - pad}px`, left: `${box.left - pad}px`,
      width: `${box.width + pad * 2}px`, height: `${box.height + pad * 2}px`,
    });
    const width = Math.min(340, innerWidth - 24);
    card.style.width = `${width}px`;
    const height = card.offsetHeight;
    // Prefer below, then above, then beside the target; always stay on screen.
    let top = box.bottom + 14, left = box.left;
    if (top + height > innerHeight - 12) top = box.top - height - 14;
    if (top < 12) {
      top = Math.min(Math.max(12, box.top), innerHeight - height - 12);
      left = box.right + 14 + width <= innerWidth - 12 ? box.right + 14 : box.left - width - 14;
    }
    left = Math.min(Math.max(12, left), innerWidth - width - 12);
    card.style.top = `${Math.max(12, top)}px`;
    card.style.left = `${left}px`;
  }

  function go(next) {
    index = Math.max(0, Math.min(next, active.length - 1));
    const step = active[index];
    if (reopen && !step.prepare) { reopen.open = false; reopen = null; }
    step.prepare?.();
    const target = step.target();
    if (!target) { active.splice(index, 1); if (!active.length) return stop(); return go(index); }
    target.scrollIntoView({block: "nearest", inline: "nearest"});
    card.querySelector("#tour-step").textContent = `${index + 1} of ${active.length}`;
    card.querySelector("#tour-title").textContent = step.title;
    card.querySelector("#tour-body").textContent = step.body;
    card.querySelector(".tour-back").hidden = index === 0;
    card.querySelector(".tour-next").textContent = index === active.length - 1 ? "Done" : "Next";
    place();
    requestAnimationFrame(place);
    card.focus({preventScroll: true});
  }

  function start() {
    stop(false);
    if (typeof view === "function" && state?.view !== "home") view("home");
    active = steps.filter((step) => (step.available || step.target)());
    if (!active.length) return;
    returnFocus = document.activeElement;
    build();
    go(0);
  }

  function stop(remember = true) {
    const restoreFocus = card?.contains(document.activeElement);
    if (remember) markSeen();
    document.removeEventListener("keydown", escape);
    removeEventListener("resize", place);
    removeEventListener("scroll", place, true);
    if (reopen) { reopen.open = false; reopen = null; }
    ring?.remove(); card?.remove();
    ring = card = null;
    if (remember && restoreFocus && visible(returnFocus)) returnFocus.focus({preventScroll: true});
    returnFocus = null;
  }

  // Automated browsers (tests, screenshots) get the tour only when asked for.
  function maybeStart() {
    const forced = new URLSearchParams(location.search).has("tour");
    if (!forced && (seen() || navigator.webdriver)) return;
    if (document.querySelector("dialog[open]")) return;
    if (typeof state !== "undefined" && state.view !== "home") return;
    start();
  }

  return {init, start, stop, maybeStart, get open() { return !!card; }};
})();
