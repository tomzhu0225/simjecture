"use strict";

const SVG_NS = "http://www.w3.org/2000/svg";

const state = {
  campaigns: [],
  selectedCampaign: null,
  selectedClaim: null,
  selectedStage: null,
  selectedExecution: null,
  snapshot: null,
  controlToken: null,
  allowMutations: false,
  activeTab: "artifacts",
  showAllClaims: true,
  graphZoom: 1,
  graphPositions: new Map(),
  currentGraphLayout: null,
  graphSignature: null,
  inspectorSignature: null,
  executionSignature: null,
  traceSignature: null,
  artifactSignature: null,
  conclusionSignature: null,
  expandedDetails: new Set(),
  executionConsoleCache: new Map(),
  executionLoads: new Set(),
  pollInFlight: false,
  pollCount: 0,
  toastTimer: null,
};

const ui = {};

document.addEventListener("DOMContentLoaded", () => {
  bindElements();
  applyStoredTheme();
  bindEvents();
  initialize();
});

function bindElements() {
  const ids = [
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
    "execution-console",
    "execution-list",
    "execution-summary",
    "graph-placeholder",
    "graph-viewport",
    "claim-graph",
    "inspector-kind",
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
    "research-trace",
    "reset-layout",
    "resume-button",
    "root-hypothesis",
    "sync-state",
    "theme-button",
    "toast",
    "token-breakdown",
    "claim-kind-toggle",
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
  ui["theme-button"].addEventListener("click", toggleTheme);
  ui["claim-kind-toggle"].addEventListener("click", toggleClaimKinds);
  ui["zoom-in"].addEventListener("click", () => changeZoom(0.15));
  ui["zoom-out"].addEventListener("click", () => changeZoom(-0.15));
  ui["zoom-fit"].addEventListener("click", fitGraph);
  ui["reset-layout"].addEventListener("click", resetGraphLayout);
  for (const tab of ui.tabs) {
    tab.addEventListener("click", () => setTab(tab.dataset.tab));
  }
  window.addEventListener("resize", debounce(() => {
    if (state.snapshot) renderGraph(true);
  }, 160));
}

function applyStoredTheme() {
  let theme = "light";
  try {
    const stored = window.localStorage.getItem("simjecture-theme");
    if (stored === "light" || stored === "dark") theme = stored;
  } catch (_) {
    // Local storage can be unavailable in hardened browsers.
  }
  document.documentElement.dataset.theme = theme;
  updateThemeButton();
}

function toggleTheme() {
  const theme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = theme;
  try {
    window.localStorage.setItem("simjecture-theme", theme);
  } catch (_) {
    // Theme still applies for this page session.
  }
  updateThemeButton();
  if (state.snapshot) renderGraph(true);
}

function updateThemeButton() {
  const dark = document.documentElement.dataset.theme === "dark";
  ui["theme-button"].textContent = dark ? "☀" : "☾";
  ui["theme-button"].setAttribute("aria-label", dark ? "Use light theme" : "Use dark theme");
  ui["theme-button"].title = dark ? "Use light theme" : "Use dark theme";
}

async function initialize() {
  setSync("connecting", "Connecting");
  try {
    const bootstrap = await api("/api/bootstrap");
    state.campaigns = bootstrap.campaigns || [];
    state.controlToken = bootstrap.control_token;
    state.allowMutations = Boolean(bootstrap.allow_mutations);
    state.selectedCampaign = bootstrap.selected_campaign;
    loadGraphPositions();
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
    // Snapshot polling owns the main connectivity indicator.
  }
}

async function refreshSnapshot(force) {
  if (!state.selectedCampaign) return;
  state.pollInFlight = true;
  try {
    const payload = await api(
      `/api/snapshot?campaign=${encodeURIComponent(state.selectedCampaign)}`,
    );
    state.snapshot = payload;
    renderSnapshot(force);
    setSync("online", "Live");
  } catch (error) {
    setSync("offline", "Retrying");
    if (force) showToast(error.message, true);
  } finally {
    state.pollInFlight = false;
  }
}

async function selectCampaign(token) {
  if (!token || token === state.selectedCampaign) return;
  state.selectedCampaign = token;
  state.selectedClaim = null;
  state.selectedStage = null;
  state.selectedExecution = null;
  state.snapshot = null;
  state.graphZoom = 1;
  loadGraphPositions();
  state.expandedDetails.clear();
  state.executionConsoleCache.clear();
  state.executionLoads.clear();
  resetRenderSignatures();
  setSync("connecting", "Loading");
  await refreshSnapshot(true);
}

function resetRenderSignatures() {
  state.graphSignature = null;
  state.inspectorSignature = null;
  state.executionSignature = null;
  state.traceSignature = null;
  state.artifactSignature = null;
  state.conclusionSignature = null;
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

function renderSnapshot(force) {
  const data = state.snapshot;
  const snapshot = data.snapshot;
  ui["empty-state"].hidden = true;
  ui.dashboard.hidden = false;

  const execution = snapshot.execution_status;
  const displayStatus = execution === "terminal" ? snapshot.phase : execution;
  setBadge(ui["campaign-status"], displayStatus, displayStatus);
  ui["campaign-id"].textContent = data.display_name || snapshot.identity.campaign_id || "unnamed campaign";
  renderMarkdown(
    ui["root-hypothesis"],
    snapshot.identity.hypothesis || "Hypothesis not yet recorded",
    { inline: true },
  );
  const instruction = snapshot.identity.campaign_instruction;
  ui["campaign-instruction"].hidden = !instruction;
  if (instruction) renderMarkdown(ui["campaign-instruction"], `**Guidance:** ${instruction}`);

  renderCurrentAction(snapshot);
  renderMetrics(data);
  renderControls(data.controls);

  const claims = data.claim_graph.nodes || [];
  const scientificClaims = claims.filter(isScientificClaim);
  const stages = data.commissioning?.stages || [];
  if (state.selectedStage && !stages.some((item) => item.id === state.selectedStage)) {
    state.selectedStage = null;
  }
  if (!state.selectedStage && (!state.selectedClaim || !data.claim_details[state.selectedClaim])) {
    state.selectedClaim = claims.find((item) => item.id === "claim_root")?.id
      || scientificClaims[0]?.id
      || claims[0]?.id
      || null;
  }

  const graphSignature = signature([data.claim_graph, data.commissioning, state.showAllClaims]);
  if (force || graphSignature !== state.graphSignature) {
    state.graphSignature = graphSignature;
    renderGraph(false);
  }

  const inspectorSignature = signature([
    state.selectedClaim,
    state.selectedStage,
    data.claim_details[state.selectedClaim] || null,
    data.claim_graph,
    data.commissioning,
  ]);
  if (force || inspectorSignature !== state.inspectorSignature) {
    state.inspectorSignature = inspectorSignature;
    renderInspector();
  }

  const executionSignature = signature(data.executions || {});
  if (force || executionSignature !== state.executionSignature) {
    state.executionSignature = executionSignature;
    renderExecutions();
  }

  const traceSignature = signature([snapshot.recent_events, snapshot.warnings, snapshot.token_usage]);
  if (force || traceSignature !== state.traceSignature) {
    state.traceSignature = traceSignature;
    renderResearchTrace();
  }

  const artifactSignature = signature(data.artifacts || []);
  if (force || artifactSignature !== state.artifactSignature) {
    state.artifactSignature = artifactSignature;
    renderArtifacts();
  }

  const conclusionSignature = signature(snapshot.report || null);
  if (force || conclusionSignature !== state.conclusionSignature) {
    state.conclusionSignature = conclusionSignature;
    renderConclusion();
  }
}

function renderCurrentAction(snapshot) {
  const container = ui["current-action"];
  const symbol = container.querySelector(".action-symbol");
  const label = container.querySelector("small");
  const value = container.querySelector("strong");
  if (snapshot.current_action) {
    symbol.textContent = snapshot.current_action.pending ? "◈" : "◇";
    label.textContent = `Current action · iteration ${snapshot.current_action.iteration}`;
    renderMarkdown(value, snapshot.current_action.description, { inline: true });
    value.title = markdownPlainText(snapshot.current_action.description);
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
  const claims = data.claim_graph.nodes || [];
  const counts = countBy(claims, (item) => item.kind || "unknown");
  ui["metric-claims"].textContent = String(claims.length);
  ui["metric-claims-detail"].textContent = claims.length
    ? ["scientific", "instrument", "diagnostic", "control"]
      .map((kind) => `${counts[kind] || 0} ${kind}`)
      .join(" · ")
    : "No registered claims";
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

function toggleClaimKinds() {
  state.showAllClaims = !state.showAllClaims;
  ui["claim-kind-toggle"].setAttribute("aria-pressed", String(state.showAllClaims));
  ui["claim-kind-toggle"].textContent = state.showAllClaims ? "All claim kinds" : "Scientific only";
  state.graphSignature = null;
  renderGraph(true);
}

function graphData() {
  if (!state.snapshot) return { nodes: [], edges: [] };
  const graph = state.snapshot.claim_graph || { nodes: [], edges: [] };
  if (!state.showAllClaims) {
    const nodes = graph.nodes.filter(isScientificClaim);
    const ids = new Set(nodes.map((node) => node.id));
    return {
      nodes,
      edges: graph.edges.filter((edge) => ids.has(edge.source) && ids.has(edge.target)),
    };
  }

  const stages = (state.snapshot.commissioning?.stages || []).map((stage) => ({
    ...stage,
    statement: "Capability evidence gate",
    evidence_count: stage.claim_ids.length,
    contract_count: stage.binding_count,
  }));
  const stageByInstrument = new Map();
  for (const stage of stages) {
    for (const claimId of stage.claim_ids) stageByInstrument.set(claimId, stage);
  }
  const edges = [];
  const linkedStages = new Set();
  for (const edge of graph.edges) {
    const stage = stageByInstrument.get(edge.target);
    if (stage && edge.source === stage.scientific_claim_id) {
      if (!linkedStages.has(stage.id)) {
        edges.push({
          source: stage.scientific_claim_id,
          target: stage.id,
          relation: "commissioning",
          derived: true,
        });
        linkedStages.add(stage.id);
      }
      edges.push({ ...edge, source: stage.id });
    } else {
      edges.push(edge);
    }
  }
  for (const stage of stages) {
    if (!linkedStages.has(stage.id)) {
      edges.push({
        source: stage.scientific_claim_id,
        target: stage.id,
        relation: "commissioning",
        derived: true,
      });
    }
  }
  return { nodes: [...graph.nodes, ...stages], edges };
}

function isScientificClaim(item) {
  return item.kind === "scientific" || item.id === "claim_root";
}

function isCommissioningStage(item) {
  return item.node_type === "stage" && item.stage === "commissioning";
}

function renderGraph(preserveScroll) {
  const graph = ui["claim-graph"];
  const viewport = ui["graph-viewport"];
  const previousScroll = { left: viewport.scrollLeft, top: viewport.scrollTop };
  clear(graph);
  if (!state.snapshot) return;
  const data = graphData();
  const nodes = data.nodes || [];
  const edges = data.edges || [];
  const scientific = nodes.filter(isScientificClaim);
  const nodesById = new Map(nodes.map((node) => [node.id, node]));
  ui["graph-placeholder"].hidden = scientific.length > 0;
  graph.hidden = scientific.length === 0;
  if (!scientific.length) return;

  const layout = layoutClaimGraph(nodes);
  state.currentGraphLayout = layout;
  graph.setAttribute("viewBox", `0 0 ${layout.width} ${layout.height}`);
  graph.setAttribute("width", String(layout.width * state.graphZoom));
  graph.setAttribute("height", String(layout.height * state.graphZoom));

  const edgeLayer = svg("g", { class: "edge-layer" });
  for (const edge of edges) {
    const source = layout.positions.get(edge.source);
    const target = layout.positions.get(edge.target);
    if (!source || !target) continue;
    const targetNode = nodesById.get(edge.target);
    const targetKind = targetNode?.kind || "scientific";
    const supporting = !isScientificClaim(targetNode || {});
    const geometry = graphEdgeGeometry(source, target);
    const path = svg("path", {
      class: `graph-edge${supporting ? ` supporting ${targetKind}` : ""}`,
      d: geometry.path,
      "data-source": edge.source,
      "data-target": edge.target,
    });
    edgeLayer.append(path);
    const label = svg("text", {
      class: "graph-edge-label",
      x: String(geometry.labelX),
      y: String(geometry.labelY),
      "text-anchor": "middle",
      "data-source": edge.source,
      "data-target": edge.target,
    });
    label.textContent = edge.relation || "related";
    edgeLayer.append(label);
  }
  graph.append(edgeLayer);

  const nodeLayer = svg("g", { class: "node-layer" });
  for (const item of nodes) {
    const point = layout.positions.get(item.id);
    if (!point) continue;
    const scientificClaim = isScientificClaim(item);
    const commissioningStage = isCommissioningStage(item);
    const kind = item.kind || "scientific";
    const selected = commissioningStage
      ? item.id === state.selectedStage
      : item.id === state.selectedClaim;
    const group = svg("g", {
      class: `graph-node ${scientificClaim ? "scientific" : `supporting ${kind}`}${selected ? " selected" : ""}`,
      "data-status": item.status,
      "data-node-id": item.id,
      role: "button",
      tabindex: "0",
      transform: `translate(${point.x} ${point.y})`,
      "aria-label": commissioningStage
        ? `Commissioning stage for ${item.scientific_claim_id}, ${item.status}`
        : `${kind} claim ${item.id}, ${item.status}: ${markdownPlainText(item.statement)}`,
    });
    group.append(svg("rect", {
      class: "node-body",
      width: String(point.width),
      height: String(point.height),
      rx: scientificClaim || commissioningStage ? "10" : "8",
    }));
    group.append(svg("line", {
      class: "status-line",
      x1: "2",
      x2: "2",
      y1: "12",
      y2: String(point.height - 12),
    }));
    appendSvgText(group, commissioningStage ? "commissioning stage" : kind, 16, 21, "node-id");
    appendSvgText(group, item.status, point.width - 14, 21, "node-status", "end");
    const copy = commissioningStage
      ? `${item.claim_ids.length} instrument claim${item.claim_ids.length === 1 ? "" : "s"} · ${item.binding_count} bound program${item.binding_count === 1 ? "" : "s"}`
      : markdownPlainText(item.statement || item.id);
    const lines = wrapText(copy, scientificClaim ? 45 : 35, scientificClaim ? 3 : 2);
    lines.forEach((line, index) => appendSvgText(group, line, 16, 48 + index * 17, "node-copy"));
    const counts = commissioningStage
      ? `${item.scientific_claim_id}${item.guided_available ? " · guided start" : ""}`
      : `${item.id} · E${item.evidence_count}/C${item.contract_count}`;
    appendSvgText(group, counts, 16, point.height - 12, "node-counts");
    bindGraphNode(group, item, point);
    nodeLayer.append(group);
  }
  graph.append(nodeLayer);
  if (preserveScroll) {
    viewport.scrollLeft = previousScroll.left;
    viewport.scrollTop = previousScroll.top;
  }
}

function layoutClaimGraph(nodes) {
  const scientificWidth = 300;
  const scientificHeight = 126;
  const supportingWidth = 230;
  const supportingHeight = 86;
  const stageWidth = 270;
  const stageHeight = 106;
  const supportingGap = 14;
  const columnPitch = 1000;
  const marginX = 42;
  const marginY = 42;
  const rowGap = 58;
  const scientific = nodes.filter(isScientificClaim);
  const attached = new Map(scientific.map((item) => [item.id, []]));
  for (const item of nodes) {
    if (!isScientificClaim(item) && attached.has(item.owner_id)) {
      attached.get(item.owner_id).push(item);
    }
  }
  const positions = new Map();
  let cursorY = marginY;
  let maxX = marginX + scientificWidth;
  for (const item of scientific) {
    const owned = attached.get(item.id) || [];
    const stages = owned.filter(isCommissioningStage);
    const instrumentIds = new Set(stages.flatMap((stage) => stage.claim_ids || []));
    const instruments = owned.filter((node) => instrumentIds.has(node.id));
    const otherClaims = owned.filter(
      (node) => !isCommissioningStage(node) && !instrumentIds.has(node.id),
    );
    const stageStack = stages.length
      ? stages.length * stageHeight + (stages.length - 1) * supportingGap
      : 0;
    const otherStack = otherClaims.length
      ? otherClaims.length * supportingHeight + (otherClaims.length - 1) * supportingGap
      : 0;
    const leftSupportingStack = stageStack && otherStack
      ? stageStack + supportingGap + otherStack
      : stageStack + otherStack;
    const instrumentStack = instruments.length
      ? instruments.length * supportingHeight + (instruments.length - 1) * supportingGap
      : 0;
    const blockHeight = Math.max(scientificHeight, leftSupportingStack, instrumentStack);
    const x = marginX + (item.depth || 0) * columnPitch;
    const y = cursorY + (blockHeight - scientificHeight) / 2;
    positions.set(item.id, {
      x,
      y,
      width: scientificWidth,
      height: scientificHeight,
    });
    const supportingX = x + scientificWidth + 64;
    stages.forEach((stage, index) => {
      const stageY = cursorY + index * (stageHeight + supportingGap);
      positions.set(stage.id, {
        x: supportingX,
        y: stageY,
        width: stageWidth,
        height: stageHeight,
      });
      maxX = Math.max(maxX, supportingX + stageWidth);
    });
    instruments.forEach((claim, index) => {
      const claimX = supportingX + stageWidth + 54 + (claim.depth || 0) * 20;
      const claimY = cursorY + index * (supportingHeight + supportingGap);
      positions.set(claim.id, {
        x: claimX,
        y: claimY,
        width: supportingWidth,
        height: supportingHeight,
      });
      maxX = Math.max(maxX, claimX + supportingWidth);
    });
    const otherStart = cursorY + (stageStack ? stageStack + supportingGap : 0);
    otherClaims.forEach((claim, index) => {
      const claimX = supportingX + (claim.depth || 0) * 26;
      const claimY = otherStart + index * (supportingHeight + supportingGap);
      positions.set(claim.id, {
        x: claimX,
        y: claimY,
        width: supportingWidth,
        height: supportingHeight,
      });
      maxX = Math.max(maxX, claimX + supportingWidth);
    });
    maxX = Math.max(maxX, x + scientificWidth);
    cursorY += blockHeight + rowGap;
  }
  for (const [nodeId, saved] of state.graphPositions.entries()) {
    const point = positions.get(nodeId);
    if (!point || !Number.isFinite(saved.x) || !Number.isFinite(saved.y)) continue;
    point.x = Math.max(10, saved.x);
    point.y = Math.max(10, saved.y);
  }
  let maxY = 590;
  for (const point of positions.values()) {
    maxX = Math.max(maxX, point.x + point.width);
    maxY = Math.max(maxY, point.y + point.height);
  }
  return {
    positions,
    width: maxX + marginX,
    height: Math.max(maxY + marginY, cursorY - rowGap + marginY),
  };
}

function graphEdgeGeometry(source, target) {
  const x1 = source.x + source.width;
  const y1 = source.y + source.height / 2;
  const x2 = target.x;
  const y2 = target.y + target.height / 2;
  const direction = x2 >= x1 ? 1 : -1;
  const bend = Math.max(35, Math.abs(x2 - x1) * 0.46);
  return {
    path: `M ${x1} ${y1} C ${x1 + direction * bend} ${y1}, ${x2 - direction * bend} ${y2}, ${x2} ${y2}`,
    labelX: (x1 + x2) / 2,
    labelY: (y1 + y2) / 2 - 7,
  };
}

function updateGraphEdges() {
  const layout = state.currentGraphLayout;
  if (!layout) return;
  for (const path of ui["claim-graph"].querySelectorAll("path.graph-edge")) {
    const source = layout.positions.get(path.dataset.source);
    const target = layout.positions.get(path.dataset.target);
    if (source && target) path.setAttribute("d", graphEdgeGeometry(source, target).path);
  }
  for (const label of ui["claim-graph"].querySelectorAll("text.graph-edge-label")) {
    const source = layout.positions.get(label.dataset.source);
    const target = layout.positions.get(label.dataset.target);
    if (!source || !target) continue;
    const geometry = graphEdgeGeometry(source, target);
    label.setAttribute("x", String(geometry.labelX));
    label.setAttribute("y", String(geometry.labelY));
  }
}

function graphPointerPosition(event) {
  const graph = ui["claim-graph"];
  const matrix = graph.getScreenCTM();
  if (!matrix) return null;
  const point = graph.createSVGPoint();
  point.x = event.clientX;
  point.y = event.clientY;
  return point.matrixTransform(matrix.inverse());
}

function bindGraphNode(group, item, point) {
  let pointerId = null;
  let start = null;
  let origin = null;
  let moved = false;
  let suppressClick = false;

  const activate = () => {
    if (isCommissioningStage(item)) selectCommissioningStage(item.id);
    else selectClaim(item.id);
  };
  group.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) return;
    const position = graphPointerPosition(event);
    if (!position) return;
    pointerId = event.pointerId;
    start = position;
    origin = { x: point.x, y: point.y };
    moved = false;
    group.classList.add("dragging");
    group.setPointerCapture(pointerId);
  });
  group.addEventListener("pointermove", (event) => {
    if (pointerId !== event.pointerId || !start || !origin) return;
    const position = graphPointerPosition(event);
    if (!position) return;
    const dx = position.x - start.x;
    const dy = position.y - start.y;
    if (!moved && Math.hypot(dx, dy) < 3) return;
    moved = true;
    event.preventDefault();
    point.x = Math.max(10, origin.x + dx);
    point.y = Math.max(10, origin.y + dy);
    group.setAttribute("transform", `translate(${point.x} ${point.y})`);
    updateGraphEdges();
  });
  const finishDrag = (event) => {
    if (pointerId !== event.pointerId) return;
    if (group.hasPointerCapture(pointerId)) group.releasePointerCapture(pointerId);
    group.classList.remove("dragging");
    pointerId = null;
    if (!moved) return;
    suppressClick = true;
    state.graphPositions.set(item.id, {
      x: Math.round(point.x * 10) / 10,
      y: Math.round(point.y * 10) / 10,
    });
    saveGraphPositions();
    window.setTimeout(() => renderGraph(true), 0);
  };
  group.addEventListener("pointerup", finishDrag);
  group.addEventListener("pointercancel", finishDrag);
  group.addEventListener("click", () => {
    if (suppressClick) {
      suppressClick = false;
      return;
    }
    activate();
  });
  group.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      activate();
    }
  });
}

