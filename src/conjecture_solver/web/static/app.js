"use strict";

const SVG_NS = "http://www.w3.org/2000/svg";

const state = {
  campaigns: [],
  selectedCampaign: null,
  selectedClaim: null,
  snapshot: null,
  controlToken: null,
  allowMutations: false,
  activeTab: "activity",
  graphZoom: 1,
  graphSignature: null,
  pollInFlight: false,
  pollCount: 0,
  toastTimer: null,
};

const ui = {};

document.addEventListener("DOMContentLoaded", () => {
  bindElements();
  bindEvents();
  initialize();
});

function bindElements() {
  const ids = [
    "activity-panel",
    "artifacts-panel",
    "campaign-id",
    "campaign-instruction",
    "campaign-select",
    "campaign-status",
    "cancel-button",
    "cancel-dialog",
    "claim-inspector",
    "claim-status",
    "close-dialog",
    "conclusion-panel",
    "current-action",
    "dashboard",
    "empty-new-run",
    "empty-state",
    "graph-placeholder",
    "graph-viewport",
    "hypothesis-graph",
    "launch-button",
    "metric-claims",
    "metric-claims-detail",
    "metric-elapsed",
    "metric-heartbeat",
    "metric-iterations",
    "metric-model",
    "metric-tokens",
    "metric-workspace",
    "new-run-button",
    "new-run-dialog",
    "new-run-error",
    "new-run-form",
    "pause-button",
    "resume-button",
    "root-hypothesis",
    "sync-state",
    "toast",
    "zoom-fit",
    "zoom-in",
    "zoom-out",
  ];
  for (const id of ids) ui[id] = document.getElementById(id);
  ui.tabs = Array.from(document.querySelectorAll("[role='tab'][data-tab]"));
}

function bindEvents() {
  ui["campaign-select"].addEventListener("change", (event) => {
    selectCampaign(event.target.value);
  });
  ui["new-run-button"].addEventListener("click", openNewRunDialog);
  ui["empty-new-run"].addEventListener("click", openNewRunDialog);
  ui["close-dialog"].addEventListener("click", closeNewRunDialog);
  ui["cancel-dialog"].addEventListener("click", closeNewRunDialog);
  ui["new-run-form"].addEventListener("submit", launchCampaign);
  ui["pause-button"].addEventListener("click", () => controlCampaign("pause"));
  ui["resume-button"].addEventListener("click", () => controlCampaign("resume"));
  ui["cancel-button"].addEventListener("click", () => controlCampaign("cancel"));
  ui["zoom-in"].addEventListener("click", () => changeZoom(0.15));
  ui["zoom-out"].addEventListener("click", () => changeZoom(-0.15));
  ui["zoom-fit"].addEventListener("click", fitGraph);
  for (const tab of ui.tabs) {
    tab.addEventListener("click", () => setTab(tab.dataset.tab));
  }
  window.addEventListener("resize", debounce(() => {
    if (state.snapshot) renderGraph(true);
  }, 160));
}

async function initialize() {
  setSync("connecting", "Connecting");
  try {
    const bootstrap = await api("/api/bootstrap");
    state.campaigns = bootstrap.campaigns || [];
    state.controlToken = bootstrap.control_token;
    state.allowMutations = Boolean(bootstrap.allow_mutations);
    state.selectedCampaign = bootstrap.selected_campaign;
    ui["new-run-button"].disabled = !state.allowMutations;
    ui["empty-new-run"].disabled = !state.allowMutations;
    renderCampaignPicker();
    if (state.selectedCampaign) {
      await refreshSnapshot(true);
    } else {
      showEmptyState();
      setSync("online", "Ready");
    }
  } catch (error) {
    showEmptyState();
    setSync("offline", "Disconnected");
    showToast(error.message, true);
  }
  window.setInterval(poll, 1000);
}

async function poll() {
  if (state.pollInFlight || !state.selectedCampaign) return;
  state.pollCount += 1;
  await refreshSnapshot(false);
  if (state.pollCount % 10 === 0) await refreshCampaigns();
}

async function refreshCampaigns() {
  try {
    const payload = await api("/api/campaigns");
    state.campaigns = payload.campaigns || [];
    renderCampaignPicker();
  } catch (_) {
    // The snapshot poll reports connectivity; campaign discovery is secondary.
  }
}

