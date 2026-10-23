"use strict";
const $ = (id) => document.getElementById(id);
const hosted = !!document.querySelector('meta[name="simjecture-hosted"]');
const state = {
  token: "",
  settings: {},
  projects: [],
  project: null,
  projectRequest: 0,
  view: "home",
  mode: "interactive",
  tools: [],
  machines: [],
  toolsRevision: "",
  toolFilter: "all",
  busy: false,
  readonly: false,
  hosting: null,
  briefDirty: false,
  messageRevision: "",
  studyRevision: "",
  studyRequest: 0,
  researchAction: null,
  launchKey: null,
  modelRequests: { home: 0, conversation: 0 },
  homeAgent: null,
  routeMemory: {},
  routing: false,
  routeStudy: null,
  dismissedSwitches: new Set(),
};
const bytes = (n) =>
  n < 1024
    ? `${n} B`
    : n < 1024 ** 2
      ? `${(n / 1024).toFixed(1)} KB`
      : `${(n / 1024 ** 2).toFixed(1)} MB`;
function el(tag, text, cls) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (cls) node.className = cls;
  return node;
}
function toast(message, error = false) {
  $("toast").textContent = message;
  $("toast").className = `toast${error ? " error" : ""}`;
  $("toast").hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(
    () => ($("toast").hidden = true),
    error ? 13000 : 5500,
  );
}
async function api(path, payload) {
  let response = await fetch(
    workspaceURL(path.startsWith("/api/") ? path : `/api/workspace/${path}`),
    payload === undefined
      ? {}
      : {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Simjecture-Token": state.token,
            ...(hosted ? {"X-CSRF-Token": state.token} : {}),
          },
          body: JSON.stringify(payload),
        },
  );
  if (hosted && response.status === 401 && path === "bootstrap") {
    const session = await fetch("/api/session", {method:"POST", headers:{"Content-Type":"application/json"},body:"{}"});
    const sessionData = await session.json();
    if (!session.ok) throw Error(sessionData.detail || "Unable to start a visitor session");
    state.token = sessionData.csrf_token;
    response = await fetch("/api/workspace/bootstrap");
  }
  const data = await response.json();
  if (!response.ok)
    throw Error(
      data.error || data.message || (typeof data.detail === "string" ? data.detail : "") || `Request failed (${response.status})`,
    );
  if (hosted && data.hosting) {state.hosting=data.hosting;renderHosting();}
  return data;
}