function graphLayoutStorageKey() {
  return state.selectedCampaign
    ? `simjecture-graph-layout-v1:${state.selectedCampaign}`
    : null;
}

function loadGraphPositions() {
  state.graphPositions = new Map();
  const key = graphLayoutStorageKey();
  if (!key) return;
  try {
    const payload = JSON.parse(window.localStorage.getItem(key) || "{}");
    for (const [nodeId, point] of Object.entries(payload)) {
      if (
        point
        && Number.isFinite(point.x)
        && Number.isFinite(point.y)
        && point.x >= 0
        && point.y >= 0
        && point.x <= 100_000
        && point.y <= 100_000
      ) {
        state.graphPositions.set(nodeId, { x: point.x, y: point.y });
      }
    }
  } catch (_) {
    state.graphPositions = new Map();
  }
}

function saveGraphPositions() {
  const key = graphLayoutStorageKey();
  if (!key) return;
  try {
    window.localStorage.setItem(key, JSON.stringify(Object.fromEntries(state.graphPositions)));
  } catch (_) {
    // Dragging still works for this page session when local storage is unavailable.
  }
}

function resetGraphLayout() {
  state.graphPositions.clear();
  const key = graphLayoutStorageKey();
  if (key) {
    try {
      window.localStorage.removeItem(key);
    } catch (_) {
      // The in-memory reset is still effective.
    }
  }
  state.currentGraphLayout = null;
  renderGraph(false);
  fitGraph();
}

