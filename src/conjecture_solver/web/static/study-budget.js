"use strict";

window.StudyBudget = (() => {
  const node = (tag, text, cls) => {
    const result = document.createElement(tag);
    if (text !== undefined) result.textContent = text;
    if (cls) result.className = cls;
    return result;
  };
  const date = (seconds) => new Date(seconds * 1000).toLocaleString();
  const hours = (seconds) => Number((seconds / 3600).toFixed(2));

  function editLimits(options) {
    const dialog = node("dialog", undefined, "study-budget-dialog");
    dialog.setAttribute("aria-label", "Study run settings");
    const form = node("form");
    form.append(node("h2", "Run settings"), node("p", "These operating settings do not extend the campaign deadline or grant more storage, memory, or compute.", "field-help"));
    const fields = {};
    for (const [key, title, help] of [
      ["worker_action_limit", "Actions per worker turn", "Blank allows the worker to continue within the campaign budget."],
      ["worker_checkpoint_seconds", "Worker checkpoint after (seconds)", "Blank avoids a forced interruption. The director reviews progress alongside the worker."],
      ["review_seconds", "Review allowance (seconds)", "Blank uses the study's recorded review or turn allowance. Every review stays within the campaign deadline."],
    ]) {
      const label = node("label", title), input = node("input");
      input.type = "number"; input.min = "1"; input.step = key === "worker_action_limit" ? "1" : "any";
      input.value = options.budget.operating_limits?.[key] ?? "";
      label.append(input); form.append(label, node("p", help, "field-help")); fields[key] = input;
    }
    const why = node("label", "Reason"), reason = node("textarea");
    reason.required = true; reason.maxLength = 2400; reason.rows = 2;
    why.append(reason); form.append(why);
    const error = node("p", "", "form-error"); error.setAttribute("role", "alert"); form.append(error);
    const controls = node("div", undefined, "study-controls");
    const cancel = node("button", "Cancel", "secondary"), save = node("button", "Save settings", "primary");
    cancel.type = "button"; save.type = "submit"; cancel.onclick = () => dialog.close();
    controls.append(cancel, save); form.append(controls);
    let busy = false;
    form.onsubmit = async event => {
      event.preventDefault(); if (busy) return;
      busy = true; save.disabled = true; cancel.disabled = true;
      const limits = Object.fromEntries(Object.entries(fields).map(([k, input]) => [k, input.value === "" ? null : Number(input.value)]));
      try {
        await options.submitLimits({campaign:options.campaign, limits, reason:reason.value});
        dialog.close(); await (options.onLimitsSaved || options.onSaved)();
      } catch (e) { error.textContent = e.message; busy = false; save.disabled = false; cancel.disabled = false; }
    };
    dialog.addEventListener("cancel", event => { if (busy) event.preventDefault(); });
    dialog.addEventListener("close", () => dialog.remove());
    dialog.append(form); document.body.append(dialog); dialog.showModal(); fields.worker_action_limit.focus();
  }

  function open({campaign, budget, request, submit, onSaved}) {
    const dialog = node("dialog", undefined, "study-budget-dialog");
    dialog.setAttribute("aria-label", "Extend study time");
    const form = node("form");
    form.append(node("h2", "Extend study time"), node("p", "Add time to this investigation. The agent keeps its context and evidence, and the running computation continues.", "field-help"));
    const label = node("label", "Additional hours");
    const amount = node("input");
    amount.type = "number"; amount.min = "0.01"; amount.step = "0.01";
    amount.required = true; amount.value = String(request?.hours || 6);
    label.append(amount); form.append(label);
    const presets = node("div", undefined, "study-budget-presets");
    for (const value of [1, 6, 12]) {
      const button = node("button", `+${value} h`, "secondary"); button.type = "button";
      button.onclick = () => { amount.value = String(value); preview(); };
      presets.append(button);
    }
    form.append(presets);
    const summary = node("dl", undefined, "study-budget-preview");
    const old = node("dd", date(budget.deadline)); const next = node("dd");
    summary.append(node("dt", "Current deadline"), old, node("dt", "New deadline"), next);
    form.append(summary);
    form.append(node("p", `Times shown in ${Intl.DateTimeFormat().resolvedOptions().timeZone}.`, "field-help"));
    const reasonLabel = node("label", "Reason (optional)");
    const reason = node("textarea"); reason.rows = 2; reason.maxLength = 2400;
    reason.value = request?.reason || ""; reasonLabel.append(reason); form.append(reasonLabel);
    form.append(node("p", "This adds wall time and may use more model credit and compute. The director is notified to update its plan. The report reserve and each experiment’s own timeout stay in place.", "field-help"));
    if (budget.experiment_limits?.length) {
      const limits = node("details"); limits.append(node("summary", "Active experiment limits"));
      for (const experiment of budget.experiment_limits) {
        const deadline = experiment.started_at && experiment.timeout
          ? Math.min(experiment.started_at + experiment.timeout, experiment.execution_deadline || Infinity)
          : experiment.execution_deadline;
        limits.append(node("p", `${experiment.id}: ${deadline ? date(deadline) : "recorded job limit unchanged"}`, "field-help"));
      }
      form.append(limits);
    }
    const error = node("p", "", "form-error"); error.setAttribute("role", "alert"); form.append(error);
    const controls = node("div", undefined, "study-controls");
    const cancel = node("button", "Cancel", "secondary"); cancel.type = "button";
    const confirm = node("button"); confirm.type = "submit";
    cancel.onclick = () => dialog.close(); controls.append(cancel, confirm); form.append(controls);
    function preview() {
      const value = Number(amount.value);
      const valid = value > 0 && Number.isFinite(new Date((budget.deadline + value * 3600) * 1000).getTime());
      next.textContent = valid ? date(budget.deadline + value * 3600) : "Choose additional time";
      confirm.disabled = !valid;
      confirm.textContent = `Add ${value > 0 ? value : ""} hours`;
    }
    amount.oninput = preview; preview();
    const key = crypto.randomUUID();
    let busy = false;
    form.onsubmit = async (event) => {
      event.preventDefault(); if (busy) return;
      busy = true; confirm.disabled = true; cancel.disabled = true;
      try {
        const result = await submit({campaign, hours:Number(amount.value), reason:reason.value,
          request_key:key, expected_deadline:budget.deadline,
          ...(request ? {request_id:request.id} : {})});
        dialog.close(); await onSaved(result);
      } catch (e) {
        error.textContent = e.message;
        busy = false; confirm.disabled = false; cancel.disabled = false;
      }
    };
    dialog.addEventListener("cancel", event => { if (busy) event.preventDefault(); });
    const routeChanged = () => { if (!busy && dialog.open) dialog.close(); };
    window.addEventListener("hashchange", routeChanged);
    dialog.addEventListener("close", () => { window.removeEventListener("hashchange", routeChanged); dialog.remove(); });
    dialog.append(form); document.body.append(dialog); dialog.showModal(); amount.focus();
  }

  function render(container, options) {
    const wasOpen = container.querySelector("details[data-budget-history]")?.open;
    container.replaceChildren();
    const {budget, readonly} = options;
    if (!budget?.supported) return;
    container.classList.add("study-budget");
    const row = node("div", undefined, "study-budget-heading");
    row.append(node("span", `Deadline · ${date(budget.deadline)}`, "field-help"));
    if (!readonly && options.submitLimits && budget.operating_limits && budget.remaining_seconds > 0) {
      const settings = node("button", "Run settings", "secondary"); settings.type = "button";
      settings.onclick = () => editLimits(options); row.append(settings);
    }
    if (budget.can_extend && !readonly) {
      const extend = node("button", "Extend time", "secondary"); extend.type = "button";
      extend.onclick = () => open(options); row.append(extend);
    }
    container.append(row);
    for (const request of budget.requests || []) {
      if (request.status !== "pending") continue;
      const line = node("div", undefined, "study-budget-request");
      line.append(node("p", `${request.requested_by === "director" ? "Director" : "Worker"} requests ${request.hours} more hours: ${request.reason}`));
      if (budget.can_extend && !readonly) {
        const review = node("button", "Review time request", "secondary"); review.type = "button";
        review.onclick = () => open({...options, request}); line.append(review);
      }
      container.append(line);
    }
    if (budget.extensions?.length) {
      const history = node("details");
      history.dataset.budgetHistory = ""; history.dataset.key = `budget-${options.campaign}`;
      history.open = !!wasOpen;
      history.append(node("summary", `Budget history · ${budget.extensions.length} ${budget.extensions.length === 1 ? "extension" : "extensions"}`));
      for (const extension of budget.extensions) {
        history.append(node("p", `+${hours(extension.additional_seconds)} h · ${extension.actor || "operator"} · deadline ${date(extension.new_deadline)}${extension.reason ? ` · ${extension.reason}` : ""}`, "field-help"));
      }
      container.append(history);
    }
  }
  return {open, render};
})();