function renderAccount() {
  const h=state.hosting;
  if(hosted && h){const allowed=h.permissions.upload_files;$("file-input").disabled=!allowed;const label=document.querySelector('label[for="file-input"]');if(label){label.hidden=false;label.title=allowed ? "Add project files" : "Sign in to add files";}}
  const box=$("hosting-account");
  const signature=JSON.stringify(h || state.settings);if(box.dataset.signature===signature)return;box.dataset.signature=signature;
  const account=h?.account;
  const button=$("account-button");button.disabled=false;button.replaceChildren();
  button.title=account ? account.name || account.login : hosted ? "Sign in" : "Workspace menu";button.setAttribute("aria-label",account ? `Account: ${account.name || account.login}` : hosted ? "Sign in and account" : "Workspace menu");
  const fallback=el("span",account ? (account.name || account.login).slice(0,1).toUpperCase() : "S","avatar-fallback");button.append(fallback);
  if(account){const photo=el("img");photo.src="/api/auth/avatar";photo.alt="";photo.onload=()=>fallback.hidden=true;photo.onerror=()=>photo.remove();button.append(photo);}
  const theme=$("theme-toggle");
  box.replaceChildren();
  box.append(el("small",hosted ? "ACCOUNT" : "SIMJECTURE","account-eyebrow"));
  box.append(el("strong",account ? account.name || account.login : hosted ? "Guest workspace" : "Local workspace"));
  if(h){
  if(h.quota.tier==="owner")box.append(el("small","Owner workspace"));
  for(const [key,label] of [["interactive","interactive turns"],["research","research campaigns"]]){
    const q=h.quota[key];box.append(el("small",q.limit===null ? `Unlimited ${label}` : `${q.remaining} / ${q.limit} ${label} available`));
  }
  box.append(el("small",h.quota.tier==="owner" ? "No hosted wall-time limit · shared queue" : "Allowance renews over 24 hours · one task at a time"));
  if(!h.account)box.append(el("small","Temporary workspace. Sign in to keep your files and results."));
  if(h.account){const out=el("button","Sign out","quiet account-signout");out.onclick=async()=>{await api("/api/auth/logout",{});location.href="/workspace";};box.append(out);}
  else {const login=el("a",h.login_available ? "Sign in with GitHub" : "GitHub sign-in · being configured","secondary");
    if(h.login_available)login.href="/api/auth/github/start";else login.setAttribute("aria-disabled","true");box.append(login);}
  }
  const menu=el("div",undefined,"account-menu-links");
  if(!hosted){const connections=el("button","Connections","quiet");connections.onclick=()=>{box.hidden=true;button.setAttribute("aria-expanded","false");view("settings");};menu.append(connections);}
  const details=el("button","Workspace details","quiet");details.onclick=()=>{box.hidden=true;button.setAttribute("aria-expanded","false");$("workspace-details-dialog").showModal();};menu.append(details);
  if(theme)menu.append(theme);
  const github=el("a","GitHub ↗","quiet");github.href="https://github.com/tomzhu0225/simjecture";github.target="_blank";github.rel="noopener noreferrer";menu.append(github);
  box.append(menu);
}
function renderHosting(){if(hosted&&state.hosting)renderAccount();}
$("close-workspace-details").onclick=()=>$("workspace-details-dialog").close();
async function action(button, fn) {
  if (button.disabled) return;
  button.disabled = true;
  try {
    await fn();
  } catch (error) {
    toast(error.message, true);
  } finally {
    button.disabled = state.readonly ||
      (button.id === "send-message" && !!state.project?.running);
  }
}
function md(node, text) {
  window.WorkspaceRich.render(node, String(text || ""), state.project);
}
function view(name) {
  if(hosted && (["settings","machines"].includes(name) ||
    (name === "knowledge" && !state.hosting?.permissions?.knowledge))) name="home";
  if (name !== "project") ++state.projectRequest;
  const changed = state.view !== name;
  if (changed && matchMedia("(max-width: 600px)").matches)
    globalThis.WorkspacePanels?.set("left", true);
  state.view = name;
  $("right-sidebar-toggle").hidden = name !== "project";
  for (const section of document.querySelectorAll(".view"))
    section.hidden = section.id !== `view-${name}`;
  for (const item of document.querySelectorAll("[data-view]")) {
    const active = item.dataset.view === name;
    item.classList.toggle("active", active);
    if (active) item.setAttribute("aria-current", "page");
    else item.removeAttribute("aria-current");
  }
  if (!state.routing && name !== "collection")
    location.hash =
      name === "project"
        ? projectHash(state.project.id, { view: state.mode })
        : name;
  if (name === "tools") refreshTools().catch((e) => toast(e.message, true));
  if (name === "benchmarks") refreshBenchmarks().catch((e) => toast(e.message, true));
  if (name === "machines") refreshMachines().catch((e) => toast(e.message, true));
  if (name === "knowledge") globalThis.WorkspaceKnowledge?.show().catch((e) => toast(e.message, true));
  if (name === "home" && state.token && changed)
    renderAgent(undefined, "home").catch((e) => toast(e.message, true));
}
function projectHash(id, options = {}) {
  const study = id === state.project?.id
    ? window.StudyNavigation.selected(state.project, state.routeStudy) : null;
  return new URLSearchParams({ project: id, ...(study ? { study } : {}), ...options }).toString();
}
function renderStudyNavigation() {
  if (!state.project) return;
  state.routeStudy = window.StudyNavigation.selected(state.project, state.routeStudy);
  const study = state.project.studies.find((item) => item.campaign === state.routeStudy);
  window.StudyNavigation.render($("study-navigation"), {
    project: state.project.id,
    campaign: state.routeStudy,
    page: state.mode === "autonomous" ? "study" : "conversation",
    title: study?.question || "",
  });
  for (const card of $("study-runs").querySelectorAll(".study-card")) {
    const selected = card.id === `study-${state.routeStudy}`;
    card.classList.toggle("selected-study", selected);
    const marker = card.querySelector(".study-selection");
    if (marker) marker.textContent = selected ? "Selected study" : "Select study";
  }
}
function projectLink(id, options = {}) {
  return `#${projectHash(id, options)}`;
}
async function followRoute({ reveal = true } = {}) {
  if (state.routing) return;
  const initial = location.hash;
  // Leaving an action's route dismisses it; a late response must not navigate back.
  if (state.researchAction && state.researchAction.route !== initial) {
    const departed = state.researchAction;
    departed.dialog?.close();
    if (state.researchAction === departed) state.researchAction = null;
  }
  state.routing = true;
  try {
    const params = new URLSearchParams(location.hash.slice(1)),
      id = params.get("project");
    if (params.get("knowledge") && (!hosted || state.hosting?.permissions?.knowledge)) {
      view("knowledge");
      await globalThis.WorkspaceKnowledge?.openRoute(params);
    } else if (id) {
      if (state.project?.id !== id) {
        if (!(await openProject(id))) return;
      } else view("project");
      state.routeStudy = window.StudyNavigation.selected(state.project, params.get("study"));
      mode(params.get("view") === "autonomous" ? "autonomous" : "interactive");
      if (location.hash !== initial) return;
      if (state.routeStudy && params.get("study") !== state.routeStudy) {
        params.set("study", state.routeStudy);
        history.replaceState(null, "", `#${params}`);
      }
      if (state.mode === "autonomous") {
        await renderStudies();
        if (state.routeStudy)
          document
            .getElementById(`study-${state.routeStudy}`)
            ?.scrollIntoView({ behavior: "smooth", block: "start" });
      }
      if (state.mode === "interactive" && params.get("turn"))
        document
          .getElementById(`turn-assistant-${params.get("turn")}`)
          ?.scrollIntoView({ behavior: "smooth", block: "start" });
      if (params.get("simulation") || params.get("command"))
        await monitor.open(params.get("simulation") || params.get("command"), {
          reveal,
        });
    } else if (params.get("collection") && globalThis.WorkspaceProjects?.select(params.get("collection"), false)) {
      if (params.get("view") === "new") {
        state.project = null;
        view("home");
        renderProjects();
      }
    } else
      view(
        ["settings", "tools", "benchmarks", "machines", "knowledge"].includes(location.hash.slice(1))
          ? location.hash.slice(1)
          : "home",
      );
  } finally {
    state.routing = false;
    if (location.hash !== initial)
      followRoute().catch((e) => toast(e.message, true));
  }
}
function renderSettings() {
  const s = state.settings;
  $("base-url").value = s.base_url || "";
  $("api-key").value = "";
  $("api-key").placeholder = s.has_key
    ? "Saved · leave blank to keep this key"
    : "API key (optional for a local server)";
  const installed = (s.clis || []).filter((c) => c.path);
  $("connection-button").title = "Configure API connections";
  $("connection-button").disabled = false;
  if(hosted) $("connection-button").hidden=true;
  $("connection-indicator").textContent = installed.length
    ? `${installed.length} CLI agents detected`
    : s.api_configured
      ? "API endpoint saved"
      : "Choose an agent in your project";
  $("connection-indicator").classList.toggle(
    "connected",
    !!installed.length || s.api_configured,
  );
  $("machine-label").textContent = s.machine || "Local workspace";
  $("machine-card").replaceChildren(
    el("strong", s.machine || "This machine"),
    el("small", `${s.platform || "Linux"} · local execution`),
  );
  $("detected-agents").replaceChildren(
    ...(s.clis || [])
      .filter((c) => c.path)
      .map((c) => el("span", c.id, "cli-chip")),
  );
  if (!$("detected-agents").children.length)
    $("detected-agents").textContent =
      "No supported CLI agents found. You can use the built-in API agent.";
  $("runtime-status").textContent = s.runtime_installed
    ? "Built-in agent powered by Hugging Face smolagents. Your existing Simjecture experiment and review services govern autonomous studies."
    : "To enable the built-in API agent, run once: uv sync --extra workspace. Installed CLI agents work without this extra.";
  $("connection-result").textContent = s.api_configured
    ? "API endpoint saved. Select its model in your conversation."
    : "Optional. You can use an installed CLI without adding an API key.";
}
function agentControls(scope = "conversation") {
  const home = scope === "home";
  return {
    backend: $(home ? "home-backend" : "conversation-backend"),
    model: $(home ? "home-model" : "conversation-model"),
    effort: $(home ? "home-effort" : "conversation-effort"),
    custom: $(home ? "home-custom-model" : "custom-model"),
    customBox: $(home ? "home-custom-model-control" : "custom-model-control"),
    refresh: $(home ? "home-refresh-models" : "refresh-models"),
    note: $(home ? "home-model-note" : "model-note"),
  };
}
function mountHomeAgent() {
  const copy = document.querySelector(".agent-controls").cloneNode(true);
  const ids = {
    "conversation-backend": "home-backend",
    "conversation-model": "home-model",
    "conversation-effort": "home-effort",
    "custom-model": "home-custom-model",
    "custom-model-control": "home-custom-model-control",
    "refresh-models": "home-refresh-models",
    "model-note": "home-model-note",
  };
  for (const node of copy.querySelectorAll("[id]"))
    node.id = ids[node.id] || node.id;
  for (const label of copy.querySelectorAll("label[for]"))
    label.htmlFor = ids[label.htmlFor] || label.htmlFor;
  copy.setAttribute("aria-label", "Agent for a new conversation");
  $("home-agent-host").append(copy);
}
async function renderAgent(backend, scope = "conversation") {
  const home = scope === "home";
  const p = home
    ? { id: "overview", agent: state.homeAgent || state.settings.default_agent }
    : state.project;
  if (!p) return;
  const controls = agentControls(scope),
    id = p.id,
    request = ++state.modelRequests[scope];
  const selected =
    backend ||
    p.agent?.backend ||
    state.settings.default_agent?.backend ||
    "builtin";
  controls.backend.replaceChildren();
  for (const cli of state.settings.clis || [])
    if (cli.path)
      controls.backend.add(new Option(`${cli.id} · local CLI`, cli.id));
  controls.backend.add(
    new Option(
      state.settings.api_configured
        ? "Compatible API"
        : "Compatible API · add endpoint",
      "builtin",
    ),
  );
  controls.backend.value = selected;
  if (!controls.backend.value) {
    controls.backend.add(new Option(`${selected} · unavailable`, selected));
    controls.backend.value = selected;
  }
  controls.model.replaceChildren(new Option("Loading model choices…", ""));
  controls.model.disabled = true;
  controls.customBox.hidden = true;
  controls.custom.value = "";
  controls.note.textContent = "Reading model choices…";
  controls.backend.disabled = state.readonly || hosted;
  controls.custom.disabled = state.readonly;
  controls.refresh.disabled = state.readonly;
  const choices = state.readonly || hosted
    ? {
        models: p.agent?.model
          ? [{ id: p.agent.model, name: p.agent.model }]
          : [],
        default: p.agent?.model || "",
        note: hosted ? "Provided by Simjecture · model settings managed by the host" : "Recorded conversation agent · read-only session",
      }
    : await api("models", { backend: selected });
  if (
    request !== state.modelRequests[scope] ||
    (!home && state.project?.id !== id)
  )
    return false;
  const current =
    p.agent?.backend === selected ? p.agent : state.routeMemory[selected];
  const model = current?.model || choices.default || "";
  controls.model.replaceChildren(
    ...choices.models.map((m) => new Option(m.name, m.id)),
    ...(hosted ? [] : [new Option("Other model…", "__custom__")]),
  );
  const known = choices.models.some((m) => m.id === model);
  controls.model.value = known ? model : "__custom__";
  controls.customBox.hidden = known;
  controls.custom.value = known ? "" : model;
  controls.effort.value = current?.reasoning_effort || "";
  controls.effort.disabled = selected === "agy" || state.readonly || hosted;
  if (selected === "agy") controls.effort.value = "";
  controls.model.disabled = state.readonly || hosted;
  if(hosted){controls.refresh.hidden=true;controls.customBox.hidden=true;}
  controls.note.textContent = choices.note;
  globalThis.WorkspaceComposer?.refresh(scope);
  return true;
}
function agentPayload(scope = "conversation") {
  const c = agentControls(scope);
  return {
    project: scope === "home" ? null : state.project.id,
    backend: c.backend.value,
    model:
      c.model.value === "__custom__" ? c.custom.value.trim() : c.model.value,
    reasoning_effort: c.effort.value,
  };
}
async function saveConversationAgent(scope = "conversation") {
  if(hosted) return state.settings.default_agent;
  const c = agentControls(scope);
  if (c.model.disabled && !state.readonly)
    throw Error(
      "Model choices are still loading. Please try again in a moment.",
    );
  const payload = agentPayload(scope);
  if (!payload.model)
    throw Error("Choose a model, or enter its exact ID in Other model.");
  const previousAgent = scope === "conversation" ? state.project?.agent : null;
  const result = await api("agent", payload);
  state.routeMemory[result.backend] = result;
  if (scope === "home") state.homeAgent = result;
  else if (state.project?.id === payload.project) {
    if (
      previousAgent &&
      (previousAgent.backend !== result.backend ||
        previousAgent.model !== result.model)
    ) {
      state.dismissedSwitches.delete(state.project.id);
    }
    state.project.agent = result;
    state.homeAgent = result;
    renderProject();
  }
  globalThis.WorkspaceComposer?.refresh(scope);
  return result;
}
function renderProjects() {
  $("project-list").replaceChildren();
  if (!state.projects.length)
    $("project-list").append(el("p", "Your work will appear here.", "muted"));
  for (const project of state.projects) {
    const button = el("button", project.name, "project-link");
    button.title = project.name;
    button.classList.toggle("selected", project.id === state.project?.id);
    if (project.id === state.project?.id) button.setAttribute("aria-current", "page");
    button.onclick = () =>
      openProject(project.id).catch((e) => toast(e.message, true));
    const row = el("div", undefined, "conversation-row");
    const remove = el("button", "×", "delete-conversation");
    remove.type = "button";
    remove.title = "Delete conversation and files";
    remove.setAttribute("aria-label", `Delete conversation: ${project.name}`);
    remove.disabled = state.readonly;
    remove.onclick = () => {
      $("delete-form").dataset.project = project.id;
      $("delete-name").textContent = project.name;
      $("delete-path").textContent = project.path || project.id;
      $("delete-error").hidden = true;
      $("delete-dialog").showModal();
      $("cancel-delete").focus();
    };
    row.append(button, remove);
    $("project-list").append(row);
  }
  globalThis.WorkspaceProjects?.render();
}
async function reloadProjects() {
  const boot = await api("bootstrap");
  state.projects = boot.projects;
  globalThis.WorkspaceProjects?.update(boot);
  renderProjects();
}
async function openProject(id) {
  const request = ++state.projectRequest;
  const project = await api(`project?id=${encodeURIComponent(id)}`);
  // A slower earlier click must not replace a newer navigation choice.
  if (request !== state.projectRequest) return false;
  $("agent-switch-warning").hidden = true;
  const sameProject = state.project?.id === id;
  state.project = project;
  globalThis.WorkspaceProjects?.setSelected(project.collection);
  state.routeStudy = window.StudyNavigation.selected(project, sameProject ? state.routeStudy : null);
  state.briefDirty = false;
  state.messageRevision = "";
  state.studyRevision = "";
  state.launchKey = null;
  renderProject(true);
  globalThis.WorkspaceKnowledge?.renderComposer();
  view("project");
  renderProjects();
  await renderAgent();
  if (request !== state.projectRequest || state.project?.id !== id) return false;
  if (state.mode === "autonomous") await renderStudies();
  return request === state.projectRequest && state.project?.id === id;
}
function mode(name) {
  state.mode = name;
  renderStudyNavigation();
  $("interactive-panel").hidden = name !== "interactive";
  $("autonomous-panel").hidden = name !== "autonomous";
  $("interactive-mode").classList.toggle("selected", name === "interactive");
  $("autonomous-mode").classList.toggle("selected", name === "autonomous");
  $("interactive-mode").setAttribute("aria-pressed", String(name === "interactive"));
  $("autonomous-mode").setAttribute("aria-pressed", String(name === "autonomous"));
  if (!state.routing && state.view === "project" && state.project)
    location.hash = projectHash(state.project.id, { view: name });
  if (name === "autonomous") {
    refreshTools()
      .then(() => renderStudies())
      .catch((e) => toast(e.message, true));
  }
}
function renderAgentSwitchWarning() {
  const p = state.project;
  const original = p?.messages
    ?.slice()
    .reverse()
    .find((m) => m.agent)?.agent;
  const changed =
    original &&
    p.agent &&
    (original.backend !== p.agent.backend || original.model !== p.agent.model);
  if (!changed && p) state.dismissedSwitches.delete(p.id);
  $("agent-switch-warning").hidden =
    !changed || state.dismissedSwitches.has(p?.id);
}
$("dismiss-agent-switch-warning").onclick = () => {
  if (state.project) state.dismissedSwitches.add(state.project.id);
  $("agent-switch-warning").hidden = true;
};
function renderProject(force = false) {
  const p = state.project;
  if (!p) return;
  renderMachineSelection();
  renderAgentSwitchWarning();
  $("project-title").textContent = p.name;
  renderStudyNavigation();
  $("agent-label").textContent = p.agent
    ? `${p.agent.backend} / ${p.agent.model || "choose model"}`
    : "Choose an agent";
  $("send-message").disabled = p.running || state.readonly;
  $("stop-agent").hidden = !p.running;
  $("launch-study").disabled = p.running || state.readonly;
  for (const id of ["grill-me", "draft-study", "start-prepared-study"])
    $(id).disabled = p.running || state.readonly;
  $("preparation-status").textContent = p.running
    ? "Your agent is working. Its questions and proposed brief appear in the conversation."
    : "The agent will ask about missing facts and fill in the details for you.";
  const pendingBrief = p.brief && !p.brief_launched;
  const preparing = !pendingBrief && !p.brief_launched;
  $("study-preparation").hidden = !preparing;
  $("prepared-brief").hidden = !pendingBrief;
  $("brief-editor").hidden = !pendingBrief;
  $("new-study").hidden = !p.studies.length || preparing || !!pendingBrief;
  $("new-study").disabled = p.running || state.readonly;
  $("continuation-chat-context").hidden = !p.continuation_draft;
  if (p.continuation_draft) $("continuation-parent-link").href = `/monitor?campaign=${encodeURIComponent(p.continuation_draft.campaign)}`;
  $("continuation-chat").disabled = p.running || state.readonly;
  $("study-stage").textContent = pendingBrief
    ? "Proposal ready — review it below, then start research."
    : preparing
      ? p.running
        ? "Preparing with your agent. Continue the conversation to answer its questions."
        : "Prepare a study with your agent. You review the proposal before it runs."
      : "Your studies are below. Finished reports return to this conversation for explanation.";
  if (p.brief) {
    const b = p.brief;
    $("prepared-question").textContent = b.question;
    $("prepared-heading").textContent = p.continuation_draft ? "CONTINUATION PROPOSAL" : "YOUR AGENT’S PROPOSAL";
    $("prepared-details").replaceChildren();
    if (p.continuation_draft) {
      const parent = el("a", `Continuation phase · ${p.continuation_draft.files.length} selected files · parent study ↗`);
      parent.href = `/monitor?campaign=${encodeURIComponent(p.continuation_draft.campaign)}`;
      $("prepared-details").append(parent);
    }
    const agentRow = el("p", `Agent: ${p.agent?.backend || "choose agent"} / ${p.agent?.model || "choose model"}`, "field-help");
    const changeAgent = el("button", "Change agent / model", "secondary"); changeAgent.type = "button";
    changeAgent.onclick = () => { mode("interactive"); globalThis.WorkspaceComposer?.open("conversation"); $("conversation-backend").focus(); };
    changeAgent.hidden=hosted;
    agentRow.append(document.createTextNode(" "), changeAgent); $("prepared-details").append(agentRow);
    for (const [label, value] of [
      ["Evidence", b.success_criteria],
      ["Constraints", b.constraints || "No additional constraints specified."],
      ["Time budget", b.hours===0 ? "No hosted time limit" : `${b.hours} hours`],
      ["Execution", b.machine_ids?.length ? b.machine_ids.join(", ") : "This host"],
      ["Solver development", (b.allow_solver_development ?? !hosted)
        ? "Private source forks allowed; changed methods require independent qualification."
        : "Use supplied solver implementations; experiment and analysis scripts remain available."],
      [
        "Completion",
        b.completion_policy === "answer"
          ? "An independently reviewed answer, including a negative result."
          : "A supported claim or independently tested repair.",
      ],
    ]) {
      const section = el("div");
      section.append(el("strong", label), el("p", value));
      $("prepared-details").append(section);
    }
  }
  monitor.render(p);
  const revision = JSON.stringify([
    p.messages,
    p.files,
    (p.simulations || []).map((j) => [j.id, j.status, j.kind]),
  ]);
  if (revision !== state.messageRevision) {
    const messageScroll = $("messages").scrollTop;
    const nearEnd =
      $("messages").scrollHeight -
        $("messages").scrollTop -
        $("messages").clientHeight <
      120;
    const openSteps = new Set(
      [...$("messages").querySelectorAll("details[open]")].map(
        (d) => d.dataset.turn,
      ),
    );
    const previousArticles = new Map(
      [...$("messages").children].map((node) => [
        node.dataset.messageKey,
        node,
      ]),
    );
    const desiredArticles = [];
    const figureRevision = JSON.stringify([
      p.files.filter((f) => /\.(png|jpe?g|gif|webp|svg)$/i.test(f.name)),
      (p.simulations || [])
        .filter((j) => j.kind === "simulation")
        .map((j) => [j.id, j.status]),
    ]);
    if (!p.messages.length) {
      const welcome = el("div", undefined, "welcome-message");
      welcome.append(
        el("h2", "Let’s work through your question."),
        el(
          "p",
          "Describe your task or attach a file. You can investigate together, then prepare an autonomous study when the question is clear.",
        ),
      );
      desiredArticles.push(welcome);
    }
    for (const message of p.messages) {
      const key = `${message.role}-${message.turn}`;
      const signature = JSON.stringify([message, figureRevision]);
      const old = previousArticles.get(key);
      if (old?.dataset.messageSignature === signature) {
        desiredArticles.push(old);
        continue;
      }
      const article = el("article", undefined, `message ${message.role}`);
      article.id = `turn-${key}`;
      article.dataset.messageKey = key;
      article.dataset.messageSignature = signature;
      article.append(
        el(
          "span",
          message.role === "user"
            ? "You"
            : message.role === "system"
              ? "Study report received"
              : message.agent
                ? `Simjecture · ${message.agent.backend} / ${message.agent.model}`
                : "Simjecture",
          "message-role",
        ),
      );
      const content = el("div", undefined, "message-content");
      md(content, message.content);
      article.append(content);
      globalThis.WorkspaceKnowledge?.renderCitations(article, message.knowledge_citations);
      const tools = (message.events || []).filter(
        (e) => e.type === "tool" || e.type === "observation",
      );
      if (tools.length) {
        const details = el("details");
        details.dataset.turn = message.turn;
        details.open = openSteps.has(message.turn);
        details.append(
          el(
            "summary",
            `${tools.filter((e) => e.type === "tool").length} actions · view activity`,
          ),
        );
        const trace = el("div", undefined, "trace");
        for (const item of tools) {
          trace.append(el("p", item.type === "tool" ? item.name : item.text));
          if (item.arguments)
            trace.append(
              el(
                "pre",
                typeof item.arguments === "string"
                  ? item.arguments
                  : JSON.stringify(item.arguments, null, 2),
              ),
            );
        }
        details.append(trace);
        article.append(details);
      }
      for (const related of message.links || []) {
        const target =
          related.kind === "simulation"
            ? { view: "interactive", simulation: related.simulation }
            : {
                view: "autonomous",
                ...(related.campaign ? { study: related.campaign } : {}),
              };
        const card = el("a", undefined, "research-link-card");
        card.href = projectLink(p.id, target);
        card.append(
          el(
            "span",
            related.kind === "simulation"
              ? "SIMULATION"
              : "AUTONOMOUS RESEARCH",
            "link-category",
          ),
          el("strong", related.label),
          el("span", "Open ↗", "link-open"),
        );
        article.append(card);
      }
      if (message.running && message.progress)
        article.append(el("p", message.progress, "agent-update"));
      if (message.running) {
        const progress = el("div", undefined, "agent-progress");
        const spinner = el("wa-spinner");
        spinner.setAttribute("aria-label", "Agent active");
        const label = el(
          "span",
          message.activity?.label || "Waiting for agent",
        );
        const elapsed = el("small");
        elapsed.dataset.elapsed = message.started_at;
        progress.append(spinner, label, elapsed);
        article.append(progress);
        if (message.activity?.detail)
          article.append(
            el("p", message.activity.detail, "agent-current-action"),
          );
        const meta = el("p", undefined, "agent-activity-meta");
        const since = el("span");
        since.dataset.idleSince =
          message.last_activity_at || message.started_at;
        meta.append(
          document.createTextNode("Last agent activity: "),
          since,
          document.createTextNode(
            ` · ${message.monitored_runs || 0} monitored simulation${message.monitored_runs === 1 ? "" : "s"} in this turn`,
          ),
        );
        article.append(meta);
      } else if (message.status === "interrupted")
        article.append(
          el(
            "p",
            "This turn was interrupted. Your files are saved; send a message to continue.",
            "thinking",
          ),
        );
      else if (message.status === "error") article.classList.add("error-text");
      const recent = message.activity?.recent_actions || [];
      if (recent.length) {
        const history = el(
          message.running ? "div" : "details",
          undefined,
          "agent-activity-history",
        );
        if (!message.running) {
          history.dataset.turn = `recent-${message.turn}`;
          history.open = openSteps.has(history.dataset.turn);
          history.append(el("summary", "Recent agent activity"));
        }
        const list = el("ol", undefined, "agent-activity-list");
        for (const item of recent.slice(-5)) {
          const row = el("li");
          row.append(
            el("strong", item.label),
            el("small", item.status.replaceAll("_", " ")),
          );
          if (item.detail) row.append(el("span", item.detail));
          list.append(row);
        }
        history.append(list);
        article.append(history);
      }
      desiredArticles.push(article);
    }
    let cursor = $("messages").firstChild;
    for (const node of desiredArticles) {
      if (node !== cursor) $("messages").insertBefore(node, cursor);
      cursor = node.nextSibling;
    }
    while (cursor) {
      const next = cursor.nextSibling;
      cursor.remove();
      cursor = next;
    }
    $("messages").scrollTop =
      nearEnd || force ? $("messages").scrollHeight : messageScroll;
    state.messageRevision = revision;
  }
  const inspector = document.querySelector(".project-context");
  const inspectorScroll = inspector.scrollTop;
  $("project-path").textContent = p.files_directory;
  $("file-count").textContent = p.files.length;
  $("project-files").replaceChildren();
  for (const file of p.files) {
    const row = el("div", undefined, "file-row"),
      link = el("a", file.name);
    link.href = workspaceURL(`/api/workspace/file?id=${encodeURIComponent(p.id)}&path=${encodeURIComponent(file.name)}`);
    link.title = file.name;
    row.append(link, el("small", bytes(file.bytes)));
    $("project-files").append(row);
  }
  if (!p.files.length)
    $("project-files").append(
      el("p", "Uploaded inputs and agent-created files will appear here."),
    );
  $("brief-summary").replaceChildren(
    el(
      "p",
      p.brief?.question ||
        "Ask your agent to prepare an autonomous investigation, or write a brief yourself.",
    ),
  );
  inspector.scrollTop = inspectorScroll;
  if (!state.briefDirty || force) {
    const b = p.brief || {};
    $("brief-question").value = b.question || "";
    $("brief-criteria").value = b.success_criteria || "";
    $("brief-constraints").value = b.constraints || "";
    $("brief-hours").value = b.hours ?? 1;
    $("brief-policy").value = b.completion_policy || "answer";
    $("solver-development").checked = b.allow_solver_development ?? !hosted;
    $("solver-development").disabled = hosted || state.readonly;
    $("solver-development-help").textContent = hosted
      ? "Hosted policy: use supplied solver implementations. Experiment and analysis scripting remains available within host permissions."
      : "The agent may modify private solver forks. Reference installations stay protected; changed methods need independent qualification before claim evidence.";
    const selectedTools = b.capability_directory ?? (hosted ? "hosted-tools" : "auto");
    if (
      [...$("study-tools").options].some(
        (o) => o.value === selectedTools,
      )
    )
      $("study-tools").value = selectedTools;
  }
}
async function send() {
  const input = $("chat-input");
  const draft = input.value;
  const message = draft.trim();
  const project = state.project?.id;
  if (!message || !project) return;
  const references = [...(globalThis.WorkspaceKnowledge?.references(project) || [])];
  // Navigation and new typing may happen while either request is pending.
  await saveConversationAgent();
  const payload = { project, message };
  if (references.length) payload.knowledge_refs = references;
  await api("message", payload);
  if (references.length) globalThis.WorkspaceKnowledge?.clear(project, references);
  if (state.project?.id === project && input.value === draft) {
    input.value = "";
    globalThis.WorkspaceComposer?.update("chat-input");
  }
  const updated = await api(`project?id=${encodeURIComponent(project)}`);
  if (state.project?.id === project) {
    state.project = updated;
    renderProject();
  }
  await reloadProjects();
}
// One accurate setup brief per tool. Each names the skill files that actually
// document that tool, so agents never receive another tool's instructions.
const toolSetupGuides = {
  "warp-lbm": {skill: "warp-lbm", read: [], focus: "Use its managed installer (`simjecture install warp-lbm`) and check the NVIDIA Warp runtime it needs."},
  "iter-pack": {skill: "iter-pack", read: ["references/diagnostics.md"], focus: "Use its isolated managed runtime and pinned package versions. It needs Git, a C compiler and a compatible Python. The pack provides CHERAB/Raysect diagnostics and IMAS data tools."},
  solps: {skill: "iter-pack", read: ["references/solps.md"], focus: "Follow the upstream installation route described there, pin the source revision and submodules, and start from a supplied example case."},
  jorek: {skill: "iter-pack", read: ["references/jorek.md"], focus: "Follow the upstream build route described there and pin the source revision and build configuration."},
  dina: {skill: "iter-pack", read: ["references/dina.md"], focus: "Follow the upstream build route described there and pin the source revision and build configuration."},
  "warpx-cpu": {skill: "warpx", read: [], focus: "Use the CPU profile installer (`simjecture install warpx-cpu`) and its pinned Conda environment."},
  "warpx-cuda": {skill: "warpx", read: ["references/local-cuda-deployment.md"], focus: "Check the GPU, driver, CUDA compatibility and build resources. The bundled recipe builds a 2D runtime and can download its pinned source.", ask: "which dimensions I need"},
  flash: {skill: "flash-mhd", read: ["references/local-deployment.md", "references/private-install.md"], focus: "FLASH is licensed, so I supply the source.", ask: "where my licensed FLASH source (folder, archive or private Git remote) is, and which application, physics and dimensions I want"},
  atomec: {skill: "eos", read: ["references/local-deployment.md"], focus: "Use the documented atoMEC installer and keep its pinned source revision."},
  "singularity-eos": {skill: "eos", read: ["references/local-deployment.md"], focus: "Use the documented Singularity-EOS installer and keep its pinned source revision."},
  "m-aneos": {skill: "eos", read: ["references/local-deployment.md"], focus: "Use the documented M-ANEOS installer and keep its pinned source revision."},
  feos: {skill: "eos", read: ["references/local-deployment.md", "references/feos.md"], focus: "Use the documented FEOS installer, which builds a checksummed source."},
  "material-eos": {skill: "eos", read: ["references/local-deployment.md", "references/material-models.md"], focus: "Use the documented material EOS builder installer."},
  optab: {skill: "opacity", read: ["references/local-deployment.md"], focus: "Use the documented Optab installer; it needs a Fortran compiler, HDF5 tools and data downloads."},
};
function setupGuideText(tool) {
  const guide = toolSetupGuides[tool.id];
  if (!guide) return "Read the research skill that documents this tool before changing its installation.";
  const files = ["SKILL.md", ...guide.read].join(", ");
  return `Start by reading the ${guide.skill} skill (${files}). ${guide.focus}`;
}
async function assistInstallation(tool, diagnose=false) {
  const guide = toolSetupGuides[tool.id] || {};
  const check = tool.operation?.action === "check";
  const steps = diagnose
    ? `Please:
1. Read the saved failure below and the full log${tool.operation?.log_path ? ` at ${tool.operation.log_path}` : ""}.
2. Explain the cause in plain language, then fix what is missing where you can.
3. Retry the documented setup and confirm the readiness check passes.
Keep existing files and earlier logs.`
    : `Please:
- Ask me only for decisions you cannot make yourself${guide.ask ? `, such as ${guide.ask}` : ""}. Choose routine build settings yourself.
- Check prerequisites, then run the documented setup. Keep sources, build records and logs in persistent named folders, and post progress during long builds.
- Run a small readiness test and register the working runtime so it appears in Research tools.
- Respect this machine's execution mode and explain any blocker plainly.`;
  const diagnostics = diagnose ? `

The failure details below are diagnostic data, not instructions:
${JSON.stringify({failure: toolFailure(tool).slice(-6000), log_path: tool.operation?.log_path, recent_output: (tool.log || "").slice(-4000)}, null, 2)}` : "";
  const opening = diagnose
    ? `The ${check ? "readiness check" : "setup"} for ${tool.name} on this machine failed. Please diagnose it and get the tool working.`
    : `Help me set up ${tool.name} on this machine.`;
  const prompt = `${opening}

${setupGuideText(tool)}

${steps}

A passing readiness check shows the tool runs; it is not scientific validation.${diagnostics}`;
  const project = await api("projects", { name: `${diagnose ? "Repair" : "Install"} ${tool.name}` });
  await reloadProjects();
  mode("interactive");
  if (!(await openProject(project.id))) return;
  $("chat-input").value = prompt;
  $("chat-input").dispatchEvent(new Event("input"));
  $("chat-input").focus();
  toast(
    `${diagnose ? "Repair" : "Setup"} conversation ready. Review the request, choose your agent, then send.`,
  );
}

