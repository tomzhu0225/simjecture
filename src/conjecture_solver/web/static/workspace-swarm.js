/* Mature Multi-Agent Swarm GUI: DAG roster, shared message board, steering & launcher. */
"use strict";
window.WorkspaceSwarm = (() => {
  let ctx = null;
  let currentProject = null;
  let selectedSwarmId = null;
  let detailCache = null;
  let detailSignature = "";
  let listSignature = "";
  let inFlight = false;
  let boardRecipient = "all";
  let activePreset = "parallel_explore";
  let draftMembers = [];

  const $ = (id) => document.getElementById(id);
  const el = (tag, text, cls) => {
    const node = document.createElement(tag);
    if (text !== undefined) SimjectureI18n.content(node, text);
    if (cls) node.className = cls;
    return node;
  };
  const ROLES = [
    "explorer",
    "analyst",
    "solver",
    "verifier",
    "falsifier",
    "critic",
    "synthesizer",
    "worker",
  ];

  // i18n-technical-start: default swarm task templates sent to worker agents
  function presetTemplates(strategy) {
    if (strategy === "adversarial_verify") {
      return [
        {
          name: "Solver",
          role: "solver",
          task: "Derive the solution or implement the numerical model and record key observables.",
          completion_criteria: "Produce solution.md and metrics.json with reproducible checks.",
          outputs: ["solution.md", "metrics.json"],
          depends_on: [],
        },
        {
          name: "Falsifier",
          role: "falsifier",
          task: "Actively search for edge cases, boundary violations, or counterexamples to the claim.",
          completion_criteria: "Produce falsification.md documenting adversarial probes and results.",
          outputs: ["falsification.md"],
          depends_on: [],
        },
        {
          name: "Verifier",
          role: "verifier",
          task: "Audit Solver and Falsifier upstream outputs independently and synthesize the verdict.",
          completion_criteria: "Produce verdict.md citing upstream checks and unresolved gaps.",
          outputs: ["verdict.md"],
          depends_on: ["Solver", "Falsifier"],
        },
      ];
    }
    if (strategy === "divide_and_conquer") {
      return [
        {
          name: "Branch A",
          role: "analyst",
          task: "Investigate the first sub-problem or parameter regime independently.",
          completion_criteria: "Produce branch_a.json with measured results.",
          outputs: ["branch_a.json"],
          depends_on: [],
        },
        {
          name: "Branch B",
          role: "analyst",
          task: "Investigate the second sub-problem or parameter regime independently.",
          completion_criteria: "Produce branch_b.json with measured results.",
          outputs: ["branch_b.json"],
          depends_on: [],
        },
        {
          name: "Synthesizer",
          role: "synthesizer",
          task: "Combine upstream branch outputs into a unified comparison report.",
          completion_criteria: "Produce synthesis.md comparing both branches quantitatively.",
          outputs: ["synthesis.md"],
          depends_on: ["Branch A", "Branch B"],
        },
      ];
    }
    return [
      {
        name: "Explorer A",
        role: "explorer",
        task: "Pursue a direct analytic or primary numerical approach to the research objective.",
        completion_criteria: "Save findings and verification script output in approach_a.md.",
        outputs: ["approach_a.md"],
        depends_on: [],
      },
      {
        name: "Explorer B",
        role: "explorer",
        task: "Pursue an independent alternative method or formulation to cross-check the problem.",
        completion_criteria: "Save alternative findings and diagnostics in approach_b.md.",
        outputs: ["approach_b.md"],
        depends_on: [],
      },
      {
        name: "Synthesizer",
        role: "synthesizer",
        task: "Compare upstream Explorer A and Explorer B results and reconcile discrepancies.",
        completion_criteria: "Produce comparison.md summarizing agreements, differences, and next steps.",
        outputs: ["comparison.md"],
        depends_on: ["Explorer A", "Explorer B"],
      },
    ];
  }
  // i18n-technical-end

  function init(options) {
    ctx = options;
    const selector = $("swarm-select");
    if (selector) {
      selector.onchange = () => {
        selectedSwarmId = selector.value || null;
        detailSignature = "";
        updateDetail().catch((e) => ctx.notify(e.message, true));
      };
    }
    const openLauncher = () => openLaunchDialog();
    const launchBtn = $("swarm-launch-open");
    if (launchBtn) launchBtn.onclick = openLauncher;
    const emptyLaunchBtn = $("swarm-empty-launch");
    if (emptyLaunchBtn) emptyLaunchBtn.onclick = openLauncher;
    const enableModeBtn = $("swarm-enable-mode");
    if (enableModeBtn) {
      enableModeBtn.onclick = () =>
        ctx.action(enableModeBtn, async () => {
          await ctx.setSwarmMode?.("auto");
          ctx.notify(SimjectureI18n.message("workspace.swarm.enabledNotice"));
        });
    }
    const closeBtn = $("swarm-dialog-close");
    if (closeBtn) closeBtn.onclick = () => $("swarm-launch-dialog")?.close();
    const cancelBtn = $("swarm-dialog-cancel");
    if (cancelBtn) cancelBtn.onclick = () => $("swarm-launch-dialog")?.close();
    const addMemberBtn = $("swarm-add-member");
    if (addMemberBtn) {
      addMemberBtn.onclick = () => {
        if (draftMembers.length >= 8) return;
        draftMembers.push({
          name: SimjectureI18n.t("workspace.swarm.defaultWorkerName", {
            index: draftMembers.length + 1,
          }),
          role: "worker",
          task: "",
          completion_criteria: "",
          outputs: [`worker_${draftMembers.length + 1}.md`],
          depends_on: [],
        });
        renderDraftMembers();
      };
    }
    for (const btn of document.querySelectorAll("[data-swarm-preset]")) {
      btn.onclick = () => {
        activePreset = btn.dataset.swarmPreset || "parallel_explore";
        updatePresetButtons();
        draftMembers = presetTemplates(activePreset);
        renderDraftMembers();
      };
    }
    const form = $("swarm-launch-form");
    if (form) {
      form.onsubmit = (event) => {
        event.preventDefault();
        ctx.action($("swarm-launch-submit"), submitLaunchDialog);
      };
    }
  }

  function updatePresetButtons() {
    for (const btn of document.querySelectorAll("[data-swarm-preset]")) {
      btn.setAttribute("aria-pressed", String(btn.dataset.swarmPreset === activePreset));
    }
  }

  function openLaunchDialog() {
    const dialog = $("swarm-launch-dialog");
    const p = ctx?.project();
    if (!dialog || !p || ctx.readonly() || ctx.hosted) return;
    activePreset = "parallel_explore";
    updatePresetButtons();
    $("swarm-title-input").value = "";
    $("swarm-objective-input").value = "";
    $("swarm-launch-error").hidden = true;
    draftMembers = presetTemplates(activePreset);
    renderDraftMembers();
    dialog.showModal();
    $("swarm-title-input").focus();
  }

  function renderDraftMembers() {
    const host = $("swarm-roster-editor");
    if (!host) return;
    host.replaceChildren();
    draftMembers.forEach((member, index) => {
      const card = el("div", undefined, "swarm-member-draft");
      const top = el("div", undefined, "swarm-member-draft-row");
      const nameInput = el("input");
      nameInput.value = member.name || "";
      nameInput.required = true;
      SimjectureI18n.attribute(nameInput, "placeholder", () =>
        SimjectureI18n.t("workspace.swarm.memberNamePlaceholder"),
      );
      nameInput.oninput = () => {
        member.name = nameInput.value;
      };
      const roleSelect = el("select");
      for (const role of ROLES) {
        roleSelect.add(
          SimjectureI18n.bindText(new Option("", role), () =>
            SimjectureI18n.t(`workspace.swarm.role.${role}`),
          ),
        );
      }
      roleSelect.value = ROLES.includes(member.role) ? member.role : "worker";
      roleSelect.onchange = () => {
        member.role = roleSelect.value;
      };
      const removeBtn = el("button", "×", "quiet");
      removeBtn.type = "button";
      removeBtn.disabled = draftMembers.length <= 1;
      SimjectureI18n.attribute(removeBtn, "aria-label", () =>
        SimjectureI18n.t("workspace.swarm.removeMember"),
      );
      removeBtn.onclick = () => {
        draftMembers.splice(index, 1);
        renderDraftMembers();
      };
      top.append(nameInput, roleSelect, removeBtn);

      const taskArea = el("textarea");
      taskArea.rows = 2;
      taskArea.required = true;
      taskArea.value = member.task || "";
      SimjectureI18n.attribute(taskArea, "placeholder", () =>
        SimjectureI18n.t("workspace.swarm.memberTaskPlaceholder"),
      );
      taskArea.oninput = () => {
        member.task = taskArea.value;
      };

      const outputsInput = el("input");
      outputsInput.value = (member.outputs || []).join(", ");
      outputsInput.required = true;
      SimjectureI18n.attribute(outputsInput, "placeholder", () =>
        SimjectureI18n.t("workspace.swarm.memberOutputsPlaceholder"),
      );
      outputsInput.oninput = () => {
        member.outputs = outputsInput.value
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);
      };

      const depsInput = el("input");
      depsInput.value = (member.depends_on || []).join(", ");
      SimjectureI18n.attribute(depsInput, "placeholder", () =>
        SimjectureI18n.t("workspace.swarm.memberDepsPlaceholder"),
      );
      depsInput.oninput = () => {
        member.depends_on = depsInput.value
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);
      };

      card.append(top, taskArea, outputsInput, depsInput);
      host.append(card);
    });
  }


  async function submitLaunchDialog() {
    const p = ctx?.project();
    if (!p) return;
    const errEl = $("swarm-launch-error");
    errEl.hidden = true;
    const title = $("swarm-title-input").value.trim() || SimjectureI18n.t("workspace.swarm.defaultTitle");
    const objective = $("swarm-objective-input").value.trim();
    // i18n-technical-start: fallback completion criteria sent to worker agents
    const members = draftMembers.map((m) => ({
      name: (m.name || "").trim(),
      role: m.role || "worker",
      task: (m.task || "").trim(),
      completion_criteria:
        (m.completion_criteria || "").trim() ||
        `Deliver validated outputs: ${(m.outputs || []).join(", ")}`,
      outputs: m.outputs || [],
      depends_on: m.depends_on || [],
    }));
    // i18n-technical-end
    try {
      const created = await ctx.api("swarm-launch", {
        project: p.id,
        title,
        objective,
        strategy: activePreset,
        members,
        wait: false,
      });
      $("swarm-launch-dialog")?.close();
      selectedSwarmId = created.id;
      detailCache = created;
      detailSignature = "";
      listSignature = "";
      window.WorkspacePanels?.set("right", false);
      $("inspector-tabs")?.setAttribute("active", "swarm");
      await ctx.refreshProject(p.id);
      await updateDetail();
      ctx.notify(SimjectureI18n.message("workspace.swarm.launchedNotice", { title: created.title }));
    } catch (error) {
      SimjectureI18n.content(errEl, error.message);
      errEl.hidden = false;
    }
  }

  function render(p) {
    if (!p || !ctx) return;
    const swarms = p.swarms || [];
    if (currentProject !== p.id) {
      currentProject = p.id;
      selectedSwarmId = null;
      detailCache = null;
      detailSignature = "";
      listSignature = "";
      boardRecipient = "all";
    }
    const activeWorkers = swarms.reduce((acc, s) => acc + (s.counts?.active || 0), 0);
    const totalWorkers = swarms.reduce((acc, s) => acc + (s.counts?.total || 0), 0);
    const badge = $("swarm-count");
    if (badge) {
      SimjectureI18n.content(
        badge,
        activeWorkers
          ? SimjectureI18n.message("workspace.subagents.activeCount", { count: activeWorkers })
          : String(totalWorkers),
      );
      badge.classList.toggle("is-active", activeWorkers > 0);
    }
    const launchBtn = $("swarm-launch-open");
    if (launchBtn) {
      launchBtn.hidden = ctx.hosted;
      launchBtn.disabled = ctx.readonly() || ctx.hosted;
    }
    const emptyLaunch = $("swarm-empty-launch");
    if (emptyLaunch) {
      emptyLaunch.hidden = ctx.hosted;
      emptyLaunch.disabled = ctx.readonly() || ctx.hosted;
    }
    const enableBtn = $("swarm-enable-mode");
    if (enableBtn) {
      enableBtn.hidden = ctx.hosted || (p.swarm_mode && p.swarm_mode !== "off");
      enableBtn.disabled = ctx.readonly() || ctx.hosted;
    }
    const modeIndicator = $("swarm-mode-indicator");
    if (modeIndicator) {
      const mode = p.swarm_mode || "off";
      modeIndicator.hidden = ctx.hosted || mode === "off";
      if (mode !== "off") {
        const modeKey =
          mode === "auto"
            ? "workspace.swarm.modeAuto"
            : `workspace.swarm.strategy.${mode}`;
        SimjectureI18n.bindText(modeIndicator, () =>
          SimjectureI18n.t("workspace.swarm.modeIndicator", { mode: SimjectureI18n.t(modeKey) }),
        );
      }
    }

    if (!swarms.some((s) => s.id === selectedSwarmId)) {
      selectedSwarmId = swarms.find((s) => s.live)?.id || swarms[0]?.id || null;
    }
    const sig = JSON.stringify([
      p.id,
      selectedSwarmId,
      swarms.map((s) => [s.id, s.title, s.status, s.counts]),
    ]);
    if (sig !== listSignature) {
      listSignature = sig;
      const select = $("swarm-select");
      if (select) {
        select.replaceChildren();
        for (const s of swarms) {
          select.add(new Option(`${s.title} (${s.counts?.succeeded || 0}/${s.counts?.total || 0})`, s.id));
        }
        select.hidden = swarms.length === 0;
        if (selectedSwarmId) select.value = selectedSwarmId;
      }
      const empty = $("swarm-empty");
      const content = $("swarm-detail");
      if (empty) empty.hidden = swarms.length > 0;
      if (content) content.hidden = swarms.length === 0;
    }
    if (selectedSwarmId) {
      updateDetail().catch((e) => ctx.notify(e.message, true));
    }
  }


  async function updateDetail() {
    const p = ctx?.project();
    if (!p || !selectedSwarmId || inFlight) return;
    const summary = (p.swarms || []).find((s) => s.id === selectedSwarmId);
    if (!summary) return;
    if (summary.legacy) {
      renderDetail(summary, p);
      return;
    }
    inFlight = true;
    const targetId = selectedSwarmId;
    const projectId = p.id;
    try {
      const detail = await ctx.api(
        `swarm?id=${encodeURIComponent(projectId)}&swarm=${encodeURIComponent(targetId)}`,
      );
      if (ctx.project()?.id !== projectId || selectedSwarmId !== targetId) return;
      detailCache = detail;
      renderDetail(detail, p);
    } finally {
      inFlight = false;
    }
  }

  function renderDetail(swarm, p) {
    const host = $("swarm-detail");
    if (!host) return;
    const sig = JSON.stringify([
      p.id,
      swarm.id,
      swarm.status,
      swarm.counts,
      swarm.members?.map((m) => [
        m.name,
        m.status,
        m.job_id,
        m.handoff?.summary,
        m.deliverables?.map((d) => d.name),
      ]),
      swarm.board?.length,
      swarm.board?.at(-1)?.id,
      boardRecipient,
    ]);
    if (sig === detailSignature) return;
    detailSignature = sig;
    const prevFeed = host.querySelector(".swarm-board-feed");
    const feedPinned =
      !prevFeed || prevFeed.scrollHeight - prevFeed.scrollTop - prevFeed.clientHeight < 28;
    const prevFeedScroll = prevFeed?.scrollTop || 0;
    const prevDraft = host.querySelector(".swarm-board-composer input")?.value || "";

    host.replaceChildren();
    const header = el("div", undefined, "swarm-header-card");
    const top = el("div", undefined, "swarm-header-top");
    top.append(el("h3", swarm.title));
    if (swarm.live && !swarm.legacy && !ctx.readonly()) {
      const stopBtn = el("button", SimjectureI18n.message("workspace.swarm.stopSwarm"), "quiet danger-text");
      stopBtn.type = "button";
      stopBtn.onclick = () =>
        ctx.action(stopBtn, async () => {
          await ctx.api("swarm-control", { project: p.id, swarm: swarm.id, action: "stop_swarm" });
          detailSignature = "";
          await ctx.refreshProject(p.id);
          await updateDetail();
        });
      top.append(stopBtn);
    }
    header.append(top);

    const pills = el("div", undefined, "swarm-meta-pills");
    pills.append(
      el(
        "span",
        SimjectureI18n.live(() => SimjectureI18n.label(swarm.status, swarm.status.replaceAll("_", " "))),
        `swarm-pill ${swarm.status}`,
      ),
      el(
        "span",
        SimjectureI18n.message(`workspace.swarm.strategy.${swarm.strategy}`),
        "swarm-pill",
      ),
      el(
        "span",
        SimjectureI18n.message("workspace.swarm.progressPill", {
          done: swarm.counts?.succeeded || 0,
          total: swarm.counts?.total || 0,
        }),
        "swarm-pill",
      ),
    );
    header.append(pills);
    if (swarm.objective) header.append(el("p", swarm.objective, "swarm-objective"));
    host.append(header);

    const stages = new Map();
    for (const member of swarm.members || []) {
      const stage = Number(member.stage || 0);
      if (!stages.has(stage)) stages.set(stage, []);
      stages.get(stage).push(member);
    }
    for (const [stageIndex, stageMembers] of [...stages.entries()].sort((a, b) => a[0] - b[0])) {
      const group = el("div", undefined, "swarm-stage-group");
      if (stages.size > 1) {
        group.append(
          el(
            "p",
            SimjectureI18n.message("workspace.swarm.stageLabel", { stage: stageIndex + 1 }),
            "swarm-stage-label",
          ),
        );
      }
      for (const member of stageMembers) {
        group.append(renderWorkerCard(member, swarm, p));
      }
      host.append(group);
    }

    if (!swarm.legacy) {
      host.append(renderBoard(swarm, p, prevDraft, feedPinned, prevFeedScroll));
    }
  }


  function renderWorkerCard(member, swarm, p) {
    const card = el(
      "article",
      undefined,
      `swarm-worker-card${member.live ? " is-running" : ""}`,
    );
    card.dataset.worker = member.name;
    const head = el("div", undefined, "swarm-worker-head");
    const title = el("div", undefined, "swarm-worker-title");
    const dot = el("span", undefined, `run-dot ${member.status || "queued"}`);
    const roleClass = ROLES.includes(member.role) ? `role-${member.role}` : "";
    const roleLabel = ROLES.includes(member.role)
      ? SimjectureI18n.message(`workspace.swarm.role.${member.role}`)
      : member.role || "";
    title.append(dot, el("strong", member.name), el("span", roleLabel, `swarm-role-badge ${roleClass}`));
    const stateLabel = el(
      "span",
      SimjectureI18n.live(() =>
        SimjectureI18n.label(member.status || "queued", String(member.status || "queued").replaceAll("_", " ")),
      ),
      `run-state ${member.status || "queued"}`,
    );
    head.append(title, stateLabel);
    card.append(head);

    if (member.depends_on?.length) {
      card.append(
        el(
          "p",
          SimjectureI18n.message("workspace.swarm.dependsOn", { deps: member.depends_on.join(", ") }),
          "swarm-worker-deps",
        ),
      );
    }
    if (member.handoff?.summary) {
      card.append(el("p", member.handoff.summary, "swarm-worker-summary"));
    } else if (member.error) {
      card.append(el("p", member.error, "swarm-worker-summary error-text"));
    }

    if (member.deliverables?.length && member.job_id) {
      const box = el("div", undefined, "swarm-deliverables");
      for (const art of member.deliverables) {
        const chip = el("span", undefined, "swarm-artifact-chip");
        chip.append(el("code", art.name));
        const viewBtn = el("button", SimjectureI18n.message("workspace.files.viewInline"));
        viewBtn.type = "button";
        viewBtn.onclick = () =>
          window.WorkspaceFiles?.open(art.name, { source: "simulation", simulation: member.job_id });
        chip.append(viewBtn);
        if (!ctx.readonly() && !ctx.hosted) {
          const impBtn = el("button", SimjectureI18n.message("workspace.swarm.importArtifact"));
          impBtn.type = "button";
          impBtn.onclick = () =>
            ctx.action(impBtn, async () => {
              await ctx.api("swarm-import", {
                project: p.id,
                swarm: swarm.id,
                worker: member.job_id || member.name,
                files: [art.name],
                overwrite: true,
              });
              await ctx.refreshProject(p.id);
              ctx.notify(SimjectureI18n.message("workspace.swarm.importedNotice", { file: art.name }));
              window.WorkspaceFiles?.open(art.name, { source: "files" });
            });
          chip.append(impBtn);
        }
        box.append(chip);
      }
      card.append(box);
    }

    const actions = el("div", undefined, "swarm-worker-actions");
    if (member.job_id) {
      const inspectBtn = el("button", SimjectureI18n.message("workspace.swarm.inspectWorker"));
      inspectBtn.type = "button";
      inspectBtn.onclick = () => ctx.openSimulation?.(member.job_id);
      actions.append(inspectBtn);
    }
    if (!swarm.legacy && !ctx.readonly() && !ctx.hosted) {
      if (member.live) {
        const steerBtn = el("button", SimjectureI18n.message("workspace.swarm.steerWorker"));
        steerBtn.type = "button";
        steerBtn.onclick = () => focusSteer(member.name);
        const stopBtn = el("button", SimjectureI18n.message("ui.stop"));
        stopBtn.type = "button";
        stopBtn.onclick = () =>
          ctx.action(stopBtn, async () => {
            await ctx.api("swarm-control", {
              project: p.id,
              swarm: swarm.id,
              action: "stop_worker",
              worker_id: member.job_id || member.name,
            });
            detailSignature = "";
            await ctx.refreshProject(p.id);
            await updateDetail();
          });
        actions.append(steerBtn, stopBtn);
      } else if (["failed", "cancelled", "timed_out", "interrupted"].includes(member.status)) {
        const retryBtn = el("button", SimjectureI18n.message("workspace.swarm.retryWorker"));
        retryBtn.type = "button";
        retryBtn.onclick = () =>
          ctx.action(retryBtn, async () => {
            await ctx.api("swarm-control", {
              project: p.id,
              swarm: swarm.id,
              action: "retry_worker",
              worker_id: member.name,
            });
            detailSignature = "";
            await ctx.refreshProject(p.id);
            await updateDetail();
          });
        actions.append(retryBtn);
      }
    }
    if (actions.children.length) card.append(actions);
    return card;
  }

  function renderBoard(swarm, p, prevDraft, feedPinned, prevFeedScroll) {
    const section = el("section", undefined, "swarm-board-section");
    const head = el("div", undefined, "swarm-board-head");
    head.append(
      el("span", SimjectureI18n.message("workspace.swarm.boardTitle")),
      el("span", String((swarm.board || []).length), "count-badge"),
    );
    section.append(head);

    const feed = el("div", undefined, "swarm-board-feed");
    for (const msg of swarm.board || []) {
      const row = el("div", undefined, "swarm-board-msg");
      row.classList.add(`kind-${msg.kind || "finding"}`);
      const meta = el("div", undefined, "swarm-board-msg-meta");
      meta.append(el("strong", msg.sender || ""));
      if (msg.recipient) meta.append(el("span", `→ @${msg.recipient}`));
      if (msg.kind) {
        meta.append(
          el(
            "span",
            SimjectureI18n.live(() => SimjectureI18n.label(msg.kind, msg.kind)),
            "swarm-pill",
          ),
        );
      }
      row.append(meta, el("p", msg.content || "", "swarm-board-msg-body"));
      feed.append(row);
    }
    if (!(swarm.board || []).length) {
      feed.append(el("p", SimjectureI18n.message("workspace.swarm.boardEmpty"), "field-help"));
    }
    section.append(feed);

    if (!ctx.readonly() && !ctx.hosted) {
      const form = el("form", undefined, "swarm-board-composer");
      const row = el("div", undefined, "swarm-board-composer-row");
      const targetSelect = el("select");
      SimjectureI18n.attribute(targetSelect, "aria-label", () =>
        SimjectureI18n.t("workspace.swarm.boardTarget"),
      );
      targetSelect.add(
        SimjectureI18n.bindText(new Option("", "all"), () =>
          SimjectureI18n.t("workspace.swarm.targetAll"),
        ),
      );
      for (const m of swarm.members || []) targetSelect.add(new Option(`@${m.name}`, m.name));
      targetSelect.value = [...targetSelect.options].some((o) => o.value === boardRecipient)
        ? boardRecipient
        : "all";
      targetSelect.onchange = () => {
        boardRecipient = targetSelect.value;
      };
      const input = el("input");
      input.id = "swarm-board-input";
      input.maxLength = 8000;
      input.value = prevDraft;
      SimjectureI18n.attribute(input, "placeholder", () =>
        SimjectureI18n.t("workspace.swarm.boardPlaceholder"),
      );
      const sendBtn = el("button", SimjectureI18n.message("workspace.swarm.boardSend"), "primary");
      sendBtn.type = "submit";
      row.append(targetSelect, input, sendBtn);
      form.append(row);
      form.onsubmit = (event) => {
        event.preventDefault();
        const text = input.value.trim();
        if (!text) return;
        ctx.action(sendBtn, async () => {
          const res = await ctx.api("swarm-message", {
            project: p.id,
            swarm: swarm.id,
            recipient: targetSelect.value,
            message: text,
            kind: "steering",
            mode: "steer",
            steer_live: true,
          });
          input.value = "";
          detailSignature = "";
          await updateDetail();
          const count = res.steered_workers?.length || 0;
          ctx.notify(
            count
              ? SimjectureI18n.message("workspace.swarm.steeredWorkersNotice", { count })
              : SimjectureI18n.message("workspace.swarm.boardPostedNotice"),
          );
        });
      };
      section.append(form);
    }
    requestAnimationFrame(() => {
      feed.scrollTop = feedPinned ? feed.scrollHeight : prevFeedScroll;
    });
    return section;
  }

  function focusSteer(memberName) {
    boardRecipient = memberName;
    detailSignature = "";
    if (detailCache && ctx?.project()) renderDetail(detailCache, ctx.project());
    const input = $("swarm-board-input");
    if (input) {
      input.scrollIntoView({ behavior: "smooth", block: "nearest" });
      input.focus();
    }
  }

  return { init, render, updateDetail, openLaunchDialog };
})();
