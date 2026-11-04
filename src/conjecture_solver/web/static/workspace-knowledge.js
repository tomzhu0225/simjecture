"use strict";
window.WorkspaceKnowledge = (() => {
  let enabled = false, sources = [], category = "all", selected = null, request = 0, previewRequest = 0;
  let homeSelection = null, pickerScope = "home", pickerProject = null, access = null, sourceRevision = "";
  const drafts = new Map();
  const names = {all:SimjectureI18n.message("ui.all"),code:SimjectureI18n.message("ui.code"),papers:SimjectureI18n.message("ui.papers"),slides:SimjectureI18n.message("ui.slides"),documents:SimjectureI18n.message("ui.documents"),conversations:SimjectureI18n.message("ui.conversations"),studies:SimjectureI18n.message("ui.studies")};
  const refs = key => drafts.get(key) || [];
  const key = () => state.view === "project" && state.project ? state.project.id : "home";
  const ago = value => (value ? new Date(value * 1000).toLocaleString() : SimjectureI18n.t("ui.not-indexed-yet"));
  function error(message) { $("knowledge-error").hidden = !message; SimjectureI18n.content($("knowledge-error"), message); }
  function button(label, handler, cls = "secondary") {
    const node = el("button", label, cls); node.type = "button"; node.onclick = handler; return node;
  }
  function init(data) {
    enabled = !!data.knowledge_available;
    if (!enabled) return;
    $("knowledge-nav").hidden = false;
    $("home-knowledge").hidden = false;
    $("conversation-knowledge").hidden = false;
    $("knowledge-connect").disabled = state.readonly;
    $("knowledge-connect").hidden = data.knowledge_capabilities?.connect_folders === false;
    document.querySelector('[data-knowledge-tab="access"]').hidden = data.knowledge_capabilities?.external_access === false;
    if (hosted) SimjectureI18n.bindText(document.querySelector("#knowledge-sources-panel .knowledge-section-intro p"), () => SimjectureI18n.t("ui.completed-replies-from-your-conversations-in-this-workspace-search-a"));
    if (hosted) SimjectureI18n.bindText($("knowledge-privacy-note"), () => SimjectureI18n.t("ui.private-to-your-account-and-workspace"));
    $("knowledge-refresh").disabled = state.readonly;
    for (const [value, name] of Object.entries(names)) {
      if (data.knowledge_capabilities?.kinds && !data.knowledge_capabilities.kinds.includes(value)) continue;
      const node = button(name, () => {
        category = value;
        for (const child of $("knowledge-kinds").children) child.setAttribute("aria-pressed", String(child === node));
        search();
      });
      node.setAttribute("aria-pressed", String(value === category));
      $("knowledge-kinds").append(node);
    }
    for (const node of document.querySelectorAll("[data-knowledge-tab]")) node.onclick = () => tab(node.dataset.knowledgeTab);
    $("knowledge-connect").onclick = () => {
      SimjectureI18n.content($("knowledge-folder-error"), "");
      $("knowledge-folder-dialog").showModal(); $("knowledge-folder-path").focus();
    };
    $("knowledge-folder-close").onclick = () => $("knowledge-folder-dialog").close();
    $("knowledge-folder-form").onsubmit = async event => {
      event.preventDefault(); const submit = event.submitter; submit.disabled = true;
      try {
        await api("knowledge-source", {
          path: $("knowledge-folder-path").value, name: $("knowledge-folder-name").value,
          excludes: $("knowledge-folder-excludes").value.split("\n").map(x => x.trim()).filter(Boolean),
        });
        $("knowledge-folder-dialog").close(); $("knowledge-folder-form").reset();
        await refresh(); tab("sources"); toast(SimjectureI18n.message("ui.folder-connected-indexing-has-started"));
      } catch (err) { SimjectureI18n.content($("knowledge-folder-error"), err.message); }
      finally { submit.disabled = false; }
    };
    $("knowledge-search-form").onsubmit = event => { event.preventDefault(); search(); };
    $("knowledge-source-filter").onchange = search;
    $("knowledge-refresh").onclick = () => action($("knowledge-refresh"), async () => {
      await api("knowledge-refresh", {}); toast(SimjectureI18n.message("ui.checking-connected-sources-for-changes")); await refresh();
    });
    $("home-knowledge-picker").onclick = () => choose("home");
    $("conversation-knowledge-picker").onclick = () => choose("conversation");
    $("knowledge-selection-close").onclick = () => $("knowledge-selection-dialog").close();
    $("knowledge-inherit").onchange = () => {
      for (const input of $("knowledge-selection-list").querySelectorAll("input")) input.disabled = $("knowledge-inherit").checked;
    };
    $("knowledge-save-selection").onclick = async () => {
      const submit = $("knowledge-save-selection"); submit.disabled = true;
      try {
        const selection = $("knowledge-inherit").checked ? null : [...$("knowledge-selection-list").querySelectorAll("input:checked")].map(n => n.value);
        if (pickerScope === "home") homeSelection = selection;
        else {
          await api("knowledge-selection", {project: pickerProject, sources: selection});
          if (state.project?.id === pickerProject) state.project.knowledge_sources = selection;
        }
        const draftKey = pickerScope === "home" ? "home" : pickerProject;
        if (selection !== null) drafts.set(draftKey, refs(draftKey).filter(ref => selection.includes(ref.source)));
        $("knowledge-selection-dialog").close(); renderComposer();
      } catch (err) { SimjectureI18n.content($("knowledge-selection-error"), err.message); }
      finally { submit.disabled = false; }
    };
    $("knowledge-copy-mcp").onclick = () => action($("knowledge-copy-mcp"), async () => {
      await navigator.clipboard.writeText(JSON.stringify(access.mcp, null, 2)); toast(SimjectureI18n.message("ui.mcp-configuration-copied"));
    });
    refresh().catch(err => error(err.message));
  }
  async function refresh() {
    if (!enabled) return;
    const data = await api("knowledge-status");
    sources = data.sources;
    SimjectureI18n.content($("knowledge-source-count"), sources.filter(s => s.enabled).length);
    const previous = $("knowledge-source-filter").value;
    $("knowledge-source-filter").replaceChildren(SimjectureI18n.bindText(new Option("", ""), () => SimjectureI18n.t("ui.all-connected-sources")));
    for (const source of sources.filter(s => s.enabled)) $("knowledge-source-filter").add(new Option(source.name, source.id));
    if (sources.some(s => s.id === previous && s.enabled)) $("knowledge-source-filter").value = previous;
    const revision = JSON.stringify(sources);
    if (revision !== sourceRevision) {
      sourceRevision = revision; renderSources();
      if (state.view === "knowledge" && !$("knowledge-search-panel").hidden) await search();
    }
    renderComposer();
  }
  function tab(name) {
    for (const node of document.querySelectorAll("[data-knowledge-tab]")) {
      if (node.dataset.knowledgeTab === name) node.setAttribute("aria-current", "page");
      else node.removeAttribute("aria-current");
    }
    for (const section of ["search","sources","access"]) $(`knowledge-${section}-panel`).hidden = name !== section;
    if (name === "access") api("knowledge-access").then(data => {
      access = data;
      SimjectureI18n.content($("knowledge-mcp-config"), JSON.stringify(data.mcp, null, 2));
      SimjectureI18n.content($("knowledge-cli"), data.cli);
      SimjectureI18n.content($("knowledge-sync-cli"), data.sync);
    }).catch(err => error(err.message));
  }
  async function show() {
    if (!enabled) return;
    error(""); await refresh();
    if (!$("knowledge-results").children.length) await search();
  }
  async function search() {
    if (!enabled) return;
    const serial = ++request, query = $("knowledge-query").value.trim();
    const params = new URLSearchParams({q: query, kind: category});
    if ($("knowledge-source-filter").value) params.set("source", $("knowledge-source-filter").value);
    SimjectureI18n.bindText($("knowledge-results-summary"), () => SimjectureI18n.t("ui.searching"));
    try {
      const data = await api(`knowledge-search?${params}`);
      if (serial !== request) return;
      error(""); $("knowledge-results").replaceChildren();
      const indexing = sources.some(s => s.enabled && ["pending","indexing"].includes(s.state));
      SimjectureI18n.bindText($("knowledge-results-summary"), () => `${data.results.length}${(data.results.length === 30 ? "+" : "")} ${(query ? SimjectureI18n.t("ui.matching-sources") : SimjectureI18n.t("ui.recent-sources"))}${(indexing ? SimjectureI18n.t("ui.library-is-updating") : "")}`);
      for (const item of data.results) {
        const node = button("", () => preview(item), "knowledge-result");
        node.classList.toggle("selected", selected?.id === item.id);
        node.dataset.document = item.id;
        node.append(el("span", `${names[item.kind] || item.kind} · ${item.source_name}`, "knowledge-result-meta"),
          el("h3", item.title), el("p", item.snippet || item.location), el("p", item.path, "knowledge-result-path"));
        $("knowledge-results").append(node);
      }
      if (!data.results.length) {
        const empty = el("div", undefined, "knowledge-empty");
        empty.append(el("h2", SimjectureI18n.live(() => query ? SimjectureI18n.t("ui.no-matching-sources-yet") : SimjectureI18n.t("ui.your-research-within-reach"))));
        empty.append(el("p", SimjectureI18n.live(() => query ? SimjectureI18n.t("ui.try-a-distinctive-phrase-a-filename-or-fewer-words-check-sources-if-") : (hosted ? SimjectureI18n.t("ui.completed-replies-from-your-conversations-in-this-workspace-will-app") : SimjectureI18n.t("ui.connect-a-research-folder-to-find-papers-code-and-notes-completed-co")))));
        empty.append(button(SimjectureI18n.message("ui.view-connected-sources"), () => tab("sources")));
        $("knowledge-results").append(empty);
      }
    } catch (err) { if (serial === request) { error(err.message); SimjectureI18n.bindText($("knowledge-results-summary"), () => SimjectureI18n.t("ui.search-could-not-finish")); } }
  }
  async function preview(item, navigate = true) {
    const serial = ++previewRequest;
    const params = new URLSearchParams({id:item.id, chunk:item.chunk || 0});
    if (item.revision) params.set("revision", item.revision);
    try {
      const result = await api(`knowledge-read?${params}`);
      if (serial !== previewRequest) return;
      selected = result; error(""); tab("search");
      if (navigate) history.replaceState(null, "", result.url);
      for (const node of $("knowledge-results").children) node.classList.toggle("selected", node.dataset.document === result.id);
      const header = el("div", undefined, "knowledge-preview-header");
      header.append(el("h2", result.title), el("p", `${result.source_name} / ${result.path}`),
        el("p", SimjectureI18n.live(() => SimjectureI18n.t("ui.indexed", {p0: result.location, p1: ago(result.indexed)}))),
        el("p", SimjectureI18n.live(() => SimjectureI18n.t("ui.revision", {p0: result.revision.slice(0,12), p1: (result.current ? "" : SimjectureI18n.t("ui.preserved-earlier-version"))}))));
      const actions = el("div", undefined, "knowledge-preview-actions");
      const discuss = button(SimjectureI18n.message("ui.discuss-this"), () => attach(result, true), "primary"); discuss.disabled = state.readonly;
      actions.append(discuss);
      if (state.project) {
        const add = button(SimjectureI18n.message("ui.use-in-conversation"), () => attach(result, false)); add.disabled = state.readonly || state.project.running;
        SimjectureI18n.attribute(add, "title", () => SimjectureI18n.t("ui.add-to", {p0: state.project.name})); actions.append(add);
      }
      if (result.downloadable) {
        const link = el("a", SimjectureI18n.message("ui.download-original"), "secondary");
        link.href = workspaceURL(`/api/workspace/knowledge-original?${new URLSearchParams({id:result.id, revision:result.revision})}`);
        actions.append(link);
      } else if (result.conversation) {
        const link = el("a", SimjectureI18n.message("ui.open-conversation"), "secondary");
        link.href = workspaceURL("/workspace") + "#" + new URLSearchParams({project: result.conversation, ...(result.turn ? {turn:result.turn} : {})});
        actions.append(link);
      }
      actions.append(button(SimjectureI18n.message("ui.copy-citation"), async () => {
        try { await navigator.clipboard.writeText(`[${result.title} · ${result.location}](${result.url})`); toast(SimjectureI18n.message("ui.citation-copied")); }
        catch (err) { toast(err.message, true); }
      }, "quiet"));
      header.append(actions);
      const pager = el("div", undefined, "knowledge-pagination");
      const previous = button(SimjectureI18n.message("ui.previous"), () => preview({...result,chunk:result.chunk-1}));
      const next = button(SimjectureI18n.message("ui.next-2"), () => preview({...result,chunk:result.chunk+1}));
      previous.disabled = result.chunk === 0; next.disabled = result.chunk + 1 >= result.chunks;
      pager.append(previous, el("span", SimjectureI18n.live(() => SimjectureI18n.t("ui.section-of", {p0: (result.chunk + 1), p1: result.chunks}))), next);
      $("knowledge-preview").replaceChildren(header, el("pre", result.text, "knowledge-preview-body"), pager);
      if (result.warning) $("knowledge-preview").append(el("p", result.warning, "knowledge-note"));
      if (!result.current || result.source_state === "unavailable") $("knowledge-preview").append(el("p", SimjectureI18n.message("ui.this-is-a-retained-indexed-passage-the-current-source-has-changed-wa"), "knowledge-note"));
      if (matchMedia("(max-width:1100px)").matches && navigate) $("knowledge-preview").scrollIntoView({behavior:"smooth",block:"start"});
    } catch (err) { if (serial === previewRequest) error(err.message); }
  }
  function renderSources() {
    $("knowledge-sources").replaceChildren();
    const states = {pending:SimjectureI18n.message("ui.queued"),indexing:SimjectureI18n.message("ui.updating"),ready:SimjectureI18n.message("ui.up-to-date"),attention:SimjectureI18n.message("ui.needs-attention"),unavailable:SimjectureI18n.message("ui.unavailable-2")};
    for (const source of sources) {
      const card = el("article", undefined, "knowledge-source-card");
      const header = el("header"), title = el("div");
      title.append(el("h3", source.name), el("p", SimjectureI18n.live(() => source.kind === "folder" ? source.path : SimjectureI18n.t("ui.available-within-this-workspace"))));
      header.append(title, el("span", SimjectureI18n.live(() => source.enabled ? (states[source.state] || source.state) : SimjectureI18n.t("ui.disabled")), `knowledge-source-state ${source.state}`));
      card.append(header);
      if (source.excludes.length) card.append(el("p", SimjectureI18n.live(() => SimjectureI18n.t("ui.excluded-paths", {p0: source.excludes.join(", ")}))));
      const footer = el("footer");
      footer.append(el("p", SimjectureI18n.live(() => SimjectureI18n.t("ui.indexed-items", {p0: source.documents.toLocaleString(), p1: (source.state === "indexing" ? SimjectureI18n.t("ui.items-checked", {p0: source.progress.toLocaleString()}) : SimjectureI18n.t("ui.checked", {p0: ago(source.checked)}))}))));
      const controls = el("div");
      const toggle = button(SimjectureI18n.live(() => source.enabled ? SimjectureI18n.t("ui.disable") : SimjectureI18n.t("ui.enable")), () => action(toggle, async () => {
        await api("knowledge-configure", {id:source.id, enabled:!source.enabled}); await refresh(); await search();
      }), "quiet"); toggle.disabled = state.readonly; controls.append(toggle);
      if (source.kind === "folder") {
        const remove = button(SimjectureI18n.message("ui.disconnect"), () => action(remove, async () => {
          await api("knowledge-configure", {id:source.id,remove:true}); await refresh(); await search();
          toast(SimjectureI18n.message("ui.folder-disconnected-from-this-workspace-original-files-are-unchanged"));
        }), "quiet"); remove.disabled = state.readonly; controls.append(remove);
      }
      footer.append(controls); card.append(footer);
      if (source.error) card.append(el("p", source.error));
      if (source.issues.length) {
        const details = el("details"), list = el("ul");
        details.append(el("summary", SimjectureI18n.live(() => SimjectureI18n.t("ui.indexing-notes", {p0: source.issues.length, p1: (source.issues.length === 30 ? "+" : "")}))));
        for (const issue of source.issues) list.append(el("li", `${issue.path}: ${issue.message}`));
        details.append(list); card.append(details);
      }
      $("knowledge-sources").append(card);
    }
  }
  async function choose(scope) {
    try {
      await refresh(); pickerScope = scope; pickerProject = state.project?.id;
      const selection = scope === "home" ? homeSelection : state.project?.knowledge_sources ?? null;
      SimjectureI18n.content($("knowledge-selection-error"), "");
      $("knowledge-inherit").checked = selection === null;
      $("knowledge-selection-list").replaceChildren();
      for (const source of sources.filter(s => s.enabled)) {
        const label = el("label", undefined, "knowledge-source-choice"), input = document.createElement("input");
        input.type="checkbox"; input.value=source.id; input.checked=selection === null || selection.includes(source.id);
        input.disabled=selection === null; label.append(input, el("span", source.name)); $("knowledge-selection-list").append(label);
      }
      $("knowledge-selection-dialog").showModal();
    } catch (err) { toast(err.message, true); }
  }
  function renderComposer() {
    if (!enabled) return;
    for (const scope of ["home","conversation"]) {
      const selection = scope === "home" ? homeSelection : state.project?.knowledge_sources ?? null;
      const count = sources.filter(s => s.enabled && (selection === null || selection.includes(s.id))).length;
      SimjectureI18n.bindText($(`${scope}-knowledge-picker`), () => SimjectureI18n.t("ui.knowledge", {p0: count, p1: SimjectureI18n.t(count === 1 ? "ui.knowledge-source" : "ui.knowledge-sources-count")}));
      $(`${scope}-knowledge-picker`).disabled = state.readonly || (scope === "conversation" && !!state.project?.running);
      const target = $(`${scope}-knowledge-refs`), draftKey = scope === "home" ? "home" : state.project?.id;
      target.replaceChildren();
      for (const ref of refs(draftKey)) {
        const chip = el("span", undefined, "knowledge-reference-chip");
        chip.append(el("span", ref.title));
        const remove = button("×", () => {
          drafts.set(draftKey, refs(draftKey).filter(r => r !== ref)); renderComposer();
        }, "");
        SimjectureI18n.attribute(remove, "aria-label", () => SimjectureI18n.t("ui.remove-reference", {p0: ref.title})); chip.append(remove); target.append(chip);
      }
    }
  }
  async function attach(result, fresh) {
    try {
      const target = fresh || !state.project ? "home" : state.project.id;
      let selection = target === "home" ? homeSelection : state.project.knowledge_sources;
      if (selection && !selection.includes(result.source)) {
        selection = [...selection, result.source];
        if (target === "home") homeSelection = selection;
        else {
          await api("knowledge-selection", {project:target,sources:selection});
          state.project.knowledge_sources = selection;
        }
      }
      if (refs(target).length >= 8) throw Error(SimjectureI18n.t("ui.choose-at-most-eight-reference-passages"));
      const reference = {id:result.id,revision:result.revision,chunk:result.chunk,title:result.title,source:result.source};
      if (target === "home") {
        $("new-project").click();
        drafts.set("home", [reference]);
        $("first-request").value = `Help me understand and use this source: ${result.title}`;
        globalThis.WorkspaceComposer?.update("first-request"); $("first-request").focus();
      } else {
        drafts.set(target, [...refs(target).filter(r => r.id !== result.id || r.chunk !== result.chunk), reference]);
        await openProject(target); mode("interactive");
        if (!$("chat-input").value.trim()) $("chat-input").value = `Use this source in our discussion: ${result.title}`;
        globalThis.WorkspaceComposer?.update("chat-input"); $("chat-input").focus();
      }
      renderComposer(); toast(SimjectureI18n.message("ui.source-attached-edit-your-question-and-send-when-ready"));
    } catch (err) { toast(err.message, true); }
  }
  function renderCitations(article, citations) {
    if (!citations?.length) return;
    const details = el("details", undefined, "knowledge-citations");
    details.append(el("summary", SimjectureI18n.live(() => SimjectureI18n.t("ui.sources-used", {p0: citations.length}))));
    for (const citation of citations) {
      const link = el("a", `${citation.title} · ${citation.location}`);
      link.href = citation.url; details.append(link);
    }
    article.append(details);
  }
  return {
    init, show, refresh, renderComposer, renderCitations,
    openRoute: params => preview({id:params.get("knowledge"),revision:params.get("revision"),chunk:Number(params.get("chunk") || 0)}, false),
    selection: () => homeSelection,
    references: id => refs(id),
    clear: (id, sent) => {
      drafts.set(id, refs(id).filter(ref => !sent.some(item =>
        item.id === ref.id && item.revision === ref.revision && item.chunk === ref.chunk)));
      renderComposer();
    },
    newConversation: () => {drafts.delete("home");renderComposer();},
    transferHome: id => {drafts.set(id, refs("home"));drafts.delete("home");renderComposer();},
  };
})();