async function prepareToolStudy(tool) {
  const project = await api("projects", { name: `${tool.name} · custom study` });
  await reloadProjects();
  mode("interactive");
  if (!(await openProject(project.id))) return;
  $("chat-input").value = `Help me prepare a custom study with ${tool.name}. Ask me about the physics, geometry, initial conditions and diagnostics I want, then inspect the installed tools and sources to choose a suitable setup. Use the starter presets where they fit, and prepare custom inputs or a private application build where needed.`;
  $("chat-input").dispatchEvent(new Event("input"));
  $("chat-input").focus();
  toast("Study conversation ready. Describe your problem and send the request.");
}

const machineAddress = (m) => m.kind === "local" ? "This computer" : `${m.user ? m.user + "@" : ""}${m.host.includes(":") ? "[" + m.host + "]" : m.host}:${m.port}`;
function machineState(record) {
  if (record.preparation?.status === "working") return ["preparing", "Preparing"];
  const live = record.availability;
  if (live?.checked_at && Date.now()/1000 - live.checked_at > 75) return ["stale", "Last check stale"];
  if (live?.status === "offline") return ["offline", "Offline"];
  if (live?.status === "ready") return ["ready", "Online"];
  if (record.preparation?.status === "failed") return ["setup_needed", "Setup needs attention"];
  if (live?.online) return ["setup_needed", "Needs setup"];
  if (record.probe?.execution?.available && !record.error) return ["stale", "Checking…"];
  return ["setup_needed", "Not prepared"];
}
function machineGlyph() {
  const span = el("span", undefined, "machine-glyph");
  span.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><rect x="3" y="3" width="18" height="7" rx="2"/><rect x="3" y="14" width="18" height="7" rx="2"/><path d="M7 6.5h.01M7 17.5h.01M12 6.5h5M12 17.5h5" stroke-linecap="round"/></svg>';
  return span;
}
function fillMachine(machine = null, hasPassword = false) {
  state.editMachine = machine;
  const automatic = machine?.automatic_setup;
  const config = machine?.config || {};
  const fields = automatic || (machine ? {...config, root:machine.root,run_as:machine.run_as} : {});
  $("machine-editor-title").textContent = machine ? "Machine settings" : "Add a machine";
  $("machine-address").value = machine?.kind === "ssh" ? machineAddress(machine) : "";
  $("machine-password").value = "";
  $("machine-password").placeholder = hasPassword ? "Leave empty to keep the saved password" : "Leave empty to use your SSH key or agent";
  for (const [id, value] of Object.entries({"machine-id":machine?.id, "machine-label-input":machine?.label,
    "machine-kind":machine?.kind || "ssh", "machine-root":fields.root, "machine-python":machine?.python || "",
    "machine-run-as":fields.run_as, "machine-identity":machine?.identity_file,
    "machine-known-hosts":automatic ? "" : machine?.known_hosts, "machine-cpus":fields.cpus,
    "machine-memory":fields.memory_mb, "machine-max-jobs":fields.max_jobs,
    "machine-gpus":fields.gpu_ids == null ? "" : fields.gpu_ids.length ? fields.gpu_ids.join(",") : "none",
    "machine-capabilities":(fields.capabilities || []).join("\n"), "machine-execution":fields.execution_backend || "auto"})) $(id).value = value ?? "";
  $("machine-advanced").open = false;
  $("machine-form-error").hidden = true;
  $("save-machine").textContent = machine ? "Save settings" : "Connect & prepare";
  updateMachineKind();
  $("machine-dialog").showModal();
}
function updateMachineKind() {
  const local = $("machine-kind").value === "local";
  for (const id of ["machine-address", "machine-password"]) {
    $(id).closest("label").hidden = local;
    $(id).closest("label").nextElementSibling.hidden = local;
  }
  $("machine-address").required = !local;
}
$("machine-dialog").addEventListener("close", () => {
  $("machine-password").value = "";
});
$("machine-kind").onchange = updateMachineKind;
$("add-machine").onclick = () => fillMachine();
for (const id of ["close-machine-editor", "cancel-machine-editor"]) $(id).onclick = () => $("machine-dialog").close();
$("machine-dialog").addEventListener("click", e => {if (e.target === $("machine-dialog")) {const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}});
$("close-machine-jobs").onclick = () => $("machine-jobs-panel").hidden = true;
function renderMachineSelection() {
  const select = $("study-machines"), saved = state.project?.brief?.machine_ids || [];
  const selected = state.briefDirty ? [...select.selectedOptions].map(o => o.value) : saved;
  select.replaceChildren(new Option("This host · existing local launcher", ""));
  for (const record of state.machines) {
    const machine = record.machine, [kind,label] = machineState(record);
    // Retain an existing selection through a temporary outage; launch rechecks it.
    const option = new Option(`${machine.label || machine.id} · ${label.toLowerCase()}`, machine.id);
    option.disabled = !["ready","stale"].includes(kind) && !selected.includes(machine.id);
    option.selected = selected.includes(machine.id); select.add(option);
  }
  select.options[0].selected = !selected.some(Boolean);
}
async function assistMachine(machine) {
  const request = await api("prepare-machine-chat", {id:machine.id});
  await reloadProjects(); mode("interactive"); if (!(await openProject(request.project))) return;
  $("chat-input").value = request.prompt; $("chat-input").dispatchEvent(new Event("input")); $("chat-input").focus();
  toast("Setup conversation ready. Choose your agent and send the request.");
}
async function showMachineJobs(machine) {
  const status = await api(`machine-jobs?id=${encodeURIComponent(machine.id)}`);
  $("machine-jobs-panel").hidden = false;
  $("machine-jobs-title").textContent = `${machine.label || machine.id} · jobs`;
  $("machine-jobs-report").textContent = JSON.stringify(status,null,2);
  const list=$("machine-jobs-list");list.replaceChildren();$("machine-job-controls").replaceChildren();
  const jobs=[...(status.jobs || [])].sort((a,b)=> (b.created_at || 0)-(a.created_at || 0));
  for (const job of jobs.slice(0,15)) {
    const row=el("div",undefined,"machine-job-row");row.append(el("code",job.id.slice(-12)),el("span",job.status.replaceAll("_"," ")));
    if (["staging","queued","running","cancelling"].includes(job.status)) {
      const stop=el("button",job.status === "cancelling" ? "Stopping…" : "Cancel","quiet");stop.disabled=state.readonly;
      stop.onclick=()=>action(stop,async()=>{await api("cancel-machine-job",{id:machine.id,job:job.id});await showMachineJobs(machine);});row.append(stop);
    } else row.append(el("span",job.assigned_gpu_ids?.length ? `GPU ${job.assigned_gpu_ids.join(",")}` : "CPU"));
    list.append(row);
  }
  if(!jobs.length)list.append(el("p","No experiments on this worker yet.","field-help"));
  $("machine-jobs-panel").scrollIntoView({behavior:"smooth",block:"nearest"});
}
function renderMachines(data) {
  if(state.view!=="machines")return;
  const revision=JSON.stringify(data.machines);if(revision===state.machineRevision)return;state.machineRevision=revision;
  const grid=$("machine-grid");grid.replaceChildren();
  let online=0,gpus=0;
  for(const record of data.machines){
    const machine=record.machine,[kind,label]=machineState(record),live=record.availability;
    if(kind==="ready")online++;gpus+=machine.config.gpu_ids.length;
    const card=el("article",undefined,"execution-machine");card.dataset.machine=machine.id;
    const top=el("div",undefined,"machine-card-top"),heading=el("div",undefined,"machine-card-name");
    heading.append(el("h2",machine.label || machine.id),el("div",machineAddress(machine),"machine-address-line"));
    top.append(machineGlyph(),heading,el("span",label,`machine-status ${kind}`));card.append(top);
    const resources=el("div",undefined,"machine-resources");
    for(const [value,title] of [[machine.config.cpus,"CPU cores"],[`${+(machine.config.memory_mb/1024).toFixed(1)} GB`,"RAM budget"],[machine.config.gpu_ids.length,"GPUs"]]){
      const metric=el("div",undefined,"machine-resource");metric.append(el("strong",String(value)),el("span",title));resources.append(metric);
    }card.append(resources);
    const instruments=el("div",undefined,"machine-instruments");
    for(const name of Object.keys(record.probe?.capabilities || {})){
      const title=name.startsWith("flash") ? "FLASH" : name.startsWith("warpx") ? `WarpX${name.includes("cuda") ? " · CUDA" : ""}` : name;
      const pill=el("span",title,"machine-instrument");pill.title=name;instruments.append(pill);
    }
    if(!instruments.children.length)instruments.append(el("span","Your agent can prepare scientific tools.","no-instruments"));card.append(instruments);
    const runtime=el("div",undefined,"machine-runtime");
    const backend=machine.config.execution_backend==="process-cooperative" ? "Native process" : machine.config.execution_backend==="proot-cooperative" ? "Cooperative runtime" : "Linux sandbox";
    const active=live?.active_jobs || 0;
    runtime.append(el("span",`${backend} · ${active}/${machine.config.max_jobs} jobs`));
    const stamp=el("span",live?.checked_at ? "just checked" : "Awaiting first check");
    if(live?.checked_at){stamp.dataset.idleSince=live.checked_at;stamp.title=`Last checked ${new Date(live.checked_at*1000).toLocaleString()} · ${live.latency_ms ?? "?"} ms`;}
    runtime.append(stamp);card.append(runtime);
    if(kind==="preparing")card.append(el("p",record.preparation.phase || "Detecting hardware and preparing the worker…","machine-note"));
    const error=kind==="offline" ? live?.error : record.preparation?.status==="failed" ? record.preparation.error : record.error;
    if(error){const note=el("details",undefined,"machine-note");note.append(el("summary",kind==="offline" ? "Connection unavailable · details" : "Setup needs attention · details"),el("pre",error));card.append(note);}
    const actions=el("div",undefined,"machine-card-bottom");
    const jobs=el("button","Jobs","secondary");jobs.disabled=kind!=="ready" && kind!=="stale";jobs.onclick=()=>action(jobs,()=>showMachineJobs(machine));actions.append(jobs);
    if(kind==="setup_needed"){
      const prepare=el("button","Prepare worker","secondary");prepare.disabled=state.readonly;prepare.onclick=()=>action(prepare,async()=>{await api("prepare-machine",{id:machine.id});await refreshMachines();});actions.append(prepare);
    }
    const agent=el("button","Prepare with agent","quiet");agent.disabled=state.readonly || kind==="preparing";agent.onclick=()=>action(agent,()=>assistMachine(machine));actions.append(agent);
    const edit=el("button","Settings","quiet settings-button");edit.disabled=state.readonly;edit.onclick=()=>fillMachine(machine,record.has_password);actions.append(edit);card.append(actions);
    if(record.preparation?.log){const log=el("details",undefined,"machine-note");log.style.margin="12px 0 0";log.append(el("summary","Setup log"),el("pre",record.preparation.log));card.append(log);}
    grid.append(card);
  }
  const summary=$("machine-summary");summary.replaceChildren();
  for(const [count,text] of [[data.machines.length,"machines"],[online,"online"],[gpus,"GPUs"]]){const item=el("span");item.append(el("strong",String(count)),document.createTextNode(text));summary.append(item);}
  if(!data.machines.length){const empty=el("div",undefined,"machine-empty");empty.append(el("h2","Your first machine is one connection away."),el("p","Add an SSH address, or use this computer to get started."));grid.append(empty);}
}
async function refreshMachines(){
  const data=await api("machines");state.machines=data.machines;renderMachineSelection();renderMachines(data);
  for(const id of ["add-machine","register-local-worker","refresh-machines"])$(id).disabled=state.readonly;
  $("register-local-worker").onclick=()=>action($("register-local-worker"),async()=>{const saved=await api("save-machine",data.local_defaults);await api("prepare-machine",{id:saved.machine.id});await refreshMachines();});
}
$("refresh-machines").onclick=()=>action($("refresh-machines"),async()=>{await Promise.all(state.machines.map(r=>api("refresh-machine",{id:r.machine.id})));await refreshMachines();});
$("machine-form").onsubmit=async e=>{
  e.preventDefault();const button=e.submitter;button.disabled=true;$("machine-form-error").hidden=true;
  try{
    const previous=state.editMachine;
    const fields={execution_backend:$("machine-execution").value,capabilities:$("machine-capabilities").value.split("\n").map(s=>s.trim()).filter(Boolean)};
    for(const [key,id] of [["root","machine-root"],["run_as","machine-run-as"]])if($(id).value.trim())fields[key]=$(id).value.trim();
    for(const [key,id] of [["cpus","machine-cpus"],["memory_mb","machine-memory"],["max_jobs","machine-max-jobs"]])if($(id).value)fields[key]=Number($(id).value);
    const devices=$("machine-gpus").value.trim();if(devices)fields.gpu_ids=devices.toLowerCase()==="none" ? [] : devices.split(",").map(s=>s.trim()).filter(Boolean);
    let payload;
    if($("machine-kind").value==="local"){
      payload={...(previous || {}),id:$("machine-id").value || "local",kind:"local",label:$("machine-label-input").value || "This computer",root:fields.root,
        python:$("machine-python").value || "python3",config:{...previous?.config,...fields}};
      delete payload.config.root;delete payload.config.run_as;
      if(payload.config.execution_backend==="auto")payload.config.execution_backend="bubblewrap";
    }else if(previous && !previous.automatic_setup){
      // Existing manual installations retain their known paths and configuration.
      payload={...previous,label:$("machine-label-input").value || previous.label,
        root:fields.root || previous.root,run_as:fields.run_as || previous.run_as,
        config:{...previous.config,...fields},password:$("machine-password").value || undefined};
      delete payload.config.root;delete payload.config.run_as;
      if(payload.config.execution_backend==="auto")payload.config.execution_backend=previous.config.execution_backend;
      // Let the server parse an edited address while preserving this manual profile.
      payload.address=$("machine-address").value;delete payload.password;
      payload.overrides=undefined;
    }else payload={address:$("machine-address").value,overrides:fields};
    if($("machine-id").value)payload.id=$("machine-id").value;
    if($("machine-label-input").value)payload.label=$("machine-label-input").value;
    for(const [key,id] of [["identity_file","machine-identity"],["known_hosts","machine-known-hosts"]])if($(id).value.trim())payload[key]=$(id).value.trim();
    if($("machine-password").value)payload.password=$("machine-password").value;
    const saved=await api("save-machine",payload);
    if(payload.kind==="local")await api("prepare-machine",{id:saved.machine.id});
    $("machine-password").value="";$("machine-dialog").close();state.editMachine=null;
    await refreshMachines();toast(saved.preparation?.status === "working" ? "Connected. Preparing the worker in the background…" : "Machine settings saved.");
  }catch(error){$("machine-form-error").textContent=error.message;$("machine-form-error").hidden=false;}
  finally{button.disabled=false;}
};

