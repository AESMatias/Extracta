import type { Plan } from "./api";
import catalog from "./plans.json";

// Generated from app/plans.py (a backend test fails if they drift). Checkout always uses the
// server's prices; this copy only lets pages render plans without waiting for the API.
export const PLANS = catalog as Plan[];

export function planFeatures(plan: Plan): { label: string; included: boolean }[] {
  const p = plan.privileges;
  return [
    { label: `${p.docs_per_24h} PDFs every 24 hours`, included: true },
    { label: `Up to ${p.max_file_mb} MB per file`, included: true },
    { label: `${p.max_files_per_upload} files per upload`, included: true },
    { label: "Excel, CSV and JSON exports", included: true },
    { label: "Live charts and 10 document types", included: true },
    { label: "Save documents to your history", included: p.can_save_to_db },
  ];
}