async function refreshSnapshot(forceGraph) {
  if (!state.selectedCampaign) return;
  state.pollInFlight = true;
  try {
    const payload = await api(
      `/api/snapshot?campaign=${encodeURIComponent(state.selectedCampaign)}`,
    );
    state.snapshot = payload;
    renderSnapshot(forceGraph);
    setSync("online", "Live");
  } catch (error) {
    setSync("offline", "Retrying");
    if (forceGraph) showToast(error.message, true);
  } finally {
    state.pollInFlight = false;
  }
}

async function selectCampaign(token) {
  if (!token || token === state.selectedCampaign) return;
  state.selectedCampaign = token;
  state.selectedClaim = null;
  state.snapshot = null;
  state.graphSignature = null;
  state.graphZoom = 1;
  setSync("connecting", "Loading");
  await refreshSnapshot(true);
}

function renderCampaignPicker() {
  const select = ui["campaign-select"];
  const previous = state.selectedCampaign;
  clear(select);
  if (!state.campaigns.length) {
    select.append(option("", "No campaigns found"));
    select.disabled = true;
    return;
  }
  select.disabled = false;
  for (const campaign of state.campaigns) {
    const label = `${campaign.display_name || campaign.campaign_id} · ${campaign.execution_status}`;
    const item = option(campaign.id, label);
    item.title = campaign.hypothesis || campaign.path;
    select.append(item);
  }
  if (previous && state.campaigns.some((item) => item.id === previous)) {
    select.value = previous;
  } else if (!state.selectedCampaign) {
    state.selectedCampaign = state.campaigns[0].id;
    select.value = state.selectedCampaign;
  }
}

function renderSnapshot(forceGraph) {
  const data = state.snapshot;
  const snapshot = data.snapshot;
  ui["empty-state"].hidden = true;
  ui.dashboard.hidden = false;

  const execution = snapshot.execution_status;
  const displayStatus = execution === "terminal" ? snapshot.phase : execution;
  setBadge(ui["campaign-status"], displayStatus, displayStatus);
  ui["campaign-id"].textContent = data.display_name || snapshot.identity.campaign_id || "unnamed campaign";
  ui["root-hypothesis"].textContent = snapshot.identity.hypothesis || "Hypothesis not yet recorded";
  const instruction = snapshot.identity.campaign_instruction;
  ui["campaign-instruction"].hidden = !instruction;
  ui["campaign-instruction"].textContent = instruction ? `Guidance: ${instruction}` : "";

  renderCurrentAction(snapshot);
  renderMetrics(data);
  renderControls(data.controls);

  const nodes = data.hypothesis_graph.nodes || [];
  if (!state.selectedClaim || !data.claim_details[state.selectedClaim]) {
    state.selectedClaim = nodes.find((item) => item.id === "claim_root")?.id || nodes[0]?.id || null;
  }
  const signature = JSON.stringify([nodes, data.hypothesis_graph.edges]);
  if (forceGraph || signature !== state.graphSignature) {
    state.graphSignature = signature;
    renderGraph(false);
  }
  renderInspector();
  renderActivity();
  renderArtifacts();
  renderConclusion();
}

function renderCurrentAction(snapshot) {
  const container = ui["current-action"];
  const symbol = container.querySelector(".action-symbol");
  const label = container.querySelector("small");
  const value = container.querySelector("strong");
  if (snapshot.current_action) {
    symbol.textContent = snapshot.current_action.pending ? "◈" : "◇";
    label.textContent = `Current action · iteration ${snapshot.current_action.iteration}`;
    value.textContent = snapshot.current_action.description;
    value.title = snapshot.current_action.description;
    return;
  }
  if (snapshot.report) {
    symbol.textContent = "◆";
    label.textContent = "Campaign record";
    value.textContent = "All model actions have ended";
  } else if (snapshot.process_live) {
    symbol.textContent = "◇";
    label.textContent = "Current action";
    value.textContent = "Waiting for the next typed model action";
  } else if (snapshot.phase === "paused") {
    symbol.textContent = "Ⅱ";
    label.textContent = "Campaign paused";
    value.textContent = "Resume from the next action boundary";
  } else {
    symbol.textContent = "○";
    label.textContent = "No live process";
    value.textContent = "The durable record remains available";
  }
}