let benchmarkRevision = "";
async function refreshBenchmarks() {
  const pack = await api("benchmarks");
  const revision = JSON.stringify(pack);
  if (revision === benchmarkRevision) return;
  benchmarkRevision = revision;
  window.WorkspaceBenchmarks.render(pack, {api, refresh:refreshBenchmarks, toast, readonly:state.readonly || hosted, hosted});
  $("benchmark-version").textContent = `Task pack ${pack.version} · finite diagnostic coding contracts`;
  $("benchmark-tasks").replaceChildren();
  for (const task of pack.tasks) {
    const card = el("article", undefined, "tool-card"), button = el("button", "Prepare conversation");
    card.append(el("h2", task.title), el("p", `${task.seconds / 60} minute suggested budget. ${task.fields ? "HDF5 fields and CSV diagnostics." : "CSV diagnostics; no HDF5 dependency."}`));
    button.disabled = state.readonly || hosted;
    if(hosted)button.title="Run your own benchmarks in a self-hosted Simjecture workspace.";
    button.onclick = () => action(button, async () => {
      const project = await api("prepare-benchmark", {task:task.id});
      await reloadProjects();
      if (!(await openProject(project.id))) return;
      mode("interactive");
      $("chat-input").value = "Complete the benchmark in ./benchmark under your current working directory. Read benchmark/TASK.md, preserve the inputs, implement the reducer and deliver the requested files in benchmark/. Record progress before a handoff. Do not inspect verifier or oracle implementations. Report limitations honestly.";
      $("chat-input").dispatchEvent(new Event("input"));
      $("chat-input").focus();
      toast("Task prepared. Choose your agent and send the request.");
    });
    card.append(button); $("benchmark-tasks").append(card);
  }
  $("benchmark-projects").replaceChildren();
  for (const project of pack.projects) {
    const card = el("article", undefined, "tool-card"), link = el("a", project.name);
    link.href = projectLink(project.id);
    card.append(link, el("p", project.grade?.passed === true ? "Passed the finite numerical contract" : project.grade?.passed === false ? "Incomplete or failed numerical contract" : "Not graded"));
    const button = el("button", "Grade delivered results");
    button.disabled = state.readonly || hosted;
    button.onclick = () => action(button, async () => {
      button.textContent = "Grading…";
      try {
        const report = await api("grade-benchmark", {project:project.id});
        $("benchmark-report").textContent = JSON.stringify(report, null, 2);
        $("benchmark-report").hidden = false;
        $("benchmark-report").closest("details").open = true;
        await refreshBenchmarks();
      } finally {button.textContent = "Grade delivered results";}
    });
    card.append(button); $("benchmark-projects").append(card);
  }
  if (!pack.projects.length) $("benchmark-projects").append(el("p", "Prepare a task to begin."));
}

