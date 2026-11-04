/* Explicit UI bindings only. Never scan research content or alter API values. */
"use strict";

window.SimjectureI18n = (() => {
  const storageKey = "simjecture-language";
  const supported = new Set(["en", "zh-CN"]);
  const messages = window.SimjectureMessages;
  const bindings = new WeakMap();
  const messageType = Symbol("UI message");
  const attributes = ["placeholder", "title", "aria-label", "aria-valuetext", "alt", "label"];
  function storedLanguage() {
    try {
      const saved = localStorage.getItem(storageKey);
      return supported.has(saved) ? saved : "en";
    } catch {
      return "en";
    }
  }
  let language = storedLanguage();
  document.documentElement.lang = language;

  function t(key, params = {}) {
    const template = messages[key]?.[language] ?? messages[key]?.en ?? key;
    // Substitute once: braces and HTML in user values are ordinary text.
    return template.replace(/\{(\w+)\}/g, (match, name) =>
      Object.hasOwn(params, name) ? String(params[name] ?? "") : match);
  }

  // Descriptors keep labels stored in UI-only arrays/maps live across switches.
  function message(key, params = {}) {
    return { ...live(() => t(key, params)), toJSON: () => ({ key, params }) };
  }

  // UI render expressions are evaluated again only on a language change.
  function live(render) {
    const value = () => String(render() ?? "");
    return { [messageType]: true, toString: value, toJSON: value };
  }

  // Only translate this explicitly identified built-in server copy when it
  // matches the catalog. User/custom data and newer server wording pass through.
  function known(key, value) {
    return messages[key] && messages[key].en === value ? t(key) : value;
  }

  function label(value, fallback = String(value ?? "").replaceAll("_", " ")) {
    const raw = String(value ?? "");
    const key = `status.${raw.toLowerCase().replaceAll(" ", "_")}`;
    return language === "zh-CN" && messages[key] ? t(key) : fallback;
  }

  function bind(node, render, attribute) {
    let record = bindings.get(node);
    if (!record) { record = new Map(); bindings.set(node, record); }
    const result = render();
    const value = String(result ?? "");
    if (attribute) {
      if (result == null) node.removeAttribute(attribute);
      else node.setAttribute(attribute, value);
      record.set(attribute, { render });
    } else {
      // Renderers may subsequently append controls. Locale changes only touch
      // this text node, so labels keep their inputs, focus and event handlers.
      node.textContent = value;
      if (!node.firstChild) node.append(document.createTextNode(""));
      record.set("text", { render, text: node.firstChild });
      record.delete("view");
    }
    node.setAttribute("data-i18n-bound", "");
    // An explicit dynamic binding supersedes the original static message.
    node.removeAttribute(attribute ? `data-i18n-${attribute}` : "data-i18n");
    return node;
  }

  const bindText = (node, render) => bind(node, render);
  const attribute = (node, name, render) => bind(node, render, name);
  function content(node, value) {
    if (value?.[messageType]) return bindText(node, () => value);
    // Called by existing DOM helpers; API data remains ordinary text.
    node.removeAttribute?.("data-i18n");
    bindings.get(node)?.delete("text");
    bindings.get(node)?.delete("view");
    node.textContent = value ?? "";
    return node;
  }
  function text(node, key, params = {}) {
    return bindText(node, () => t(key, params));
  }

  // Explicit adapters for UI-only Markdown. Raw reports take the ordinary path.
  function render(node, value, renderer) {
    bindings.get(node)?.delete("view");
    bindings.get(node)?.delete("text");
    // Raw research content also supersedes an initial localized placeholder.
    node.removeAttribute("data-i18n");
    renderer(String(value ?? ""));
    if (!value?.[messageType]) return node;
    if (!bindings.has(node)) bindings.set(node, new Map());
    bindings.get(node).set("view", { render: () => renderer(String(value)) });
    node.setAttribute("data-i18n-bound", "");
    return node;
  }

  function apply(root = document) {
    const select = (selector) => [
      ...(root.matches?.(selector) ? [root] : []), ...root.querySelectorAll(selector),
    ];
    for (const node of select("[data-i18n]")) {
      const value = t(node.dataset.i18n);
      if (node.textContent !== value) node.textContent = value;
    }
    for (const name of attributes) {
      for (const node of select(`[data-i18n-${name}]`)) {
        const key = node.getAttribute(`data-i18n-${name}`);
        const value = t(key);
        if (node.getAttribute(name) !== value) node.setAttribute(name, value);
      }
    }
    for (const node of select("[data-i18n-bound]")) {
      for (const [name, binding] of bindings.get(node) || []) {
        if (name === "text") {
          // A renderer that replaced this node's content owns its new text.
          if (binding.text.parentNode === node) binding.text.nodeValue = String(binding.render() ?? "");
        } else if (name === "view") binding.render();
        else {
          const value = binding.render();
          if (value == null) node.removeAttribute(name);
          else node.setAttribute(name, String(value));
        }
      }
    }
    for (const select of document.querySelectorAll("[data-language-select]"))
      select.value = language;
  }

  function update(value) {
    const changed = language !== value;
    language = value;
    document.documentElement.lang = language;
    apply();
    if (changed) window.dispatchEvent(new Event("simjecture-language"));
  }

  function setLanguage(value) {
    if (!supported.has(value)) return;
    // Only an explicit choice writes a preference; storage may be unavailable.
    try { localStorage.setItem(storageKey, value); } catch {}
    update(value);
  }

  document.addEventListener("change", (event) => {
    if (event.target.matches("[data-language-select]"))
      setLanguage(event.target.value);
  });
  window.addEventListener("storage", (event) => {
    if (event.key === storageKey || event.key === null) update(storedLanguage());
  });
  // Restore the preference when returning to a page from the browser's cache.
  window.addEventListener("pageshow", () => update(storedLanguage()));
  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", () => apply(), { once: true });
  else apply();

  return { t, message, live, label, known, text, content, render, bindText, attribute, apply, setLanguage,
    getLanguage: () => language };
})();