function renderMetrics(data) {
  const snapshot = data.snapshot;
  const scientific = data.hypothesis_graph.nodes || [];
  const counts = countBy(scientific, (item) => item.status);
  ui["metric-claims"].textContent = String(scientific.length);
  ui["metric-claims-detail"].textContent = [
    counts.open ? `${counts.open} open` : null,
    counts.supported ? `${counts.supported} supported` : null,
    counts.falsified ? `${counts.falsified} falsified` : null,
  ].filter(Boolean).join(" · ") || "No registered hypotheses";
  ui["metric-elapsed"].textContent = data.formatted.elapsed;
  ui["metric-iterations"].textContent = `${formatInteger(snapshot.iterations)} model turns`;
  ui["metric-tokens"].textContent = compactNumber(snapshot.token_usage.total_tokens);
  ui["metric-model"].textContent = snapshot.last_model || "No model usage recorded";
  ui["metric-workspace"].textContent = data.formatted.workspace;
  ui["metric-heartbeat"].textContent = data.formatted.heartbeat_age
    ? `Heartbeat ${data.formatted.heartbeat_age}`
    : `${data.artifacts.length} visible artifacts`;
}

function renderControls(controls) {
  const enabled = state.allowMutations;
  ui["pause-button"].disabled = !enabled || !controls.can_pause;
  ui["resume-button"].disabled = !enabled || !controls.can_resume;
  ui["cancel-button"].disabled = !enabled || !controls.can_cancel;
  if (!enabled) {
    for (const button of [ui["pause-button"], ui["resume-button"], ui["cancel-button"]]) {
      button.title = "This web session is read-only";
    }
  }
}

function renderGraph(preserveScroll) {
  const graph = ui["hypothesis-graph"];
  const viewport = ui["graph-viewport"];
  const previousScroll = { left: viewport.scrollLeft, top: viewport.scrollTop };
  clear(graph);
  if (!state.snapshot) return;
  const nodes = state.snapshot.hypothesis_graph.nodes || [];
  const edges = state.snapshot.hypothesis_graph.edges || [];
  ui["graph-placeholder"].hidden = nodes.length > 0;
  graph.hidden = nodes.length === 0;
  if (!nodes.length) return;

  const nodeWidth = 258;
  const nodeHeight = 108;
  const xGap = 102;
  const yGap = 34;
  const marginX = 38;
  const marginY = 34;
  const positions = layoutTree(nodes, nodeWidth, nodeHeight, xGap, yGap, marginX, marginY);
  const maxX = Math.max(...Array.from(positions.values()).map((point) => point.x));
  const maxY = Math.max(...Array.from(positions.values()).map((point) => point.y));
  const width = maxX + nodeWidth + marginX;
  const height = Math.max(viewport.clientHeight || 493, maxY + nodeHeight + marginY);
  graph.setAttribute("viewBox", `0 0 ${width} ${height}`);
  graph.setAttribute("width", String(width * state.graphZoom));
  graph.setAttribute("height", String(height * state.graphZoom));

  const edgeLayer = svg("g", { class: "edge-layer" });
  for (const edge of edges) {
    const source = positions.get(edge.source);
    const target = positions.get(edge.target);
    if (!source || !target) continue;
    const x1 = source.x + nodeWidth;
    const y1 = source.y + nodeHeight / 2;
    const x2 = target.x;
    const y2 = target.y + nodeHeight / 2;
    const bend = Math.max(35, (x2 - x1) * 0.48);
    edgeLayer.append(svg("path", {
      class: "graph-edge",
      d: `M ${x1} ${y1} C ${x1 + bend} ${y1}, ${x2 - bend} ${y2}, ${x2} ${y2}`,
    }));
    const label = svg("text", {
      class: "graph-edge-label",
      x: String((x1 + x2) / 2),
      y: String((y1 + y2) / 2 - 7),
      "text-anchor": "middle",
    });
    label.textContent = edge.relation || "refines";
    edgeLayer.append(label);
  }
  graph.append(edgeLayer);

  const nodeLayer = svg("g", { class: "node-layer" });
  for (const item of nodes) {
    const point = positions.get(item.id);
    if (!point) continue;
    const group = svg("g", {
      class: `graph-node${item.id === state.selectedClaim ? " selected" : ""}`,
      "data-status": item.status,
      role: "button",
      tabindex: "0",
      transform: `translate(${point.x} ${point.y})`,
      "aria-label": `${item.id}, ${item.status}: ${item.statement}`,
    });
    group.append(svg("rect", {
      class: "node-body",
      width: String(nodeWidth),
      height: String(nodeHeight),
      rx: "11",
    }));
    group.append(svg("line", {
      class: "status-line",
      x1: "2",
      x2: "2",
      y1: "13",
      y2: String(nodeHeight - 13),
    }));
    appendSvgText(group, item.id, 15, 20, "node-id");
    appendSvgText(group, item.status, nodeWidth - 14, 20, "node-status", "end");
    const lines = wrapText(item.statement || item.id, 40, 3);
    lines.forEach((line, index) => appendSvgText(group, line, 15, 44 + index * 15, "node-copy"));
    const counts = `${item.evidence_count} evidence · ${item.contract_count} contracts`;
    appendSvgText(group, counts, 15, nodeHeight - 11, "node-counts");
    group.addEventListener("click", () => selectClaim(item.id));
    group.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        selectClaim(item.id);
      }
    });
    nodeLayer.append(group);
  }
  graph.append(nodeLayer);
  if (preserveScroll) {
    viewport.scrollLeft = previousScroll.left;
    viewport.scrollTop = previousScroll.top;
  }
}