const toolLabels = {
  "python": ["Python research stack", "Numerical exploration", "PY", "Analysis & data"],
  "warp-lbm": ["Cylinder flow", "Warp-LBM · 2D fluid dynamics", "LB", "Fluids & MHD"],
  "iter-pack": ["ITER pack", "Diagnostics & data", "IT", "Analysis & data"],
  "solps": ["SOLPS-ITER", "Edge plasma", "SP", "Plasma & fusion"],
  "jorek": ["JOREK", "Tokamak MHD", "JK", "Plasma & fusion"],
  "dina": ["DINA-PS", "Scenario modelling", "DN", "Plasma & fusion"],
  "warpx-cpu": ["WarpX · CPU", "Particle-in-cell", "WX", "Plasma & fusion"],
  "warpx-cuda": ["WarpX · CUDA", "GPU particle-in-cell", "WX", "Plasma & fusion"],
  "flash": ["FLASH", "Hydrodynamics & MHD", "FL", "Fluids & MHD"],
  "atomec": ["atoMEC", "Atomic physics", "AT", "Materials & radiation"],
  "singularity-eos": ["Singularity-EOS", "Equation of state", "ES", "Materials & radiation"],
  "m-aneos": ["M-ANEOS", "Equation of state", "ES", "Materials & radiation"],
  "feos": ["Frankfurt FEOS", "Electron/ion equation of state", "ES", "Materials & radiation"],
  "material-eos": ["Material EOS builder", "Model profiles and table export", "ES", "Materials & radiation"],
  "optab": ["Optab", "Opacity tables", "OP", "Materials & radiation"],
};
// Setup stages reported by the installer itself; they are not percentages.
const toolStageText = {
  prepare: ["Prepare", "Checking prerequisites"],
  install: ["Install", "Downloading and building"],
  verify: ["Verify", "Running readiness checks"],
};
// Local start time per running tool, so elapsed time ticks between polls.
const toolClock = {};
state.toolWatch = new Set();
state.toolStarting = new Set();
function duration(seconds) {
  const total = Math.max(0, Math.round(seconds));
  if (total < 60) return `${total}s`;
  const minutes = Math.floor(total / 60);
  if (minutes < 60) return `${minutes}m ${String(total % 60).padStart(2, "0")}s`;
  return `${Math.floor(minutes / 60)}h ${String(minutes % 60).padStart(2, "0")}m`;
}
function roughDuration(seconds) {
  if (seconds < 60) return "under a minute";
  const minutes = Math.round(seconds / 60);
  return minutes < 60 ? `about ${minutes} min` : `about ${(seconds / 3600).toFixed(1)} h`;
}
function ago(epoch) {
  const seconds = Date.now() / 1000 - epoch;
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} h ago`;
  return `${Math.floor(seconds / 86400)} d ago`;
}
function catalogTools() {
  const general = !hosted || state.hosting?.permissions.general_execution;
  const python = {
    id: "python", name: "Python research stack", installed: true, included: true,
    description: general
      ? "General Python with NumPy, SciPy, pandas and plotting. Ask your agent to write and run a numerical calculation."
      : "Numerical libraries support the installed examples. Available through the tools provided by your administrator.",
  };
  // The hosted API is the authority for its fixed collection; never add local install offers.
  return [python, ...state.tools.filter(tool => !hosted || tool.installed)];
}
function toolCategory(tool) {
  return toolLabels[tool.id]?.[3] || tool.category || "Connected tools";
}
function toolRunning(tool) {
  return tool?.state === "working";
}
function toolStages(tool) {
  const operation = tool.operation || {};
  return operation.stages || (operation.action === "check" ? ["verify"] : ["prepare", "install", "verify"]);
}
function toolFailure(tool) {
  return tool.report?.error || (tool.report?.checks || [])
    .filter(check=>check.status === "fail" && check.required !== false)
    .map(check=>[check.detail,check.remedy].filter(Boolean).join(" ")).join("\n");
}
function toolNeedsDiagnosis(tool) {
  // A managed-profile failure says nothing about unregistered local builds.
  if(tool.installed && tool.registered === false)return false;
  return !toolRunning(tool) && !tool.included && !!(toolFailure(tool) || tool.readiness === "failed" || tool.state === "failed");
}
function toolStopped(tool) {
  return !toolRunning(tool) && !!tool.operation?.cancelled;
}
function toolSection(tool) {
  if (!hosted && (toolRunning(tool) || toolNeedsDiagnosis(tool))) return "active";
  return tool.installed ? "installed" : "available";
}
function toolPresentation(tool) {
  const [name,category,glyph] = toolLabels[tool.id] || [tool.name,"Connected tool","RS"];
  const base = {name, category, glyph};
  if(tool.included)return {...base,status:"Included",kind:"installed",note:"Included with Simjecture"};
  if(hosted)return {...base,status:"Available",kind:"installed",note:"Provided by your administrator"};
  if(toolRunning(tool)){
    const check = tool.operation?.action === "check";
    if(tool.operation?.stopping)return {...base,status:"Stopping…",kind:"working",note:"Stopping setup…"};
    return {...base,status:check ? "Checking…" : "Installing…",kind:"working",note:check ? "Readiness check is running." : "Setup is running."};
  }
  if(toolNeedsDiagnosis(tool))return {...base,status:"Needs attention",kind:"attention",note:tool.installed ? "Readiness check failed · diagnose with an agent" : "Setup did not finish · diagnose with an agent"};
  if(toolStopped(tool) && !tool.installed)return {...base,status:"Stopped",kind:"not-installed",note:"Setup was stopped · install again when ready"};
  if(tool.installed && tool.registered === false)return {...base,status:"Detected",kind:"installed",note:`${tool.variants?.length || 1} local build${tool.variants?.length === 1 ? "" : "s"} · registration needed`};
  if(tool.installed)return {...base,status:tool.readiness === "passed" ? "✓ Ready" : "✓ Installed",kind:"installed",
    note:tool.readiness === "passed" ? "Readiness check passed" : "Installed · check readiness when you need it"};
  return {...base,status:"Not installed",kind:"not-installed",
    note:["agent","source"].includes(tool.action) ? "Guided setup with your agent" : "One-click install when you need it"};
}
function toolActionLabel(tool) {
  if(toolRunning(tool))return tool.operation?.action === "check" ? "Checking…" : "Installing…";
  if(toolNeedsDiagnosis(tool))return "Diagnose with agent";
  return tool.installed ? tool.registered === false ? "View installations" : "Check readiness" :
    tool.action === "custom" ? "Check readiness" : ["agent","source"].includes(tool.action) ? "Install with agent" : "Install";
}
function syncToolClock(tool) {
  const elapsed = tool.operation?.elapsed_seconds;
  if (!toolRunning(tool) || elapsed == null || tool.operation?.optimistic) return;
  const started = Date.now() / 1000 - elapsed;
  // Ignore sub-second polling jitter so the visible timer never steps backwards.
  if (toolClock[tool.id] === undefined || Math.abs(toolClock[tool.id] - started) > 2) toolClock[tool.id] = started;
}
function toolRunView(tool, large = false) {
  const region = el("div", undefined, `tool-run${large ? " large" : ""}`);
  region.dataset.toolRun = tool.id;
  if (large && toolStages(tool).length > 1) region.append(el("ol", undefined, "tool-steps"));
  const head = el("div", undefined, "tool-run-head");
  head.append(el("span", "", "tool-run-stage"), el("span", "", "tool-run-time"));
  const bar = el("div", undefined, "tool-bar");
  bar.setAttribute("role", "progressbar");
  bar.setAttribute("aria-label", `${toolPresentation(tool).name} setup progress`);
  region.append(head, bar);
  if (large) region.append(el("div", "", "tool-run-meta"));
  region.append(el("div", "", "tool-run-activity"));
  updateToolRun(region, tool);
  return region;
}
function updateToolRun(region, tool) {
  const operation = tool.operation || {};
  const stages = toolStages(tool);
  const index = Math.max(0, stages.indexOf(operation.stage));
  const started = toolClock[tool.id] ?? Date.now() / 1000;
  const elapsed = Math.max(0, Date.now() / 1000 - started);
  // Plain stage names; the activity line below shows the installer's own output.
  const detail = operation.optimistic ? "Starting…" : toolStageText[stages[index]]?.[1] || "Working";
  const stageText = operation.stopping ? "Stopping setup…"
    : stages.length > 1 ? `Step ${index + 1} of ${stages.length} · ${detail}` : detail;
  region.querySelector(".tool-run-stage").textContent = stageText;
  region.querySelector(".tool-run-time").textContent = duration(elapsed);
  const steps = region.querySelector(".tool-steps");
  if (steps) {
    if (steps.children.length !== stages.length) {
      steps.replaceChildren(...stages.map((stage) => {
        const item = el("li");
        item.append(el("span", "", "tool-step-mark"), el("strong", toolStageText[stage]?.[0] || stage), el("small", toolStageText[stage]?.[1] || ""));
        return item;
      }));
    }
    [...steps.children].forEach((item, position) => {
      const status = position < index ? "done" : position === index ? "active" : "pending";
      item.className = status;
      item.querySelector(".tool-step-mark").textContent = status === "done" ? "✓" : String(position + 1);
      if (status === "active") item.setAttribute("aria-current", "step"); else item.removeAttribute("aria-current");
    });
  }
  // A measured estimate exists only after an earlier successful run on this machine.
  const estimate = operation.estimate_seconds;
  const bar = region.querySelector(".tool-bar");
  const mode = estimate ? "estimate" : `stages-${stages.length}`;
  if (bar.dataset.mode !== mode) {
    bar.dataset.mode = mode;
    bar.replaceChildren(...(estimate ? [el("span", undefined, "tool-bar-segment")] : stages.map(() => el("span", undefined, "tool-bar-segment"))));
  }
  if (estimate) {
    const percent = Math.round(Math.min(95, Math.max(3, (elapsed / estimate) * 100)));
    bar.firstChild.className = "tool-bar-segment measured";
    bar.firstChild.style.setProperty("--fill", `${percent}%`);
    bar.setAttribute("aria-valuemin", "0");
    bar.setAttribute("aria-valuemax", "100");
    bar.setAttribute("aria-valuenow", String(percent));
    bar.removeAttribute("aria-valuetext");
  } else {
    [...bar.children].forEach((segment, position) => {
      segment.className = `tool-bar-segment ${position < index ? "done" : position === index ? "active" : ""}`;
    });
    for (const name of ["aria-valuemin", "aria-valuemax", "aria-valuenow"]) bar.removeAttribute(name);
    bar.setAttribute("aria-valuetext", stageText);
  }
  const meta = region.querySelector(".tool-run-meta");
  if (meta) {
    const timing = estimate
      ? elapsed < estimate ? `About ${roughDuration(estimate - elapsed).replace(/^about /, "")} left · usually ${roughDuration(estimate)}`
        : `Taking longer than the usual ${roughDuration(estimate).replace(/^about /, "")}`
      : "First timed run on this machine · duration depends on network and CPU";
    meta.textContent = operation.log_bytes ? `${timing} · ${bytes(operation.log_bytes)} of output` : timing;
  }
  const activity = region.querySelector(".tool-run-activity");
  activity.textContent = operation.activity ? `› ${operation.activity}` : "Waiting for output…";
  activity.title = operation.activity || "";
}
function toolFailureView(tool) {
  const box = el("div", undefined, "tool-callout attention");
  box.append(el("strong", tool.installed ? "The readiness check failed" : "Setup did not finish"));
  const list = el("ul", undefined, "tool-failure");
  if (tool.report?.error) list.append(el("li", tool.report.error));
  for (const check of (tool.report?.checks || []).filter(c => c.status === "fail" && c.required !== false)) {
    const item = el("li");
    item.append(el("span", check.detail));
    if (check.remedy) item.append(el("small", check.remedy));
    list.append(item);
  }
  if (!list.children.length) list.append(el("li", "The last attempt reported a failed readiness check."));
  box.append(list, el("p", "Diagnose with agent prepares a conversation with this error and the saved output. You review it and choose the agent before anything runs.", "tool-callout-help"));
  return box;
}
function toolConsole(tool, opened) {
  const running = toolRunning(tool);
  const details = el("details", undefined, "tool-console");
  details.dataset.key = `installation-${tool.id}`;
  details.dataset.toolConsole = tool.id;
  details.open = running || toolNeedsDiagnosis(tool) || opened.has(details.dataset.key);
  const summary = el("summary", hosted ? "Readiness checks" : running ? "Live output" : "Output from the last run");
  details.append(summary);
  const bar = el("div", undefined, "tool-console-bar");
  bar.append(el("span", running ? "Updates automatically" : tool.operation?.finished_at ? `Finished ${ago(tool.operation.finished_at)}` : "", "tool-console-state"));
  const copy = el("button", "Copy output", "quiet");
  copy.type = "button";
  const pre = el("pre", "", "tool-console-log");
  pre.tabIndex = 0;
  copy.onclick = async () => {
    try { await navigator.clipboard.writeText(pre.textContent); toast("Output copied"); }
    catch { toast("Copying is unavailable in this browser; select the text instead.", true); }
  };
  bar.append(copy);
  details.append(bar, pre);
  const facts = [];
  if (tool.operation?.log_path && !hosted) facts.push(`Full log: ${tool.operation.log_path}`);
  if (tool.operation?.attempts) facts.push(`${tool.operation.attempts} earlier attempt${tool.operation.attempts === 1 ? "" : "s"} kept`);
  if (facts.length) details.append(el("p", facts.join(" · "), "tool-console-foot"));
  updateToolConsole(details, tool);
  return details;
}
function updateToolConsole(details, tool) {
  const pre = details.querySelector("pre");
  const text = tool.log || (toolRunning(tool) ? "Waiting for setup output…" :
    Object.keys(tool.report || {}).length ? JSON.stringify(tool.report, null, 2) : "No output was recorded.");
  if (pre.textContent === text) return;
  // Follow new output only when the reader is already at the end.
  const following = !pre.textContent || pre.scrollHeight - pre.scrollTop - pre.clientHeight < 24;
  pre.textContent = text;
  if (following) pre.scrollTop = pre.scrollHeight;
}
async function runToolAction(tool, button) {
  if(hosted || state.readonly || tool.included || toolRunning(tool))return;
  await action(button,async()=>{
    if(toolNeedsDiagnosis(tool)){closeToolDetails();await assistInstallation(tool,true);return;}
    if(tool.installed && tool.registered === false){openToolDetails(tool,"variants");return;}
    if(["agent","source"].includes(tool.action) && !tool.installed){closeToolDetails();await assistInstallation(tool);return;}
    await startToolOperation(tool, tool.installed || tool.action === "custom" ? "check" : "install");
  });
  if(button.id === "tool-detail-action")button.disabled=state.readonly || hosted || toolRunning(state.tools.find(t=>t.id === tool.id) || tool);
}
async function startToolOperation(tool, operation) {
  const entry = state.tools.find(t => t.id === tool.id) || tool;
  const previous = structuredClone(entry);
  const stages = operation === "check" ? ["verify"] : ["prepare", "install", "verify"];
  // Show the start immediately; the server confirms it within the request.
  Object.assign(entry, {state: "working", log: "", operation: {
    action: operation, running: true, optimistic: true, stages, stage: stages[0],
    stage_detail: "Starting…", attempts: entry.operation?.attempts,
  }});
  toolClock[entry.id] = Date.now() / 1000;
  state.toolStarting.add(entry.id);
  renderToolChange(entry);
  try {
    await api("install", {name: entry.id, action: operation});
  } catch (error) {
    for (const key of Object.keys(entry)) delete entry[key];
    Object.assign(entry, previous);
    renderToolChange(entry);
    throw error;
  } finally {
    state.toolStarting.delete(entry.id);
  }
  state.toolWatch.add(entry.id);
  pollToolProgress().catch(() => {});
}
async function stopToolOperation(tool, button) {
  const name = toolPresentation(tool).name;
  if (!confirm(`Stop setting up ${name}?\n\nOutput so far is kept and you can start again later.`)) return;
  await action(button, async () => {
    await api("stop-install", {name: tool.id});
    const entry = state.tools.find(t => t.id === tool.id);
    if (entry?.operation) entry.operation.stopping = true;
    renderToolChange(entry || tool);
    toast(`Stopping ${name} setup…`);
  });
}
function closeToolDetails() {$("tool-details-dialog").close();state.selectedTool=null;state.toolDetailsRevision="";}
$("close-tool-details").onclick=closeToolDetails;
$("tool-details-dialog").addEventListener("close",()=>{
  const tool=state.tools.find(t=>t.id===state.selectedTool);
  if(toolRunning(tool))toast("Setup continues in the background. Follow it in Research tools.");
  state.selectedTool=null;state.toolDetailsRevision="";
});
function openToolDetails(tool, section=null) {
  state.selectedTool=tool.id;state.toolDetailsRevision="";
  $("tool-details-body").replaceChildren();
  $("tool-details-body").scrollTop=0;
  renderToolDetails(tool,section);
  if(!$("tool-details-dialog").open)$("tool-details-dialog").showModal();
}
function toolSetupExplainer(tool) {
  const box = el("div", undefined, "tool-explainer");
  if (["agent", "source"].includes(tool.action)) {
    box.append(el("strong", "Guided setup"), el("p", tool.id === "flash"
      ? "FLASH is licensed software, so you supply the source. Install with agent opens a conversation that asks for it, along with the application and physics you need, then builds and registers the runtime."
      : "This tool needs choices that only you can make. Install with agent opens a conversation with setup instructions for your agent. You review the request and choose the agent before anything runs."));
  } else if (tool.action === "custom") {
    box.append(el("strong", "Connected tool"), el("p", "Check readiness runs the probe defined by its capability descriptor."));
  } else {
    box.append(el("strong", "One-click install"), el("p", "Simjecture runs the pinned installer in its own runtime folder, then checks that the tool works. Progress and output appear here; you can close this window or stop setup at any time."));
  }
  return box;
}
function renderToolDetails(tool,section=null) {
  const body=$("tool-details-body");
  const presentation=toolPresentation(tool);
  const operation=tool.operation || {};
  const structure=JSON.stringify([tool.id,presentation,tool.installed,tool.registered,tool.action,tool.path,tool.variants,tool.report,tool.description,
    operation.stopping,operation.finished_at,operation.attempts,operation.log_path,toolStages(tool),state.readonly,state.hosting?.permissions.general_execution,state.hosting?.quota.interactive.remaining]);
  if(structure===state.toolDetailsRevision && !section){
    // Live data updates in place, keeping the reader's position and selection.
    const run=body.querySelector("[data-tool-run]");if(run)updateToolRun(run,tool);
    const output=body.querySelector("[data-tool-console]");if(output)updateToolConsole(output,tool);
    return;
  }
  const scroll=body.scrollTop;
  const opened=new Set([...body.querySelectorAll("details[open][data-key]")].map(d=>d.dataset.key));
  const previousLog=body.querySelector(".tool-console-log");
  const following=!previousLog || previousLog.scrollHeight-previousLog.scrollTop-previousLog.clientHeight<24;
  const logScroll=previousLog?.scrollTop || 0;
  $("tool-detail-title").textContent=presentation.name;
  $("tool-detail-category").textContent=presentation.category;
  $("tool-detail-state").textContent=presentation.status;
  $("tool-detail-state").className=`tool-status ${presentation.kind}`;
  body.replaceChildren();
  const running=toolRunning(tool);
  if(running)body.append(toolRunView(tool,true));
  else if(toolNeedsDiagnosis(tool) && !hosted)body.append(toolFailureView(tool));
  else if(tool.installed && tool.registered === false)body.append(el("div","Local builds are present. Connect a capability directory to use one in recorded studies. A managed-profile check does not test these detected builds.","tool-detail-note"));
  else if(tool.installed && tool.readiness === "passed" && !tool.included && !hosted){
    const ready=el("div",undefined,"tool-callout ready");
    ready.append(el("strong","Ready to use"),el("p",`Readiness check passed${operation.finished_at ? ` ${ago(operation.finished_at)}` : ""}. Each investigation still validates its own scientific method.`));
    body.append(ready);
  } else if(toolStopped(tool))body.append(el("div","The last setup was stopped before it finished. Its output is kept below.","tool-detail-note"));
  body.append(el("h3","About this tool","tool-about-heading"),el("p",tool.description));
  if(tool.author_url){const credit=el("a",`Contributed by ${tool.author}`);credit.href=tool.author_url;credit.target="_blank";credit.rel="noopener noreferrer";body.append(credit);}
  if(!tool.installed && !running && !hosted && !tool.included && !toolNeedsDiagnosis(tool))body.append(toolSetupExplainer(tool));
  if(tool.path && !hosted){const location=el("details");location.dataset.key=`location-${tool.id}`;location.open=opened.has(location.dataset.key);
    location.append(el("summary","Connected capability directory"),el("code",tool.path));body.append(location);}
  if(tool.variants?.length){
    const variants=el("details",undefined,"installed-variants");variants.dataset.key=`variants-${tool.id}`;
    variants.open=section === "variants" || opened.has(variants.dataset.key);
    variants.append(el("summary",`${tool.variants.length} ${hosted ? "starter preset" : "installed application"}${tool.variants.length === 1 ? "" : "s"}`));
    for(const variant of tool.variants){const item=el("div");item.append(el("strong",variant.label || variant.name || "Local build"),el("p",variant.description || ""));if(!hosted)item.append(el("code",variant.runtime || variant.path || ""));variants.append(item);}
    body.append(variants);
  }
  if(!hosted && tool.installed && tool.registered === false && toolFailure(tool)){
    const diagnostics=el("details");diagnostics.dataset.key=`diagnostics-${tool.id}`;
    diagnostics.open=opened.has(diagnostics.dataset.key);
    diagnostics.append(el("summary","Managed profile · setup diagnostics"),el("pre",toolFailure(tool),"tool-failure"));
    body.append(diagnostics);
  }
  if(!tool.included && (tool.log || Object.keys(tool.report || {}).length || running)){
    const output=toolConsole(tool,opened);body.append(output);
    const log=output.querySelector("pre");log.scrollTop=following ? log.scrollHeight : logScroll;
  }
  $("tool-detail-status").textContent=hosted ? "This collection is managed by your administrator." : state.readonly ? "Read-only workspace · tool setup is disabled." : tool.included ? "Included with Simjecture. No installation needed." :
    running ? "You can close this window; setup continues and its progress stays on this page." :
    toolNeedsDiagnosis(tool) ? "Your agent receives the saved error and output. You choose the agent and send the request." :
    tool.installed ? "Installation is separate from scientific validation." : "Optional research tool · install when you need it";
  const actionButton=$("tool-detail-action");actionButton.textContent=toolActionLabel(tool);
  actionButton.disabled=running || state.readonly || hosted;
  actionButton.hidden=hosted || !!tool.included;
  actionButton.className=toolNeedsDiagnosis(tool) || (!tool.installed && !running) ? "primary" : "secondary";
  actionButton.onclick=()=>runToolAction(tool,actionButton);
  renderToolOptions(tool);
  body.scrollTop=section ? 0 : scroll;state.toolDetailsRevision=structure;
}
function researchToolCard(tool) {
  const p=toolPresentation(tool),card=el("article",undefined,"research-tool-card");card.dataset.tool=tool.id;card.dataset.state=p.kind;
  const top=el("div",undefined,"research-tool-top"),name=el("div",undefined,"research-tool-name");
  name.append(el("h3",p.name),el("small",p.category));
  top.append(el("span",p.glyph,"research-tool-icon"),name,el("span",p.status,`tool-status ${p.kind}`));
  const description=el("p",tool.description,"research-tool-description");description.title=tool.description;
  card.append(top,description);
  if(toolRunning(tool))card.append(toolRunView(tool));
  else card.append(el("div",p.note,`research-tool-note${p.kind === "attention" ? " attention" : ""}`));
  card.dataset.category=toolCategory(tool);
  const details=el("button",toolRunning(tool) ? "View progress →" : toolNeedsDiagnosis(tool) && !hosted ? "Diagnose setup →" : "Explore tool →","tool-card-open");
  details.type="button";details.setAttribute("aria-label",`View ${p.name} details`);
  details.setAttribute("aria-haspopup","dialog");details.onclick=()=>openToolDetails(state.tools.find(t=>t.id===tool.id) || tool);
  card.append(details);
  return card;
}
function renderToolOptions(tool) {
  const actions=$("tool-detail-options");
  const revision=JSON.stringify([tool.id,tool.installed,tool.action,tool.state,tool.readiness,tool.report,tool.operation?.stopping,tool.variants,tool.benchmark,tool.general_execution,state.readonly,state.hosting?.permissions.general_execution,state.hosting?.quota.interactive.remaining]);
  if(actions.dataset.revision===revision)return;
  const previousChoice=actions.querySelector("select")?.value;
  const previousTool=actions.dataset.selectedTool;
  actions.replaceChildren();actions.dataset.revision=revision;actions.dataset.selectedTool=tool.id;
  if(tool.included)return;
  if(!hosted && toolRunning(tool)){
    const stop=el("button",tool.operation?.stopping ? "Stopping…" : "Stop setup","quiet danger-text");stop.type="button";
    stop.disabled=state.readonly || !!tool.operation?.stopping;
    stop.onclick=()=>stopToolOperation(tool,stop);actions.append(stop);
  }
  if(!hosted && toolNeedsDiagnosis(tool)){
    const retry=el("button",tool.installed || tool.action === "custom" ? "Retry readiness check" : "Retry installation","quiet");
    retry.disabled=state.readonly;
    retry.onclick=()=>action(retry,async()=>{
      if(["agent","source"].includes(tool.action) && !tool.installed){closeToolDetails();return assistInstallation(tool,true);}
      await startToolOperation(tool,tool.installed || tool.action === "custom" ? "check" : "install");
    });actions.append(retry);
  }
  if(hosted && tool.variants?.some(v=>v.tool_id)){
    const general=tool.general_execution ?? state.hosting?.permissions.general_execution;
    const choice=el("select");choice.setAttribute("aria-label",`${tool.name} study setup`);
    if(general)choice.add(new Option("Custom study · prepare with agent","custom-study"));
    const presets=el("optgroup");presets.label="Starter presets";
    for(const variant of tool.variants.filter(v=>v.tool_id))presets.append(new Option(variant.label,variant.tool_id));
    choice.append(presets);
    if(previousTool===tool.id && [...choice.options].some(o=>o.value===previousChoice))choice.value=previousChoice;
    choice.disabled=state.readonly;
    const demo=el("button",general ? "Prepare in chat" : "Run preset","secondary");
    demo.disabled=state.readonly || state.hosting?.quota.interactive.remaining===0;
    choice.onchange=()=>demo.textContent=choice.value==="custom-study" ? "Prepare in chat" : "Run preset";
    choice.onchange();
    demo.onclick=()=>action(demo,async()=>{
      if(choice.value==="custom-study"){closeToolDetails();return prepareToolStudy(tool);}
      const result=await api("tool-demo",{name:choice.value});closeToolDetails();await reloadProjects();mode("interactive");await openProject(result.project);toast("Starter preset queued. Follow its run in Simulations.");
    });
    actions.append(choice,demo);
  }
  if(!hosted && !tool.installed && tool.action !== "custom" && !toolRunning(tool) && !toolNeedsDiagnosis(tool)){
    const check=el("button","Check existing install","quiet");check.disabled=state.readonly;
    check.title="Already installed this tool yourself? Run its readiness check.";
    check.onclick=()=>action(check,()=>startToolOperation(tool,"check"));actions.append(check);
  }
  if(["iter-pack","warp-lbm"].includes(tool.id) && tool.installed && !hosted){const demo=el("button",tool.id === "warp-lbm" ? "Run cylinder wake" : "Run demo","quiet");demo.disabled=toolRunning(tool) || state.readonly;
    demo.onclick=()=>action(demo,async()=>{const result=await api("tool-demo",{name:tool.id});closeToolDetails();await reloadProjects();mode("interactive");if (!(await openProject(result.project))) return;await monitor.open(result.simulation.id);toast("Simulation started. Its plots and results will appear in Simulations.");});actions.append(demo);}
  if(tool.benchmark && tool.installed){const benchmark=el("button","Prepare benchmark","quiet");benchmark.disabled=state.readonly;
    benchmark.onclick=()=>action(benchmark,async()=>{const project=await api("projects",{name:tool.benchmark.title});closeToolDetails();await reloadProjects();if (!(await openProject(project.id)))return;mode("interactive");$("chat-input").value=tool.benchmark.prompt;$("chat-input").dispatchEvent(new Event("input"));$("chat-input").focus();toast("Benchmark task prepared. Choose your agent and send the request.");});actions.append(benchmark);}
}
$("connect-research-tool").onclick=()=>$("custom-tool-dialog").showModal();
for(const id of ["close-custom-tool","cancel-custom-tool"])$(id).onclick=()=>$("custom-tool-dialog").close();
$("tools-open-machines").onclick=()=>view("machines");
function filterToolCatalog() {
  const terms=$("tool-search").value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  const category=$("tool-category").value;
  const tools=catalogTools();
  const cards=new Map([...document.querySelectorAll(".research-tool-card")].map(card=>[card.dataset.tool,card]));
  const counts={active:0,installed:0,available:0};
  for(const tool of tools){
    const card=cards.get(tool.id);
    if(!card)continue;
    const p=toolPresentation(tool);
    const searchable=[tool.id,tool.name,p.name,p.category,toolCategory(tool),tool.description,
      ...(tool.variants || []).flatMap(v=>[v.label,v.name,v.description])].filter(Boolean).join(" ").toLocaleLowerCase();
    const matches=terms.every(term=>searchable.includes(term)) && (category==="all" || category===toolCategory(tool)) &&
      (hosted || state.toolFilter==="all" || (state.toolFilter==="installed" ? tool.installed : !tool.installed));
    card.hidden=!matches;
    if(matches)counts[toolSection(tool)]++;
  }
  const total=counts.active+counts.installed+counts.available;
  $("active-count").textContent=counts.active;
  $("installed-count").textContent=counts.installed;
  $("available-count").textContent=counts.available;
  $("active-tool-section").hidden=counts.active===0;
  $("installed-tool-section").hidden=counts.installed===0;
  $("available-tool-section").hidden=counts.available===0 || hosted;
  $("tool-search-empty").hidden=total>0;
  $("tool-results-count").textContent=`${total} of ${tools.length} tools`;
  for(const button of document.querySelectorAll("[data-tool-filter]"))button.setAttribute("aria-pressed",String(button.dataset.toolFilter===state.toolFilter));
}
$("tool-search").addEventListener("input",filterToolCatalog);
$("tool-category").addEventListener("change",filterToolCatalog);
for(const button of document.querySelectorAll("[data-tool-filter]"))button.onclick=()=>{state.toolFilter=button.dataset.toolFilter;filterToolCatalog();};
$("clear-tool-filters").onclick=()=>{
  $("tool-search").value="";$("tool-category").value="all";state.toolFilter="all";
  filterToolCatalog();$("tool-search").focus();
};
function renderToolActivity() {
  const nav=document.querySelector('.nav-item[data-view="tools"]');
  if(!nav)return;
  const running=hosted ? 0 : state.tools.filter(toolRunning).length;
  let badge=nav.querySelector(".nav-activity");
  if(!running){badge?.remove();return;}
  if(!badge){badge=el("span",undefined,"nav-activity");nav.append(badge);}
  badge.textContent=String(running);
  const label=`${running} tool setup${running === 1 ? "" : "s"} running`;
  badge.title=label;badge.setAttribute("aria-label",label);badge.setAttribute("role","status");
}
function renderToolChange(tool) {
  renderToolsView();
  if(tool && state.selectedTool===tool.id && $("tool-details-dialog").open)renderToolDetails(tool);
  renderToolActivity();
}
function renderToolsView() {
  if(state.view!=="tools")return;
  const tools=catalogTools();
  $("tool-collection-note").hidden=!hosted && !state.readonly;
  $("tool-collection-note").textContent=hosted
    ? "Managed collection · Your administrator chooses and maintains the tools available on this server. Explore a tool to see how you can use it."
    : "Read-only workspace · You can explore tools and their details. Installation and setup changes are disabled.";
  $("tool-availability-filters").hidden=hosted;
  $("tools-machines-help").hidden=hosted;
  $("installed-tool-label").textContent=hosted ? "Available in this workspace" : "On your workbench";
  $("installed-tool-help").textContent=hosted ? "Provided and maintained by your administrator" : "Installed tools and detected local builds";
  $("connect-research-tool").hidden=hosted;
  $("connect-research-tool").disabled=state.readonly || hosted;
  for(const button of $("custom-tool-form").querySelectorAll("button[type='submit']"))button.disabled=state.readonly || hosted;
  if(state.selectedTool && $("tool-details-dialog").open){const selected=tools.find(t=>t.id===state.selectedTool);if(selected)renderToolDetails(selected);else closeToolDetails();}
  // Raw logs and timers update in place; cards are rebuilt only when their state changes.
  const revision=JSON.stringify(tools.map(t=>({id:t.id,presentation:toolPresentation(t),section:toolSection(t),stages:toolRunning(t) ? toolStages(t) : null,category:toolCategory(t),description:t.description,installed:t.installed,variants:t.variants})));
  if(revision===state.toolsRevision){
    for(const region of document.querySelectorAll(".research-tool-card [data-tool-run]")){const tool=tools.find(t=>t.id===region.dataset.toolRun);if(tool)updateToolRun(region,tool);}
    return;
  }
  const scroll=document.scrollingElement.scrollTop;
  const grids={active:$("active-tool-grid"),installed:$("installed-tool-grid"),available:$("available-tool-grid")};
  for(const grid of Object.values(grids))grid.replaceChildren();
  const category=$("tool-category").value;
  const categories=[...new Set(tools.map(toolCategory))].sort();
  $("tool-category").replaceChildren(new Option("All categories","all"),...categories.map(c=>new Option(c,c)));
  if(categories.includes(category))$("tool-category").value=category;
  for(const tool of tools)grids[toolSection(tool)].append(researchToolCard(tool));
  filterToolCatalog();
  document.scrollingElement.scrollTop=scroll;state.toolsRevision=revision;
}
async function refreshTools() {
  const fetched=await api("tools");
  // Keep an optimistic start visible until the server has recorded it.
  state.tools=fetched.map(tool=>state.toolStarting.has(tool.id) ? state.tools.find(t=>t.id===tool.id) || tool : tool);
  for(const tool of state.tools){syncToolClock(tool);if(toolRunning(tool) && !hosted && !state.toolStarting.has(tool.id))state.toolWatch.add(tool.id);}
  const previous=$("study-tools").value;$("study-tools").replaceChildren(new Option("All available tools (default)","auto"),new Option("Python only · no external solver",""));
  const paths=new Set();
  for(const tool of state.tools){const variants=tool.variants?.length ? tool.variants : [tool];for(const item of variants)if(item.path && !paths.has(item.path)){paths.add(item.path);$("study-tools").add(new Option(item.label || item.name,item.path));}}
  const desired=state.project?.brief?.capability_directory ?? previous ?? "auto";
  if(desired && ![...$("study-tools").options].some(o=>o.value===desired))$("study-tools").add(new Option("Saved tool restriction · check availability",desired));
  $("study-tools").value=desired;
  if(hosted){$("study-tools").replaceChildren(new Option("All verified hosted tools","hosted-tools"));$("study-tools").disabled=true;}
  renderToolActivity();
  renderToolsView();
}
function announceToolResult(id) {
  const tool=state.tools.find(t=>t.id===id);
  if(!tool)return;
  const name=toolPresentation(tool).name, check=tool.operation?.action === "check";
  if(tool.operation?.cancelled)toast(`${name}: setup stopped. Its output is kept.`);
  else if(toolNeedsDiagnosis(tool))toast(`${name} needs attention. Open it in Research tools to see why and diagnose with an agent.`,true);
  else if(tool.installed)toast(`✓ ${name} ${check ? "passed its readiness check" : "is installed and ready"}.`);
  else toast(`${name}: ${check ? "readiness check" : "setup"} finished.`);
}
async function pollToolProgress() {
  if(hosted || state.toolPolling || !state.toolWatch.size)return;
  state.toolPolling=true;
  const finished=[];
  try {
    for(const id of [...state.toolWatch]){
      if(state.toolStarting.has(id))continue;
      const data=await api(`tool-progress?name=${encodeURIComponent(id)}`);
      const tool=state.tools.find(t=>t.id===id);
      if(!tool){state.toolWatch.delete(id);continue;}
      if(data.operation?.running){
        Object.assign(tool,{state:"working",operation:data.operation,log:data.log});
        syncToolClock(tool);
        renderToolChange(tool);
      } else {state.toolWatch.delete(id);finished.push(id);}
    }
    if(finished.length){
      await refreshTools();
      for(const id of finished)announceToolResult(id);
    }
  } finally {state.toolPolling=false;}
}
// Elapsed time and estimated progress advance every second between polls.
setInterval(()=>{
  for(const region of document.querySelectorAll("[data-tool-run]")){
    const tool=state.tools.find(t=>t.id===region.dataset.toolRun);
    if(toolRunning(tool))updateToolRun(region,tool);
  }
},1000);

function briefPayload() {
  return {
    project: state.project.id,
    question: $("brief-question").value,
    success_criteria: $("brief-criteria").value,
    constraints: $("brief-constraints").value,
    hours: Number($("brief-hours").value),
    completion_policy: $("brief-policy").value,
    allow_solver_development: $("solver-development").checked,
    capability_directory: $("study-tools").value,
    machine_ids: [...$("study-machines").selectedOptions].map(o=>o.value).filter(Boolean),
  };
}
async function saveBrief() {
  const brief = await api("brief", briefPayload());
  state.project.brief = brief;
  state.briefDirty = false;
  state.launchKey = null;
  renderProject();
}
async function renderStudies() {
  if (!state.project || state.mode !== "autonomous") return;
  const projectId = state.project.id;
  const request = ++state.studyRequest;
  const studies = state.project.studies;
  const responses = await Promise.all(
    studies.map(async (study) => {
      try {
        return { study, data: await api(`study?id=${study.campaign}`) };
      } catch (error) {
        return { study, error: error.message };
      }
    }),
  );
  if (request !== state.studyRequest || state.project?.id !== projectId || state.mode !== "autonomous") return;
  renderStudyNavigation();
  const rev = JSON.stringify(responses);
  if (rev === state.studyRevision) return;
  const openDetails = new Set(
    [...$("study-runs").querySelectorAll("details[open]")].map(
      (x) => x.dataset.key,
    ),
  );
  $("study-runs").replaceChildren();
  for (const { study, data, error } of responses.reverse()) {
    const card = el("article", undefined, "study-card");
    card.id = `study-${study.campaign}`;
    card.classList.toggle("selected-study", study.campaign === state.routeStudy);
    const heading = el("h3");
    const selectedLink = el("a", study.question);
    selectedLink.href = projectLink(projectId, { view: "autonomous", study: study.campaign });
    heading.append(selectedLink);
    if (error) {
      card.append(heading, el("p", error, "error-text"));
      $("study-runs").append(card);
      continue;
    }
    const snap = data.snapshot,
      report = data.report || {},
      raw = snap.snapshot || {};
    const status =
      data.live?.status || raw.phase || report.status || "starting";
    const meta = el("div", undefined, "study-meta");
    meta.append(
      el("span", String(status).replaceAll("_", " ").toUpperCase(), "badge"),
      el("span", study.campaign_id),
    );
    const select = el("a", study.campaign === state.routeStudy ? "Selected study" : "Select study", "study-selection");
    select.href = selectedLink.href;
    meta.append(select);
    card.append(meta, heading);
    const finished = ["completed", "cancelled", "budget_exhausted"].includes(
      status,
    );
    if (finished) {
      card.append(
        el(
          "p",
          status === "completed"
            ? "Study finished. Review its findings and independent assessment below."
            : "Study stopped before an accepted outcome. The report records the partial findings.",
          "field-help",
        ),
      );
      const returned = el(
        "a",
        study.report_turn
          ? "Read the agent’s explanation in conversation ↗"
          : "Return to the conversation ↗",
        "secondary",
      );
      returned.href = projectLink(state.project.id, {
        view: "interactive",
        study: study.campaign,
        ...(study.report_turn ? { turn: study.report_turn } : {}),
      });
      card.append(returned);
      if (!study.explain_on_finish && !study.report_turn) {
        const explain = el("button", "Explain in conversation", "secondary");
        explain.disabled = state.readonly;
        explain.onclick = () =>
          action(explain, async () => {
            await api("explain-study", {
              project: state.project.id,
              campaign: study.campaign,
            });
            mode("interactive");
            toast("Report queued for your interactive agent.");
          });
        card.append(explain);
      }
      card.append(
        el(
          "p",
          study.report_turn
            ? "The report has been handed to your interactive agent. Its explanation appears in the conversation."
            : study.explain_on_finish
              ? "The report will be explained here automatically when the interactive agent is free. Keep the workspace server running; closing the browser is fine."
              : "Ask your interactive agent to explain this report when you are ready.",
          "field-help",
        ),
      );
    }
    const metrics = el("div", undefined, "metrics");
    for (const [label, value] of [
      [
        "Experiments",
        report.experiments?.length ?? snap.executions?.length ?? 0,
      ],
      ["Independent reviews", report.reviews?.length ?? 0],
      ["Input tokens", data.live?.usage ? data.live.usage.input_tokens.toLocaleString() : "—"],
      ["Output tokens", data.live?.usage ? data.live.usage.output_tokens.toLocaleString() : "—"],
      ["Provider retry wait", `${Math.round((data.live?.provider_wait_seconds || 0) / 60)} min`],
      [
        "Time remaining",
        data.live?.remaining === null ? "Unlimited" : data.live?.remaining === undefined
          ? "—"
          : `${Math.max(0, Math.ceil(data.live.remaining / 60))} min`,
      ],
    ]) {
      const item = el("div", label);
      item.prepend(el("strong", String(value)));
      metrics.append(item);
    }
    card.append(metrics);
    const budget = el("div");
    window.StudyBudget.render(budget, {
      campaign:study.campaign, budget:data.live?.budget_control, readonly:state.readonly,
      submit:payload => api("extend-study", payload),
      submitLimits:hosted ? undefined : payload => api("study-limits", payload),
      onLimitsSaved:async () => {
        toast("Run settings saved. New worker and review calls will use them.");
        state.studyRevision = "";
        if (state.project?.id === projectId) await renderStudies();
      },
      onSaved:async () => {
        toast("Study time extended. The director will update its plan.");
        state.studyRevision = "";
        if (state.project?.id === projectId) await renderStudies();
      },
    });
    const budgetHistory = budget.querySelector("details[data-budget-history]");
    if (budgetHistory && openDetails.has(budgetHistory.dataset.key)) budgetHistory.open = true;
    card.append(budget);
    card.append(el("p", data.live?.activity || "", "field-help"));
    if (data.live?.background_review) card.append(el("p", "Director reviewing alongside the worker", "field-help"));
    if (data.live?.usage_details) {
      const usage = data.live.usage_details;
      card.append(el("p", `${usage.requests} tracked requests; ${usage.requests_without_usage} without usage yet. Cache usage ${usage.cache_usage_complete ? "reported" : "not fully reported"}. ${usage.cost_note}`, "field-help"));
    }
    const instrument = data.live?.instrument_requirement;
    if (instrument?.prefixes?.length) card.append(el("p", `Instrument family: any of ${instrument.prefixes.join(" or ")}. ${instrument.satisfied ? "Available" : "Not available"}; scientific qualification is separate.`, "field-help"));
    const controls = el("div", undefined, "study-controls");
    for (const [verb, label, allowed] of [
      ["pause", "Pause", snap.controls?.can_pause],
      ["resume", "Resume", snap.controls?.can_resume],
      ["cancel", "Stop", snap.controls?.can_cancel],
    ])
      if (allowed) {
        const b = el("button", label, "secondary");
        b.disabled = state.readonly;
        b.onclick = () =>
          action(b, async () => {
            const result = await api(
              `/api/campaigns/${study.campaign}/control/${verb}`,
              {},
            );
            toast(result.message);
            state.studyRevision = "";
            await renderStudies();
          });
        controls.append(b);
      }
    const monitor = el("a", "Evidence & review ↗", "secondary");
    monitor.href = window.StudyNavigation.evidence(study.campaign);
    controls.append(monitor);
    if (data.live?.mode === "minimal") {
      for (const [kind, label] of [["continue", "Continue investigation"], ["steer", "Send guidance"]]) {
        if (kind === "steer" && (data.live.remaining <= 0 || ["completed", "cancelled", "budget_exhausted"].includes(status))) continue;
        const button = el("button", label, "secondary"); button.disabled = state.readonly;
        button.onclick = () => action(button, () => openResearchAction(study.campaign, kind)); controls.append(button);
      }
    }
    card.append(controls);
    if (study.parent_campaign) {
      const parent = el("a", "Continues an earlier study ↗", "field-help"); parent.href = `/monitor?campaign=${encodeURIComponent(study.parent_campaign)}`; card.append(parent);
    }
    if (data.steering?.length) {
      const notes = el("details"); notes.dataset.key = `steering-${study.campaign}`; notes.open = openDetails.has(notes.dataset.key);
      notes.append(el("summary", `Operator guidance (${data.steering.filter(n => !n.delivered_at).length} queued)`));
      for (const note of data.steering) {
        notes.append(el("p", `${note.delivered_at ? "Included at agent checkpoint" : "Queued"} · ${new Date(note.created_at * 1000).toLocaleString()}`, "field-help"), el("p", note.message));
      }
      card.append(notes);
    }
    const findings = el("div", undefined, "study-findings");
    findings.append(el("p", "Experiment outputs are recorded results. Scientific acceptance comes from independent review; completing a run alone does not establish a claim.", "field-help"));
    for (const review of report.reviews || [])
      if (review.verdict) {
        const v = review.verdict;
        findings.append(
          el(
            "p",
            `${v.decision === "approved" ? "Accepted" : "More evidence needed"}: ${v.disposition}. ${v.rationale}`,
          ),
        );
      }
    if (data.results) {
      const details = el("details");
      details.dataset.key = `results-${study.campaign}`;
      details.open = openDetails.has(details.dataset.key);
      details.append(el("summary", "Scientific results"));
      const prose = el("div", undefined, "message-content");
      md(prose, data.results);
      details.append(prose);
      findings.append(details);
    }
    const files = el("details");
    files.dataset.key = `files-${study.campaign}`;
    files.open = openDetails.has(files.dataset.key);
    files.append(
      el("summary", "Results, reports, and simulation files"),
      el("code", study.path),
    );
    const linkFile = (name, label) => {
      const link = el("a", label);
      link.href = `/api/artifact?campaign=${study.campaign}&path=${encodeURIComponent(name)}`;
      const row = el("div", undefined, "file-row");
      row.append(link);
      return row;
    };
    for (const artifact of snap.artifacts || [])
      if (
        [
          "RESULTS_INDEX.md",
          "STUDY_LEDGER.md",
          "research_report.json",
          "research/RESULTS.md",
        ].includes(artifact.path)
      )
        files.append(linkFile(artifact.path, artifact.name));
    for (const [index, experiment] of (report.experiments || []).entries()) {
      files.append(
        el(
          "p",
          `${index + 1}. ${experiment.key || experiment.binding?.source || "Simulation"} · ${experiment.status}`,
        ),
      );
      for (const output of experiment.outputs || [])
        files.append(
          linkFile(`experiments/${experiment.id}/workspace/${output}`, output),
        );
      if (experiment.machine) files.append(el("p", `Machine: ${experiment.machine} · ${experiment.transport_status || "recorded"}`));
      const retained = Object.keys(experiment.remote_artifacts || {}).filter(name=>!experiment.artifacts?.[name]);
      if (retained.length) {
        const select = el("select"); select.setAttribute("aria-label", "Remote artifact to retrieve");
        for (const name of retained) select.add(new Option(name, name));
        const fetch = el("button", "Retrieve from worker", "secondary"); fetch.disabled = state.readonly;
        fetch.onclick = () => action(fetch, async () => {
          await api("fetch-remote-artifact", {campaign:study.campaign,experiment:experiment.id,path:select.value});
          state.studyRevision = ""; await renderStudies(); toast("Artifact retrieved and SHA256 verified.");
        });
        files.append(select, fetch);
      }
    }
    const all = el("details");
    all.append(el("summary", "All recorded files"));
    for (const artifact of snap.artifacts || [])
      all.append(linkFile(artifact.path, artifact.path));
    files.append(all);
    findings.append(files);
    card.append(findings);
    $("study-runs").append(card);
  }
  state.studyRevision = rev;
}
async function boot() {
  const data = await api("bootstrap");
  state.token = data.control_token;
  state.settings = data.settings;
  if(!hosted)renderAccount();
  if(hosted){
    state.hosting=data.hosting;renderHosting();
    for(const name of ["machines","settings"])document.querySelector(`[data-view="${name}"]`).hidden=true;
    for(const id of ["connect-research-tool","tools-open-machines","connection-button","continuation-chat"])$(id).hidden=true;
    if(data.hosting.wall_seconds===null){$("brief-hours").removeAttribute("max");$("brief-hours").min="0";$("brief-hours").value="0";document.querySelector('label[for="brief-hours"]').textContent="Time budget (hours; 0 = unlimited)";}else{$("brief-hours").max=String(data.hosting.wall_seconds/3600);$("brief-hours").value=$("brief-hours").max;}
    for(const id of ["execution-backend","study-machines","research-director","review-backend","review-model","review-effort"])$(id).disabled=true;
    $("research-director").checked=false;
    $("research-director").closest("label").hidden=true;
    $("brief-policy").value="answer";
    $("brief-policy").disabled=true;
    $("first-request-help").textContent="Enter to send · Shift + Enter for a new line. The hosted agent and compute are ready.";
    $("execution-backend").replaceChildren(new Option("Managed experiments","trusted-template"));
    $("review-model").placeholder="Assigned by the host";
    $("review-agent-help").textContent="The review agent is managed by the host.";
    document.querySelector(".research-tools-heading .lead").textContent="Verified tools provided for this hosted workspace.";
  }
  const reviewBackend = $("review-backend");
  for (const cli of state.settings.clis || [])
    if (cli.path) reviewBackend.add(new Option(`${cli.id} · local CLI`, cli.id));
  reviewBackend.add(new Option("Compatible API · Connections", "builtin"));
  reviewBackend.onchange = () => {
    const different = reviewBackend.value && reviewBackend.value !== state.project?.agent?.backend;
    $("review-model").required = Boolean(different);
    $("review-model").placeholder = different ? "Model ID for the selected agent" : "Default: conversation agent model";
    $("review-effort").disabled = hosted || reviewBackend.value === "agy";
    if (reviewBackend.value === "agy") $("review-effort").value = "";
  };
  const execution = data.settings.execution;
  $("execution-backend").value = execution?.backend || "bubblewrap";
  let executionNoticeKey = "";
  function executionWarning() {
    const cooperative =
      ["proot-cooperative", "process-cooperative"].includes(execution?.backend) ||
      ["proot-cooperative", "process-cooperative"].includes($("execution-backend").value);
    const blocked = execution && !execution.available;
    const warning = cooperative
      ? execution?.warning ||
        "Cooperative execution is not a security sandbox: it does not isolate host files or networking. Use only trusted code under a dedicated non-root account."
      : blocked
        ? "Isolated experiments cannot run on this host. Cooperative mode needs PRoot and a dedicated non-root account."
        : "";
    executionNoticeKey = JSON.stringify([
      data.settings.machine,
      execution,
      cooperative,
    ]);
    let dismissed = false;
    try {
      dismissed =
        localStorage.getItem("simjecture-execution-notice-dismissed") ===
        executionNoticeKey;
    } catch {}
    const label = hosted ? "Verified tools ready" : cooperative
      ? "Limited isolation"
      : blocked
        ? "Experiments unavailable"
        : execution?.available
          ? "Isolated experiments ready"
          : "Execution status unchecked";
    $("execution-status").textContent = label;
    $("execution-status").disabled = !warning;
    $("execution-warning-title").textContent = cooperative
      ? "Limited isolation"
      : "Execution needs setup";
    $("execution-warning-message").textContent = warning;
    $("execution-warning-diagnostics").textContent = [
      execution?.reason,
      execution?.fallback_reason,
      execution?.fallback_unavailable,
    ]
      .filter(Boolean)
      .join("\n");
    $("execution-warning-details").hidden = !$("execution-warning-diagnostics")
      .textContent;
    $("execution-warning").hidden = !warning || dismissed;
    $("execution-status").setAttribute(
      "aria-expanded",
      String(!$("execution-warning").hidden),
    );
  }
  $("dismiss-execution-warning").onclick = () => {
    try {
      localStorage.setItem(
        "simjecture-execution-notice-dismissed",
        executionNoticeKey,
      );
    } catch {}
    $("execution-warning").hidden = true;
    $("execution-status").setAttribute("aria-expanded", "false");
  };
  $("execution-status").onclick = () => {
    try {
      localStorage.removeItem("simjecture-execution-notice-dismissed");
    } catch {}
    executionWarning();
  };
  $("execution-backend").addEventListener("change", executionWarning);
  executionWarning();
  state.projects = data.projects;
  state.readonly = !data.allow_mutations;
  globalThis.WorkspaceProjects?.init(data);
  globalThis.WorkspaceKnowledge?.init(data);
  $("readonly").hidden = !state.readonly;
  renderSettings();
  renderProjects();
  await renderAgent(undefined, "home");
  if (state.readonly)
    for (const b of document.querySelectorAll(
      "form button, #new-project, #check-machine",
    ))
      b.disabled = true;
  await followRoute({ reveal: false });
}
for (const item of document.querySelectorAll("[data-view]"))
  item.onclick = () => {
    if (item.dataset.view === "home") globalThis.WorkspaceProjects?.setSelected(null);
    // User navigation supersedes an unfinished route, including its pending fetches.
    location.hash = item.dataset.view;
    view(item.dataset.view);
  };
$("connection-button").onclick = () => view("settings");
$("rail-toggle").onclick = () => $("left-sidebar-toggle").click();
$("rail-new-project").onclick = () => $("new-project").click();
const accountBox=$("hosting-account"), accountButton=$("account-button");
function closeAccount() {accountBox.hidden=true;accountButton.setAttribute("aria-expanded","false");}
accountButton.onclick=()=>{accountBox.hidden=!accountBox.hidden;accountButton.setAttribute("aria-expanded",String(!accountBox.hidden));if(!accountBox.hidden)accountBox.querySelector("a,button")?.focus();};
document.addEventListener("pointerdown",e=>{if(!document.querySelector(".account-rail").contains(e.target)&&!accountBox.contains(e.target))closeAccount();});
document.addEventListener("keydown",e=>{if(e.key==="Escape"&&!accountBox.hidden){closeAccount();accountButton.focus();}});
mountHomeAgent();
globalThis.WorkspaceComposer?.mount($("chat-form"), $("chat-input"), document.querySelector("#chat-form .agent-controls"), "conversation");
globalThis.WorkspaceComposer?.mount($("quick-start"), $("first-request"), document.querySelector("#quick-start .agent-controls"), "home");
for (const scope of ["home", "conversation"]) {
  const c = agentControls(scope);
  c.backend.onchange = () =>
    renderAgent(c.backend.value, scope)
      .then((ready) => {
        if (ready && agentPayload(scope).model)
          return saveConversationAgent(scope);
      })
      .catch((e) => toast(e.message, true));
  c.model.onchange = () => {
    globalThis.WorkspaceComposer?.refresh(scope);
    c.customBox.hidden = c.model.value !== "__custom__";
    if (!c.customBox.hidden) {
      c.custom.focus();
      return;
    }
    saveConversationAgent(scope).catch((e) => toast(e.message, true));
  };
  c.custom.onchange = () =>
    saveConversationAgent(scope).catch((e) => toast(e.message, true));
  c.effort.onchange = () =>
    saveConversationAgent(scope).catch((e) => toast(e.message, true));
  c.refresh.onclick = () =>
    action(c.refresh, () => renderAgent(c.backend.value, scope));
}
$("provider-preset").onchange = () => {
  const preset = {
    deepseek: ["https://api.deepseek.com/v1", "deepseek-chat"],
    openrouter: ["https://openrouter.ai/api/v1", ""],
    local: ["http://localhost:11434/v1", ""],
  }[$("provider-preset").value];
  if (preset) {
    $("base-url").value = preset[0];
  }
};
$("settings-form").onsubmit = (e) => {
  e.preventDefault();
  action($("save-connection"), async () => {
    $("connection-result").textContent = "Saving API connection…";
    try {
      state.settings = await api("api-settings", {
        base_url: $("base-url").value,
        api_key: $("api-key").value,
      });
    } catch (error) {
      $("connection-result").textContent = `Connection not saved: ${error.message}`;
      throw error;
    }
    $("api-key").value = "";
    renderSettings();
    toast("API connection saved. Choose its model in a conversation.");
    await renderAgent(undefined, "home");
    if (state.project) await renderAgent();
  });
};
$("check-machine").onclick = () =>
  action($("check-machine"), async () => {
    $("machine-result").textContent = "Checking Linux experiment execution…";
    const result = await api("machine");
    $("machine-result").textContent = result.available
      ? "Ready. Recorded experiments can run in the Linux sandbox."
      : `${result.reason} ${result.remedy || ""}`;
  });
$("new-project").onclick = () => {
  state.project = null;
  globalThis.WorkspaceKnowledge?.newConversation();
  renderProjects();
  view("home");
  const collection = globalThis.WorkspaceProjects?.selected();
  if (collection) location.hash = new URLSearchParams({collection, view:"new"}).toString();
  $("first-request").value = "";
  globalThis.WorkspaceComposer?.update("first-request");
  $("first-request").focus();
};
$("quick-start").onsubmit = (e) => {
  e.preventDefault();
  const button =
    e.submitter || $("quick-start").querySelector("button[type=submit]");
  action(button, async () => {
    const draft = $("first-request").value;
    const message = draft.trim();
    const request = state.projectRequest;
    if (!message) return;
    const agent = await saveConversationAgent("home");
    if (request !== state.projectRequest) return;
    const p = await api("projects", {
      name: message.split("\n")[0].slice(0, 80),
      agent,
      collection: globalThis.WorkspaceProjects?.selected(),
      knowledge_sources: globalThis.WorkspaceKnowledge?.selection(),
    });
    await reloadProjects();
    if (request !== state.projectRequest) return;
    mode("interactive");
    if (!(await openProject(p.id))) return;
    globalThis.WorkspaceKnowledge?.transferHome(p.id);
    $("chat-input").value = message;
    if ($("first-request").value === draft) $("first-request").value = "";
    globalThis.WorkspaceComposer?.update("first-request");
    globalThis.WorkspaceComposer?.update("chat-input");
    await send();
  });
};
for (const b of document.querySelectorAll("[data-example]"))
  b.onclick = () => {
    $("first-request").value = b.dataset.example;
    globalThis.WorkspaceComposer?.update("first-request");
    $("first-request").focus();
  };
$("chat-form").onsubmit = (e) => {
  e.preventDefault();
  action($("send-message"), send);
};
for (const [input, form] of [
  ["chat-input", "chat-form"],
  ["first-request", "quick-start"],
]) {
  $(input).onkeydown = (e) => {
    if (
      e.key === "Enter" &&
      !e.shiftKey &&
      !e.isComposing &&
      e.keyCode !== 229
    ) {
      e.preventDefault();
      const submit = $(form).querySelector("button[type=submit]");
      if (!state.readonly && !submit.disabled) $(form).requestSubmit(submit);
    }
  };
}
$("stop-agent").onclick = () =>
  action($("stop-agent"), async () => {
    toast((await api("stop", { project: state.project.id })).message);
  });
$("interactive-mode").onclick = () => mode("interactive");
$("autonomous-mode").onclick = () => mode("autonomous");
$("open-brief").onclick = () => mode("autonomous");
async function prepareStudy(approach) {
  await saveConversationAgent();
  await api("prepare", { project: state.project.id, approach });
  state.project = await api(
    `project?id=${encodeURIComponent(state.project.id)}`,
  );
  mode("interactive");
  renderProject();
  toast(
    approach === "interview"
      ? "Your agent will ask focused questions in the conversation."
      : "Your agent is drafting the study from this conversation.",
  );
}
$("new-study").onclick = () =>
  action($("new-study"), async () => {
    await api("new-study", { project: state.project.id });
    state.project = await api(
      `project?id=${encodeURIComponent(state.project.id)}`,
    );
    state.briefDirty = false;
    state.launchKey = null;
    renderProject(true);
    $("study-preparation").scrollIntoView({
      behavior: "smooth",
      block: "center",
    });
  });
$("grill-me").onclick = () =>
  action($("grill-me"), () => prepareStudy("interview"));
$("draft-study").onclick = () =>
  action($("draft-study"), () => prepareStudy("draft"));
$("continuation-chat").onclick = () =>
  action($("continuation-chat"), () => prepareStudy("continuation"));
$("revise-study").onclick = () => {
  mode("interactive");
  $("chat-input").value = "I'd like to refine the proposed study: ";
  $("chat-input").focus();
};
$("brief-form").oninput = () => {
  state.briefDirty = true;
  state.launchKey = null;
};
$("save-brief").onclick = () =>
  action($("save-brief"), async () => {
    await saveBrief();
    toast("Study brief saved");
  });
async function launchStudy() {
  const id = state.project.id;
  const request = state.projectRequest;
  const route = location.hash;
  const stillHere = () => state.project?.id === id && state.projectRequest === request && location.hash === route;
  await saveConversationAgent();
  if (!stillHere()) return;
  if (state.briefDirty || !state.project.brief) await saveBrief();
  if (!stillHere()) return;
  state.launchKey ||= crypto.randomUUID();
  const launched = await api("launch", {
    project: id,
    request_key: state.launchKey,
    capability_directory: $("study-tools").value,
    execution_backend: $("execution-backend").value,
    director_enabled: $("research-director").checked,
    allow_solver_development: $("solver-development").checked,
    judge_model: $("review-model").value.trim(),
    judge_backend: $("review-backend").value || null,
    judge_reasoning_effort: $("review-effort").value || null,
  });
  const project = await api(`project?id=${encodeURIComponent(id)}`);
  if (!stillHere()) return;
  state.project = project;
  state.routeStudy = launched.campaign || project.studies.at(-1)?.campaign || null;
  mode("autonomous");
  renderProject();
  await renderStudies();
  toast(
    hosted && !state.hosting?.account ? "Research started. Keep a tab open, or sign in to retain the investigation." : "Autonomous research started. You can close this page and return later.",
  );
}
$("brief-form").onsubmit = (e) => {
  e.preventDefault();
  action($("launch-study"), launchStudy);
};
$("start-prepared-study").onclick = () =>
  action($("start-prepared-study"), launchStudy);
$("file-input").onchange = async () => {
  for (const file of $("file-input").files) {
    try {
      if (file.size > 64 * 1024 ** 2)
        throw Error(
          `${file.name} exceeds 64 MB. Copy it to the project folder directly.`,
        );
      const data = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result.split(",")[1]);
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });
      await api("upload", { project: state.project.id, name: file.name, data });
      toast(`Saved ${file.name}`);
    } catch (error) {
      toast(error.message, true);
    }
  }
  $("file-input").value = "";
  state.project = await api(
    `project?id=${encodeURIComponent(state.project.id)}`,
  );
  renderProject();
};
$("custom-tool-form").onsubmit = (e) => {
  e.preventDefault();
  action(e.submitter, async () => {
    await api("register-tool", {
      name: $("tool-name").value,
      path: $("tool-path").value,
    });
    toast("Research tool registered");
    $("custom-tool-dialog").close();
    await refreshTools();
  });
};
const monitor = window.WorkspaceMonitor.create({
  api,
  project: () => state.project,
  link: projectLink,
  notify: toast,
  readonly: () => state.readonly,
});
window.addEventListener("hashchange", () =>
  followRoute().catch((e) => toast(e.message, true)),
);
setInterval(() => {
  for (const element of document.querySelectorAll("[data-idle-since]")) {
    const seconds = Math.max(
      0,
      Math.floor(Date.now() / 1000 - Number(element.dataset.idleSince)),
    );
    element.textContent =
      seconds < 60
        ? `${seconds}s ago`
        : `${Math.floor(seconds / 60)}m ${seconds % 60}s ago`;
  }
  for (const element of document.querySelectorAll("[data-elapsed]")) {
    const seconds = Math.max(
      0,
      Math.floor(Date.now() / 1000 - Number(element.dataset.elapsed)),
    );
    element.textContent =
      seconds < 60
        ? `${seconds}s`
        : `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  }
}, 1000);
const narrow = matchMedia("(max-width: 1000px)");
function sizeInspector() {
  const split = $("research-layout");
  split.setAttribute("orientation", narrow.matches ? "vertical" : "horizontal");
  split.disabled = narrow.matches;
  split.setAttribute("position", narrow.matches ? "40" : "32");
  requestAnimationFrame(() => window.WorkspacePanels?.resize());
}
narrow.addEventListener("change", sizeInspector);
sizeInspector();
let polling = false,
  ticks = 0, organizationTicks = 0;
