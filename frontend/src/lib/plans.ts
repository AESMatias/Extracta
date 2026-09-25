import type { PagePack, Plan, Privileges } from "./api";
import catalog from "./plans.json";
import { fill } from "./fill";
import type { Messages } from "./messages/en";

// Generated from app/plans.py (a backend test fails if they drift). Checkout always uses the
// server's prices; this copy only lets pages render plans without waiting for the API.
export const PLANS = catalog.plans as Plan[];
export const PACKS = catalog.packs as PagePack[];

export function formatPages(pages: number, locale: string): string {
  return new Intl.NumberFormat(locale === "es" ? "es-CL" : "en-US").format(pages);
}

/** The privileges of a plan (or of an account) as readable lines. */
export function planFeatures(privileges: Privileges, m: Messages, locale: string): { label: string; included: boolean }[] {
  const f = m.planFeatures;
  const pages = formatPages(privileges.pages, locale);
  return [
    { label: fill(privileges.window_hours <= 24 ? f.pagesDay : f.pagesMonth, { pages }), included: true },
    { label: fill(f.maxPages, { pages: privileges.max_pages_per_pdf }), included: true },
    { label: fill(f.maxMb, { mb: privileges.max_file_mb }), included: true },
    { label: fill(f.files, { files: privileges.max_files_per_upload }), included: true },
    { label: f.exports, included: true },
    { label: f.history, included: privileges.can_save_to_db },
  ];
}

export function planTagline(plan: Plan, m: Messages): string {
  return m.planFeatures.taglines[plan.id] ?? plan.tagline;
}
