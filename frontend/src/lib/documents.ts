import {
  Banknote,
  BriefcaseBusiness,
  ClipboardList,
  FileBarChart2,
  FileQuestion,
  FileSignature,
  FileText,
  Landmark,
  Receipt,
  ShoppingCart,
  type LucideIcon,
} from "lucide-react";

import type { DocumentType, ExtractedDocument } from "./api";

export const DOCUMENT_TYPES: Record<DocumentType, { label: string; icon: LucideIcon; color: string; examples: string }> = {
  invoice: { label: "Invoice", icon: FileText, color: "#6366f1", examples: "Invoices, utility bills" },
  receipt: { label: "Receipt", icon: Receipt, color: "#8b5cf6", examples: "Receipts, sales tickets" },
  purchase_order: { label: "Purchase order", icon: ShoppingCart, color: "#0ea5e9", examples: "Orders to suppliers" },
  quote: { label: "Quote", icon: ClipboardList, color: "#14b8a6", examples: "Quotes, estimates" },
  bank_statement: { label: "Bank statement", icon: Landmark, color: "#22c55e", examples: "Account statements" },
  contract: { label: "Contract", icon: FileSignature, color: "#f59e0b", examples: "Service, lease, employment" },
  payslip: { label: "Payslip", icon: Banknote, color: "#ec4899", examples: "Salary statements" },
  resume: { label: "Resume", icon: BriefcaseBusiness, color: "#f97316", examples: "CVs and resumes" },
  report: { label: "Report", icon: FileBarChart2, color: "#06b6d4", examples: "Financial, technical, periodic" },
  other: { label: "Other", icon: FileQuestion, color: "#94a3b8", examples: "Anything else, summarized" },
};

export function formatAmount(amount: number | null | undefined, currency?: string | null): string {
  if (typeof amount !== "number") return "";
  try {
    return new Intl.NumberFormat(undefined, { style: "currency", currency: currency || "XXX", maximumFractionDigits: 2 }).format(amount);
  } catch {
    return `${amount.toLocaleString()} ${currency ?? ""}`.trim(); // unknown currency code
  }
}

/** One readable line with the most useful fields of any document type. */
export function describeDocument(doc: ExtractedDocument): string {
  const parts: (string | null | undefined)[] = [];
  const c = doc.commercial;
  if (c) parts.push(c.issuer?.name, c.document_number && `No. ${c.document_number}`, formatAmount(c.total_amount, c.currency));
  else if (doc.bank_statement) {
    const b = doc.bank_statement;
    parts.push(b.bank_name, b.account_number_last4 && `•••• ${b.account_number_last4}`, formatAmount(b.closing_balance, b.currency));
  } else if (doc.contract) parts.push(doc.contract.title, doc.contract.parties.map((p) => p.name).join(" · "));
  else if (doc.payslip) parts.push(doc.payslip.employee_name, formatAmount(doc.payslip.net_pay, doc.payslip.currency));
  else if (doc.resume) parts.push(doc.resume.full_name, doc.resume.current_title);
  else if (doc.report) parts.push(doc.report.title, doc.report.period_covered);
  else parts.push(doc.title);
  return parts.filter(Boolean).join(" — ") || doc.summary;
}

export function formatDate(iso: string | null | undefined, withTime = false): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat(undefined, withTime ? { dateStyle: "medium", timeStyle: "short" } : { dateStyle: "medium" }).format(
    new Date(iso),
  );
}

export function timeUntil(iso: string | null | undefined): string {
  if (!iso) return "";
  const minutes = Math.max(0, Math.round((new Date(iso).getTime() - Date.now()) / 60000));
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  return `${hours} h ${minutes % 60} min`;
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}