setInterval(async () => {
  if (polling || !state.token) return;
  polling = true;
  try {
    if (!hosted && ++organizationTicks % 5 === 0) await reloadProjects();
    if (state.view === "project" && state.project) {
      const id = state.project.id;
      const project = await api(`project?id=${encodeURIComponent(id)}`);
      if (state.project?.id === id) {
        state.project = project;
        renderProject();
        globalThis.WorkspaceProjects?.render();
        globalThis.WorkspaceKnowledge?.renderComposer();
        if (state.mode === "autonomous") await renderStudies();
      }
    }
    // Running setups are followed from every page; the full catalogue scan is slower.
    if (!hosted && state.toolWatch.size) await pollToolProgress();
    if (state.view === "tools" && ++ticks % (state.toolWatch.size ? 8 : 3) === 0) await refreshTools();
    if (state.view === "machines") await refreshMachines();
    if (state.view === "benchmarks") await refreshBenchmarks();
    if (state.view === "knowledge") await globalThis.WorkspaceKnowledge?.refresh();
  } catch (error) {
    toast(
      `Connection interrupted: ${error.message}. Your work stays on disk.`,
      true,
    );
  } finally {
    polling = false;
  }
}, 2000);
boot().then(async () => {
  if(!hosted)await refreshMachines();
  // Resume following setups that were running before this page was opened.
  if(!hosted && state.view !== "tools")refreshTools().catch(() => {});
  const query = new URLSearchParams(location.search);
  const campaign = query.get("continue-study") || query.get("steer-study");
  if (campaign) {
    const kind = query.has("continue-study") ? "continue" : "steer";
    const url = new URL(location.href); url.searchParams.delete("continue-study"); url.searchParams.delete("steer-study");
    history.replaceState(null, "", url);
    await openResearchAction(campaign, kind);
  }
}).catch((error) => toast(error.message, true));

