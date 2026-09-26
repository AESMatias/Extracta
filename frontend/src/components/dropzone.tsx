"use client";

import clsx from "clsx";
import { FileCode, FileText, Image as ImageIcon, UploadCloud, X } from "lucide-react";
import { useId, useState, type DragEvent } from "react";
import { fill, useI18n } from "@/lib/i18n";

import { formatBytes } from "@/lib/documents";

export interface Picked {
  file: File;
  error: string | null;
}

// What the server accepts (app/formats.py). It checks the real bytes; this is only quick feedback.
const ACCEPT = "application/pdf,.pdf,application/xml,text/xml,.xml,image/jpeg,image/png,image/webp,image/heic,image/heif,.jpg,.jpeg,.png,.webp,.heic,.heif";
const XML_MAX_MB = 2; // e-invoices are small: the server caps XML at 2 MB whatever the plan

export type FileKind = "pdf" | "xml" | "image";

export function fileKind(file: File): FileKind | null {
  const name = file.name.toLowerCase();
  if (file.type === "application/pdf" || name.endsWith(".pdf")) return "pdf";
  if (file.type.endsWith("/xml") || name.endsWith(".xml")) return "xml";
  if (file.type.startsWith("image/") || /\.(jpe?g|png|webp|heic|heif)$/.test(name)) return "image";
  return null;
}

export function validateFiles(
  files: File[],
  existing: Picked[],
  maxFileMb: number,
  texts: { unsupported: string; tooLarge: string },
): Picked[] {
  const next = [...existing];
  for (const file of files) {
    if (next.some((p) => p.file.name === file.name && p.file.size === file.size)) continue;
    const kind = fileKind(file);
    const limitMb = kind === "xml" ? Math.min(XML_MAX_MB, maxFileMb) : maxFileMb;
    const error = !kind ? texts.unsupported : file.size > limitMb * 1024 * 1024 ? fill(texts.tooLarge, { mb: limitMb }) : null;
    next.push({ file, error });
  }
  return next;
}

const KIND_ICON = { pdf: FileText, xml: FileCode, image: ImageIcon } as const;

function KindIcon({ file, error }: { file: File; error: boolean }) {
  const Icon = KIND_ICON[fileKind(file) ?? "pdf"];
  return <Icon className={clsx("size-5 shrink-0", error ? "text-rose-500" : "text-brand-500")} />;
}

export function Dropzone({ onFiles, disabled, hint }: { onFiles: (files: File[]) => void; disabled?: boolean; hint: string }) {
  const [active, setActive] = useState(false);
  const { m } = useI18n();
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
        "group relative flex cursor-pointer flex-col items-center justify-center gap-3 border-2 border-dashed px-6 py-10 text-center transition duration-200 has-[:focus-visible]:ring-4 has-[:focus-visible]:ring-brand-500/20 sm:py-14",
        active
          ? "scale-[1.01] border-brand-500 bg-brand-50/80 dark:bg-brand-500/10"
          : "border-slate-300 bg-slate-50/50 hover:border-brand-400 hover:bg-brand-50/40 dark:border-slate-700 dark:bg-slate-900/40 dark:hover:border-brand-500/60 dark:hover:bg-brand-500/5",
        disabled && "pointer-events-none opacity-60",
      )}
    >
      <input
        id={inputId}
        type="file"
        accept={ACCEPT}
        multiple
        disabled={disabled}
        className="sr-only"
        onChange={(event) => {
          onFiles(Array.from(event.target.files ?? []));
          event.target.value = ""; // allow picking the same file again after removing it
        }}
      />
      <div className="grid size-14 place-items-center bg-signature text-white shadow-lg shadow-brand-600/25 transition group-hover:scale-110 group-hover:rotate-3">
        <UploadCloud className="size-7" />
      </div>
      <div>
        <p className="text-base font-semibold">
          <span className="hidden sm:inline">{m.dropzone.drag}</span>
          <span className="text-brand-600 underline decoration-brand-300 underline-offset-4 dark:text-brand-400">
            <span className="sm:hidden">{m.dropzone.tap}</span>
            <span className="hidden sm:inline">{m.dropzone.browse}</span>
          </span>
        </p>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{hint}</p>
      </div>
    </label>
  );
}

export function PickedList({ items, onRemove }: { items: Picked[]; onRemove: (index: number) => void }) {
  const { m } = useI18n();
  if (items.length === 0) return null;
  return (
    <ul className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2" aria-label={m.dropzone.selected}>
      {items.map((item, index) => (
        <li
          key={`${item.file.name}-${item.file.size}`}
          className={clsx(
            "flex items-center gap-3 border px-3 py-2.5",
            item.error
              ? "border-rose-200 bg-rose-50 dark:border-rose-500/30 dark:bg-rose-500/10"
              : "border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900",
          )}
        >
          <KindIcon file={item.file} error={Boolean(item.error)} />
          <div className="min-w-0 flex-1">
            <p className="line-clamp-2 [overflow-wrap:anywhere] text-sm font-medium" title={item.file.name}>
              {item.file.name}
            </p>
            <p className={clsx("text-xs", item.error ? "text-rose-600 dark:text-rose-400" : "text-slate-500")}>
              {item.error ?? formatBytes(item.file.size)}
            </p>
          </div>
          <button
            type="button"
            onClick={() => onRemove(index)}
            className="p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800"
            aria-label={fill(m.dropzone.remove, { name: item.file.name })}
          >
            <X className="size-4" />
          </button>
        </li>
      ))}
    </ul>
  );
}
