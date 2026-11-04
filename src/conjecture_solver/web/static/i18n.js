/* Shared, opt-in UI copy only. Never translate API data or research content. */
"use strict";

window.SimjectureI18n = (() => {
  const storageKey = "simjecture-language";
  const supported = new Set(["en", "zh-CN"]);
  const messages = window.SimjectureMessages;
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

  function t(key) {
    return messages[key]?.[language] ?? messages[key]?.en ?? key;
  }

  // Mark leaf elements so later language changes preserve surrounding controls.
  function text(node, key) {
    node.dataset.i18n = key;
    const value = t(key);
    if (node.textContent !== value) node.textContent = value;
    return node;
  }

  function apply(root = document) {
    for (const node of root.querySelectorAll("[data-i18n]"))
      text(node, node.dataset.i18n);
    for (const attribute of ["placeholder", "title"]) {
      for (const node of root.querySelectorAll(`[data-i18n-${attribute}]`)) {
        const key = node.getAttribute(`data-i18n-${attribute}`);
        const value = t(key);
        if (node.getAttribute(attribute) !== value) node.setAttribute(attribute, value);
      }
    }
    for (const select of document.querySelectorAll("[data-language-select]"))
      select.value = language;
  }

  function update(value) {
    language = value;
    document.documentElement.lang = language;
    apply();
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

  return { t, text, apply, setLanguage, getLanguage: () => language };
})();
