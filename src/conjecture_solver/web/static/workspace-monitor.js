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
      selected = null,
      announced = new Set(),
      inFlight = false,
      detailRevision = "";
    function open(id) {
      selected = id;
      detailRevision = "";
      $("inspector-tabs").setAttribute("active", "simulations");
      render(project());
      return update();
    }
    function render(p) {
      if (!p) return;
      const jobs = p.simulations || [];
      if (currentProject !== p.id) {
        currentProject = p.id;
        selected = null;
        announced = new Set(jobs.map((j) => j.id));
        detailRevision = "";
      }
      $("simulation-count").textContent = jobs.length;
      $("sidebar-simulations").hidden = !jobs.length;
      $("sidebar-run-list").replaceChildren();
      $("simulation-list").replaceChildren();
      for (const job of [...jobs].reverse()) {
        const a = node(
          "a",
          undefined,
          `simulation-item ${job.id === selected ? "selected" : ""}`,
        );
        a.href = link(p.id, { simulation: job.id, view: "interactive" });
        const dot = node("span", undefined, `run-dot ${job.status}`);
        const label = node("span", job.name);
        const status = node("small", job.status.replaceAll("_", " "));
        a.append(dot, label, status);
        $("simulation-list").append(a);
        if ($("sidebar-run-list").children.length < 5) {
          const b = a.cloneNode(true);
          b.className = "sidebar-run";
          $("sidebar-run-list").append(b);
        }
      }
      const fresh = [...jobs]
        .reverse()
        .find(
          (j) =>
            !announced.has(j.id) &&
            (j.kind === "simulation" || (j.live && j.elapsed_seconds > 1)),
        );
      if (fresh) {
        announced.add(fresh.id);
        selected = fresh.id;
        detailRevision = "";
        $("inspector-tabs").setAttribute("active", "simulations");
      }
      if (!selected && jobs.length)
        selected =
          [...jobs].reverse().find((j) => j.live)?.id ||
          jobs[jobs.length - 1].id;
      if (selected) update().catch((e) => notify(e.message, true));
    }
    async function update() {
      const p = project();
      if (!p || !selected || inFlight) return;
      const identifier = selected,
        projectId = p.id;
      const observed = p.simulations?.find((j) => j.id === identifier);
      if (!observed) return;
      inFlight = true;
      try {
        const job = observed.native
          ? observed
          : await api(
              `simulation?id=${encodeURIComponent(p.id)}&simulation=${encodeURIComponent(identifier)}`,
            );
        if (project()?.id !== projectId || selected !== identifier) return;
        const revision = JSON.stringify([
          job.status,
          job.output,
          job.files,
          job.error,
        ]);
        if (revision === detailRevision) return;
        detailRevision = revision;
        const container = $("simulation-detail"),
          oldConsole = container.querySelector(".live-console");
        const pinned =
          !oldConsole ||
          oldConsole.scrollHeight -
            oldConsole.scrollTop -
            oldConsole.clientHeight <
            60;
        const scroll = oldConsole?.scrollTop || 0;
        container.replaceChildren();
        const header = node("div", undefined, "run-heading");
        header.append(
          node("h3", job.name),
          node(
            "span",
            job.status.replaceAll("_", " "),
            `run-state ${job.status}`,
          ),
        );
        container.append(header);
        const meta = node("div", undefined, "run-meta");
        const elapsed = node("span");
        if (job.live && job.created_at)
          elapsed.dataset.elapsed = job.created_at;
        else if (job.elapsed_seconds !== undefined)
          elapsed.textContent = `${Math.floor(job.elapsed_seconds)}s elapsed`;
        meta.append(
          elapsed,
          node(
            "span",
            job.native ? "CLI-managed command" : "Interactive exploration",
          ),
        );
        container.append(meta);
        const command = node("details");
        command.append(
          node("summary", "Command & location"),
          node("pre", job.command || ""),
          node("code", job.work_directory || "Conversation files"),
        );
        container.append(command);
        const title = node("div", undefined, "console-heading");
        title.append(node("span", "LIVE CONSOLE"));
        if (job.live && !job.native) {
          const stop = node("button", "Stop run", "quiet");
          stop.disabled = readonly();
          stop.onclick = async () => {
            stop.disabled = true;
            try {
              notify(
                (
                  await api("stop-simulation", {
                    project: p.id,
                    simulation: identifier,
                  })
                ).message,
              );
            } catch (e) {
              notify(e.message, true);
            }
          };
          title.append(stop);
        }
        container.append(title);
        const output = node(
          "pre",
          (job.output || job.error || "Waiting for simulation output…").replace(
            /\x1b\[[0-?]*[ -/]*[@-~]/g,
            "",
          ),
          "live-console",
        );
        output.setAttribute("aria-label", "Simulation console");
        container.append(output);
        output.scrollTop = pinned ? output.scrollHeight : scroll;
        const files = node("div", undefined, "simulation-files");
        if (job.files?.length) files.append(node("h4", "Saved files"));
        for (const file of job.files || []) {
          const source = `simulation:${identifier}/${file.name}`;
          const figure = window.WorkspaceRich.figure(source, file.name, p);
          if (figure) files.append(figure);
          const a = node("a", file.name, "file-row");
          a.href = window.WorkspaceRich.artifactURL(source, p, false);
          files.append(a);
        }
        container.append(files);
      } finally {
        inFlight = false;
      }
    }
    return { render, open, update };
  },
};
