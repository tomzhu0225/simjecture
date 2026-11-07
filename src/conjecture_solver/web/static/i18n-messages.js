/* Locale resources live in language/. Keep this loader independent of UI state. */
"use strict";

window.SimjectureMessages = {};
window.SimjectureLanguages = { en: "English" };
window.SimjectureMessagesReady = (async () => {
  async function load(name) {
    const response = await fetch(`/assets/language/${name}.json`);
    if (!response.ok) throw new Error(`Unable to load interface language: ${name}`);
    return response.json();
  }
  function add(locale, copy) {
    for (const [key, value] of Object.entries(copy)) {
      (window.SimjectureMessages[key] ??= {})[locale] = value;
    }
  }

  const [english, languages] = await Promise.all([
    load("en"),
    load("manifest").catch(error => {
      console.warn(error);
      return { en: "English" };
    }),
  ]);
  add("en", english);
  Object.assign(window.SimjectureLanguages, languages);
  // The current two-language UI loads its catalogs once so switching stays
  // synchronous. A failed optional catalog still uses the English fallback.
  await Promise.all(Object.keys(languages).filter(locale => locale !== "en").map(async locale => {
    try { add(locale, await load(locale)); }
    catch (error) { console.warn(error); }
  }));
})();