$("cancel-delete").onclick = () => $("delete-dialog").close();
$("delete-form").onsubmit = async (event) => {
  event.preventDefault();
  const id = $("delete-form").dataset.project;
  const button = $("confirm-delete");
  button.disabled = true;
  try {
    const result = await api("delete-project", { project: id, confirm: id });
    if (state.project?.id === id) {
      state.project = null;
      state.messageRevision = "";
      $("sidebar-simulations").hidden = true;
      view("home");
    }
    $("delete-dialog").close();
    await reloadProjects();
    toast(result.message || "Conversation and saved folders deleted");
  } catch (error) {
    $("delete-error").textContent = error.message;
    $("delete-error").hidden = false;
  } finally {
    button.disabled = state.readonly;
  }
};
function updateThemeToggle() {
  const dark = document.documentElement.dataset.theme === "dark";
  $("theme-toggle").textContent = dark ? "☀ Light mode" : "☾ Dark mode";
  $("theme-toggle").setAttribute(
    "aria-label",
    dark ? "Switch to light mode" : "Switch to dark mode",
  );
}
$("theme-toggle").onclick = () => {
  WorkspaceTheme.set(
    document.documentElement.dataset.theme === "dark" ? "light" : "dark",
  );
  updateThemeToggle();
};
window.addEventListener("workspace-theme", updateThemeToggle);
updateThemeToggle();