function selectClaim(claimId) {
  state.selectedClaim = claimId;
  state.selectedStage = null;
  state.inspectorSignature = null;
  renderGraph(true);
  renderInspector();
}

function selectCommissioningStage(stageId) {
  state.selectedClaim = null;
  state.selectedStage = stageId;
  state.inspectorSignature = null;
  renderGraph(true);
  renderInspector();
}

function claimGraphNode(claimId) {
  if (!state.snapshot) return null;
  return (state.snapshot.claim_graph?.nodes || []).find((item) => item.id === claimId) || null;
}

function commissioningStageById(stageId) {
  if (!state.snapshot) return null;
  return (state.snapshot.commissioning?.stages || []).find((item) => item.id === stageId) || null;
}

function renderInspector() {
  const container = ui["claim-inspector"];
  clear(container);
  if (!state.snapshot) {
    container.append(paragraph("panel-placeholder", "Select a claim or stage to inspect it."));
    setBadge(ui["claim-status"], "", "—");
    return;
  }
  if (state.selectedStage) {
    const stage = commissioningStageById(state.selectedStage);
    if (stage) {
      renderCommissioningInspector(container, stage);
      return;
    }
  }
  if (!state.selectedClaim) {
    container.append(paragraph("panel-placeholder", "Select a claim or stage to inspect it."));
    setBadge(ui["claim-status"], "", "—");
    return;
  }
  const detail = state.snapshot.claim_details[state.selectedClaim];
  if (!detail) {
    container.append(paragraph("panel-placeholder", "Claim details are not available yet."));
    return;
  }
  const node = claimGraphNode(state.selectedClaim);
  const kind = detail.kind || (detail.id === "claim_root" ? "scientific" : "unknown");
  const supporting = kind !== "scientific";
  ui["inspector-kind"].textContent = `${capitalize(kind)} claim`;
  setBadge(ui["claim-status"], detail.status, detail.status);
  container.append(markdownBlock(detail.statement || detail.id, "claim-statement"));

  const metadata = element("div", "claim-metadata");
  for (const value of [detail.id, detail.kind, detail.relation]) {
    if (value) metadata.append(element("span", "metadata-chip", value));
  }
  if (Number.isInteger(detail.created_iteration)) {
    metadata.append(element("span", "metadata-chip", `created: iteration ${detail.created_iteration}`));
  }
  if (Number.isInteger(detail.updated_iteration)) {
    metadata.append(element("span", "metadata-chip", `updated: iteration ${detail.updated_iteration}`));
  }
  if (detail.parent_id) {
    const parent = element("button", "metadata-chip", `parent: ${detail.parent_id}`);
    parent.type = "button";
    parent.addEventListener("click", () => selectClaim(detail.parent_id));
    metadata.append(parent);
  }
  if (supporting && node?.owner_id && node.owner_id !== detail.parent_id) {
    const owner = element("button", "metadata-chip", `scientific owner: ${node.owner_id}`);
    owner.type = "button";
    owner.addEventListener("click", () => selectClaim(node.owner_id));
    metadata.append(owner);
  }
  container.append(metadata);

  if (detail.rationale) container.append(inspectorSection("Rationale", detail.rationale));
  if (detail.closed_reason) container.append(inspectorSection("Closure", detail.closed_reason));

  const childClaims = (state.snapshot.claim_graph.nodes || []).filter(
    (item) => item.parent_id === detail.id,
  );
  if (childClaims.length) {
    const section = inspectorSection(`Child claims · ${childClaims.length}`);
    for (const child of childClaims) {
      section.append(claimLinkCard(child, `${child.kind || "unknown"} · ${child.relation || "related"}`));
    }
    container.append(section);
  }

  const contractSection = inspectorSection(
    `Evidence contracts · ${detail.evidence_contracts?.length || 0}`,
  );
  if (detail.evidence_contracts?.length) {
    detail.evidence_contracts.forEach((contract, index) => {
      const card = element("div", "contract-card");
      card.append(element("strong", null, `Contract v${contract.version ?? index + 1}`));
      const fields = [
        ["Observable", contract.observable],
        ["Expected outcomes", contract.expected_outcomes],
        ["Decision rule", contract.decision_rule],
        ["Required observation", contract.required_observation],
        ["Uncertainty", contract.uncertainty_criterion],
        ["Inconclusive when", contract.inconclusive_conditions],
      ];
      for (const [label, copy] of fields) {
        if (!copy) continue;
        card.append(persistentDetails(`contract:${detail.id}:${index}:${label}`, label, copy));
      }
      contractSection.append(card);
    });
  } else {
    contractSection.append(paragraph("inspector-empty", "No evidence contract is recorded for this claim."));
  }
  container.append(contractSection);

  const evidenceSection = inspectorSection(`Evidence · ${detail.evidence?.length || 0}`);
  if (detail.evidence?.length) {
    detail.evidence.forEach((evidence, index) => {
      evidenceSection.append(evidenceCard(evidence, `${detail.id}:${index}`));
    });
  } else {
    evidenceSection.append(paragraph("inspector-empty", "No evidence is linked to this claim yet."));
  }
  container.append(evidenceSection);
}

