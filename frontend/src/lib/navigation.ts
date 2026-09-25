/** Only same-site paths: never redirect to another website after signing in (open redirect). */
export function safeNext(value: string | null): string {
  return value && value.startsWith("/") && !value.startsWith("//") && !value.startsWith("/\\") ? value : "/app";
}
