"use strict";
// Explicit URL scope: never a process-global or cookie-selected workspace.
window.workspaceURL = (path, space = new URLSearchParams(location.search).get("workspace")) => {
  const url = new URL(path, location.origin);
  if (space && space !== "personal") url.searchParams.set("workspace", space);
  return url.pathname + url.search + url.hash;
};
// Resources keeps the reader's last choice; short screens start collapsed so
// conversations stay visible.
window.WorkspaceResources = (() => {
  const key = "simjecture-resources-open";
  const saved = () => { try { return localStorage.getItem(key); } catch { return null; } };
  function apply(preferOpen = true) {
    const group = document.querySelector(".workspace-resources");
    if (!group) return;
    const choice = saved();
    group.open = choice === null ? preferOpen && innerHeight >= 860 : choice === "true";
  }
  document.addEventListener("DOMContentLoaded", () => {
    const group = document.querySelector(".workspace-resources");
    if (!group) return;
    apply();
    group.querySelector("summary").addEventListener("click", () => {
      // The click runs before the toggle, so store the state it is about to take.
      try { localStorage.setItem(key, String(!group.open)); } catch {}
    });
  });
  return {apply};
})();
window.WorkspaceProjects = (() => {
  let enabled = false, spaces = [], collections = [], selected = null, editing = null;
  const activeSpace = () => new URLSearchParams(location.search).get("workspace") || "personal";
  const spaceName = space => space?.id === "personal"
    ? SimjectureI18n.t("ui.personal") : space?.name || SimjectureI18n.t("ui.personal");
  function switchSpace(id) {
    let hash = "";
    try { localStorage.setItem(`simjecture-route-${activeSpace()}`, location.hash); hash = localStorage.getItem(`simjecture-route-${id}`) || ""; } catch {}
    location.href = workspaceURL("/workspace", id) + hash;
  }
  function editor(record = null) {
    editing = record?.id || null;
    SimjectureI18n.bindText($("collection-editor-title"), () => record ? SimjectureI18n.t("ui.project-settings") : SimjectureI18n.t("ui.new-project"));
    $("collection-name").value = record?.name || "";
    $("collection-summary").value = record?.description || "";
    $("collection-guidance").value = record?.instructions || "";
    SimjectureI18n.content($("collection-error"), "");
    $("collection-dialog").showModal();
    $("collection-name").focus();
  }
  function init(data) {
    enabled = !!data.workspaces;
    if (!enabled) return;
    spaces = data.workspaces; collections = data.collections || [];
    window.WorkspaceResources.apply(activeSpace() === "personal" && !collections.length);
    $("workspace-switcher").hidden = false;
    SimjectureI18n.bindText($("workspace-name"), () => spaceName(spaces.find(s => s.id === activeSpace())));
    $("collection-sidebar").hidden = false;
    $("new-collection").disabled = state.readonly;
    $("workspace-switcher").onclick = () => {
      $("spaces-list").replaceChildren();
      for (const space of spaces) {
        const button = el("button", undefined, "space-choice");
        button.append(el("span", SimjectureI18n.live(() => spaceName(space))), el("span", space.id === activeSpace() ? "✓" : "↗"));
        if (space.id === activeSpace()) button.setAttribute("aria-current", "true");
        button.onclick = () => space.id === activeSpace() ? $("spaces-dialog").close() : switchSpace(space.id);
        $("spaces-list").append(button);
      }
      $("create-space-form").hidden = state.readonly;
      $("spaces-dialog").showModal();
    };
    $("new-collection").onclick = () => editor();
    $("collection-new-chat").onclick = () => $("new-project").click();
    $("edit-collection").onclick = () => editor(collections.find(c => c.id === selected));
    $("home-collection").onclick = () => select(selected);
    for (const button of document.querySelectorAll("[data-close-organization]")) button.onclick = () => $(button.dataset.closeOrganization).close();
    $("create-space-form").onsubmit = async (event) => {
      event.preventDefault(); const button = event.submitter || event.currentTarget.querySelector("button[type=submit]");
      button.disabled = true;
      try { const result = await api("workspaces", {name: $("new-space-name").value}); switchSpace(result.id); }
      catch (error) { SimjectureI18n.content($("space-error"), error.message); button.disabled = false; }
    };
    $("collection-form").onsubmit = async event => {
      event.preventDefault(); const button = event.submitter || event.currentTarget.querySelector("button[type=submit]"); button.disabled = true;
      try {
        const result = await api("collections", { ...(editing ? {id: editing} : {}), name: $("collection-name").value, description: $("collection-summary").value, instructions: $("collection-guidance").value});
        await reloadProjects(); $("collection-dialog").close(); select(result.id);
      } catch (error) { SimjectureI18n.content($("collection-error"), error.message); }
      finally { button.disabled = false; }
    };
    $("collection-upload").onchange = async event => {
      const key = selected;
      try {
        for (const file of event.target.files) {
          if (file.size > 20 * 1024 ** 2) throw Error(SimjectureI18n.t("ui.shared-files-may-be-at-most-20-mb-each"));
          const content = await new Promise((resolve, reject) => {const reader = new FileReader(); reader.onload = () => resolve(reader.result.split(",")[1]); reader.onerror = reject; reader.readAsDataURL(file);});
          await api("collection-file", {id:key, name:file.name, content});
        }
        await reloadProjects(); if (selected === key && state.view === "collection") select(key);
      } catch (error) { toast(error.message, true); }
      finally { event.target.value = ""; }
    };
    $("conversation-collection").onchange = () => action($("conversation-collection"), async () => {
      const id = state.project.id;
      const result = await api("assign-collection", {project:id, collection:$("conversation-collection").value || null});
      await reloadProjects(); if (state.project?.id === id) {state.project = result; selected = result.collection || null; render();}
    });
    for (const link of document.querySelectorAll('.rail-brand,.rail-monitor,.sidebar .brand')) link.href = workspaceURL(link.getAttribute("href"));
    render();
  }
  function update(data) { if (!enabled) return; collections = data.collections || []; spaces = data.workspaces || spaces; render(); }
  function render() {
    if (!enabled) return;
    $("collection-list").replaceChildren();
    for (const collection of collections) {
      const button = el("button", undefined, "collection-link"); button.append(el("span", "▱"), el("span", collection.name));
      button.classList.toggle("selected", selected === collection.id); button.onclick = () => select(collection.id);
      $("collection-list").append(button);
    }
    const current = collections.find(c => c.id === selected);
    $("home-collection").hidden = !current;
    SimjectureI18n.content($("home-collection"), current ? `▱ ${current.name}` : "");
    $("conversation-collection-label").hidden = !collections.length;
    const picker = $("conversation-collection"); picker.replaceChildren(SimjectureI18n.bindText(new Option("", ""), () => SimjectureI18n.t("ui.no-project")));
    for (const item of collections) picker.add(new Option(item.name, item.id));
    picker.value = state.project?.collection || ""; picker.disabled = state.readonly || !!state.project?.running;
  }
  function select(id, navigate = true) {
    const collection = collections.find(c => c.id === id);
    if (!collection) { selected = null; return false; }
    selected = id;
    view("collection");
    if (navigate && !state.routing) location.hash = new URLSearchParams({collection:id}).toString();
    SimjectureI18n.content($("collection-title"), collection.name);
    SimjectureI18n.content($("collection-description"), SimjectureI18n.live(() => collection.description || SimjectureI18n.t("ui.conversations-shared-context-and-research-studies")));
    $("collection-conversations").replaceChildren();
    for (const conversation of state.projects.filter(p => p.collection === id)) {
      const button = el("button", undefined, "collection-conversation");
      button.append(el("span", conversation.name), el("small", SimjectureI18n.live(() => SimjectureI18n.t("ui.studies-2", {p0: conversation.studies.length}))));
      button.onclick = () => openProject(conversation.id).catch(e => toast(e.message, true));
      $("collection-conversations").append(button);
    }
    if (!$("collection-conversations").children.length) $("collection-conversations").append(el("p", SimjectureI18n.message("ui.start-a-conversation-to-explore-a-question-in-this-project"), "muted"));
    $("collection-files").replaceChildren();
    for (const file of collection.files) {const link = el("a", file.name); link.href = workspaceURL(`/api/workspace/collection-download?id=${encodeURIComponent(id)}&path=${encodeURIComponent(file.name)}`); $("collection-files").append(link);}
    SimjectureI18n.content($("collection-instructions"), collection.context_error || collection.instructions || "");
    $("edit-collection").disabled = state.readonly;
    $("collection-upload").disabled = state.readonly || (hosted && !state.hosting?.permissions?.project_files);
    document.querySelector('label[for="collection-upload"]').hidden = hosted && !state.hosting?.permissions?.project_files;
    if (hosted) SimjectureI18n.attribute($("collection-upload"), "title", () => SimjectureI18n.t("ui.add-scientific-files-within-a-conversation"));
    $("collection-new-chat").disabled = state.readonly;
    render(); return true;
  }
  return {init, update, render, select, selected:() => selected, setSelected:id => {selected=id || null; render();}};
})();