function layoutTree(nodes, nodeWidth, nodeHeight, xGap, yGap, marginX, marginY) {
  const byId = new Map(nodes.map((item) => [item.id, item]));
  const children = new Map(nodes.map((item) => [item.id, []]));
  for (const item of nodes) {
    if (item.parent_id && children.has(item.parent_id)) children.get(item.parent_id).push(item.id);
  }
  const roots = nodes.filter((item) => !item.parent_id || !byId.has(item.parent_id));
  const positions = new Map();
  const visited = new Set();
  let nextY = marginY;

  function place(id, depth) {
    if (visited.has(id)) return positions.get(id)?.y ?? nextY;
    visited.add(id);
    const childIds = children.get(id) || [];
    let y;
    if (childIds.length) {
      const childYs = childIds.map((child) => place(child, depth + 1));
      y = childYs.reduce((sum, value) => sum + value, 0) / childYs.length;
    } else {
      y = nextY;
      nextY += nodeHeight + yGap;
    }
    positions.set(id, { x: marginX + depth * (nodeWidth + xGap), y });
    return y;
  }

  for (const root of roots) {
    place(root.id, 0);
    nextY += yGap;
  }
  for (const item of nodes) {
    if (!visited.has(item.id)) place(item.id, item.depth || 0);
  }
  return positions;
}

function selectClaim(claimId) {
  state.selectedClaim = claimId;
  renderGraph(true);
  renderInspector();
}