function renderCommissioningInspector(container, stage) {
  const target = state.snapshot.claim_details[stage.scientific_claim_id];
  const guided = state.snapshot.commissioning?.guided || { available: false };
  ui["inspector-kind"].textContent = "Workflow stage";
  setBadge(ui["claim-status"], stage.status, stage.status);
  container.append(markdownBlock(
    `Commissioning gate for \`${stage.scientific_claim_id}\``,
    "claim-statement",
  ));

  const metadata = element("div", "claim-metadata");
  metadata.append(
    element("span", "metadata-chip", "commissioning"),
    element("span", "metadata-chip", `${stage.claim_ids.length} instrument claims`),
    element("span", "metadata-chip", `${stage.binding_count} bound programs`),
  );
  container.append(metadata);

  if (target) {
    const section = inspectorSection("Scientific target");
    section.append(claimLinkCard(target, "scientific claim"));
    container.append(section);
  }

  if (stage.guided_available && guided.available) {
    const section = inspectorSection("Guided starting point");
    if (guided.name) section.append(element("strong", null, guided.name));
    if (guided.description) section.append(markdownBlock(guided.description));
    const chips = element("div", "claim-metadata compact");
    for (const value of [guided.capability, guided.program_path, guided.policy]) {
      if (value) chips.append(element("span", "metadata-chip", value));
    }
    if (chips.childElementCount) section.append(chips);
    if (guided.operator_validation) {
      section.append(persistentDetails(
        `stage:${stage.id}:operator-validation`,
        "Operator validation",
        guided.operator_validation,
      ));
    }
    if (guided.limitations?.length) {
      const limitations = element("ul", "markdown-list");
      for (const limitation of guided.limitations) {
        const item = element("li");
        item.append(markdownBlock(limitation));
        limitations.append(item);
      }
      section.append(element("h4", null, "Starting-point limitations"), limitations);
    }
    container.append(section);
  }

  const claimSection = inspectorSection(`Commissioning claims · ${stage.claim_ids.length}`);
  if (stage.claim_ids.length) {
    for (const claimId of stage.claim_ids) {
      const claim = state.snapshot.claim_details[claimId];
      if (claim) claimSection.append(claimLinkCard(claim, "instrument · instrument_of"));
    }
  } else {
    claimSection.append(paragraph(
      "inspector-empty",
      "No campaign-generated instrument claim has been registered for this stage yet.",
    ));
  }
  container.append(claimSection);

  const executions = (state.snapshot.executions?.items || []).filter(
    (item) => stage.claim_ids.includes(item.active_claim_id),
  );
  const executionSection = inspectorSection(`Bound executions · ${executions.length}`);
  if (executions.length) {
    for (const execution of executions) {
      const button = element("button", "linked-claim-card");
      button.type = "button";
      const header = element("header");
      header.append(element("strong", null, execution.label));
      const badge = element("span", "status-badge");
      setBadge(badge, execution.status, execution.status);
      header.append(badge);
      button.append(
        header,
        paragraph(null, `Iteration ${execution.iteration} · ${execution.active_claim_id}`),
      );
      button.addEventListener("click", () => {
        state.selectedExecution = execution.id;
        renderExecutions();
        ui["execution-console"].scrollIntoView({ behavior: "smooth", block: "nearest" });
      });
      executionSection.append(button);
    }
  } else {
    executionSection.append(paragraph(
      "inspector-empty",
      "No recorded capability execution is bound to these commissioning claims.",
    ));
  }
  container.append(executionSection);
}

