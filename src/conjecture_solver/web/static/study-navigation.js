"use strict";

// URL-backed context shared by the conversation and detailed study views.
// A campaign's owning conversation comes from the server, never a return URL.
window.StudyNavigation = (() => {
  function workspace(project, campaign, view = "autonomous", options = {}) {
    const params = { project, view, ...(campaign ? { study: campaign } : {}), ...options };
    return `/workspace#${new URLSearchParams(params)}`;
  }
  function evidence(campaign) {
    return `/monitor?${new URLSearchParams({ campaign })}`;
  }
  function selected(project, requested) {
    const studies = project?.studies || [];
    if (studies.some((study) => study.campaign === requested)) return requested;
    if (requested && project?.continuation_draft?.campaign === requested) return requested;
    return studies.at(-1)?.campaign || project?.continuation_draft?.campaign || null;
  }
  function render(container, { project, campaign, page, title = "" }) {
    container.replaceChildren();
    const list = document.createElement("ul");
    const items = [
      [project ? "Conversation" : "Workspace", project ? workspace(project, campaign, "interactive") : "/workspace", "conversation"],
      [project ? "Study" : "Standalone study", project ? workspace(project, campaign) : null, "study"],
      ["Evidence & review", campaign ? evidence(campaign) : null, "evidence"],
    ];
    for (const [label, href, step] of items) {
      const item = document.createElement("li");
      const link = document.createElement(href && step !== page ? "a" : "span");
      link.textContent = label;
      if (href && step !== page) link.href = href;
      if (step === page) link.setAttribute("aria-current", "page");
      else if (!href) link.setAttribute("aria-disabled", "true");
      if (step === "study" && title) link.title = title;
      if (step === "evidence" && !campaign) link.title = "Available after a study is started";
      item.append(link);
      list.append(item);
    }
    container.append(list);
  }
  return { workspace, evidence, selected, render };
})();