function renderInspector() {
  const container = ui["claim-inspector"];
  clear(container);
  if (!state.snapshot || !state.selectedClaim) {
    container.append(paragraph("panel-placeholder", "Select a hypothesis to inspect its evidence."));
    setBadge(ui["claim-status"], "", "—");
    return;
  }
  const detail = state.snapshot.claim_details[state.selectedClaim];
  if (!detail) {
    container.append(paragraph("panel-placeholder", "Claim details are not available yet."));
    return;
  }
  setBadge(ui["claim-status"], detail.status, detail.status);
  container.append(paragraph("claim-statement", detail.statement || detail.id));

  const metadata = element("div", "claim-metadata");
  for (const value of [detail.id, detail.kind, detail.relation]) {
    if (value) metadata.append(element("span", "metadata-chip", value));
  }
  if (detail.parent_id) {
    const parent = element("button", "metadata-chip", `parent: ${detail.parent_id}`);
    parent.type = "button";
    parent.addEventListener("click", () => selectClaim(detail.parent_id));
    metadata.append(parent);
  }
  container.append(metadata);

  if (detail.rationale) container.append(inspectorSection("Rationale", detail.rationale));
  if (detail.closed_reason) container.append(inspectorSection("Closure", detail.closed_reason));

  if (detail.evidence_contracts?.length) {
    const section = inspectorSection("Evidence contracts");
    detail.evidence_contracts.forEach((contract, index) => {
      const card = element("div", "contract-card");
      card.append(element("strong", null, `Contract v${contract.version ?? index + 1}`));
      const fields = [
        ["Observable", contract.observable],
        ["Decision rule", contract.decision_rule],
        ["Required observation", contract.required_observation],
        ["Uncertainty", contract.uncertainty_criterion],
        ["Inconclusive when", contract.inconclusive_conditions],
      ];
      for (const [label, copy] of fields) {
        if (!copy) continue;
        const details = element("details");
        details.append(element("summary", null, label));
        details.append(paragraph(null, copy));
        card.append(details);
      }
      section.append(card);
    });
    container.append(section);
  }

  if (detail.evidence?.length) {
    const section = inspectorSection(`Evidence · ${detail.evidence.length}`);
    for (const evidence of detail.evidence) section.append(evidenceCard(evidence));
    container.append(section);
  }

  const validationIds = state.snapshot.validation_claims[state.selectedClaim] || [];
  if (validationIds.length) {
    const section = inspectorSection(`Validation claims · ${validationIds.length}`);
    for (const id of validationIds) {
      const validation = state.snapshot.claim_details[id];
      if (!validation) continue;
      const card = element("button", "validation-card");
      card.type = "button";
      const header = element("header");
      header.append(element("strong", null, validation.kind || "validation"));
      const badge = element("span", "status-badge");
      setBadge(badge, validation.status, validation.status);
      header.append(badge);
      card.append(header, paragraph(null, validation.statement || id));
      card.addEventListener("click", () => selectClaim(id));
      section.append(card);
    }
    container.append(section);
  }
}

function evidenceCard(evidence) {
  const card = element("article", "evidence-card");
  const header = element("header");
  const path = evidence.artifact_path || evidence.path;
  if (evidence.artifact_path) {
    const link = element("a", null, evidence.path || evidence.artifact_path);
    link.href = artifactUrl(evidence.artifact_path);
    link.target = "_blank";
    link.rel = "noopener";
    header.append(link);
  } else {
    header.append(element("strong", null, path || "Evidence record"));
  }
  const sufficient = evidence.observation_sufficient;
  if (typeof sufficient === "boolean") {
    const badge = element("span", "status-badge");
    setBadge(badge, sufficient ? "supported" : "unresolved", sufficient ? "sufficient" : "limited");
    header.append(badge);
  }
  card.append(header);
  if (evidence.note) card.append(paragraph(null, evidence.note));
  if (evidence.observation_note) {
    const details = element("details");
    details.append(element("summary", null, "Observation assessment"));
    details.append(paragraph(null, evidence.observation_note));
    card.append(details);
  }
  return card;
}

function renderActivity() {
  const panel = ui["activity-panel"];
  clear(panel);
  if (!state.snapshot) return;
  const snapshot = state.snapshot.snapshot;
  if (snapshot.warnings?.length) {
    const list = element("ul", "warning-list");
    snapshot.warnings.forEach((warning) => list.append(element("li", null, warning)));
    panel.append(list);
  }
  const events = [...(snapshot.recent_events || [])].reverse();
  if (!events.length) {
    panel.append(paragraph("panel-placeholder", "No model or tool actions have been recorded yet."));
    return;
  }
  const list = element("div", "activity-list");
  for (const event of events) {
    const row = element("article", "activity-event");
    const mark = element("span", "event-mark", eventSymbol(event.kind));
    const copy = element("div");
    copy.append(paragraph(null, event.summary));
    const metadata = [
      event.iteration ? `iteration ${event.iteration}` : null,
      event.action_name || event.kind,
    ].filter(Boolean).join(" · ");
    copy.append(element("small", null, metadata));
    row.append(mark, copy);
    list.append(row);
  }
  panel.append(list);
}

