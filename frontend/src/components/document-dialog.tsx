"use client";

import { Braces, List, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import type { ExtractedDocument } from "@/lib/api";
import { DOCUMENT_TYPES } from "@/lib/documents";

import { Badge } from "./ui";

type Row = [string, string];

function humanize(key: string): string {
  return key.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

/** Flatten the document into readable "field: value" rows (nested objects become "a · b"). */
function rows(value: unknown, prefix = ""): Row[] {
  if (value === null || value === undefined || value === "") return [];
  if (Array.isArray(value)) {
    if (value.length === 0) return [];
    if (typeof value[0] !== "object") return [[prefix, value.join(", ")]];
    return value.flatMap((item, index) => rows(item, `${prefix} #${index + 1}`));
  }
  if (typeof value === "object") {
    return Object.entries(value as Record<string, unknown>).flatMap(([key, inner]) =>
      rows(inner, prefix ? `${prefix} · ${humanize(key)}` : humanize(key)),
    );
  }
  return [[prefix, String(value)]];
}

export function DocumentDialog({ filename, document, onClose }: { filename: string; document: ExtractedDocument; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [raw, setRaw] = useState(false);
  const type = DOCUMENT_TYPES[document.document_type];
  const { summary, document_type, ...fields } = document;

  useEffect(() => {
    dialog.current?.showModal(); // native <dialog>: focus trap, Esc to close, inert background
  }, []);

  return (
    <dialog
      ref={dialog}
      onClose={onClose}
      onClick={(event) => event.target === dialog.current && dialog.current?.close()}
      className="m-auto max-h-[90dvh] w-[min(42rem,calc(100vw-1.5rem))] overflow-hidden border border-slate-200 bg-white p-0 text-slate-900 shadow-2xl backdrop:bg-slate-950/60 backdrop:backdrop-blur-sm dark:border-slate-800 dark:bg-slate-900 dark:text-slate-100"
    >
      <div className="flex max-h-[90dvh] flex-col">
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 p-5 dark:border-slate-800">
          <div className="min-w-0">
            <p className="truncate text-lg font-semibold">{filename}</p>
            <div className="mt-1 flex items-center gap-2">
              <Badge tone="brand">{type.label}</Badge>
              {document.language && <Badge tone="slate">{document.language.toUpperCase()}</Badge>}
            </div>
          </div>
          <button
            onClick={() => dialog.current?.close()}
            className="p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800"
            aria-label="Close"
          >
            <X className="size-5" />
          </button>
        </div>
        <div className="overflow-y-auto p-5">
          <p className="bg-slate-50 p-4 text-sm leading-relaxed text-slate-700 dark:bg-slate-800/60 dark:text-slate-300">{summary}</p>
          <div className="mt-4 flex justify-end">
            <button
              onClick={() => setRaw((value) => !value)}
              className="inline-flex items-center gap-1.5 px-2 py-1 text-xs font-semibold text-brand-600 hover:bg-brand-50 dark:text-brand-400 dark:hover:bg-brand-500/10"
            >
              {raw ? <List className="size-3.5" /> : <Braces className="size-3.5" />} {raw ? "Show fields" : "Show JSON"}
            </button>
          </div>
          {raw ? (
            <pre className="mt-2 overflow-x-auto bg-slate-950 p-4 font-mono text-xs leading-relaxed text-slate-100">
              {JSON.stringify({ document_type, summary, ...fields }, null, 2)}
            </pre>
          ) : (
            <dl className="mt-2 divide-y divide-slate-100 dark:divide-slate-800">
              {rows(fields).map(([key, value], index) => (
                <div key={`${key}-${index}`} className="grid gap-1 py-2.5 text-sm sm:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] sm:gap-4">
                  <dt className="text-slate-500 dark:text-slate-400">{key}</dt>
                  <dd className="font-medium break-words">{value}</dd>
                </div>
              ))}
            </dl>
          )}
        </div>
      </div>
    </dialog>
  );
}
