"use strict";
// Explicit URL scope: never a process-global or cookie-selected workspace.
window.workspaceURL = (path, space = new URLSearchParams(location.search).get("workspace")) => {
  const url = new URL(path, location.origin);
  if (space && space !== "personal") url.searchParams.set("workspace", space);
  return url.pathname + url.search + url.hash;
};
window.WorkspaceProjects = (() => {
  let enabled = false, spaces = [], collections = [], selected = null, editing = null;
  const activeSpace = () => new URLSearchParams(location.search).get("workspace") || "personal";
  function switchSpace(id) {
    let hash = "";
    try { localStorage.setItem(`simjecture-route-${activeSpace()}`, location.hash); hash = localStorage.getItem(`simjecture-route-${id}`) || ""; } catch {}
    location.href = workspaceURL("/workspace", id) + hash;
  }
  function editor(record = null) {
    editing = record?.id || null;
    $("collection-editor-title").textContent = record ? "Project settings" : "New project";
    $("collection-name").value = record?.name || "";
    $("collection-summary").value = record?.description || "";
    $("collection-guidance").value = record?.instructions || "";
    $("collection-error").textContent = "";
    $("collection-dialog").showModal();
    $("collection-name").focus();
  }
  function init(data) {
    enabled = !!data.workspaces;
    if (!enabled) return;
    spaces = data.workspaces; collections = data.collections || [];
    document.querySelector(".workspace-resources").open = activeSpace() === "personal" && !collections.length;
    $("workspace-switcher").hidden = false;
    $("workspace-name").textContent = spaces.find(s => s.id === activeSpace())?.name || "Personal";
    $("collection-sidebar").hidden = false;
    $("new-collection").disabled = state.readonly;
    $("workspace-switcher").onclick = () => {
      $("spaces-list").replaceChildren();
      for (const space of spaces) {
        const button = el("button", undefined, "space-choice");
        button.append(el("span", space.name), el("span", space.id === activeSpace() ? "✓" : "↗"));
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
      event.preventDefault(); const button = event.submitter;
      button.disabled = true;
      try { const result = await api("workspaces", {name: $("new-space-name").value}); switchSpace(result.id); }
      catch (error) { $("space-error").textContent = error.message; button.disabled = false; }
    };
    $("collection-form").onsubmit = async event => {
      event.preventDefault(); const button = event.submitter; button.disabled = true;
      try {
        const result = await api("collections", { ...(editing ? {id: editing} : {}), name: $("collection-name").value, description: $("collection-summary").value, instructions: $("collection-guidance").value});
        await reloadProjects(); $("collection-dialog").close(); select(result.id);
      } catch (error) { $("collection-error").textContent = error.message; }
      finally { button.disabled = false; }
    };
    $("collection-upload").onchange = async event => {
      const key = selected;
      try {
        for (const file of event.target.files) {
          if (file.size > 20 * 1024 ** 2) throw Error("Shared files may be at most 20 MB each");
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
    $("home-collection").textContent = current ? `▱ ${current.name}` : "";
    $("conversation-collection-label").hidden = !collections.length;
    const picker = $("conversation-collection"); picker.replaceChildren(new Option("No project", ""));
    for (const item of collections) picker.add(new Option(item.name, item.id));
    picker.value = state.project?.collection || ""; picker.disabled = state.readonly || !!state.project?.running;
  }
  function select(id, navigate = true) {
    const collection = collections.find(c => c.id === id);
    if (!collection) { selected = null; return false; }
    selected = id;
    view("collection");
    if (navigate && !state.routing) location.hash = new URLSearchParams({collection:id}).toString();
    $("collection-title").textContent = collection.name;
    $("collection-description").textContent = collection.description || "Conversations, shared context and research studies.";
    $("collection-conversations").replaceChildren();
    for (const conversation of state.projects.filter(p => p.collection === id)) {
      const button = el("button", undefined, "collection-conversation");
      button.append(el("span", conversation.name), el("small", `${conversation.studies.length} studies`));
      button.onclick = () => openProject(conversation.id).catch(e => toast(e.message, true));
      $("collection-conversations").append(button);
    }
    if (!$("collection-conversations").children.length) $("collection-conversations").append(el("p", "Start a conversation to explore a question in this project.", "muted"));
    $("collection-files").replaceChildren();
    for (const file of collection.files) {const link = el("a", file.name); link.href = workspaceURL(`/api/workspace/collection-download?id=${encodeURIComponent(id)}&path=${encodeURIComponent(file.name)}`); $("collection-files").append(link);}
    $("collection-instructions").textContent = collection.context_error || collection.instructions || "";
    $("edit-collection").disabled = state.readonly;
    $("collection-upload").disabled = state.readonly;
    $("collection-new-chat").disabled = state.readonly;
    render(); return true;
  }
  return {init, update, render, select, selected:() => selected, setSelected:id => {selected=id || null; render();}};
})();