// Shared entry point from a study card or a directly opened CLI study monitor.
async function openResearchAction(campaign, kind) {
  if (state.readonly) throw Error("This workspace is read-only");
  if (state.researchAction) return;
  const continuing = kind === "continue";
  const route = location.hash;
  const projectRequest = state.projectRequest;
  // Capture the source before awaiting a preview. Never use a later conversation.
  const project = state.project?.studies.some((study) => study.campaign === campaign)
    || state.project?.continuation_draft?.campaign === campaign ? state.project.id : null;
  const active = { route, dialog: null };
  state.researchAction = active;
  let preview;
  try {
    preview = continuing ? await api(`continuation-preview?id=${encodeURIComponent(campaign)}`) : null;
  } catch (error) {
    if (state.researchAction === active) state.researchAction = null;
    throw error;
  }
  if (state.researchAction !== active || location.hash !== route || state.projectRequest !== projectRequest) {
    if (state.researchAction === active) state.researchAction = null;
    return;
  }
  const dialog = el("dialog", undefined, "research-action-dialog");
  active.dialog = dialog;
  dialog.setAttribute("aria-label", continuing ? "Continue investigation" : "Send guidance");
  const form = el("form");
  form.append(el("h2", continuing ? "Continue investigation" : "Send guidance"));
  form.append(el("p", continuing
    ? "Prepare a linked phase with a new budget. The previous study stays unchanged. Selected files are snapshotted at launch; earlier results keep their original status. Review the brief and model before starting."
    : "Guidance reaches the agent at its next checkpoint. It does not change the deadline or existing experiment contracts. Use Continue investigation for a new question or requirements.", "field-help"));
  const label = el("label", continuing ? "What should the next phase investigate?" : "Guidance for the agent");
  const message = el("textarea");
  message.required = !continuing; message.maxLength = 8000; message.rows = 6;
  label.append(message); form.append(label);
  if (continuing) form.append(el("p", "Optional when preparing with an agent: discuss the next direction in chat, then review the agent’s brief before launch.", "field-help"));
  const hours = el("input"); hours.type = "number"; hours.min = "0.01"; hours.max = "168"; hours.step = "0.01"; hours.value = "1";
  const selection = [];
  if (continuing) {
    const budget = el("label", "New wall-time budget (hours)"); budget.append(hours); form.append(budget);
    const files = el("details"); files.append(el("summary", `Working files to inherit (${preview.files.length} available)`));
    const list = el("div", undefined, "inherit-file-list");
    preview.files.forEach((file, i) => {
      const row = el("label"); const check = el("input"); check.type = "checkbox"; check.checked = i < 64;
      selection.push([check, file.path]); row.append(check, document.createTextNode(`${file.path} · ${bytes(file.bytes)}`)); list.append(row);
    });
    files.append(list); form.append(files);
  }
  const error = el("p", "", "form-error"); error.setAttribute("role", "alert"); form.append(error);
  const controls = el("div", undefined, "study-controls");
  const cancel = el("button", "Cancel", "secondary"); cancel.type = "button"; cancel.onclick = () => dialog.close();
  const submit = el("button", continuing ? "Prepare directly" : "Send guidance"); submit.type = "submit"; submit.value = "direct";
  const withAgent = continuing ? el("button", "Prepare with agent", "secondary") : null;
  if (withAgent) { withAgent.type = "submit"; withAgent.value = "agent"; }
  controls.append(cancel, submit); if (withAgent) controls.append(withAgent); form.append(controls); dialog.append(form); document.body.append(dialog);
  const key = crypto.randomUUID();
  let submitting = false;
  form.onsubmit = async (event) => {
    event.preventDefault();
    if (submitting || !dialog.open) return;
    submitting = true;
    cancel.disabled = true;
    submit.disabled = true; if (withAgent) withAgent.disabled = true;
    const approach = event.submitter?.value || "direct";
    try {
      if (continuing) {
        const result = await api("prepare-continuation", {campaign, project,
          approach, guidance: message.value, hours: Number(hours.value), files: selection.filter(([c]) => c.checked).map(([,p]) => p)});
        const stillHere = dialog.open && location.hash === route && state.projectRequest === projectRequest;
        dialog.close();
        await reloadProjects();
        if (!stillHere || location.hash !== route || state.projectRequest !== projectRequest) return;
        if (!(await openProject(result.project))) return;
        state.routeStudy = window.StudyNavigation.selected(state.project, campaign);
        mode(result.view || "autonomous");
        toast(result.preparation_error || result.message, !!result.preparation_error);
      } else {
        await api("steer-study", {campaign, message: message.value, request_key: key});
        dialog.close(); toast("Guidance queued for the next agent checkpoint."); state.studyRevision = ""; await renderStudies();
      }
    } catch (e) {
      error.textContent = e.message;
      submitting = false;
      cancel.disabled = false;
      submit.disabled = false; if (withAgent) withAgent.disabled = false;
    }
  };
  dialog.addEventListener("cancel", (event) => { if (submitting) event.preventDefault(); });
  dialog.addEventListener("close", () => {
    if (state.researchAction === active) state.researchAction = null;
    dialog.remove();
  });
  dialog.showModal(); message.focus();
}
