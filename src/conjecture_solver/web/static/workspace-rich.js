/* Rich conversation rendering uses the existing sanitizer and KaTeX plus highlight.js. */
"use strict";
window.WorkspaceRich = (() => {
  const figureTypes = /\.(png|jpe?g|gif|webp|svg)$/i;
  function artifactURL(source, project, preview = false) {
    if (!project || !source) return null;
    if (source.startsWith("/api/workspace/")) {
      const url = new URL(source, location.origin);
      if (url.searchParams.get("id") !== project.id) return null;
      if (
        ![
          "/api/workspace/file",
          "/api/workspace/preview",
          "/api/workspace/simulation-file",
        ].includes(url.pathname)
      )
        return null;
      if (preview) {
        if (url.pathname === "/api/workspace/file")
          url.pathname = "/api/workspace/preview";
        url.searchParams.set("preview", "1");
      }
      return url.pathname + url.search;
    }
    if (source.startsWith("study:")) {
      const slash = source.indexOf("/", 6);
      const campaign = source.slice(6, slash);
      const path = source.slice(slash + 1);
      if (
        slash < 7 ||
        !project.studies?.some((s) => s.campaign === campaign) ||
        path.startsWith("/") ||
        path.split("/").includes("..")
      )
        return null;
      return `/api/artifact?${new URLSearchParams({ campaign, path, ...(preview ? { preview: "1" } : {}) })}`;
    }
    let path = source,
      simulation = null;
    if (source.startsWith("simulation:")) {
      const split = source.slice(11).indexOf("/");
      if (split < 1) return null;
      simulation = source.slice(11, 11 + split);
      path = source.slice(12 + split);
      if (!project.simulations?.some((j) => j.id === simulation)) return null;
    } else {
      if (
        project.files_directory &&
        path.startsWith(project.files_directory + "/")
      )
        path = path.slice(project.files_directory.length + 1);
      path = path.replace(/^\.\//, "").replace(/^files\//, "");
      if (!project.files?.some((f) => f.name === path)) return null;
    }
    if (path.startsWith("/") || path.split("/").includes("..")) return null;
    const params = new URLSearchParams({ id: project.id, path });
    if (simulation) params.set("simulation", simulation);
    if (preview) params.set("preview", "1");
    return `/api/workspace/${simulation ? "simulation-file" : preview ? "preview" : "file"}?${params}`;
  }
  function figure(source, caption, project) {
    if (!figureTypes.test(source.split("?")[0])) return null;
    const url = artifactURL(source, project, true);
    if (!url) return null;
    const node = document.createElement("figure"),
      link = document.createElement("a"),
      img = document.createElement("img");
    node.className = "chat-figure";
    img.src = url;
    img.alt = caption || "Research figure";
    img.loading = "lazy";
    link.href = artifactURL(source, project, false);
    link.target = "_blank";
    link.rel = "noopener";
    link.append(img);
    node.append(link);
    const label = document.createElement("figcaption");
    label.textContent = caption || source;
    node.append(label);
    return node;
  }
  function render(target, text, project) {
    const figures = [];
    // Work on Markdown image tokens only. Raw HTML remains disabled by the shared sanitizer.
    const source = String(text || "").replace(
      /```[\s\S]*?```|~~~[\s\S]*?~~~|`[^`\n]*`|(!?)\[([^\]]*)\]\(([^\s)]+)(?:\s+"[^"]*")?\)/g,
      (full, image, caption, path) => {
        if (!path) return full;
        if (!image) {
          const local = artifactURL(path, project, false);
          return local ? `[${caption}](${local})` : full;
        }
        const node = figure(path, caption, project);
        if (!node) return `[${caption || "Figure"}](${path})`;
        const marker = `SIMJECTUREFIGURE${figures.length}PLACEHOLDER`;
        figures.push({ marker, node });
        return `\n\n${marker}\n\n`;
      },
    );
    window.SimjectureMarkdown.render(target, source);
    for (const item of figures) {
      for (const p of target.querySelectorAll("p")) {
        if (p.textContent.trim() === item.marker) {
          p.replaceWith(item.node);
          break;
        }
      }
    }
    for (const link of target.querySelectorAll("a[href]")) {
      const raw = link.getAttribute("href");
      const local = artifactURL(raw, project, false);
      if (local) {
        link.href = local;
        link.removeAttribute("target");
      } else if (raw.startsWith("#project=")) {
        link.removeAttribute("target");
      }
    }
    for (const pre of target.querySelectorAll("pre")) {
      const code = pre.querySelector("code");
      if (!code) continue;
      const raw = code.textContent;
      if (window.hljs) window.hljs.highlightElement(code);
      const bar = document.createElement("div");
      bar.className = "code-toolbar";
      const language = document.createElement("span");
      language.textContent =
        (code.className.match(/language-([\w+-]+)/) || [])[1] || "Code";
      const copy = document.createElement("button");
      copy.type = "button";
      copy.textContent = "Copy";
      copy.setAttribute("aria-label", "Copy code");
      copy.onclick = async () => {
        try {
          await navigator.clipboard.writeText(raw);
          copy.textContent = "Copied";
          setTimeout(() => (copy.textContent = "Copy"), 1600);
        } catch {
          const range = document.createRange();
          range.selectNodeContents(code);
          const selection = window.getSelection();
          selection.removeAllRanges();
          selection.addRange(range);
          copy.textContent = "Press Ctrl+C to copy";
        }
      };
      bar.append(language, copy);
      pre.before(bar);
      pre.classList.add("highlighted-code");
    }
  }
  return { render, figure, artifactURL };
})();