function claimLinkCard(claim, label) {
  const card = element("button", "linked-claim-card");
  card.type = "button";
  const header = element("header");
  header.append(element("strong", null, label));
  const badge = element("span", "status-badge");
  setBadge(badge, claim.status, claim.status);
  header.append(badge);
  card.append(header, markdownBlock(claim.statement || claim.id, "linked-claim-copy"));
  card.addEventListener("click", () => selectClaim(claim.id));
  return card;
}

function evidenceCard(evidence, keyPrefix) {
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
  if (evidence.note) card.append(markdownBlock(evidence.note));
  if (evidence.observation_note) {
    card.append(persistentDetails(`evidence:${keyPrefix}:assessment`, "Observation assessment", evidence.observation_note));
  }
  return card;
}

function persistentDetails(key, label, copy) {
  const fullKey = `${state.selectedCampaign || "campaign"}:${key}`;
  const details = element("details");
  details.dataset.detailKey = fullKey;
  details.open = state.expandedDetails.has(fullKey);
  details.append(element("summary", null, label));
  details.append(markdownBlock(copy));
  details.addEventListener("toggle", () => {
    if (details.open) state.expandedDetails.add(fullKey);
    else state.expandedDetails.delete(fullKey);
  });
  return details;
}

function renderExecutions() {
  const list = ui["execution-list"];
  const consolePanel = ui["execution-console"];
  clear(list);
  clear(consolePanel);
  if (!state.snapshot) return;
  const projection = state.snapshot.executions || { items: [], total: 0, status_counts: {} };
  const items = projection.items || [];
  const counts = projection.status_counts || {};
  const summary = [
    projection.total ? `${projection.total} total` : null,
    counts.running ? `${counts.running} running` : null,
    counts.succeeded ? `${counts.succeeded} succeeded` : null,
    counts.failed ? `${counts.failed} failed` : null,
    projection.truncated ? `${projection.visible} recent shown` : null,
  ].filter(Boolean).join(" · ");
  ui["execution-summary"].textContent = summary || (projection.total ? `${projection.total} recorded` : "No executions");

  if (!items.length) {
    list.append(paragraph("panel-placeholder", "No numerical execution has been recorded."));
    consolePanel.append(element("div", "console-empty", "The first simulation or calculation will appear here with its real state and heartbeat."));
    state.selectedExecution = null;
    return;
  }
  if (!state.selectedExecution || !items.some((item) => item.id === state.selectedExecution)) {
    state.selectedExecution = projection.active_id || items[0].id;
  }
  for (const item of items) {
    const button = element("button", `execution-item${item.id === state.selectedExecution ? " selected" : ""}`);
    button.type = "button";
    button.setAttribute("role", "option");
    button.setAttribute("aria-selected", String(item.id === state.selectedExecution));
    const header = element("header");
    header.append(element("strong", null, item.label));
    const badge = element("span", "status-badge");
    setBadge(badge, item.status, item.status);
    header.append(badge);
    const metadata = [
      `iteration ${item.iteration}`,
      item.stage,
      item.active_claim_id,
    ].filter(Boolean).join(" · ");
    button.append(header, paragraph(null, item.description), element("small", null, metadata));
    button.addEventListener("click", () => {
      state.selectedExecution = item.id;
      renderExecutions();
    });
    list.append(button);
  }
  const selected = items.find((item) => item.id === state.selectedExecution) || items[0];
  const cacheKey = executionCacheKey(selected);
  const rendered = state.executionConsoleCache.has(cacheKey)
    ? { ...selected, console_excerpt: state.executionConsoleCache.get(cacheKey) }
    : selected;
  renderExecutionConsole(consolePanel, rendered);
  if (selected.console_available && !state.executionConsoleCache.has(cacheKey)) {
    loadExecutionConsole(selected, cacheKey);
  }
}

