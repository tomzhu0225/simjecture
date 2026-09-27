"use strict";
const $ = (id) => document.getElementById(id);
const state = {
  token: "",
  settings: {},
  projects: [],
  project: null,
  view: "home",
  mode: "interactive",
  tools: [],
  toolsRevision: "",
  busy: false,
  readonly: false,
  briefDirty: false,
  messageRevision: "",
  studyRevision: "",
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
  const response = await fetch(
    path.startsWith("/api/") ? path : `/api/workspace/${path}`,
    payload === undefined
      ? {}
      : {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Simjecture-Token": state.token,
          },
          body: JSON.stringify(payload),
        },
  );
  const data = await response.json();
  if (!response.ok)
    throw Error(
      data.error || data.message || `Request failed (${response.status})`,
    );
  return data;
}
async function action(button, fn) {
  if (button.disabled) return;
  button.disabled = true;
  try {
    await fn();
  } catch (error) {
    toast(error.message, true);
  } finally {
    button.disabled = state.readonly;
  }
}
function md(node, text) {
  window.WorkspaceRich.render(node, String(text || ""), state.project);
}
function view(name) {
  const changed = state.view !== name;
  state.view = name;
  for (const section of document.querySelectorAll(".view"))
    section.hidden = section.id !== `view-${name}`;
  for (const item of document.querySelectorAll("[data-view]"))
    item.classList.toggle("active", item.dataset.view === name);
  $("breadcrumb").replaceChildren(
    el("span", "Workspace"),
    document.createTextNode(" / "),
    document.createTextNode(
      name === "project"
        ? state.project?.name || "Project"
        : {
            home: "Overview",
            tools: "Research tools",
            settings: "Connections",
          }[name],
    ),
  );
  if (!state.routing)
    location.hash =
      name === "project"
        ? projectHash(state.project.id, { view: state.mode })
        : name;
  if (name === "tools") refreshTools().catch((e) => toast(e.message, true));
  if (name === "home" && state.token && changed)
    renderAgent(undefined, "home").catch((e) => toast(e.message, true));
}
function projectHash(id, options = {}) {
  return new URLSearchParams({ project: id, ...options }).toString();
}
function projectLink(id, options = {}) {
  return `#${projectHash(id, options)}`;
}
async function followRoute({ reveal = true } = {}) {
  if (state.routing) return;
  const initial = location.hash;
  state.routing = true;
  try {
    const params = new URLSearchParams(location.hash.slice(1)),
      id = params.get("project");
    if (id) {
      if (state.project?.id !== id) await openProject(id);
      else view("project");
      mode(params.get("view") === "autonomous" ? "autonomous" : "interactive");
      state.routeStudy = params.get("study");
      if (state.mode === "autonomous") {
        await renderStudies();
        if (state.routeStudy)
          document
            .getElementById(`study-${state.routeStudy}`)
            ?.scrollIntoView({ behavior: "smooth", block: "start" });
      }
      if (params.get("simulation") || params.get("command"))
        await monitor.open(params.get("simulation") || params.get("command"), {
          reveal,
        });
    } else
      view(
        ["settings", "tools"].includes(location.hash.slice(1))
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
  $("connection-button").textContent = "API connections ↗";
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
  $("home-agent-host").replaceChildren(copy);
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
  controls.backend.disabled = state.readonly;
  controls.custom.disabled = state.readonly;
  controls.refresh.disabled = state.readonly;
  const choices = state.readonly
    ? {
        models: p.agent?.model
          ? [{ id: p.agent.model, name: p.agent.model }]
          : [],
        default: p.agent?.model || "",
        note: "Recorded conversation agent · read-only session",
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
    new Option("Other model…", "__custom__"),
  );
  const known = choices.models.some((m) => m.id === model);
  controls.model.value = known ? model : "__custom__";
  controls.customBox.hidden = known;
  controls.custom.value = known ? "" : model;
  controls.effort.value = current?.reasoning_effort || "";
  controls.effort.disabled = selected === "agy" || state.readonly;
  if (selected === "agy") controls.effort.value = "";
  controls.model.disabled = state.readonly;
  controls.note.textContent = choices.note;
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
}
async function reloadProjects() {
  const boot = await api("bootstrap");
  state.projects = boot.projects;
  renderProjects();
}
async function openProject(id) {
  $("agent-switch-warning").hidden = true;
  state.project = await api(`project?id=${encodeURIComponent(id)}`);
  state.briefDirty = false;
  state.messageRevision = "";
  state.studyRevision = "";
  state.launchKey = null;
  renderProject(true);
  view("project");
  renderProjects();
  await renderAgent();
  if (state.mode === "autonomous") await renderStudies();
}
function mode(name) {
  state.mode = name;
  $("interactive-panel").hidden = name !== "interactive";
  $("autonomous-panel").hidden = name !== "autonomous";
  $("interactive-mode").classList.toggle("selected", name === "interactive");
  $("autonomous-mode").classList.toggle("selected", name === "autonomous");
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
  renderAgentSwitchWarning();
  $("project-title").textContent = p.name;
  $("agent-label").textContent = p.agent
    ? `${p.agent.backend} / ${p.agent.model || "choose model"}`
    : "Choose an agent";
  $("conversation-status").textContent = p.running
    ? "Agent working · files and activity are saved as it goes"
    : "Work through the next step together";
  $("send-message").disabled = p.running || state.readonly;
  $("stop-agent").hidden = !p.running;
  $("launch-study").disabled = p.running || state.readonly;
  for (const id of ["grill-me", "draft-study", "start-prepared-study"])
    $(id).disabled = p.running || state.readonly;
  $("preparation-status").textContent = p.running
    ? "Your agent is working. Its questions and proposed brief appear in the conversation."
    : "The agent will ask about missing facts and fill in the details for you.";
  $("prepared-brief").hidden = !p.brief;
  $("brief-editor").hidden = !p.brief;
  if (p.brief) {
    const b = p.brief;
    $("prepared-question").textContent = b.question;
    $("prepared-details").replaceChildren();
    for (const [label, value] of [
      ["Evidence", b.success_criteria],
      ["Constraints", b.constraints || "No additional constraints specified."],
      ["Time budget", `${b.hours} hours`],
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
    (p.simulations || []).map((j) => [j.id, j.status]),
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
      article.dataset.messageKey = key;
      article.dataset.messageSignature = signature;
      article.append(
        el(
          "span",
          message.role === "user"
            ? "You"
            : message.agent
              ? `Simjecture · ${message.agent.backend} / ${message.agent.model}`
              : "Simjecture",
          "message-role",
        ),
      );
      const content = el("div", undefined, "message-content");
      md(content, message.content);
      article.append(content);
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
      if (message.progress)
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
    link.href = `/api/workspace/file?id=${encodeURIComponent(p.id)}&path=${encodeURIComponent(file.name)}`;
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
    $("brief-hours").value = b.hours || 1;
    $("brief-policy").value = b.completion_policy || "answer";
    if (
      b.capability_directory &&
      [...$("study-tools").options].some(
        (o) => o.value === b.capability_directory,
      )
    )
      $("study-tools").value = b.capability_directory;
  }
}
async function send() {
  const message = $("chat-input").value.trim();
  if (!message) return;
  await saveConversationAgent();
  await api("message", { project: state.project.id, message });
  $("chat-input").value = "";
  state.project = await api(
    `project?id=${encodeURIComponent(state.project.id)}`,
  );
  renderProject();
  await reloadProjects();
}
async function assistInstallation(tool) {
  const flash = tool.id === "flash";
  const guidance = flash
    ? "Read the flash-mhd skill and references/local-deployment.md and references/private-install.md with read_skill. Ask which FLASH application, physics and dimensions I need, and where my supplied source folder or archive is. Do not assume a generic FLASH executable or an island-coalescence build suits every application."
    : "Read the warpx skill and references/local-cuda-deployment.md with read_skill. Check the GPU, driver, CUDA compatibility and build resources. Ask which dimensions I need: the bundled CUDA recipe targets 2D. Use the documented pinned source/bootstrap when appropriate; do not require me to supply a checkout if the documented source can be downloaded.";
  const prompt = `Help me install ${tool.name} on this execution machine. ${guidance}

Guide me through the missing decisions in plain language. Inspect prerequisites, prepare a compatible toolchain and build configuration, compile, run a small readiness test, and register the actual working application so it appears in Research tools. Do not ask me to write build environment variables myself. Keep source, build records and logs in persistent named folders, and show progress during long builds. Respect this machine's selected execution mode and explain blockers. Installation/readiness is not scientific qualification.`;
  const project = await api("projects", { name: `Install ${tool.name}` });
  await reloadProjects();
  mode("interactive");
  await openProject(project.id);
  $("chat-input").value = prompt;
  $("chat-input").dispatchEvent(new Event("input"));
  $("chat-input").focus();
  toast(
    "Installation conversation prepared. Choose your agent/model and send the request.",
  );
}

async function refreshTools() {
  state.tools = await api("tools");
  const previous = $("study-tools").value;
  $("study-tools").replaceChildren(
    new Option("Ordinary Python · no external solver", ""),
  );
  const paths = new Set();
  for (const tool of state.tools) {
    const variants = tool.variants?.length ? tool.variants : [tool];
    for (const item of variants)
      if (item.path && !paths.has(item.path)) {
        paths.add(item.path);
        $("study-tools").add(new Option(item.label || item.name, item.path));
      }
  }
  const desired = state.project?.brief?.capability_directory || previous;
  $("study-tools").value = [...$("study-tools").options].some(
    (o) => o.value === desired,
  )
    ? desired
    : "";
  if (state.view !== "tools") return;
  const revision = JSON.stringify(state.tools);
  if (revision === state.toolsRevision) return;
  const scroll = document.scrollingElement.scrollTop;
  const opened = new Set(
    [...$("view-tools").querySelectorAll("details[open][data-key]")].map(
      (d) => d.dataset.key,
    ),
  );
  const logScroll = new Map(
    [...$("view-tools").querySelectorAll("details[data-key] pre")].map((e) => [
      e.parentElement.dataset.key,
      e.scrollTop,
    ]),
  );
  $("installed-tool-grid").replaceChildren();
  $("available-tool-grid").replaceChildren();
  $("installed-count").textContent =
    state.tools.filter((t) => t.installed).length + 1;
  $("available-count").textContent = state.tools.filter(
    (t) => !t.installed,
  ).length;
  const python = el("article", undefined, "tool-card tool-installed");
  python.append(
    el("span", "✓ Installed", "tool-status installed"),
    el("h3", "Python research stack"),
    el("p", "NumPy, SciPy, pandas, and plotting. Included with Simjecture."),
    el("small", "Ready for numerical exploration", "field-help"),
  );
  $("installed-tool-grid").append(python);
  for (const tool of state.tools) {
    const card = el(
      "article",
      undefined,
      `tool-card ${tool.installed ? "tool-installed" : "tool-missing"}`,
    );
    card.dataset.tool = tool.id;
    card.append(
      el(
        "span",
        tool.state === "working"
          ? "◌ Working…"
          : tool.state === "failed"
            ? "Needs attention"
            : tool.installed
              ? "✓ Installed"
              : "Not installed",
        `tool-status ${tool.installed ? "installed" : "not-installed"}`,
      ),
      el("h3", tool.name),
      el("p", tool.description),
    );
    const failure =
      tool.report?.error ||
      (tool.report?.checks || [])
        .filter((check) => check.status === "fail" && check.required !== false)
        .map((check) => [check.detail, check.remedy].filter(Boolean).join(" "))
        .join("\n");
    if (failure && tool.state !== "working") {
      const warning = el("p", failure, "tool-failure");
      warning.setAttribute("role", "status");
      card.append(warning);
    }
    if (tool.installed)
      card.append(
        el(
          "small",
          tool.readiness === "passed"
            ? "Installation check passed"
            : tool.readiness === "failed"
              ? "Installed, but its readiness check needs attention"
              : "Detected on this machine · readiness not yet checked",
          "field-help",
        ),
      );
    if (tool.variants?.length) {
      const details = el("details", undefined, "installed-variants");
      details.dataset.key = `variants-${tool.id}`;
      details.open = opened.has(details.dataset.key);
      details.append(
        el(
          "summary",
          `${tool.variants.length} installed application${tool.variants.length === 1 ? "" : "s"}`,
        ),
      );
      for (const variant of tool.variants) {
        const item = el("div");
        item.append(
          el("strong", variant.label),
          el("p", variant.description),
          el("code", variant.runtime),
        );
        details.append(item);
      }
      card.append(details);
    }
    const actions = el("div", undefined, "tool-actions");
    if (tool.action !== "custom") {
      const install = el(
        "button",
        tool.installed
          ? tool.registered === false
            ? "View installations"
            : "Check readiness"
          : ["agent", "source"].includes(tool.action)
            ? "Install with agent"
            : "Install",
        "secondary",
      );
      install.disabled = tool.state === "working" || state.readonly;
      install.onclick = () =>
        action(install, async () => {
          if (tool.installed && tool.registered === false) {
            const details = card.querySelector(".installed-variants");
            if (details) details.open = true;
          } else if (
            ["agent", "source"].includes(tool.action) &&
            !tool.installed
          ) {
            await assistInstallation(tool);
          } else {
            await api("install", {
              name: tool.id,
              action: tool.installed ? "check" : "install",
            });
            toast(`${tool.name}: started`);
            await refreshTools();
          }
        });
      actions.append(install);
      if (!tool.installed) {
        const check = el("button", "Check installed", "quiet");
        check.disabled = tool.state === "working" || state.readonly;
        check.onclick = () =>
          action(check, async () => {
            await api("install", { name: tool.id, action: "check" });
            await refreshTools();
          });
        actions.append(check);
      }
    } else card.append(el("code", tool.path));
    card.append(actions);
    if (tool.log || Object.keys(tool.report || {}).length) {
      const details = el("details");
      details.dataset.key = `installation-${tool.id}`;
      details.open = opened.has(details.dataset.key);
      details.append(
        el("summary", "Installation details"),
        el("pre", tool.log || JSON.stringify(tool.report, null, 2)),
      );
      card.append(details);
    }
    $(tool.installed ? "installed-tool-grid" : "available-tool-grid").append(
      card,
    );
  }
  for (const pre of $("view-tools").querySelectorAll("details[data-key] pre"))
    pre.scrollTop = logScroll.get(pre.parentElement.dataset.key) || 0;
  document.scrollingElement.scrollTop = scroll;
  state.toolsRevision = revision;
}
function briefPayload() {
  return {
    project: state.project.id,
    question: $("brief-question").value,
    success_criteria: $("brief-criteria").value,
    constraints: $("brief-constraints").value,
    hours: Number($("brief-hours").value),
    completion_policy: $("brief-policy").value,
    capability_directory: $("study-tools").value,
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
    if (error) {
      card.append(el("h3", study.question), el("p", error, "error-text"));
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
    card.append(meta, el("h3", study.question));
    const metrics = el("div", undefined, "metrics");
    for (const [label, value] of [
      [
        "Experiments",
        report.experiments?.length ?? snap.executions?.length ?? 0,
      ],
      ["Independent reviews", report.reviews?.length ?? 0],
      [
        "Time remaining",
        data.live?.remaining === undefined
          ? "—"
          : `${Math.max(0, Math.ceil(data.live.remaining / 60))} min`,
      ],
    ]) {
      const item = el("div", label);
      item.prepend(el("strong", String(value)));
      metrics.append(item);
    }
    card.append(metrics);
    card.append(el("p", data.live?.activity || "", "field-help"));
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
    const monitor = el("a", "Open experiment monitor ↗", "secondary");
    monitor.href = `/monitor?campaign=${study.campaign}`;
    controls.append(monitor);
    card.append(controls);
    const findings = el("div", undefined, "study-findings");
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
  const execution = data.settings.execution;
  $("execution-backend").value = execution?.backend || "bubblewrap";
  function executionWarning() {
    const cooperative = $("execution-backend").value === "proot-cooperative";
    const warning =
      execution?.warning ||
      (cooperative
        ? "Cooperative execution (PRoot) is not a security sandbox: it does not isolate host files or networking. Use only trusted code under a dedicated non-root account."
        : execution && !execution.available
          ? `Isolated experiments are unavailable: ${execution.reason}. Cooperative fallback: ${execution.fallback_unavailable || "not configured"}.`
          : "");
    $("execution-warning").textContent = warning;
    $("execution-warning").hidden = !warning;
  }
  $("execution-backend").addEventListener("change", executionWarning);
  executionWarning();
  state.projects = data.projects;
  state.readonly = !data.allow_mutations;
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
  item.onclick = () => view(item.dataset.view);
$("connection-button").onclick = () => view("settings");
mountHomeAgent();
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
    state.settings = await api("api-settings", {
      base_url: $("base-url").value,
      api_key: $("api-key").value,
    });
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
  renderProjects();
  view("home");
  $("first-request").value = "";
  $("first-request").focus();
};
$("quick-start").onsubmit = (e) => {
  e.preventDefault();
  const button =
    e.submitter || $("quick-start").querySelector("button[type=submit]");
  action(button, async () => {
    const message = $("first-request").value.trim();
    if (!message) return;
    const agent = await saveConversationAgent("home");
    const p = await api("projects", {
      name: message.split("\n")[0].slice(0, 80),
      agent,
    });
    await reloadProjects();
    mode("interactive");
    await openProject(p.id);
    $("chat-input").value = message;
    $("first-request").value = "";
    await send();
  });
};
for (const b of document.querySelectorAll("[data-example]"))
  b.onclick = () => {
    $("first-request").value = b.dataset.example;
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
$("grill-me").onclick = () =>
  action($("grill-me"), () => prepareStudy("interview"));
$("draft-study").onclick = () =>
  action($("draft-study"), () => prepareStudy("draft"));
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
  await saveConversationAgent();
  if (state.briefDirty || !state.project.brief) await saveBrief();
  state.launchKey ||= crypto.randomUUID();
  await api("launch", {
    project: state.project.id,
    request_key: state.launchKey,
    capability_directory: $("study-tools").value,
    execution_backend: $("execution-backend").value,
  });
  state.project = await api(
    `project?id=${encodeURIComponent(state.project.id)}`,
  );
  renderProject();
  await renderStudies();
  toast(
    "Autonomous research started. You can close this page and return later.",
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
      if (file.size > 20 * 1024 ** 2)
        throw Error(
          `${file.name} exceeds 20 MB. Copy it to the project folder directly.`,
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
}
narrow.addEventListener("change", sizeInspector);
sizeInspector();
let polling = false,
  ticks = 0;
setInterval(async () => {
  if (polling || !state.token) return;
  polling = true;
  try {
    if (state.view === "project" && state.project) {
      const id = state.project.id;
      const project = await api(`project?id=${encodeURIComponent(id)}`);
      if (state.project?.id === id) {
        state.project = project;
        renderProject();
        if (state.mode === "autonomous") await renderStudies();
      }
    }
    if (state.view === "tools" && ++ticks % 3 === 0) await refreshTools();
  } catch (error) {
    toast(
      `Connection interrupted: ${error.message}. Your work stays on disk.`,
      true,
    );
  } finally {
    polling = false;
  }
}, 2000);
boot().catch((error) => toast(error.message, true));

$("cancel-delete").onclick = () => $("delete-dialog").close();
$("delete-form").onsubmit = async (event) => {
  event.preventDefault();
  const id = $("delete-form").dataset.project;
  const button = $("confirm-delete");
  button.disabled = true;
  try {
    await api("delete-project", { project: id, confirm: id });
    if (state.project?.id === id) {
      state.project = null;
      state.messageRevision = "";
      $("sidebar-simulations").hidden = true;
      view("home");
    }
    $("delete-dialog").close();
    await reloadProjects();
    toast("Conversation and saved folders deleted");
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
