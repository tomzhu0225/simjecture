/* Explicit UI bindings only. Never scan research content or alter API values. */
"use strict";

window.SimjectureI18n = (() => {
  const storageKey = "simjecture-language";
  const supported = value => Object.hasOwn(window.SimjectureLanguages, value);
  const messages = window.SimjectureMessages;
  const bindings = new WeakMap();
  const messageType = Symbol("UI message");
  const attributes = ["placeholder", "title", "aria-label", "aria-valuetext", "alt", "label"];
  function storedLanguage() {
    try {
      const saved = localStorage.getItem(storageKey);
      return supported(saved) ? saved : "en";
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

  function label(value, fallback = String(value ?? ""), locale = language) {
    if (locale === "en") return fallback;
    const raw = String(value ?? "");
    const key = `status.${raw.toLowerCase().replaceAll(" ", "_")}`;
    return messages[key]?.[locale] ?? fallback;
  }

  function bindingsFor(node) {
    let record = bindings.get(node);
    if (!record) {
      record = new Map();
      bindings.set(node, record);
      node.setAttribute("data-i18n-bound", "");
    }
    return record;
  }

  function updateAttribute(node, name, result) {
    if (result == null) {
      if (node.hasAttribute(name)) node.removeAttribute(name);
    } else {
      const value = String(result);
      if (node.getAttribute(name) !== value) node.setAttribute(name, value);
    }
  }

  function bind(node, render, attribute) {
    const record = bindingsFor(node);
    const result = render();
    if (attribute) {
      updateAttribute(node, attribute, result);
      record.set(attribute, { render });
    } else {
      // A poll may rebind a label after its renderer appended a control.
      // Keep updating the owned text node so the control retains focus.
      const value = String(result ?? "");
      let text = record.get("text")?.text;
      if (text?.parentNode !== node) {
        text = document.createTextNode(value);
        node.replaceChildren(text);
      } else if (text.data !== value) {
        text.data = value;
      }
      record.set("text", { render, text });
      record.delete("view");
    }
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
    const copy = String(value ?? "");
    renderer(copy);
    if (!value?.[messageType]) return node;
    bindingsFor(node).set("view", { render: () => String(value), renderer, value: copy });
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
          const value = String(binding.render() ?? "");
          if (binding.text.parentNode === node && binding.text.nodeValue !== value)
            binding.text.nodeValue = value;
        } else if (name === "view") {
          const value = binding.render();
          if (binding.value !== value) {
            binding.renderer(value);
            binding.value = value;
          }
        } else {
          updateAttribute(node, name, binding.render());
        }
      }
    }
    for (const select of document.querySelectorAll("[data-language-select]"))
      if (select.value !== language) select.value = language;
  }

  function update(value) {
    if (language === value) return;
    language = value;
    document.documentElement.lang = language;
    apply();
    window.dispatchEvent(new Event("simjecture-language"));
  }

  function setLanguage(value) {
    if (!initialized) return ready.then(() => setLanguage(value));
    if (!supported(value)) return;
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
  let initialized = false;
  const ready = window.SimjectureMessagesReady.then(async () => {
    if (document.readyState === "loading")
      await new Promise(resolve => document.addEventListener("DOMContentLoaded", resolve, { once: true }));
    for (const select of document.querySelectorAll("[data-language-select]")) {
      select.replaceChildren(...Object.entries(window.SimjectureLanguages).map(([code, name]) => {
        const option = new Option(name, code);
        option.lang = code;
        return option;
      }));
      select.disabled = false;
    }
    language = storedLanguage();
    document.documentElement.lang = language;
    initialized = true;
    apply();
  });

  return { t, message, live, label, known, text, content, render, bindText, attribute, apply, setLanguage,
    ready, getLanguage: () => language };
})();