function executionCacheKey(item) {
  return [
    state.selectedCampaign,
    item.id,
    item.status,
    item.stdout_bytes,
    item.stderr_bytes,
  ].join(":");
}

async function loadExecutionConsole(item, cacheKey) {
  if (state.executionLoads.has(cacheKey)) return;
  state.executionLoads.add(cacheKey);
  try {
    const query = new URLSearchParams({
      campaign: state.selectedCampaign,
      iteration: String(item.iteration),
    });
    const payload = await api(`/api/execution?${query.toString()}`);
    state.executionConsoleCache.set(cacheKey, payload.execution.console_excerpt || null);
    if (state.selectedExecution === item.id) renderExecutions();
  } catch (error) {
    state.executionConsoleCache.set(cacheKey, null);
    showToast(`Execution console unavailable: ${error.message}`, true);
    if (state.selectedExecution === item.id) renderExecutions();
  } finally {
    state.executionLoads.delete(cacheKey);
  }
}

function renderExecutionConsole(container, item) {
  const heading = element("div", "console-heading");
  const copy = element("div");
  copy.append(element("h3", null, item.label));
  copy.append(paragraph(null, `Iteration ${item.iteration} · ${item.action_name.replaceAll("_", " ")}`));
  const badge = element("span", "status-badge");
  setBadge(badge, item.status, item.status);
  heading.append(copy, badge);
  container.append(heading);

  const progress = element("div", `progress-track ${item.status}`);
  progress.setAttribute("role", "progressbar");
  progress.setAttribute("aria-label", `Execution ${item.status}`);
  if (item.status !== "running") {
    progress.setAttribute("aria-valuemin", "0");
    progress.setAttribute("aria-valuemax", "1");
    progress.setAttribute("aria-valuenow", item.status === "succeeded" ? "1" : "0");
  }
  container.append(progress);

  const stats = element("div", "execution-stats");
  const values = [
    ["Elapsed", item.elapsed_wall_seconds == null ? "—" : formatDuration(item.elapsed_wall_seconds)],
    ["Stdout", item.stdout_bytes == null ? "—" : formatBytes(item.stdout_bytes)],
    ["Stderr", item.stderr_bytes == null ? "—" : formatBytes(item.stderr_bytes)],
    ["Workspace", item.workspace_bytes == null ? "—" : formatBytes(item.workspace_bytes)],
  ];
  for (const [label, value] of values) {
    const stat = element("div");
    stat.append(element("span", null, label), element("strong", null, value));
    stats.append(stat);
  }
  container.append(stats);

  const binding = element("p", "execution-binding");
  const bindingParts = [
    item.active_claim_id ? `claim ${item.active_claim_id}` : "no claim binding",
    item.stage ? `stage ${item.stage}` : null,
    item.model ? `model ${item.model}` : null,
    item.route ? `route ${item.route}` : null,
    item.returncode == null ? null : `return code ${item.returncode}`,
    item.timed_out ? "timed out" : null,
  ].filter(Boolean);
  binding.textContent = bindingParts.join(" · ");
  container.append(binding);

  let output = item.console_excerpt;
  if (item.console_available && item.console_excerpt === undefined) {
    output = "Loading the bounded console record…";
  }
  if (!output && item.status === "running") {
    output = [
      "$ execution in progress",
      item.argv?.length ? `$ ${item.argv.join(" ")}` : null,
      item.elapsed_wall_seconds == null ? "Waiting for the first command heartbeat…" : `Heartbeat received after ${formatDuration(item.elapsed_wall_seconds)}.`,
      item.stdout_bytes == null ? null : `stdout captured: ${formatBytes(item.stdout_bytes)}`,
      item.stderr_bytes == null ? null : `stderr captured: ${formatBytes(item.stderr_bytes)}`,
    ].filter(Boolean).join("\n");
  }
  if (!output) {
    output = item.argv?.length
      ? `$ ${item.argv.join(" ")}\n\nNo console excerpt was retained for this execution.`
      : "No console excerpt was retained for this execution.";
  }
  container.append(element("pre", "console-output", output));
}