function renderArtifacts() {
  const panel = ui["artifacts-panel"];
  clear(panel);
  if (!state.snapshot) return;
  const artifacts = state.snapshot.artifacts || [];
  if (!artifacts.length) {
    panel.append(paragraph("panel-placeholder", "No browser-visible artifacts have been recorded yet."));
    return;
  }
  const grid = element("div", "artifact-grid");
  for (const artifact of artifacts) {
    const card = element("article", "artifact-card");
    const preview = element("div", "artifact-preview");
    if (artifact.preview === "image") {
      const image = element("img");
      image.src = artifactUrl(artifact.path);
      image.alt = artifact.name;
      image.loading = "lazy";
      preview.append(image);
    } else {
      preview.append(element("span", null, artifact.preview === "text" ? "¶" : "◇"));
    }
    const copy = element("div", "artifact-copy");
    copy.append(element("strong", null, artifact.name));
    const claimed = artifact.claimed_by?.length
      ? ` · evidence for ${artifact.claimed_by.join(", ")}`
      : "";
    const meta = element("small", artifact.claimed_by?.length ? "claim-links" : null);
    meta.textContent = `${artifact.size_label}${claimed}`;
    copy.append(meta);
    const link = element("a", null, artifact.preview === "download" ? "Open artifact" : "Preview artifact");
    link.href = artifactUrl(artifact.path);
    link.target = "_blank";
    link.rel = "noopener";
    copy.append(link);
    card.append(preview, copy);
    grid.append(card);
  }
  panel.append(grid);
}

function renderConclusion() {
  const panel = ui["conclusion-panel"];
  clear(panel);
  if (!state.snapshot) return;
  const report = state.snapshot.snapshot.report;
  if (!report) {
    panel.append(paragraph("panel-placeholder", "The campaign has not written a terminal conclusion."));
    return;
  }
  const conclusion = element("article", "conclusion");
  conclusion.append(element("pre", null, report.final_answer || "No final answer was recorded."));
  panel.append(conclusion);
}

function setTab(name) {
  state.activeTab = name;
  for (const tab of ui.tabs) tab.setAttribute("aria-selected", String(tab.dataset.tab === name));
  ui["activity-panel"].hidden = name !== "activity";
  ui["artifacts-panel"].hidden = name !== "artifacts";
  ui["conclusion-panel"].hidden = name !== "conclusion";
}

function openNewRunDialog() {
  if (!state.allowMutations) return;
  ui["new-run-error"].hidden = true;
  ui["new-run-dialog"].showModal();
  ui["new-run-form"].elements.hypothesis.focus();
}

function closeNewRunDialog() {
  ui["new-run-dialog"].close();
}

async function launchCampaign(event) {
  event.preventDefault();
  const form = new FormData(ui["new-run-form"]);
  const payload = {
    hypothesis: form.get("hypothesis"),
    instruction: form.get("instruction") || null,
    campaign_id: form.get("campaign_id") || null,
    max_wall_seconds: Number(form.get("max_wall_seconds")),
    max_command_seconds: Number(form.get("max_command_seconds")),
    max_workspace_mb: Number(form.get("max_workspace_mb")),
    max_memory_mb: Number(form.get("max_memory_mb")),
  };
  ui["launch-button"].disabled = true;
  ui["launch-button"].textContent = "Launching…";
  ui["new-run-error"].hidden = true;
  try {
    const result = await api("/api/campaigns", { method: "POST", body: payload });
    ui["new-run-form"].reset();
    closeNewRunDialog();
    await refreshCampaigns();
    state.selectedCampaign = result.campaign;
    state.selectedClaim = null;
    state.graphSignature = null;
    renderCampaignPicker();
    await refreshSnapshot(true);
    showToast(`Launched ${result.campaign_id}`);
  } catch (error) {
    ui["new-run-error"].textContent = error.message;
    ui["new-run-error"].hidden = false;
  } finally {
    ui["launch-button"].disabled = false;
    ui["launch-button"].textContent = "Launch campaign";
  }
}

async function controlCampaign(action) {
  if (!state.selectedCampaign || !state.allowMutations) return;
  if (action === "cancel") {
    const confirmed = window.confirm(
      "Stop the verified campaign process? Partial workspace files remain non-evidentiary.",
    );
    if (!confirmed) return;
  }
  const buttons = [ui["pause-button"], ui["resume-button"], ui["cancel-button"]];
  buttons.forEach((button) => { button.disabled = true; });
  try {
    const result = await api(
      `/api/campaigns/${encodeURIComponent(state.selectedCampaign)}/control/${action}`,
      { method: "POST", body: {} },
    );
    showToast(result.message);
    await refreshSnapshot(true);
  } catch (error) {
    showToast(error.message, true);
    if (state.snapshot) renderControls(state.snapshot.controls);
  }
}

