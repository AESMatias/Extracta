import { CheckCircle2, FileSpreadsheet, FileJson, FileText, Sparkles } from "lucide-react";

const FIELDS = [
  ["Type", "Invoice"],
  ["Issuer", "Acme Servicios SpA"],
  ["Tax ID", "76.123.456-7"],
  ["Issue date", "2026-08-15"],
  ["Total", "CLP 119,000"],
  ["VAT", "CLP 19,000"],
];

/** Decorative product preview: a PDF on the left, the data Extracta pulls out of it on the right. */
export function HeroVisual() {
  return (
    <div className="relative mx-auto w-full max-w-md lg:max-w-none" aria-hidden>
      <div className="absolute -inset-8 -z-10 rounded-full bg-gradient-to-tr from-brand-500/30 via-fuchsia-500/20 to-sky-400/20 blur-3xl" />

      {/* The source PDF */}
      <div className="relative w-[78%] rotate-[-4deg] rounded-2xl border border-slate-200 bg-white p-5 shadow-xl shadow-slate-900/10 dark:border-slate-700 dark:bg-slate-800">
        <div className="flex items-center gap-2">
          <div className="grid size-8 place-items-center rounded-lg bg-rose-100 text-rose-600 dark:bg-rose-500/15">
            <FileText className="size-4" />
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-800 dark:text-slate-100">factura_004512.pdf</p>
            <p className="text-[10px] text-slate-500">1 page · 84 KB</p>
          </div>
        </div>
        <div className="mt-4 space-y-2">
          <div className="h-2.5 w-2/3 rounded-full bg-slate-200 dark:bg-slate-700" />
          <div className="h-2 w-1/2 rounded-full bg-slate-100 dark:bg-slate-700/70" />
          <div className="mt-4 grid grid-cols-3 gap-2">
            {Array.from({ length: 9 }).map((_, i) => (
              <div key={i} className="h-2 rounded-full bg-slate-100 dark:bg-slate-700/70" />
            ))}
          </div>
          <div className="mt-4 ml-auto h-3 w-1/3 rounded-full bg-brand-100 dark:bg-brand-500/20" />
        </div>
      </div>

      {/* The extracted data */}
      <div className="glass relative -mt-16 ml-auto w-[82%] animate-float rounded-2xl p-5 shadow-2xl shadow-brand-900/15">
        <div className="flex items-center justify-between">
          <p className="flex items-center gap-1.5 text-xs font-semibold text-brand-700 dark:text-brand-300">
            <Sparkles className="size-3.5" /> Extracted with AI
          </p>
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300">
            <CheckCircle2 className="size-3" /> Completed
          </span>
        </div>
        <dl className="mt-4 divide-y divide-slate-200/70 text-xs dark:divide-slate-700/70">
          {FIELDS.map(([key, value]) => (
            <div key={key} className="flex items-center justify-between gap-3 py-1.5">
              <dt className="text-slate-500 dark:text-slate-400">{key}</dt>
              <dd className="truncate font-semibold text-slate-900 dark:text-white">{value}</dd>
            </div>
          ))}
        </dl>
        <div className="mt-4 flex gap-2">
          {[
            { icon: FileSpreadsheet, label: "XLSX", color: "text-emerald-600" },
            { icon: FileText, label: "CSV", color: "text-sky-600" },
            { icon: FileJson, label: "JSON", color: "text-amber-600" },
          ].map(({ icon: Icon, label, color }) => (
            <span
              key={label}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-1 text-[10px] font-semibold dark:border-slate-700 dark:bg-slate-900"
            >
              <Icon className={`size-3 ${color}`} /> {label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