function renderResearchTrace() {
  const panel = ui["research-trace"];
  const usagePanel = ui["token-breakdown"];
  clear(panel);
  clear(usagePanel);
  if (!state.snapshot) return;
  const snapshot = state.snapshot.snapshot;
  const usage = snapshot.token_usage || {};
  const usageRows = [
    ["Input", compactNumber(usage.prompt_tokens)],
    ["Output", compactNumber(usage.completion_tokens)],
    ["Reasoning", compactNumber(usage.reasoning_tokens)],
    ["Cached", compactNumber(usage.cached_tokens)],
  ];
  for (const [label, value] of usageRows) {
    const cell = element("div");
    cell.append(element("span", null, label), element("strong", null, value));
    usagePanel.append(cell);
  }
  if (snapshot.warnings?.length) {
    const warnings = element("ul", "warning-list");
    snapshot.warnings.forEach((warning) => warnings.append(element("li", null, warning)));
    panel.append(warnings);
  }
  const events = [...(snapshot.recent_events || [])].reverse();
  if (!events.length) {
    panel.append(paragraph("panel-placeholder", "No model or tool actions have been recorded yet."));
    return;
  }
  for (const event of events) {
    const row = element("article", "trace-event");
    const mark = element("span", "event-mark", eventSymbol(event.kind));
    const copy = element("div", "trace-copy");
    copy.append(markdownBlock(event.summary));
    const metadata = [
      event.iteration ? `iteration ${event.iteration}` : null,
      event.action_name || event.kind,
      event.model,
      event.route,
      event.outcome && event.kind !== "assistant" ? event.outcome : null,
    ].filter(Boolean).join(" · ");
    copy.append(element("small", null, metadata));
    if (event.research_note) {
      copy.append(markdownBlock(event.research_note, "research-note"));
    }
    row.append(mark, copy);
    panel.append(row);
  }
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
  conclusion.append(markdownBlock(
    report.final_answer || "No final answer was recorded.",
    "conclusion-markdown",
  ));
  panel.append(conclusion);
}

