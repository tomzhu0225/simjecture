"use strict";
window.WorkspaceMonitor = {
  create({ api, project, link, notify, readonly }) {
    const $ = (id) => document.getElementById(id);
    const node = (tag, text, cls) => {
      const n = document.createElement(tag);
      if (text !== undefined) n.textContent = text;
      if (cls) n.className = cls;
      return n;
    };
    let currentProject = null,
      selected = { simulations: null, commands: null },
      announced = new Set(),
      inFlight = {},
      detailRevision = {},
      listRevision = "";
    const panelFor = (job) =>
      job.kind === "command" ? "commands" : "simulations";
    const prefixFor = (panel) =>
      panel === "commands" ? "command" : "simulation";
    function open(id) {
      render(project());
      const job = project()?.simulations?.find((j) => j.id === id);
      if (!job) return;
      const panel = panelFor(job);
      selected[panel] = id;
      detailRevision[panel] = "";
      $("inspector-tabs").setAttribute("active", panel);
      render(project());
      return update();
    }
    function render(p) {
      if (!p) return;
      const jobs = p.simulations || [];
      if (currentProject !== p.id) {
        currentProject = p.id;
        selected = { simulations: null, commands: null };
        announced = new Set(jobs.map((j) => j.id));
        detailRevision = {};
        for (const panel of ["simulations", "commands"]) {
          const container = $(`${prefixFor(panel)}-detail`);
          container.replaceChildren(
            node(
              "p",
              panel === "commands"
                ? "No command selected."
                : "No simulation selected.",
              "monitor-empty",
            ),
          );
          delete container.dataset.job;
        }
      }
      const simulations = jobs.filter((j) => panelFor(j) === "simulations");
      $("simulation-count").textContent = simulations.length;
      $("command-count").textContent = jobs.length - simulations.length;
      $("sidebar-simulations").hidden = !simulations.length;
      for (const panel of ["simulations", "commands"]) {
        const entries = jobs.filter((j) => panelFor(j) === panel);
        if (!entries.some((j) => j.id === selected[panel]))
          selected[panel] =
            [...entries].reverse().find((j) => j.live)?.id ||
            entries.at(-1)?.id ||
            null;
      }
      const fresh = [...simulations]
        .reverse()
        .find((j) => !announced.has(j.id));
      if (fresh) {
        announced.add(fresh.id);
        selected.simulations = fresh.id;
        detailRevision.simulations = "";
        $("inspector-tabs").setAttribute("active", "simulations");
      }
      const nextList = JSON.stringify([
        p.id,
        selected,
        jobs.map((j) => [j.id, j.name, j.status, j.kind]),
      ]);
      if (nextList !== listRevision) {
        listRevision = nextList;
        const inspector = document.querySelector(".project-context");
        const inspectorScroll = inspector.scrollTop;
        const sidebarScroll = $("sidebar-run-list").scrollTop;
        $("sidebar-run-list").replaceChildren();
        $("simulation-list").replaceChildren();
        $("command-list").replaceChildren();
        for (const job of [...jobs].reverse()) {
          const panel = panelFor(job);
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
          const status = node("small", job.status.replaceAll("_", " "));
          a.append(dot, label, status);
          $(`${prefixFor(panel)}-list`).append(a);
          if (
            panel === "simulations" &&
            $("sidebar-run-list").children.length < 5
          ) {
            const b = a.cloneNode(true);
            b.className = "sidebar-run";
            $("sidebar-run-list").append(b);
          }
        }
        inspector.scrollTop = inspectorScroll;
        $("sidebar-run-list").scrollTop = sidebarScroll;
      }
      update().catch((e) => notify(e.message, true));
    }
    async function update() {
      await Promise.all(["simulations", "commands"].map(updatePanel));
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
          job.output,
          job.files,
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
              job.native ? "CLI-managed command" : "Interactive exploration",
            ),
          );
          const command = node("details");
          command.append(
            node("summary", "Command & location"),
            node("pre", job.command || ""),
            node("code", job.work_directory || "Conversation files"),
          );
          const title = node("div", undefined, "console-heading");
          title.append(node("span", "LIVE CONSOLE"));
          const stop = node(
            "button",
            panel === "commands" ? "Stop command" : "Stop run",
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
          const output = node("pre", "", "live-console");
          output.setAttribute(
            "aria-label",
            panel === "commands" ? "Command console" : "Simulation console",
          );
          container.append(
            header,
            meta,
            command,
            title,
            output,
            node("div", undefined, "simulation-files"),
          );
        }
        const status = container.querySelector(".run-state");
        status.textContent = job.status.replaceAll("_", " ");
        status.className = `run-state ${job.status}`;
        const elapsed = container.querySelector(".run-elapsed");
        if (job.live && job.created_at)
          elapsed.dataset.elapsed = job.created_at;
        else {
          delete elapsed.dataset.elapsed;
          elapsed.textContent =
            job.elapsed_seconds === undefined
              ? ""
              : `${Math.floor(job.elapsed_seconds)}s elapsed`;
        }
        const stop = container.querySelector(".stop-run");
        stop.hidden = !job.live || job.native;
        stop.disabled = readonly();
        const output = container.querySelector(".live-console");
        const pinned =
          !output.textContent ||
          output.scrollHeight - output.scrollTop - output.clientHeight < 30;
        const scroll = output.scrollTop;
        const text = (
          job.output ||
          job.error ||
          (panel === "commands"
            ? "Waiting for command output…"
            : "Waiting for simulation output…")
        ).replace(/\x1b\[[0-?]*[ -/]*[@-~]/g, "");
        if (output.textContent !== text) {
          output.textContent = text;
          output.scrollTop = pinned ? output.scrollHeight : scroll;
        }
        const files = container.querySelector(".simulation-files");
        const names = new Set((job.files || []).map((f) => f.name));
        for (const row of files.querySelectorAll("[data-file]")) {
          if (!names.has(row.dataset.file)) row.remove();
        }
        if (names.size && !files.querySelector("h4"))
          files.prepend(node("h4", "Saved files"));
        const existing = new Set(
          [...files.querySelectorAll("[data-file]")].map((e) => e.dataset.file),
        );
        for (const file of job.files || []) {
          if (existing.has(file.name)) continue;
          const row = node("div");
          row.dataset.file = file.name;
          const source = `simulation:${identifier}/${file.name}`;
          const figure = window.WorkspaceRich.figure(source, file.name, p);
          if (figure) row.append(figure);
          const a = node("a", file.name, "file-row");
          a.href = window.WorkspaceRich.artifactURL(source, p, false);
          row.append(a);
          files.append(row);
        }
      } finally {
        inFlight[panel] = false;
      }
    }
    return { render, open, update };
  },
};
