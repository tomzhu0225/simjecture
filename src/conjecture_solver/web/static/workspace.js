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
  busy: false,
  readonly: false,
  briefDirty: false,
  messageRevision: "",
  studyRevision: "",
  sourceTool: null,
  launchKey: null,
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
  window.SimjectureMarkdown.render(node, String(text || ""));
}
function view(name) {
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
  location.hash =
    name === "project"
      ? `project=${encodeURIComponent(state.project.id)}`
      : name;
  if (name === "tools") refreshTools().catch((e) => toast(e.message, true));
}
function renderSettings() {
  const s = state.settings;
  $("backend").replaceChildren(
    new Option("Built-in agent · compatible API", "builtin"),
  );
  for (const cli of s.clis || [])
    if (cli.path)
      $("backend").add(
        new Option(`${cli.id} · detected on this machine`, cli.id),
      );
  $("backend").value = s.backend || "builtin";
  $("model").value = s.model || "";
  $("judge-model").value = s.judge_model || "";
  $("base-url").value = s.base_url || "";
  $("api-key").value = "";
  $("api-key").placeholder = s.has_key
    ? "Saved · leave blank to keep this key"
    : "API key (optional for a local server)";
  $("api-fields").hidden = $("backend").value !== "builtin";
  $("connection-button").textContent = s.tested
    ? `${s.backend === "builtin" ? s.model : s.backend} ↗`
    : "Connect a model ↗";
  $("connection-indicator").textContent = s.tested
    ? "Agent connected"
    : "No agent connected";
  $("connection-indicator").classList.toggle("connected", !!s.tested);
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
  $("connection-result").textContent = s.test_message || "";
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
    $("project-list").append(button);
  }
}
async function reloadProjects() {
  const boot = await api("bootstrap");
  state.projects = boot.projects;
  renderProjects();
}
async function openProject(id) {
  state.project = await api(`project?id=${encodeURIComponent(id)}`);
  state.briefDirty = false;
  state.messageRevision = "";
  state.studyRevision = "";
  state.launchKey = null;
  renderProject(true);
  view("project");
  renderProjects();
  if (state.mode === "autonomous") await renderStudies();
}
function mode(name) {
  state.mode = name;
  $("interactive-panel").hidden = name !== "interactive";
  $("autonomous-panel").hidden = name !== "autonomous";
  $("interactive-mode").classList.toggle("selected", name === "interactive");
  $("autonomous-mode").classList.toggle("selected", name === "autonomous");
  if (name === "autonomous") {
    refreshTools()
      .then(() => renderStudies())
      .catch((e) => toast(e.message, true));
  }
}
function renderProject(force = false) {
  const p = state.project;
  if (!p) return;
  $("project-title").textContent = p.name;
  $("agent-label").textContent =
    state.settings.backend === "builtin"
      ? state.settings.model || "No model"
      : state.settings.backend || "No agent";
  $("conversation-status").textContent = p.running
    ? "Agent working · files and activity are saved as it goes"
    : "Work through the next step together";
  $("send-message").disabled = p.running || state.readonly;
  $("stop-agent").hidden = !p.running;
  $("launch-study").disabled = p.running || state.readonly;
  const revision = JSON.stringify(p.messages);
  if (revision !== state.messageRevision) {
    const nearEnd =
      $("messages").scrollHeight -
        $("messages").scrollTop -
        $("messages").clientHeight <
      120;
    $("messages").replaceChildren();
    if (!p.messages.length) {
      const welcome = el("div", undefined, "welcome-message");
      welcome.append(
        el("h2", "Let’s work through your question."),
        el(
          "p",
          "Describe your task or attach a file. You can investigate together, then prepare an autonomous study when the question is clear.",
        ),
      );
      $("messages").append(welcome);
    }
    for (const message of p.messages) {
      const article = el("article", undefined, `message ${message.role}`);
      article.append(
        el(
          "span",
          message.role === "user" ? "You" : "Simjecture",
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
      if (message.running)
        article.append(
          el(
            "p",
            "Working… You can leave this page and return later.",
            "thinking",
          ),
        );
      else if (message.status === "interrupted")
        article.append(
          el(
            "p",
            "This turn was interrupted. Your files are saved; send a message to continue.",
            "thinking",
          ),
        );
      else if (message.status === "error") article.classList.add("error-text");
      $("messages").append(article);
    }
    if (nearEnd || force) $("messages").scrollTop = $("messages").scrollHeight;
    state.messageRevision = revision;
  }
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
  if (!state.briefDirty || force) {
    const b = p.brief || {};
    $("brief-question").value = b.question || "";
    $("brief-criteria").value = b.success_criteria || "";
    $("brief-constraints").value = b.constraints || "";
    $("brief-hours").value = b.hours || 1;
    $("brief-policy").value = b.completion_policy || "answer";
  }
}
async function send() {
  const message = $("chat-input").value.trim();
  if (!message) return;
  if (!state.settings.tested) {
    toast(
      "Connect and test your agent first. Your draft stays in this project.",
    );
    view("settings");
    return;
  }
  await api("message", { project: state.project.id, message });
  $("chat-input").value = "";
  state.project = await api(
    `project?id=${encodeURIComponent(state.project.id)}`,
  );
  renderProject();
  await reloadProjects();
}
async function refreshTools() {
  state.tools = await api("tools");
  const previous = $("study-tools").value;
  $("study-tools").replaceChildren(
    new Option("Ordinary Python · no external solver", ""),
  );
  const paths = new Set();
  for (const tool of state.tools)
    if (tool.path && !paths.has(tool.path)) {
      paths.add(tool.path);
      $("study-tools").add(new Option(tool.name, tool.path));
    }
  $("study-tools").value = previous;
  if (state.view !== "tools") return;
  $("tool-grid").replaceChildren();
  for (const tool of state.tools) {
    const card = el("article", undefined, "tool-card");
    card.append(
      el(
        "span",
        {
          available: "AVAILABLE",
          installed: "DETECTED · CHECK READINESS",
          tested: "INSTALLATION TESTED",
          working: "WORKING…",
          registered: "REGISTERED LOCALLY",
        }[tool.state],
        "badge",
      ),
      el("h3", tool.name),
      el("p", tool.description),
    );
    const actions = el("div", undefined, "tool-actions");
    if (tool.action !== "custom") {
      const install = el(
        "button",
        tool.action === "source"
          ? "Connect source"
          : tool.state === "tested"
            ? "Check again"
            : "Install",
        "secondary",
      );
      install.disabled = tool.state === "working" || state.readonly;
      install.onclick = () =>
        action(install, async () => {
          if (tool.action === "source") {
            state.sourceTool = tool.id;
            $("source-title").textContent = `Set up ${tool.name}`;
            $("source-dialog").showModal();
          } else {
            await api("install", {
              name: tool.id,
              action: tool.state === "tested" ? "check" : "install",
            });
            toast(`${tool.name}: started`);
            await refreshTools();
          }
        });
      actions.append(install);
      if (tool.state !== "tested") {
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
      details.append(
        el("summary", "Installation details"),
        el("pre", tool.log || JSON.stringify(tool.report, null, 2)),
      );
      card.append(details);
    }
    $("tool-grid").append(card);
  }
}
function briefPayload() {
  return {
    project: state.project.id,
    question: $("brief-question").value,
    success_criteria: $("brief-criteria").value,
    constraints: $("brief-constraints").value,
    hours: Number($("brief-hours").value),
    completion_policy: $("brief-policy").value,
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
  state.projects = data.projects;
  state.readonly = !data.allow_mutations;
  $("readonly").hidden = !state.readonly;
  renderSettings();
  renderProjects();
  if (state.readonly)
    for (const b of document.querySelectorAll(
      "form button, #new-project, #check-machine",
    ))
      b.disabled = true;
  const hash = location.hash.slice(1);
  if (hash.startsWith("project=")) {
    await openProject(decodeURIComponent(hash.slice(8)));
  } else view(["settings", "tools"].includes(hash) ? hash : "home");
}
for (const item of document.querySelectorAll("[data-view]"))
  item.onclick = () => view(item.dataset.view);
$("connection-button").onclick = () => view("settings");
$("backend").onchange = () => {
  $("api-fields").hidden = $("backend").value !== "builtin";
  $("connection-result").textContent = "";
};
$("provider-preset").onchange = () => {
  const preset = {
    deepseek: ["https://api.deepseek.com/v1", "deepseek-chat"],
    openrouter: ["https://openrouter.ai/api/v1", ""],
    local: ["http://localhost:11434/v1", ""],
  }[$("provider-preset").value];
  if (preset) {
    $("base-url").value = preset[0];
    $("model").value = preset[1];
  }
};
$("settings-form").onsubmit = (e) => {
  e.preventDefault();
  action($("save-connection"), async () => {
    $("connection-result").textContent = "Testing model connection…";
    state.settings = await api("settings", {
      backend: $("backend").value,
      base_url: $("base-url").value || "https://api.deepseek.com/v1",
      api_key: $("api-key").value,
      model: $("model").value,
      judge_model: $("judge-model").value,
    });
    $("api-key").value = "";
    try {
      const result = await api("test", {});
      state.settings = result.settings;
      renderSettings();
      toast(result.message);
    } catch (error) {
      renderSettings();
      $("connection-result").textContent = error.message;
      throw error;
    }
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
  $("new-project-dialog").showModal();
  $("project-name").focus();
};
$("cancel-new-project").onclick = () => $("new-project-dialog").close();
$("new-project-form").onsubmit = (e) => {
  e.preventDefault();
  action(e.submitter, async () => {
    const p = await api("projects", { name: $("project-name").value });
    $("new-project-dialog").close();
    $("project-name").value = "";
    await reloadProjects();
    mode("interactive");
    await openProject(p.id);
  });
};
$("quick-start").onsubmit = (e) => {
  e.preventDefault();
  action(e.submitter, async () => {
    const message = $("first-request").value.trim();
    const p = await api("projects", { name: message.slice(0, 80) });
    await reloadProjects();
    mode("interactive");
    await openProject(p.id);
    $("chat-input").value = message;
    $("first-request").value = "";
    if (state.settings.tested) await send();
    else
      toast(
        "Project created. Connect your agent, then send your first message.",
      );
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
$("chat-input").onkeydown = (e) => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
    e.preventDefault();
    $("chat-form").requestSubmit();
  }
};
$("stop-agent").onclick = () =>
  action($("stop-agent"), async () => {
    toast((await api("stop", { project: state.project.id })).message);
  });
$("interactive-mode").onclick = () => mode("interactive");
$("autonomous-mode").onclick = () => mode("autonomous");
$("open-brief").onclick = () => mode("autonomous");
$("brief-form").oninput = () => {
  state.briefDirty = true;
  state.launchKey = null;
};
$("save-brief").onclick = () =>
  action($("save-brief"), async () => {
    await saveBrief();
    toast("Study brief saved");
  });
$("brief-form").onsubmit = (e) => {
  e.preventDefault();
  action($("launch-study"), async () => {
    if (!state.settings.tested) {
      view("settings");
      throw Error(
        "Connect and test a model before starting research. Your brief is still here.",
      );
    }
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
  });
};
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
$("cancel-source").onclick = () => $("source-dialog").close();
$("source-form").onsubmit = (e) => {
  e.preventDefault();
  action(e.submitter, async () => {
    await api("install", {
      name: state.sourceTool,
      action: "install",
      source: $("source-path").value,
    });
    $("source-dialog").close();
    toast("Tool setup started");
    await refreshTools();
  });
};
let polling = false,
  ticks = 0;
setInterval(async () => {
  if (polling || !state.token) return;
  polling = true;
  try {
    if (state.view === "project" && state.project) {
      const id = state.project.id;
      const project = await api(`project?id=${encodeURIComponent(id)}`);
      if (state.project.id === id) {
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
