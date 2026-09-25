/** Only same-site paths: never redirect to another website after signing in (open redirect). */
export function safeNext(value: string | null): string {
  return value && value.startsWith("/") && !value.startsWith("//") && !value.startsWith("/\\") ? value : "/app";
}

/**
 * The token of an email link (/verify-email#token=...). It travels after "#", so it never reaches
 * a server log; once read it is removed from the address bar and the browser history.
 */
export function takeTokenFromHash(): string | null {
  const token = new URLSearchParams(window.location.hash.slice(1)).get("token");
  if (window.location.hash) window.history.replaceState(null, "", window.location.pathname + window.location.search);
  return token;
}
