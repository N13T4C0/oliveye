/** Theme constants safe to import from server components (no React hooks here). */

export const THEME_STORAGE_KEY = "oliveye-theme";

/**
 * Inline script for <head>: applies the saved theme (or the system one) before the first paint,
 * so a dark-mode visitor never sees a white flash.
 */
export const THEME_BOOT_SCRIPT = `try{var t=localStorage.getItem("${THEME_STORAGE_KEY}");if(t!=="light"&&t!=="dark"){t=matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"}document.documentElement.dataset.theme=t}catch(e){document.documentElement.dataset.theme="light"}`;
