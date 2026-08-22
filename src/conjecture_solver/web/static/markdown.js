"use strict";

(function exposeScientificMarkdown(global) {
  const markdownOptions = {
    async: false,
    breaks: false,
    gfm: true,
  };
  const sanitizeOptions = {
    USE_PROFILES: { html: true },
    SANITIZE_NAMED_PROPS: true,
    FORBID_TAGS: [
      "audio", "button", "canvas", "embed", "form", "iframe", "img", "input",
      "object", "select", "style", "svg", "textarea", "video",
    ],
    FORBID_ATTR: ["style"],
  };
  const mathOptions = {
    delimiters: [
      { left: "$$", right: "$$", display: true },
      { left: "\\[", right: "\\]", display: true },
      { left: "\\(", right: "\\)", display: false },
      { left: "$", right: "$", display: false },
    ],
    ignoredTags: ["script", "noscript", "style", "textarea", "pre", "code", "option"],
    output: "mathml",
    strict: "warn",
    throwOnError: false,
    trust: false,
  };

  function dependenciesAvailable() {
    return Boolean(global.marked && global.DOMPurify && global.renderMathInElement);
  }

  function safeHtml(markdown, inline) {
    const source = String(markdown ?? "");
    const rendered = inline
      ? global.marked.parseInline(source, markdownOptions)
      : global.marked.parse(source, markdownOptions);
    return global.DOMPurify.sanitize(rendered, sanitizeOptions);
  }

  function normalizeLinks(root) {
    for (const link of root.querySelectorAll("a[href]")) {
      let target;
      try {
        target = new URL(link.getAttribute("href"), global.location.href);
      } catch (_) {
        link.replaceWith(document.createTextNode(link.textContent || ""));
        continue;
      }
      if (!new Set(["http:", "https:", "mailto:"]).has(target.protocol)) {
        link.replaceWith(document.createTextNode(link.textContent || ""));
        continue;
      }
      if (target.protocol === "http:" || target.protocol === "https:") {
        link.target = "_blank";
        link.rel = "noopener noreferrer nofollow";
      }
    }
  }

  function render(target, markdown, options = {}) {
    target.classList.add("markdown-body");
    if (options.inline) target.classList.add("markdown-inline");
    else target.classList.remove("markdown-inline");
    if (!dependenciesAvailable()) {
      target.textContent = String(markdown ?? "");
      return target;
    }
    try {
      const template = document.createElement("template");
      template.innerHTML = safeHtml(markdown, Boolean(options.inline));
      target.replaceChildren(template.content.cloneNode(true));
      normalizeLinks(target);
      global.renderMathInElement(target, mathOptions);
    } catch (_) {
      target.textContent = String(markdown ?? "");
    }
    return target;
  }

  function plainText(markdown) {
    const source = String(markdown ?? "");
    if (!dependenciesAvailable()) return source;
    try {
      const template = document.createElement("template");
      template.innerHTML = safeHtml(source, true);
      return (template.content.textContent || "").replace(/\s+/g, " ").trim();
    } catch (_) {
      return source;
    }
  }

  global.SimjectureMarkdown = Object.freeze({ plainText, render });
})(window);
