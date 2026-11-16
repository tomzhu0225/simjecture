"use strict";

window.StudyBudget = (() => {
  const node = (tag, text, cls) => {
    const result = document.createElement(tag);
    if (text !== undefined) SimjectureI18n.content(result, text);
    if (cls) result.className = cls;
    return result;
  };
  const date = (seconds) => new Date(seconds * 1000).toLocaleString();
  const hours = (seconds) => Number((seconds / 3600).toFixed(2));

  function editLimits(options) {
    const dialog = node("dialog", undefined, "study-budget-dialog");
    SimjectureI18n.attribute(dialog, "aria-label", () => SimjectureI18n.t("ui.study-run-settings"));
    const form = node("form");
    form.append(node("h2", SimjectureI18n.message("ui.run-settings")), node("p", SimjectureI18n.message("ui.these-operating-settings-do-not-extend-the-campaign-deadline-or-gran"), "field-help"));
    const fields = {};
    for (const [key, title, help] of [
      ["worker_action_limit", SimjectureI18n.message("ui.actions-per-worker-turn"), SimjectureI18n.message("ui.blank-allows-the-worker-to-continue-within-the-campaign-budget")],
      ["worker_checkpoint_seconds", SimjectureI18n.message("ui.worker-checkpoint-after-seconds"), SimjectureI18n.message("ui.blank-avoids-a-forced-interruption-the-director-reviews-progress-alo")],
      ["review_seconds", SimjectureI18n.message("ui.review-allowance-seconds"), SimjectureI18n.message("ui.blank-uses-the-study-s-recorded-review-or-turn-allowance-every-revie")],
    ]) {
      const label = node("label", title), input = node("input");
      input.type = "number"; input.min = "1"; input.step = key === "worker_action_limit" ? "1" : "any";
      input.value = options.budget.operating_limits?.[key] ?? "";
      label.append(input); form.append(label, node("p", help, "field-help")); fields[key] = input;
    }
    const why = node("label", SimjectureI18n.message("ui.reason")), reason = node("textarea");
    reason.required = true; reason.maxLength = 2400; reason.rows = 2;
    why.append(reason); form.append(why);
    const error = node("p", "", "form-error"); error.setAttribute("role", "alert"); form.append(error);
    const controls = node("div", undefined, "study-controls");
    const cancel = node("button", SimjectureI18n.message("ui.cancel"), "secondary"), save = node("button", SimjectureI18n.message("ui.save-settings"), "primary");
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
      } catch (e) { SimjectureI18n.content(error, e.message); busy = false; save.disabled = false; cancel.disabled = false; }
    };
    dialog.addEventListener("cancel", event => { if (busy) event.preventDefault(); });
    dialog.addEventListener("close", () => dialog.remove());
    dialog.append(form); document.body.append(dialog); dialog.showModal(); fields.worker_action_limit.focus();
  }

  function open({campaign, budget, request, submit, onSaved}) {
    const dialog = node("dialog", undefined, "study-budget-dialog");
    SimjectureI18n.attribute(dialog, "aria-label", () => SimjectureI18n.t("ui.extend-study-time"));
    const form = node("form");
    form.append(node("h2", SimjectureI18n.message("ui.extend-study-time")), node("p", SimjectureI18n.message("ui.add-time-to-this-investigation-the-agent-keeps-its-context-and-evide"), "field-help"));
    const label = node("label", SimjectureI18n.message("ui.additional-hours"));
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
    summary.append(node("dt", SimjectureI18n.message("ui.current-deadline")), old, node("dt", SimjectureI18n.message("ui.new-deadline")), next);
    form.append(summary);
    form.append(node("p", SimjectureI18n.live(() => SimjectureI18n.t("ui.times-shown-in", {p0: Intl.DateTimeFormat().resolvedOptions().timeZone})), "field-help"));
    const reasonLabel = node("label", SimjectureI18n.message("ui.reason-optional"));
    const reason = node("textarea"); reason.rows = 2; reason.maxLength = 2400;
    reason.value = request?.reason || ""; reasonLabel.append(reason); form.append(reasonLabel);
    form.append(node("p", SimjectureI18n.message("ui.this-adds-wall-time-and-may-use-more-model-credit-and-compute-the-di"), "field-help"));
    if (budget.experiment_limits?.length) {
      const limits = node("details"); limits.append(node("summary", SimjectureI18n.message("ui.active-experiment-limits")));
      for (const experiment of budget.experiment_limits) {
        const deadline = experiment.started_at && experiment.timeout
          ? Math.min(experiment.started_at + experiment.timeout, experiment.execution_deadline || Infinity)
          : experiment.execution_deadline;
        limits.append(node("p", SimjectureI18n.live(() => `${experiment.id}: ${(deadline ? date(deadline) : SimjectureI18n.t("ui.recorded-job-limit-unchanged"))}`), "field-help"));
      }
      form.append(limits);
    }
    const error = node("p", "", "form-error"); error.setAttribute("role", "alert"); form.append(error);
    const controls = node("div", undefined, "study-controls");
    const cancel = node("button", SimjectureI18n.message("ui.cancel"), "secondary"); cancel.type = "button";
    const confirm = node("button"); confirm.type = "submit";
    cancel.onclick = () => dialog.close(); controls.append(cancel, confirm); form.append(controls);
    function preview() {
      const value = Number(amount.value);
      const valid = value > 0 && Number.isFinite(new Date((budget.deadline + value * 3600) * 1000).getTime());
      SimjectureI18n.bindText(next, () => valid ? date(budget.deadline + value * 3600) : SimjectureI18n.t("ui.choose-additional-time"));
      confirm.disabled = !valid;
      SimjectureI18n.bindText(confirm, () => SimjectureI18n.t("ui.add-hours", {p0: (value > 0 ? value : "")}));
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
        SimjectureI18n.content(error, e.message);
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
    row.append(node("span", SimjectureI18n.live(() => SimjectureI18n.t("ui.deadline", {p0: date(budget.deadline)})), "field-help"));
    if (!readonly && options.submitLimits && budget.operating_limits && budget.remaining_seconds > 0) {
      const settings = node("button", SimjectureI18n.message("ui.run-settings"), "secondary"); settings.type = "button";
      settings.onclick = () => editLimits(options); row.append(settings);
    }
    if (budget.can_extend && !readonly) {
      const extend = node("button", SimjectureI18n.message("ui.extend-time"), "secondary"); extend.type = "button";
      extend.onclick = () => open(options); row.append(extend);
    }
    container.append(row);
    for (const request of budget.requests || []) {
      if (request.status !== "pending") continue;
      const line = node("div", undefined, "study-budget-request");
      line.append(node("p", SimjectureI18n.live(() => SimjectureI18n.t("ui.requests-more-hours", {p0: (request.requested_by === "director" ? SimjectureI18n.t("ui.director") : SimjectureI18n.t("ui.worker")), p1: request.hours, p2: request.reason}))));
      if (budget.can_extend && !readonly) {
        const review = node("button", SimjectureI18n.message("ui.review-time-request"), "secondary"); review.type = "button";
        review.onclick = () => open({...options, request}); line.append(review);
      }
      container.append(line);
    }
    if (budget.extensions?.length) {
      const history = node("details");
      history.dataset.budgetHistory = ""; history.dataset.key = `budget-${options.campaign}`;
      history.open = !!wasOpen;
      history.append(node("summary", SimjectureI18n.live(() => SimjectureI18n.t("ui.budget-history", {p0: budget.extensions.length, p1: (budget.extensions.length === 1 ? SimjectureI18n.t("ui.extension") : SimjectureI18n.t("ui.extensions"))}))));
      for (const extension of budget.extensions) {
        history.append(node("p", SimjectureI18n.live(() => SimjectureI18n.t("ui.h-deadline", {p0: hours(extension.additional_seconds), p1: (extension.actor || SimjectureI18n.t("ui.operator")), p2: date(extension.new_deadline), p3: (extension.reason ? ` · ${extension.reason}` : "")})), "field-help"));
      }
      container.append(history);
    }
  }
  return {open, render};
})();
