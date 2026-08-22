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

  const protectedMarkdownPattern = /(```[\s\S]*?```|`[^`\n]*`|\$\$[\s\S]*?\$\$|\$[^$\n]+\$|\\\[[\s\S]*?\\\]|\\\([^\n]*?\\\))/g;
  const subscriptVariablePattern = /\b(?:theta|alpha|beta|gamma|delta|lambda|mu|omega|Omega|[A-Za-z])_[A-Za-z0-9{}]+\b/g;
  const chainedInequalityPattern = /(^|[^\w$])([+-]?\d+(?:\.\d+)?\s*(?:<=|>=|<|>)\s*(?:theta|alpha|beta|gamma|delta|lambda|mu|omega|Omega|[A-Za-z])_[A-Za-z0-9{}]+\s*(?:<=|>=|<|>)\s*[+-]?\d+(?:\.\d+)?(?:\s*(?:rad|deg|s))?)/g;
  const assignmentPattern = /\b((?:theta|alpha|beta|gamma|delta|lambda|mu|omega|Omega|[A-Za-z])_[A-Za-z0-9{}]+\s*=\s*(?:(?:\d+(?:\.\d+)?|pi\b|sqrt\([^()\n]+\)|[A-Za-z](?:_[A-Za-z0-9{}]+)?(?![A-Za-z])|[*/+\-^()]|\s))+)/g;

  function greekIdentifier(identifier) {
    const match = /^(theta|alpha|beta|gamma|delta|lambda|mu|omega|Omega)(.*)$/.exec(identifier);
    return match ? `\\${match[1]}${match[2]}` : identifier;
  }

  function asciiMathToLatex(expression) {
    let result = String(expression).trim();
    result = result.replace(/sqrt\(([^()]*)\)/g, (_, inner) => {
      return `\\sqrt{${asciiMathToLatex(inner)}}`;
    });
    result = result.replace(/\b(theta|alpha|beta|gamma|delta|lambda|mu|omega|Omega)(?=\b|_)/g, "\\$1");
    result = result.replace(/\bpi\b/g, "\\pi");
    result = result.replace(/<=/g, "\\le ").replace(/>=/g, "\\ge ");
    result = result.replace(/\*/g, " ");
    result = result.replace(/\b(rad|deg|s)\b/g, "\\mathrm{$1}");
    return result.replace(/\s+/g, " ").trim();
  }

  function enhancePlainScientificText(value) {
    const formulas = [];
    const stash = (expression) => {
      const token = `\u0000SIMJECTUREMATH${formulas.length}\u0000`;
      formulas.push(`$${asciiMathToLatex(expression)}$`);
      return token;
    };
    let result = value.replace(chainedInequalityPattern, (_, prefix, expression) => {
      return `${prefix}${stash(expression)}`;
    });
    result = result.replace(assignmentPattern, (expression) => {
      const trailingSpace = expression.match(/\s+$/)?.[0] || "";
      return `${stash(expression.trimEnd())}${trailingSpace}`;
    });
    result = result.replace(subscriptVariablePattern, (identifier) => {
      return stash(greekIdentifier(identifier));
    });
    return result.replace(/\u0000SIMJECTUREMATH(\d+)\u0000/g, (_, index) => formulas[Number(index)]);
  }

  function prepare(markdown, options = {}) {
    const source = String(markdown ?? "");
    if (!options.autoMath) return source;
    return source
      .split(protectedMarkdownPattern)
      .map((part, index) => (index % 2 ? part : enhancePlainScientificText(part)))
      .join("");
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
    const prepared = prepare(markdown, options);
    if (!dependenciesAvailable()) {
      target.textContent = prepared;
      return target;
    }
    try {
      const template = document.createElement("template");
      template.innerHTML = safeHtml(prepared, Boolean(options.inline));
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

  global.SimjectureMarkdown = Object.freeze({ plainText, prepare, render });
})(window);
