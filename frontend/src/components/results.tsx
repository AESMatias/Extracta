"use client";

import clsx from "clsx";
import { CircleAlert, CircleCheck, Clock, Database, Download, Eye, Hourglass, LoaderCircle, Trash2 } from "lucide-react";
import { localizeError } from "@/lib/errors";
import { fill, useI18n } from "@/lib/i18n";

import type { ExportFormat, ExtractedDocument } from "@/lib/api";
import { DOCUMENT_TYPES, describeDocument } from "@/lib/documents";

import { Badge, Button } from "./ui";

export type EntryStatus = "pending" | "processing" | "completed" | "failed" | "rejected" | "expired";

export interface BatchEntry {
  key: string;
  taskId?: string;
  filename: string;
  status: EntryStatus;
  document?: ExtractedDocument;
  savedToDb?: boolean;
  truncated?: boolean;
  error?: string;
  pages?: number;
}

const STATUS: Record<EntryStatus, { tone: "brand" | "amber" | "green" | "red" | "slate"; icon: typeof Clock }> = {
  pending: { tone: "brand", icon: Clock },
  processing: { tone: "amber", icon: LoaderCircle },
  completed: { tone: "green", icon: CircleCheck },
  failed: { tone: "red", icon: CircleAlert },
  rejected: { tone: "red", icon: CircleAlert },
  expired: { tone: "slate", icon: Hourglass },
};

export function StatusBadge({ status }: { status: EntryStatus }) {
  const { m } = useI18n();
  const { tone, icon: Icon } = STATUS[status];
  const label = m.results.status[status];
  // Icon + text: the status never depends on color alone.
  return (
    <Badge tone={tone}>
      <Icon className={clsx("size-3.5", status === "processing" && "animate-spin")} aria-hidden /> {label}
    </Badge>
  );
}

export function FormatButtons({ onExport, label }: { onExport: (fmt: ExportFormat) => void; label: string }) {
  const { m } = useI18n();
  return (
    <div className="flex gap-1.5" role="group" aria-label={label}>
      {(["xlsx", "csv", "json"] as const).map((fmt) => (
        <Button key={fmt} size="sm" variant="outline" onClick={() => onExport(fmt)} aria-label={fill(m.results.as, { label, format: fmt.toUpperCase() })}>
          {fmt.toUpperCase()}
        </Button>
      ))}
    </div>
  );
}

export function ResultCard({
  entry,
  onView,
  onExport,
  onDelete,
}: {
  entry: BatchEntry;
  onView: () => void;
  onExport: (fmt: ExportFormat) => void;
  onDelete?: () => void;
}) {
  const { m, locale } = useI18n();
  const r = m.results;
  const type = entry.document ? DOCUMENT_TYPES[entry.document.document_type] : null;
  const typeLabel = entry.document ? m.documentTypes.types[entry.document.document_type]?.label : null;
  const Icon = type?.icon;
  return (
    <li className="animate-fade-up border border-slate-200 bg-white p-4 transition hover:shadow-md dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-start gap-3">
        <div
          className="grid size-11 shrink-0 place-items-center"
          style={{ backgroundColor: `${type?.color ?? "#94a3b8"}1f`, color: type?.color ?? "#94a3b8" }}
        >
          {Icon ? <Icon className="size-5" /> : <Hourglass className="size-5" />}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="truncate font-semibold" title={entry.filename}>
              {entry.filename}
            </p>
            <StatusBadge status={entry.status} />
            {typeLabel && <Badge tone="slate">{typeLabel}</Badge>}
            {entry.pages ? <Badge tone="slate">{fill(r.pages, { pages: entry.pages })}</Badge> : null}
            {entry.savedToDb && (
              <Badge tone="violet">
                <Database className="size-3" /> {r.saved}
              </Badge>
            )}
          </div>
          <p className={clsx("mt-1 line-clamp-2 text-sm", entry.error ? "text-rose-600 dark:text-rose-400" : "text-slate-600 dark:text-slate-400")}>
            {entry.document
              ? describeDocument(entry.document)
              : entry.error
                ? localizeError(entry.error, locale)
                : entry.status === "processing"
                  ? r.reading
                  : r.waiting}
          </p>
          {entry.truncated && <p className="mt-1 text-xs text-amber-600">{r.truncated}</p>}
          {(entry.status === "pending" || entry.status === "processing") && <div className="skeleton mt-3 h-2 w-full" />}
        </div>
      </div>
      {entry.document && (
        <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3 dark:border-slate-800">
          <Button size="sm" variant="ghost" onClick={onView} icon={<Eye className="size-4" />}>
            {r.view}
          </Button>
          <div className="flex items-center gap-1.5">
            <Download className="size-4 text-slate-400" aria-hidden />
            <FormatButtons onExport={onExport} label={fill(r.download, { name: entry.filename })} />
            {onDelete && (
              <Button size="sm" variant="ghost" onClick={onDelete} aria-label={fill(r.delete, { name: entry.filename })} icon={<Trash2 className="size-4 text-rose-500" />} />
            )}
          </div>
        </div>
      )}
    </li>
  );
}