function changeZoom(delta) {
  state.graphZoom = Math.min(1.8, Math.max(0.55, state.graphZoom + delta));
  renderGraph(true);
}

function fitGraph() {
  const graph = ui["hypothesis-graph"];
  const viewBox = graph.viewBox.baseVal;
  if (!viewBox.width) return;
  const available = Math.max(100, ui["graph-viewport"].clientWidth - 20);
  state.graphZoom = Math.min(1, Math.max(0.55, available / viewBox.width));
  renderGraph(false);
  ui["graph-viewport"].scrollTo({ left: 0, top: 0 });
}

function showEmptyState() {
  ui.dashboard.hidden = true;
  ui["empty-state"].hidden = false;
  renderControls({ can_pause: false, can_resume: false, can_cancel: false });
}

function artifactUrl(path) {
  const query = new URLSearchParams({ campaign: state.selectedCampaign, path });
  return `/api/artifact?${query.toString()}`;
}

async function api(path, options = {}) {
  const headers = { Accept: "application/json" };
  const fetchOptions = { method: options.method || "GET", headers, cache: "no-store" };
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    headers["X-Simjecture-Token"] = state.controlToken || "";
    fetchOptions.body = JSON.stringify(options.body);
  }
  const response = await fetch(path, fetchOptions);
  let payload;
  try {
    payload = await response.json();
  } catch (_) {
    throw new Error(`The local server returned HTTP ${response.status}`);
  }
  if (!response.ok) throw new Error(payload.error || `Request failed with HTTP ${response.status}`);
  return payload;
}

function setSync(kind, label) {
  const target = ui["sync-state"];
  target.classList.remove("online", "offline");
  if (kind === "online" || kind === "offline") target.classList.add(kind);
  target.querySelector("span").textContent = label;
}

function showToast(message, error = false) {
  window.clearTimeout(state.toastTimer);
  ui.toast.textContent = message;
  ui.toast.classList.toggle("error", error);
  ui.toast.hidden = false;
  state.toastTimer = window.setTimeout(() => { ui.toast.hidden = true; }, 4200);
}

function setBadge(target, status, label) {
  target.dataset.status = status || "unknown";
  target.textContent = String(label || status || "—").replaceAll("_", " ");
}

function inspectorSection(title, copy = null) {
  const section = element("section", "inspector-section");
  section.append(element("h3", null, title));
  if (copy) section.append(paragraph(null, copy));
  return section;
}

function eventSymbol(kind) {
  return { assistant: "A", tool: "✓", tool_heartbeat: "·", control: "!" }[kind] || "◇";
}

function wrapText(value, width, maxLines) {
  const words = String(value).trim().split(/\s+/);
  const lines = [];
  let current = "";
  for (const word of words) {
    const candidate = current ? `${current} ${word}` : word;
    if (candidate.length <= width || !current) {
      current = candidate;
    } else {
      lines.push(current);
      current = word;
      if (lines.length === maxLines - 1) break;
    }
  }
  if (current && lines.length < maxLines) lines.push(current);
  const consumed = lines.join(" ").length;
  if (consumed < String(value).trim().length && lines.length) {
    lines[lines.length - 1] = `${lines[lines.length - 1].replace(/[.…]+$/, "")}…`;
  }
  return lines;
}

function appendSvgText(parent, copy, x, y, className, anchor = "start") {
  const text = svg("text", {
    class: className,
    x: String(x),
    y: String(y),
    "text-anchor": anchor,
  });
  text.textContent = copy;
  parent.append(text);
}

function svg(tag, attributes = {}) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
  return node;
}

function element(tag, className = null, text = null) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== null && text !== undefined) node.textContent = String(text);
  return node;
}

function paragraph(className, text) {
  return element("p", className, text);
}

function option(value, label) {
  const node = element("option", null, label);
  node.value = value;
  return node;
}

function clear(node) {
  node.replaceChildren();
}

function countBy(items, key) {
  const result = {};
  for (const item of items) {
    const value = key(item);
    result[value] = (result[value] || 0) + 1;
  }
  return result;
}

function formatInteger(value) {
  return new Intl.NumberFormat().format(value || 0);
}

function compactNumber(value) {
  return new Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 1 }).format(value || 0);
}

function debounce(callback, delay) {
  let timer;
  return (...args) => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => callback(...args), delay);
  };
}
