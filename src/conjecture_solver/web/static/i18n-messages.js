/* Both servers supply the complete English catalog in this loader's final argument. */
"use strict";

window.SimjectureMessages = Object.create(null);
window.SimjectureLanguages = { en: "English" };
window.SimjectureMessagesReady = (async (english) => {
  async function load(name) {
    try {
      const response = await fetch(`/assets/language/${encodeURIComponent(name)}.json`);
      if (!response.ok) throw new Error(`Unable to load interface language: ${name}`);
      const copy = await response.json();
      if (!copy || typeof copy !== "object" || Array.isArray(copy))
        throw new TypeError(`Expected an interface language dictionary: ${name}`);
      return Object.entries(copy).filter(([, value]) => typeof value === "string" && value.length);
    } catch (error) {
      console.warn(error);
      return [];
    }
  }
  function add(locale, entries) {
    for (const [key, value] of entries) {
      (window.SimjectureMessages[key] ??= Object.create(null))[locale] = value;
    }
  }

  add("en", Object.entries(english));
  const languages = await load("manifest");
  // Fetch concurrently, keeping the manifest's option order. Only advertise
  // languages that can actually be displayed on this visit.
  const available = await Promise.all(languages.map(async ([locale, name]) => {
    if (locale !== "en") {
      const entries = await load(locale);
      if (!entries.length) return null;
      add(locale, entries);
    }
    return [locale, name];
  }));
  Object.assign(window.SimjectureLanguages, Object.fromEntries(available.filter(Boolean)));
})(/* ENGLISH_CATALOG */ {});
