"use strict";
window.WorkspaceMonitor = {
  create({ api, project, link, notify, readonly }) {
    const $ = (id) => document.getElementById(id);
    const node = (tag, text, cls) => {
      const n = document.createElement(tag);
      if (text !== undefined) SimjectureI18n.content(n, text);
      if (cls) n.className = cls;
      return n;
    };
    let currentProject = null,
      selected = { simulations: null, commands: null },
      announced = new Set(),
      inFlight = {},
      detailRevision = {},
      visibleCounts = { simulations: 50, commands: 50 },
      listRevision = "";
    const panelFor = (job) =>
      job.kind === "command" ? "commands" : "simulations";
    const prefixFor = (panel) =>
      panel === "commands" ? "command" : "simulation";
    function open(id, { reveal = true } = {}) {
      render(project());
      const job = project()?.simulations?.find((j) => j.id === id);
      if (!job) return;
      const panel = panelFor(job);
      if (reveal) window.WorkspacePanels?.set("right", false);
      selected[panel] = id;
      detailRevision[panel] = "";
      $("inspector-tabs").setAttribute("active", panel);
      render(project());
      return update();
    }
    const subagents = $("subagent-panel");
    let subagentRevision = "";
    document.addEventListener("pointerdown", (event) => {
      if (subagents.open && !subagents.contains(event.target)) subagents.open = false;
    });
    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape" || !subagents.open) return;
      if (subagents.contains(document.activeElement)) $("subagent-toggle").focus();
      subagents.open = false;
    });
    function renderSubagents(p, jobs, fresh) {
      const tasks = jobs.filter((job) => job.subagent).reverse();
      const revision = JSON.stringify([p.id, tasks.map((j) => [j.id, j.kind, j.name, j.status])]);
      if (revision === subagentRevision) return;
      subagentRevision = revision;
      subagents.hidden = tasks.length === 0;
      if (fresh) subagents.open = true;
      const active = tasks.filter((j) => ["queued", "running"].includes(j.status));
      $("subagent-count").textContent = active.length ? `${active.length} active` : String(tasks.length);
      const list = $("subagent-list");
      const rows = new Map([...list.children].map((a) => [a.dataset.id, a]));
      let cursor = list.firstChild;
      for (const job of tasks) {
        let row = rows.get(job.id);
        if (!row) {
          row = node("a", undefined, "subagent-row");
          row.dataset.id = job.id;
          row.append(node("span"), node("small"));
          row.addEventListener("click", () => {
            subagents.open = false;
            window.WorkspacePanels?.set("right", false);
          });
        }
        row.href = link(p.id, {
          view: "interactive", [job.kind === "command" ? "command" : "simulation"]: job.id,
        });
        row.firstChild.textContent = job.name;
        row.lastChild.textContent = job.status.replaceAll("_", " ");
        row.dataset.status = job.status;
        if (row !== cursor) list.insertBefore(row, cursor);
        cursor = row.nextSibling;
      }
      while (cursor) {
        const next = cursor.nextSibling;
        cursor.remove();
        cursor = next;
      }
    }
    function render(p) {
      if (!p) return;
      const jobs = p.simulations || [];
      if (currentProject !== p.id) {
        currentProject = p.id;
        subagents.open = false;
        $("subagent-list").replaceChildren();
        selected = { simulations: null, commands: null };
        announced = new Set(jobs.map((j) => j.id));
        detailRevision = {};
        visibleCounts = { simulations: 50, commands: 50 };
        for (const panel of ["simulations", "commands"]) {
          const container = $(`${prefixFor(panel)}-detail`);
          container.replaceChildren(
            window.SimjectureI18n.text(node("p", undefined, "monitor-empty"),
              panel === "commands" ? "workspace.noCommandSelected" : "workspace.noSimulationSelected"),
          );
          delete container.dataset.job;
          container.scrollTop = 0;
          $(`${prefixFor(panel)}-list`).scrollTop = 0;
        }
      }
      const simulations = jobs.filter((j) => panelFor(j) === "simulations");
      SimjectureI18n.content($("simulation-count"), simulations.length);
      SimjectureI18n.content($("command-count"), jobs.length - simulations.length);
      $("sidebar-simulations").hidden = !simulations.length;
      for (const panel of ["simulations", "commands"]) {
        const entries = jobs.filter((j) => panelFor(j) === panel);
        if (!entries.some((j) => j.id === selected[panel]))
          selected[panel] =
            [...entries].reverse().find((j) => j.live)?.id ||
            entries.at(-1)?.id ||
            null;
      }
      const newJobs = jobs.filter((job) => !announced.has(job.id));
      renderSubagents(p, jobs, newJobs.some((job) => job.subagent));
      for (const job of newJobs) announced.add(job.id);
      const fresh = newJobs.filter((job) => job.kind === "simulation" && !job.subagent).at(-1);
      if (fresh) {
        selected.simulations = fresh.id;
        detailRevision.simulations = "";
        $("inspector-tabs").setAttribute("active", "simulations");
      }
      const nextList = JSON.stringify([
        p.id,
        selected,
        visibleCounts,
        jobs.map((j) => [j.id, j.name, j.status, j.kind]),
      ]);
      if (nextList !== listRevision) {
        listRevision = nextList;
        const listScroll = {
          simulations: $("simulation-list").scrollTop,
          commands: $("command-list").scrollTop,
        };
        const sidebarScroll = $("sidebar-run-list").scrollTop;
        $("sidebar-run-list").replaceChildren();
        $("simulation-list").replaceChildren();
        $("command-list").replaceChildren();
        const shown = { simulations: 0, commands: 0 };
        for (const job of [...jobs].reverse()) {
          const panel = panelFor(job);
          const inPage = shown[panel]++ < visibleCounts[panel];
          if (!inPage && job.id !== selected[panel]) continue;
          const a = node(
            "a",
            undefined,
            `simulation-item ${job.id === selected[panel] ? "selected" : ""}`,
          );
          a.href = link(p.id, {
            [panel === "commands" ? "command" : "simulation"]: job.id,
            view: "interactive",
          });
          const dot = node("span", undefined, `run-dot ${job.status}`);
          const label = node("span", job.name);
          const status = node("small", SimjectureI18n.live(() => SimjectureI18n.label(job.status, job.status.replaceAll("_", " "))));
          a.append(dot, label, status);
          $(`${prefixFor(panel)}-list`).append(a);
          if (
            panel === "simulations" &&
            $("sidebar-run-list").children.length < 5
          ) {
            const b = a.cloneNode(true);
            b.className = "sidebar-run";
            SimjectureI18n.bindText(b.querySelector("small"), () => SimjectureI18n.label(job.status, job.status.replaceAll("_", " ")));
            b.onclick = () => window.WorkspacePanels?.set("right", false);
            $("sidebar-run-list").append(b);
          }
        }
        for (const panel of ["simulations", "commands"]) {
          const remaining = shown[panel] - visibleCounts[panel];
          if (remaining <= 0) continue;
          const more = node(
            "button",
            SimjectureI18n.live(() => SimjectureI18n.t("ui.show-more", {p0: Math.min(50, remaining), p1: SimjectureI18n.t(panel === "commands" ? "ui.commands" : "ui.simulations")})),
            "quiet load-more-runs",
          );
          more.type = "button";
          more.onclick = () => {
            visibleCounts[panel] += 50;
            render(project());
          };
          $(`${prefixFor(panel)}-list`).append(more);
        }
        for (const panel of ["simulations", "commands"])
          $(`${prefixFor(panel)}-list`).scrollTop = listScroll[panel];
        $("sidebar-run-list").scrollTop = sidebarScroll;
      }
      update().catch((e) => notify(e.message, true));
    }
    async function update() {
      await Promise.all(["simulations", "commands"].map(updatePanel));
    }
    function renderFiles(container, job, p, identifier) {
      const revision = JSON.stringify([
        job.kind,
        job.native,
        job.files,
        job.console_logs,
        job.file_provenance,
      ]);
      if (container.dataset.revision === revision) return;
      const inputsOpen = container.querySelector(".run-inputs")?.open || false;
      container.dataset.revision = revision;
      container.replaceChildren();
      const shared = job.file_provenance === "shared" ||
        (job.kind === "command" && !job.file_provenance);
      const command = job.kind === "command";
      const inputs = new Set(job.inputs || []);
      const rows = (job.files || []).map((file) => ({
        ...file,
        role:
          file.role ||
          (shared ? "shared" : inputs.has(file.name) ? "input" : "output"),
      }));
      const appendFiles = (target, entries, previews) => {
        for (const file of entries) {
          const row = node("div");
          row.dataset.file = file.name;
          const source = `simulation:${identifier}/${file.name}`;
          if (previews) {
            const figure = window.WorkspaceRich.figure(source, file.name, p);
            if (figure) row.append(figure);
          }
          const a = node("a", file.name, "file-row");
          a.href = window.WorkspaceRich.artifactURL(source, p, false);
          row.append(a);
          if (file.role === "modified_input")
            row.append(
              node("small", SimjectureI18n.message("ui.changed-from-the-copied-input"), "field-help"),
            );
          target.append(row);
        }
      };
      const outputs = node(
        "div", undefined, shared ? "run-shared-files" : "run-outputs",
      );
      outputs.append(
        node("h4", SimjectureI18n.live(() => shared ? SimjectureI18n.t("ui.conversation-files-shared") : (command ? SimjectureI18n.t("ui.command-outputs") : SimjectureI18n.t("ui.run-outputs")))),
        node(
          "p",
          SimjectureI18n.live(() => shared ? SimjectureI18n.t("ui.this-job-used-the-shared-project-folder-these-files-are-not-specific") : (command ? SimjectureI18n.t("ui.files-retained-from-this-command-s-isolated-workspace") : SimjectureI18n.t("ui.files-created-or-changed-in-this-simulation-s-workspace"))),
          "field-help",
        ),
      );
      const results = rows.filter((file) => file.role !== "input");
      appendFiles(outputs, results, !shared);
      if (!results.length)
        outputs.append(
          node(
            "p",
            SimjectureI18n.live(() => shared ? SimjectureI18n.t("ui.no-project-files-listed") : SimjectureI18n.t("ui.no-run-outputs-saved-yet")),
            "field-help",
          ),
        );
      container.append(outputs);
      if (job.console_logs?.length) {
        const logs = node("details"); logs.append(node("summary", SimjectureI18n.message("ui.complete-console-logs")));
        appendFiles(logs, job.console_logs, false); container.append(logs);
      }
      const copied = rows.filter((file) => file.role === "input");
      if (copied.length) {
        const details = node("details", undefined, "run-inputs");
        details.open = inputsOpen;
        details.append(node("summary", SimjectureI18n.live(() => SimjectureI18n.t("ui.copied-inputs", {p0: copied.length}))));
        details.append(
          node(
            "p",
            SimjectureI18n.message("ui.conversation-files-copied-when-this-run-started-they-can-include-rep"),
            "field-help",
          ),
        );
        if (job.file_provenance === "paths_only")
          details.append(
            node(
              "p",
              SimjectureI18n.message("ui.this-older-run-recorded-input-paths-only-changes-to-those-input-file"),
              "field-help",
            ),
          );
        appendFiles(details, copied, false);
        container.append(details);
      }
    }
    async function updatePanel(panel) {
      const p = project();
      if (!p || !selected[panel] || inFlight[panel]) return;
      const identifier = selected[panel],
        projectId = p.id;
      const observed = p.simulations?.find((j) => j.id === identifier);
      if (!observed) return;
      inFlight[panel] = true;
      try {
        const job = observed.native
          ? observed
          : await api(
              `simulation?id=${encodeURIComponent(p.id)}&simulation=${encodeURIComponent(identifier)}`,
            );
        if (project()?.id !== projectId || selected[panel] !== identifier)
          return;
        const revision = JSON.stringify([
          projectId,
          identifier,
          job.status,
          job.kind,
          job.output,
          job.files,
          job.file_provenance,
          job.error,
        ]);
        if (revision === detailRevision[panel]) return;
        detailRevision[panel] = revision;
        const container = $(`${prefixFor(panel)}-detail`);
        const key = `${projectId}/${identifier}`;
        if (container.dataset.job !== key) {
          container.replaceChildren();
          container.dataset.job = key;
          const header = node("div", undefined, "run-heading");
          header.append(node("h3", job.name), node("span", "", "run-state"));
          const meta = node("div", undefined, "run-meta");
          meta.append(
            node("span", "", "run-elapsed"),
            node(
              "span",
              job.native
                ? SimjectureI18n.message("ui.cli-managed-command")
                : job.subagent
                  ? "Isolated subagent"
                  : SimjectureI18n.message("ui.interactive-exploration"),
            ),
          );
          const command = node("details");
          command.append(
            node("summary", SimjectureI18n.message("ui.command-location")),
            node("pre", job.command || ""),
            node("code", SimjectureI18n.live(() => job.work_directory || SimjectureI18n.t("ui.conversation-files"))),
          );
          const title = node("div", undefined, "console-heading");
          title.append(node("span", SimjectureI18n.message("ui.live-console")));
          const stop = node(
            "button",
            SimjectureI18n.live(() => panel === "commands" ? SimjectureI18n.t("ui.stop-command") : SimjectureI18n.t("ui.stop-run")),
            "quiet stop-run",
          );
          stop.onclick = async () => {
            stop.disabled = true;
            try {
              notify(
                (
                  await api("stop-simulation", {
                    project: projectId,
                    simulation: identifier,
                  })
                ).message,
              );
            } catch (e) {
              notify(e.message, true);
            }
          };
          title.append(stop);
          const classify = node(
            "button",
            SimjectureI18n.live(() => panel === "commands" ? SimjectureI18n.t("ui.move-to-simulations") : SimjectureI18n.t("ui.move-to-commands")),
            "quiet classify-run",
          );
          classify.onclick = async () => {
            classify.disabled = true;
            try {
              const kind = job.kind === "command" ? "simulation" : "command";
              const updated = await api("classify-simulation", {
                project: projectId, simulation: identifier, kind,
              });
              if (project()?.id === projectId) {
                const current = project();
                current.simulations = current.simulations.map((j) => j.id === identifier ? updated : j);
                selected[panel] = null;
                render(current);
                location.hash = link(projectId, {view: "interactive", [kind]: identifier});
                await open(identifier);
              }
              notify(kind === "simulation" ? SimjectureI18n.live(() => SimjectureI18n.t("ui.moved-to-simulations")) : SimjectureI18n.live(() => SimjectureI18n.t("ui.moved-to-commands")));
            } catch (e) {
              notify(e.message, true);
            } finally {
              classify.disabled = readonly();
            }
          };
          title.append(classify);
          const output = node("pre", "", "live-console");
          SimjectureI18n.attribute(output, "aria-label", () => panel === "commands" ? SimjectureI18n.t("ui.command-console") : SimjectureI18n.t("ui.simulation-console"));
          container.append(
            header,
            meta,
            command,
            title,
            output,
            node("div", undefined, "simulation-files"),
          );
          container.scrollTop = 0;
        }
        const status = container.querySelector(".run-state");
        SimjectureI18n.content(status, SimjectureI18n.live(() => SimjectureI18n.label(job.status, job.status.replaceAll("_", " "))));
        status.className = `run-state ${job.status}`;
        const elapsed = container.querySelector(".run-elapsed");
        if (job.live && job.created_at)
          elapsed.dataset.elapsed = job.created_at;
        else {
          delete elapsed.dataset.elapsed;
          SimjectureI18n.bindText(elapsed, () => job.elapsed_seconds === undefined ? "" : SimjectureI18n.t("ui.s-elapsed", {p0: Math.floor(job.elapsed_seconds)}));
        }
        const stop = container.querySelector(".stop-run");
        stop.hidden = !job.live || job.native;
        stop.disabled = readonly();
        const classify = container.querySelector(".classify-run");
        classify.hidden = job.native || readonly();
        classify.disabled = readonly();
        const output = container.querySelector(".live-console");
        const pinned =
          !output.textContent ||
          output.scrollHeight - output.scrollTop - output.clientHeight < 30;
        const scroll = output.scrollTop;
        const text = (
          job.output ||
          job.error ||
          (panel === "commands"
            ? SimjectureI18n.t("ui.waiting-for-command-output")
            : SimjectureI18n.t("ui.waiting-for-simulation-output"))
        ).replace(/\x1b\[[0-?]*[ -/]*[@-~]/g, "");
        if (output.textContent !== text) {
          SimjectureI18n.bindText(output, () => job.output || job.error ? text : panel === "commands" ? SimjectureI18n.t("ui.waiting-for-command-output") : SimjectureI18n.t("ui.waiting-for-simulation-output"));
          output.scrollTop = pinned ? output.scrollHeight : scroll;
        }
        renderFiles(container.querySelector(".simulation-files"), job, p, identifier);
      } finally {
        inFlight[panel] = false;
      }
    }
    return { render, open, update };
  },
};