function setTab(name) {
  state.activeTab = name;
  for (const tab of ui.tabs) tab.setAttribute("aria-selected", String(tab.dataset.tab === name));
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
    state.selectedStage = null;
    state.selectedExecution = null;
    state.expandedDetails.clear();
    state.executionConsoleCache.clear();
    state.executionLoads.clear();
    loadGraphPositions();
    resetRenderSignatures();
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
  state.graphZoom = Math.min(1.8, Math.max(0.5, state.graphZoom + delta));
  renderGraph(true);
}

function fitGraph() {
  const graph = ui["claim-graph"];
  const viewBox = graph.viewBox.baseVal;
  if (!viewBox.width) return;
  const available = Math.max(100, ui["graph-viewport"].clientWidth - 20);
  state.graphZoom = Math.min(1, Math.max(0.5, available / viewBox.width));
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
  if (copy) section.append(markdownBlock(copy));
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

function renderMarkdown(target, copy, options = {}) {
  if (window.SimjectureMarkdown) {
    window.SimjectureMarkdown.render(target, copy, options);
  } else {
    target.textContent = String(copy ?? "");
  }
  return target;
}

function markdownBlock(copy, className = null) {
  return renderMarkdown(element("div", className), copy);
}

function markdownPlainText(copy) {
  return window.SimjectureMarkdown
    ? window.SimjectureMarkdown.plainText(copy)
    : String(copy ?? "");
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

function signature(value) {
  return JSON.stringify(value);
}

function capitalize(value) {
  const text = String(value || "");
  return text ? `${text[0].toUpperCase()}${text.slice(1)}` : text;
}

function formatInteger(value) {
  return new Intl.NumberFormat().format(value || 0);
}

function compactNumber(value) {
  return new Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 1 }).format(value || 0);
}

function formatDuration(seconds) {
  const value = Math.max(0, Number(seconds) || 0);
  if (value < 60) return `${Math.round(value)} s`;
  if (value < 3600) return `${Math.floor(value / 60)}m ${Math.round(value % 60)}s`;
  return `${Math.floor(value / 3600)}h ${Math.floor((value % 3600) / 60)}m`;
}

function formatBytes(bytes) {
  let value = Math.max(0, Number(bytes) || 0);
  const units = ["B", "KB", "MB", "GB", "TB"];
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  const digits = value >= 10 || unit === 0 ? 0 : 1;
  return `${value.toFixed(digits)} ${units[unit]}`;
}

function debounce(callback, delay) {
  let timer;
  return (...args) => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => callback(...args), delay);
  };
}
