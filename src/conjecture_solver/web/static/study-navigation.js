"use strict";

// URL-backed context shared by the conversation and detailed study views.
// A campaign's owning conversation comes from the server, never a return URL.
window.StudyNavigation = (() => {
  function workspace(project, campaign, view = "autonomous", options = {}) {
    const {space, ...rest} = options;
    const selectedSpace = space || new URLSearchParams(globalThis.location?.search || "").get("workspace");
    const query = selectedSpace && selectedSpace !== "personal" ? `?${new URLSearchParams({workspace:selectedSpace})}` : "";
    const params = { project, view, ...(campaign ? { study: campaign } : {}), ...rest };
    return `/workspace${query}#${new URLSearchParams(params)}`;
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
  function render(container, { project, campaign, page, title = "", space }) {
    container.replaceChildren();
    const list = document.createElement("ul");
    const items = [
      [SimjectureI18n.live(() => project ? SimjectureI18n.t("ui.conversation") : SimjectureI18n.t("ui.workspace")), project ? workspace(project, campaign, "interactive", {space}) : "/workspace", "conversation"],
      [SimjectureI18n.live(() => project ? SimjectureI18n.t("ui.study") : SimjectureI18n.t("ui.standalone-study")), project ? workspace(project, campaign, "autonomous", {space}) : null, "study"],
      [SimjectureI18n.message("ui.evidence-review-2"), campaign ? evidence(campaign) : null, "evidence"],
    ];
    for (const [label, href, step] of items) {
      const item = document.createElement("li");
      const link = document.createElement(href && step !== page ? "a" : "span");
      SimjectureI18n.content(link, label);
      if (href && step !== page) link.href = href;
      if (step === page) link.setAttribute("aria-current", "page");
      else if (!href) link.setAttribute("aria-disabled", "true");
      if (step === "study" && title) SimjectureI18n.attribute(link, "title", () => title);
      if (step === "evidence" && !campaign) SimjectureI18n.attribute(link, "title", () => SimjectureI18n.t("ui.available-after-a-study-is-started"));
      item.append(link);
      list.append(item);
    }
    container.append(list);
  }
  return { workspace, evidence, selected, render };
})();
