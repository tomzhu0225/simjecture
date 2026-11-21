/* Refactored right sidebar: edited-files tracking and integrated inline file viewer. */
"use strict";
window.WorkspaceFiles = (() => {
  let ctx = null;
  let filterMode = "all";
  let searchQuery = "";
  let activeFile = null; // { projectId, path, source, simulation, viewMode, wrap, mtime, bytes }
  let activeData = null;
  let loadRequest = 0;
  let listSignature = "";

  const $ = (id) => document.getElementById(id);
  const el = (tag, text, cls) => {
    const node = document.createElement(tag);
    if (text !== undefined) SimjectureI18n.content(node, text);
    if (cls) node.className = cls;
    return node;
  };
  const fmtBytes = (n) => {
    const value = Number(n || 0);
    if (value < 1024) return `${value} B`;
    if (value < 1024 ** 2) return `${(value / 1024).toFixed(1)} KB`;
    return `${(value / 1024 ** 2).toFixed(1)} MB`;
  };

  function init(options) {
    ctx = options;
    const allBtn = $("files-filter-all");
    const editedBtn = $("files-filter-edited");
    const searchInput = $("files-search");
    const editedPill = $("inspector-edited-pill");
    const wideToggle = $("inspector-wide-toggle");

    if (allBtn) {
      allBtn.onclick = () => {
        filterMode = "all";
        listSignature = "";
        render(ctx.project());
      };
    }
    if (editedBtn) {
      editedBtn.onclick = () => {
        filterMode = "edited";
        listSignature = "";
        render(ctx.project());
      };
    }
    if (searchInput) {
      searchInput.addEventListener("input", () => {
        searchQuery = searchInput.value.trim().toLowerCase();
        listSignature = "";
        render(ctx.project());
      });
    }
    if (editedPill) {
      editedPill.onclick = () => {
        window.WorkspacePanels?.set("right", false);
        $("inspector-tabs")?.setAttribute("active", "files");
        filterMode = "edited";
        listSignature = "";
        const p = ctx.project();
        render(p);
        const firstEdited = p?.edited_files?.[0];
        if (firstEdited) open(firstEdited.name, { source: "files", preferredView: "diff" });
      };
    }
    if (wideToggle) {
      wideToggle.onclick = () => {
        const wide = window.WorkspacePanels?.toggleWide?.();
        wideToggle.setAttribute("aria-pressed", String(Boolean(wide)));
      };
    }
  }

  function reset(projectId) {
    if (activeFile && activeFile.projectId !== projectId) {
      activeFile = null;
      activeData = null;
      const pane = $("file-viewer-pane");
      if (pane) {
        pane.hidden = true;
        pane.replaceChildren();
      }
    }
    listSignature = "";
  }


  function render(p) {
    if (!p || !ctx) return;
    reset(p.id);
    const files = p.files || [];
    const edited = p.edited_files || files.filter((f) => f.change && f.change !== "unchanged");
    const editedPill = $("inspector-edited-pill");
    if (editedPill) {
      editedPill.hidden = edited.length === 0;
      if (edited.length) {
        SimjectureI18n.content(
          editedPill,
          SimjectureI18n.message("workspace.files.editedPill", { count: edited.length }),
        );
      }
    }
    const allBtn = $("files-filter-all");
    const editedBtn = $("files-filter-edited");
    if (allBtn) {
      allBtn.setAttribute("aria-pressed", String(filterMode === "all"));
      SimjectureI18n.content(
        allBtn,
        SimjectureI18n.message("workspace.files.filterAll", { count: files.length }),
      );
    }
    if (editedBtn) {
      editedBtn.setAttribute("aria-pressed", String(filterMode === "edited"));
      SimjectureI18n.content(
        editedBtn,
        SimjectureI18n.message("workspace.files.filterEdited", { count: edited.length }),
      );
    }

    const filtered = files.filter((f) => {
      if (filterMode === "edited" && (!f.change || f.change === "unchanged")) return false;
      if (searchQuery && !f.name.toLowerCase().includes(searchQuery)) return false;
      return true;
    });

    const sig = JSON.stringify([
      p.id,
      filterMode,
      searchQuery,
      activeFile?.source === "files" ? activeFile.path : null,
      filtered.map((f) => [f.name, f.bytes ?? f.size, f.change, f.added_lines, f.removed_lines]),
    ]);
    if (sig !== listSignature) {
      listSignature = sig;
      const container = $("project-files");
      container.replaceChildren();
      for (const file of filtered) {
        const sizeVal = file.bytes ?? file.size ?? 0;
        const selected = activeFile?.source === "files" && activeFile.path === file.name;
        const row = el("div", undefined, `file-row${selected ? " is-selected" : ""}`);
        row.dataset.file = file.name;
        const main = el("div", undefined, "file-row-main");
        const link = el("a", file.name);
        link.href = ctx.workspaceURL(
          `/api/workspace/file?id=${encodeURIComponent(p.id)}&path=${encodeURIComponent(file.name)}`,
        );
        link.dataset.viewFile = file.name;
        SimjectureI18n.attribute(link, "title", () => file.name);
        link.addEventListener("click", (event) => {
          if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0)
            return;
          event.preventDefault();
          open(file.name, { source: "files" });
        });
        main.append(link);
        const meta = el("div", undefined, "file-row-meta");
        if (file.change && file.change !== "unchanged") {
          const badgeKey =
            file.change === "created" ? "workspace.files.newBadge" : "workspace.files.editedBadge";
          meta.append(el("span", SimjectureI18n.message(badgeKey), `file-change-badge ${file.change}`));
        }
        if ((file.added_lines || 0) > 0 || (file.removed_lines || 0) > 0) {
          const stat = el("span", undefined, "file-diff-stat");
          if (file.added_lines) stat.append(el("span", `+${file.added_lines}`, "diff-add"));
          if (file.removed_lines) stat.append(el("span", `-${file.removed_lines}`, "diff-del"));
          meta.append(stat);
        }
        meta.append(el("small", fmtBytes(sizeVal)));
        const dl = el("a", "↓", "file-row-download");
        dl.href = link.href;
        dl.download = file.name.split("/").pop() || file.name;
        SimjectureI18n.attribute(dl, "title", () => SimjectureI18n.t("workspace.files.download"));
        SimjectureI18n.attribute(dl, "aria-label", () =>
          SimjectureI18n.t("workspace.files.downloadFile", { name: file.name }),
        );
        meta.append(dl);
        row.append(main, meta);
        container.append(row);
      }
      if (!filtered.length) {
        const emptyKey =
          files.length && (filterMode === "edited" || searchQuery)
            ? "workspace.files.noMatches"
            : "workspace.fileEmpty";
        container.append(SimjectureI18n.text(el("p"), emptyKey));
      }
    }

    // Live-refresh the currently open project file when its disk mtime or size changes.
    if (activeFile && activeFile.projectId === p.id && activeFile.source === "files") {
      const latest = files.find((f) => f.name === activeFile.path);
      if (
        latest &&
        (latest.mtime !== activeFile.mtime || (latest.bytes ?? latest.size) !== activeFile.bytes)
      ) {
        loadViewer(activeFile, { silent: true });
      }
    }
  }


  async function open(path, { source = "files", simulation = null, preferredView = null } = {}) {
    const p = ctx?.project();
    if (!p || !path) return;
    window.WorkspacePanels?.set("right", false);
    $("inspector-tabs")?.setAttribute("active", "files");
    activeFile = {
      projectId: p.id,
      path,
      source,
      simulation: simulation || null,
      viewMode: preferredView || "primary",
      wrap: false,
      mtime: null,
      bytes: null,
    };
    listSignature = "";
    render(p);
    await loadViewer(activeFile, { silent: false });
    $("file-viewer-pane")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  async function loadViewer(target, { silent = false } = {}) {
    const pane = $("file-viewer-pane");
    if (!pane || !target) return;
    const req = ++loadRequest;
    const prevBody = pane.querySelector(".file-viewer-body");
    const prevScroll = prevBody ? prevBody.scrollTop : 0;
    if (!silent) {
      pane.hidden = false;
      pane.replaceChildren(
        el("div", SimjectureI18n.message("workspace.files.loading"), "file-viewer-binary"),
      );
    }
    const params = new URLSearchParams({
      id: target.projectId,
      path: target.path,
      source: target.source || "files",
    });
    if (target.simulation) params.set("simulation", target.simulation);
    try {
      const data = await ctx.api(`file-content?${params}`);
      if (req !== loadRequest || !activeFile || activeFile.path !== target.path) return;
      activeFile.mtime = data.mtime;
      activeFile.bytes = data.bytes;
      activeData = data;
      renderViewer(data, prevScroll);
    } catch (error) {
      if (req !== loadRequest) return;
      pane.hidden = false;
      pane.replaceChildren(el("div", error.message, "file-viewer-binary error-text"));
    }
  }

  function renderViewer(data, restoreScroll = 0) {
    const pane = $("file-viewer-pane");
    if (!pane || !activeFile) return;
    pane.hidden = false;
    pane.replaceChildren();

    const head = el("div", undefined, "file-viewer-head");
    const titleBox = el("div", undefined, "file-viewer-title");
    const nameEl = el("strong", data.path);
    SimjectureI18n.attribute(nameEl, "title", () => data.path);
    titleBox.append(nameEl);
    if (data.change && data.change !== "unchanged") {
      const key =
        data.change === "created" ? "workspace.files.newBadge" : "workspace.files.editedBadge";
      titleBox.append(el("span", SimjectureI18n.message(key), `file-change-badge ${data.change}`));
    }
    if (data.source === "simulation" && data.source_label) {
      titleBox.append(el("span", data.source_label, "file-viewer-source"));
    }

    const controls = el("div", undefined, "file-viewer-controls");
    const modes = [];
    if (data.kind === "markdown") {
      modes.push(["primary", "workspace.files.viewRendered"], ["raw", "workspace.files.viewSource"]);
    } else if (data.kind === "table") {
      modes.push(["primary", "workspace.files.viewTable"], ["raw", "workspace.files.viewRaw"]);
    } else if (data.kind === "text") {
      modes.push(["primary", "workspace.files.viewCode"]);
    }
    if (data.diff?.has_diff) {
      modes.push(["diff", "workspace.files.viewDiff"]);
    }
    if (!modes.some(([id]) => id === activeFile.viewMode)) {
      activeFile.viewMode = modes[0]?.[0] || "primary";
    }
    for (const [modeId, labelKey] of modes) {
      const btn = el("button", SimjectureI18n.message(labelKey));
      btn.type = "button";
      btn.dataset.viewerMode = modeId;
      btn.setAttribute("aria-pressed", String(activeFile.viewMode === modeId));
      btn.onclick = () => {
        activeFile.viewMode = modeId;
        renderViewer(data, 0);
      };
      controls.append(btn);
    }
    if (data.content !== undefined) {
      const wrapBtn = el("button", SimjectureI18n.message("workspace.files.wrap"));
      wrapBtn.type = "button";
      wrapBtn.setAttribute("aria-pressed", String(activeFile.wrap));
      wrapBtn.onclick = () => {
        activeFile.wrap = !activeFile.wrap;
        renderViewer(data, pane.querySelector(".file-viewer-body")?.scrollTop || 0);
      };
      const copyBtn = el("button", SimjectureI18n.message("ui.copy"));
      copyBtn.type = "button";
      copyBtn.onclick = async () => {
        try {
          await navigator.clipboard.writeText(data.content || "");
          ctx.notify(SimjectureI18n.message("ui.copied"));
        } catch {
          ctx.notify(SimjectureI18n.message("ui.press-ctrl-c-to-copy"));
        }
      };
      controls.append(wrapBtn, copyBtn);
    }
    const dl = el("a", SimjectureI18n.message("workspace.files.download"));
    dl.href = ctx.workspaceURL(data.download_url);
    dl.download = data.name;
    const closeBtn = el("button", "×");
    closeBtn.type = "button";
    SimjectureI18n.attribute(closeBtn, "aria-label", () =>
      SimjectureI18n.t("workspace.files.closeViewer"),
    );
    closeBtn.onclick = () => {
      activeFile = null;
      activeData = null;
      pane.hidden = true;
      pane.replaceChildren();
      listSignature = "";
      render(ctx.project());
    };
    controls.append(dl, closeBtn);
    head.append(titleBox, controls);
    pane.append(head);

    const meta = el("div", undefined, "file-viewer-meta");
    const leftMeta = el(
      "span",
      SimjectureI18n.live(() => {
        const parts = [fmtBytes(data.bytes)];
        if (data.line_count !== undefined)
          parts.push(SimjectureI18n.t("workspace.files.lineCount", { count: data.line_count }));
        if (data.truncated) parts.push(SimjectureI18n.t("workspace.files.truncated"));
        return parts.join(" · ");
      }),
    );
    meta.append(leftMeta);
    if (data.diff?.has_diff) {
      const stat = el("span", undefined, "file-diff-stat");
      stat.append(
        el("span", `+${data.diff.added_lines || 0}`, "diff-add"),
        el("span", `-${data.diff.removed_lines || 0}`, "diff-del"),
      );
      meta.append(stat);
    }
    pane.append(meta);

    const body = el("div", undefined, "file-viewer-body");
    renderViewerBody(body, data);
    pane.append(body);
    if (restoreScroll) body.scrollTop = restoreScroll;
  }

  function renderViewerBody(body, data) {
    if (activeFile.viewMode === "diff" && data.diff?.has_diff) {
      const diffWrap = el("div", undefined, "file-viewer-diff");
      for (const line of data.diff.lines || []) {
        const row = el("div", undefined, `file-diff-line ${line.type}`);
        const prefix = line.type === "add" ? "+" : line.type === "del" ? "-" : line.type === "hunk" ? "@" : " ";
        row.append(
          el("span", line.old_line == null ? "" : String(line.old_line), "file-diff-num"),
          el("span", line.new_line == null ? "" : String(line.new_line), "file-diff-num"),
          el("span", prefix),
          el("span", line.text || ""),
        );
        diffWrap.append(row);
      }
      body.append(diffWrap);
      return;
    }
    if (data.kind === "image") {
      const img = el("img", undefined, "file-viewer-image");
      img.src = ctx.workspaceURL(data.preview_url);
      img.alt = data.name;
      body.append(img);
      return;
    }
    if (data.kind === "binary") {
      body.append(
        el(
          "div",
          SimjectureI18n.message("workspace.files.binaryNotice", { size: fmtBytes(data.bytes) }),
          "file-viewer-binary",
        ),
      );
      return;
    }
    if (data.kind === "markdown" && activeFile.viewMode === "primary") {
      const mdBox = el("div", undefined, "file-viewer-markdown");
      window.WorkspaceRich?.render(mdBox, data.content || "", ctx.project());
      body.append(mdBox);
      return;
    }
    if (data.kind === "table" && activeFile.viewMode === "primary" && data.table) {
      const wrap = el("div", undefined, "file-viewer-table-wrap");
      const table = el("table", undefined, "file-viewer-table");
      if (data.table.headers?.length) {
        const thead = el("thead");
        const tr = el("tr");
        for (const col of data.table.headers) tr.append(el("th", col));
        thead.append(tr);
        table.append(thead);
      }
      const tbody = el("tbody");
      for (const row of data.table.rows || []) {
        const tr = el("tr");
        for (const cell of row) tr.append(el("td", cell));
        tbody.append(tr);
      }
      table.append(tbody);
      wrap.append(table);
      body.append(wrap);
      return;
    }
    const pre = el("pre", undefined, `file-viewer-code${activeFile.wrap ? " is-wrapped" : ""}`);
    const code = el("code", data.content || "");
    if (data.language && data.language !== "plaintext") {
      code.className = `language-${data.language}`;
    }
    pre.append(code);
    body.append(pre);
    if (window.hljs && data.language && data.language !== "plaintext") {
      try {
        window.hljs.highlightElement(code);
      } catch {}
    }
  }

  return { init, render, open, reset };
})();
