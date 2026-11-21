/* Codex-style instant mid-turn direct steering and follow-up queue UI. */
"use strict";
window.WorkspaceSteering = (() => {
  let ctx = null;
  let selectedMode = "steer"; // "steer" | "interrupt" | "queue"
  let queueSignature = "";
  let pendingKey = null;

  const $ = (id) => document.getElementById(id);
  const el = (tag, text, cls) => {
    const node = document.createElement(tag);
    if (text !== undefined) SimjectureI18n.content(node, text);
    if (cls) node.className = cls;
    return node;
  };

  function init(options) {
    ctx = options;
    for (const btn of document.querySelectorAll("[data-steer-mode]")) {
      btn.onclick = () => {
        selectedMode = btn.dataset.steerMode || "steer";
        updateModeButtons();
        updateComposerControls(ctx.project());
      };
    }
    const steerButton = $("steer-message");
    if (steerButton) {
      steerButton.onclick = () => {
        ctx.action(steerButton, () => submit(selectedMode));
      };
    }
    updateModeButtons();
  }

  function updateModeButtons() {
    for (const btn of document.querySelectorAll("[data-steer-mode]")) {
      btn.setAttribute("aria-pressed", String(btn.dataset.steerMode === selectedMode));
    }
  }

  function modeLabelKey(mode) {
    if (mode === "interrupt") return "workspace.steering.interruptButton";
    if (mode === "queue") return "workspace.steering.queueButton";
    return "workspace.steering.steerButton";
  }

  function updateComposerControls(p) {
    const canSteer = Boolean(p && p.running && !ctx.hosted && !ctx.readonly());
    const panel = $("steering-panel");
    const bar = $("steering-bar");
    const sendBtn = $("send-message");
    const steerBtn = $("steer-message");
    const input = $("chat-input");
    const queued = p?.steering?.queued || [];
    const active = (p?.steering?.active || []).filter((item) => item.status !== "cancelled");

    if (panel) panel.hidden = !canSteer && queued.length === 0;
    if (bar) bar.hidden = !canSteer;
    if (sendBtn && steerBtn) {
      sendBtn.hidden = canSteer;
      steerBtn.hidden = !canSteer;
      steerBtn.disabled = !canSteer;
      steerBtn.classList.toggle("is-interrupt", selectedMode === "interrupt");
      SimjectureI18n.bindText(steerBtn, () => SimjectureI18n.t(modeLabelKey(selectedMode)));
      SimjectureI18n.attribute(steerBtn, "title", () =>
        SimjectureI18n.t(modeLabelKey(selectedMode)),
      );
    }
    if (input) {
      SimjectureI18n.attribute(input, "placeholder", () =>
        SimjectureI18n.t(
          canSteer ? "workspace.steering.placeholder" : "workspace.chatPlaceholder",
        ),
      );
    }
    renderQueue(p, active, queued);
  }


  function renderQueue(p, active, queued) {
    const host = $("steering-queue");
    if (!host) return;
    const items = [
      ...active.slice(-4).map((item) => ({ ...item, bucket: "active" })),
      ...queued.map((item) => ({ ...item, bucket: "queued" })),
    ];
    const sig = JSON.stringify([
      p?.id,
      items.map((i) => [i.id, i.mode, i.status, i.message, i.bucket]),
    ]);
    if (sig === queueSignature) return;
    queueSignature = sig;
    host.replaceChildren();
    host.hidden = items.length === 0;
    for (const item of items) {
      const chip = el("div", undefined, "steering-chip");
      chip.dataset.steerId = item.id;
      const badgeClass =
        item.status === "applied"
          ? "applied"
          : item.mode === "interrupt"
            ? "interrupt"
            : item.mode;
      const badgeKey =
        item.status === "applied"
          ? "workspace.steering.statusApplied"
          : item.bucket === "queued"
            ? "workspace.steering.statusQueued"
            : item.mode === "interrupt"
              ? "workspace.steering.statusInterrupting"
              : "workspace.steering.statusDelivering";
      chip.append(
        el("span", SimjectureI18n.message(badgeKey), `steering-chip-badge ${badgeClass}`),
        el("span", item.message, "steering-chip-text"),
      );
      if (item.bucket === "queued" && !ctx.readonly()) {
        const actions = el("div", undefined, "steering-chip-actions");
        if (p?.running) {
          const promote = el("button", SimjectureI18n.message("workspace.steering.steerNow"));
          promote.type = "button";
          promote.onclick = () =>
            ctx.action(promote, async () => {
              await ctx.api("promote-steer", { project: p.id, id: item.id, mode: "steer" });
              await ctx.refreshProject(p.id);
              ctx.notify(SimjectureI18n.message("workspace.steering.sentDirect"));
            });
          actions.append(promote);
        }
        const cancelBtn = el("button", "×");
        cancelBtn.type = "button";
        SimjectureI18n.attribute(cancelBtn, "aria-label", () =>
          SimjectureI18n.t("workspace.steering.removeQueued"),
        );
        cancelBtn.onclick = () =>
          ctx.action(cancelBtn, async () => {
            await ctx.api("cancel-steer", { project: p.id, id: item.id });
            await ctx.refreshProject(p.id);
          });
        actions.append(cancelBtn);
        chip.append(actions);
      }
      host.append(chip);
    }
  }

  async function submit(modeOverride) {
    const p = ctx.project();
    const input = $("chat-input");
    if (!p || !input) return;
    const draft = input.value;
    const message = draft.trim();
    if (!message) return;
    const mode = modeOverride || selectedMode;
    pendingKey ||= crypto.randomUUID();
    const key = pendingKey;
    const result = await ctx.api("steer", {
      project: p.id,
      message,
      mode,
      request_key: key,
    });
    pendingKey = null;
    if (ctx.project()?.id === p.id && input.value === draft) {
      input.value = "";
      globalThis.WorkspaceComposer?.update("chat-input");
    }
    const toastKey =
      result.mode === "queue"
        ? "workspace.steering.queuedNotice"
        : result.mode === "interrupt"
          ? "workspace.steering.interruptNotice"
          : "workspace.steering.sentDirect";
    ctx.notify(SimjectureI18n.message(toastKey));
    await ctx.refreshProject(p.id);
  }

  function renderTimelineMarkers(article, events) {
    const steers = (events || []).filter((e) => e.type === "steer" || e.type === "steer_applied");
    if (!steers.length) return;
    const appliedIds = new Set(steers.filter((e) => e.type === "steer_applied").map((e) => e.id));
    const seen = new Set();
    for (const event of steers) {
      if (event.type !== "steer" || seen.has(event.id)) continue;
      seen.add(event.id);
      const isInterrupt = event.mode === "interrupt";
      const marker = el("div", undefined, `steer-timeline-marker${isInterrupt ? " is-interrupt" : ""}`);
      const labelKey = appliedIds.has(event.id)
        ? isInterrupt
          ? "workspace.steering.markerInterruptApplied"
          : "workspace.steering.markerApplied"
        : isInterrupt
          ? "workspace.steering.markerInterruptPending"
          : "workspace.steering.markerPending";
      const box = el("div");
      box.append(el("strong", SimjectureI18n.message(labelKey)), el("p", event.message || ""));
      marker.append(box);
      article.append(marker);
    }
  }

  function isActive() {
    const p = ctx?.project();
    return Boolean(p && p.running && !ctx.hosted && !ctx.readonly());
  }

  function submitFromKeyboard(urgent = false) {
    const btn = $("steer-message");
    if (!btn || btn.disabled) return;
    ctx.action(btn, () => submit(urgent ? "interrupt" : selectedMode));
  }

  return { init, render: updateComposerControls, renderTimelineMarkers, isActive, submitFromKeyboard };
})();
