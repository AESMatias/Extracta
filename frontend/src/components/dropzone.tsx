"use client";

import clsx from "clsx";
import { FileText, UploadCloud, X } from "lucide-react";
import { useId, useState, type DragEvent } from "react";

import { formatBytes } from "@/lib/documents";

export interface Picked {
  file: File;
  error: string | null;
}

export function validateFiles(files: File[], existing: Picked[], maxFileMb: number): Picked[] {
  const next = [...existing];
  for (const file of files) {
    if (next.some((p) => p.file.name === file.name && p.file.size === file.size)) continue;
    const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
    const error = !isPdf ? "Not a PDF" : file.size > maxFileMb * 1024 * 1024 ? `Larger than ${maxFileMb} MB` : null;
    next.push({ file, error });
  }
  return next;
}

export function Dropzone({ onFiles, disabled, hint }: { onFiles: (files: File[]) => void; disabled?: boolean; hint: string }) {
  const [active, setActive] = useState(false);
  const inputId = useId();

  function onDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setActive(false);
    if (!disabled) onFiles(Array.from(event.dataTransfer.files));
  }

  return (
    <label
      htmlFor={inputId}
      onDragEnter={(e) => {
        e.preventDefault();
        setActive(true);
      }}
      onDragOver={(e) => e.preventDefault()}
      onDragLeave={() => setActive(false)}
      onDrop={onDrop}
      className={clsx(
        "group relative flex cursor-pointer flex-col items-center justify-center gap-3 rounded-3xl border-2 border-dashed px-6 py-10 text-center transition duration-200 has-[:focus-visible]:ring-4 has-[:focus-visible]:ring-brand-500/20 sm:py-14",
        active
          ? "scale-[1.01] border-brand-500 bg-brand-50/80 dark:bg-brand-500/10"
          : "border-slate-300 bg-slate-50/50 hover:border-brand-400 hover:bg-brand-50/40 dark:border-slate-700 dark:bg-slate-900/40 dark:hover:border-brand-500/60 dark:hover:bg-brand-500/5",
        disabled && "pointer-events-none opacity-60",
      )}
    >
      <input
        id={inputId}
        type="file"
        accept="application/pdf,.pdf"
        multiple
        disabled={disabled}
        className="sr-only"
        onChange={(event) => {
          onFiles(Array.from(event.target.files ?? []));
          event.target.value = ""; // allow picking the same file again after removing it
        }}
      />
      <div className="grid size-14 place-items-center rounded-2xl bg-gradient-to-br from-brand-500 to-fuchsia-500 text-white shadow-lg shadow-brand-600/25 transition group-hover:scale-110 group-hover:rotate-3">
        <UploadCloud className="size-7" />
      </div>
      <div>
        <p className="text-base font-semibold">
          <span className="hidden sm:inline">Drag your PDFs here or </span>
          <span className="text-brand-600 underline decoration-brand-300 underline-offset-4 dark:text-brand-400">
            <span className="sm:hidden">Tap to choose PDFs</span>
            <span className="hidden sm:inline">browse your files</span>
          </span>
        </p>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{hint}</p>
      </div>
    </label>
  );
}

export function PickedList({ items, onRemove }: { items: Picked[]; onRemove: (index: number) => void }) {
  if (items.length === 0) return null;
  return (
    <ul className="mt-4 grid gap-2 sm:grid-cols-2" aria-label="Selected files">
      {items.map((item, index) => (
        <li
          key={`${item.file.name}-${item.file.size}`}
          className={clsx(
            "flex items-center gap-3 rounded-2xl border px-3 py-2.5",
            item.error
              ? "border-rose-200 bg-rose-50 dark:border-rose-500/30 dark:bg-rose-500/10"
              : "border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900",
          )}
        >
          <FileText className={clsx("size-5 shrink-0", item.error ? "text-rose-500" : "text-brand-500")} />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium" title={item.file.name}>
              {item.file.name}
            </p>
            <p className={clsx("text-xs", item.error ? "text-rose-600 dark:text-rose-400" : "text-slate-500")}>
              {item.error ?? formatBytes(item.file.size)}
            </p>
          </div>
          <button
            type="button"
            onClick={() => onRemove(index)}
            className="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800"
            aria-label={`Remove ${item.file.name}`}
          >
            <X className="size-4" />
          </button>
        </li>
      ))}
    </ul>
  );
}
