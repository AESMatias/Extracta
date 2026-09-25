// Visitor preferences kept in the browser: color theme and language.

export type Theme = "light" | "dark";
export type Locale = "en" | "es";

export const THEME_KEY = "extracta-theme";
export const LOCALE_KEY = "extracta-lang";
export const LOCALES: Locale[] = ["en", "es"];

/**
 * Runs in <head> before the page paints: applies the saved theme (light by default) and picks the
 * language (saved choice, else the browser's). A non-English visitor's page stays hidden until the
 * translations apply (max 1.5 s), so it never flashes in English first.
 */
export const PREFERENCES_SCRIPT = `(function(){try{var d=document.documentElement;if(localStorage.getItem("${THEME_KEY}")==="dark")d.classList.add("dark");var l=localStorage.getItem("${LOCALE_KEY}");if(l!=="en"&&l!=="es"){var n=(navigator.languages&&navigator.languages[0])||navigator.language||"en";l=/^es\\b/i.test(n)?"es":"en"}d.lang=l;if(l!=="en"){d.classList.add("i18n-pending");setTimeout(function(){d.classList.remove("i18n-pending")},1500)}}catch(e){}})();`;

export function saveTheme(theme: Theme): void {
  document.documentElement.classList.toggle("dark", theme === "dark");
  try {
    localStorage.setItem(THEME_KEY, theme);
  } catch {
    // Private mode: the choice lasts for this page view.
  }
}

export function currentTheme(): Theme {
  return document.documentElement.classList.contains("dark") ? "dark" : "light";
}

export function saveLocale(locale: Locale): void {
  document.documentElement.lang = locale;
  try {
    localStorage.setItem(LOCALE_KEY, locale);
  } catch {
    // Private mode: the choice lasts for this page view.
  }
}
