"use client";

import { CheckCircle2, FileJson, FileSpreadsheet, FileText, Sparkles } from "lucide-react";
import type { CSSProperties } from "react";

import { useI18n } from "@/lib/i18n";

// Made-up but realistic invoices (Chilean in Spanish, US in English). Every name, tax ID and code is fictitious.
const ITEMS = [
  ["Licencia software contable (anual)", "1", "80.000", "80.000"],
  ["Soporte técnico (horas)", "4", "5.000", "20.000"],
];

/** A deterministic fake QR code: random-looking modules plus the three corner finder patterns. */
function FakeQr({ size = 21, className }: { size?: number; className?: string }) {
  let seed = 7;
  const random = () => {
    seed = (seed * 16807) % 2147483647;
    return seed / 2147483647;
  };
  const inFinder = (x: number, y: number) =>
    (x < 8 && y < 8) || (x >= size - 8 && y < 8) || (x < 8 && y >= size - 8);
  const cells: [number, number][] = [];
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) if (!inFinder(x, y) && random() > 0.52) cells.push([x, y]);
  const finder = (x: number, y: number) => (
    <g key={`${x}-${y}`}>
      <rect x={x} y={y} width="7" height="7" fill="currentColor" />
      <rect x={x + 1} y={y + 1} width="5" height="5" fill="#fff" />
      <rect x={x + 2} y={y + 2} width="3" height="3" fill="currentColor" />
    </g>
  );
  return (
    <svg viewBox={`-1 -1 ${size + 2} ${size + 2}`} className={className} shapeRendering="crispEdges" aria-hidden>
      <rect x="-1" y="-1" width={size + 2} height={size + 2} fill="#fff" />
      {cells.map(([x, y]) => (
        <rect key={`${x}.${y}`} x={x} y={y} width="1" height="1" fill="currentColor" />
      ))}
      {finder(0, 0)}
      {finder(size - 7, 0)}
      {finder(0, size - 7)}
    </svg>
  );
}

/** Spanish visitors: a Chilean electronic invoice (red SII box, RUT, IVA 19%, electronic stamp). */
function ChileanInvoice() {
  return (
    <div className="p-3.5 font-sans text-[7.5px] leading-snug text-slate-700 sm:text-[8.5px]">
      <div className="flex items-start justify-between gap-3">
        <div className="flex gap-2">
          <div className="grid size-7 shrink-0 place-items-center bg-gradient-to-br from-emerald-500 to-brand-600 text-[9px] font-black text-white">AS</div>
          <div>
            <p className="text-[9px] font-bold text-slate-900 sm:text-[10px]">ACME SERVICIOS SpA</p>
            <p>Giro: Servicios informáticos</p>
            <p>Av. Providencia 1234, of. 501, Santiago</p>
          </div>
        </div>
        <div className="shrink-0 text-center">
          <div className="border-2 border-rose-600 px-2 py-1 font-bold text-rose-600">
            <p>R.U.T.: 76.123.456-7</p>
            <p className="text-[8.5px] sm:text-[9.5px]">FACTURA ELECTRÓNICA</p>
            <p>Nº 004512</p>
          </div>
          <p className="mt-0.5 font-semibold text-rose-600">S.I.I. - SANTIAGO ORIENTE</p>
        </div>
      </div>

      <div className="mt-2.5 grid grid-cols-2 gap-x-3 border border-slate-200 p-1.5">
        <p>
          <b>Señor(es):</b> Comercial Andes Ltda.
        </p>
        <p>
          <b>Fecha:</b> 15 de agosto de 2026
        </p>
        <p>
          <b>RUT:</b> 77.654.321-K
        </p>
        <p>
          <b>Condición:</b> 30 días
        </p>
      </div>

      <table className="mt-2 w-full border-collapse">
        <thead>
          <tr className="bg-slate-800 text-left text-white">
            <th className="px-1 py-0.5 font-semibold">Descripción</th>
            <th className="px-1 py-0.5 text-right font-semibold">Cant.</th>
            <th className="px-1 py-0.5 text-right font-semibold">Precio</th>
            <th className="px-1 py-0.5 text-right font-semibold">Total</th>
          </tr>
        </thead>
        <tbody>
          {ITEMS.map(([description, qty, price, total]) => (
            <tr key={description} className="border-b border-slate-100">
              <td className="px-1 py-0.5">{description}</td>
              <td className="px-1 py-0.5 text-right">{qty}</td>
              <td className="px-1 py-0.5 text-right">{price}</td>
              <td className="px-1 py-0.5 text-right">{total}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="mt-2 flex items-end justify-between gap-3">
        <div className="flex items-end gap-2">
          <FakeQr className="size-12 text-slate-900 sm:size-14" />
          <div className="max-w-[7.5rem] text-[6.5px] text-slate-500 sm:text-[7px]">
            <p className="font-semibold text-slate-700">Timbre Electrónico SII</p>
            <p>Res. 80 de 2014</p>
            <p>Verifique documento: www.sii.cl</p>
            <div className="mt-1 flex h-3 gap-px" aria-hidden>
              {"311213121131213112131121".split("").map((w, i) => (
                <span key={i} className="bg-slate-800" style={{ width: `${Number(w)}px` }} />
              ))}
            </div>
          </div>
        </div>
        <div className="w-[42%] text-right">
          <p className="flex justify-between">
            <span>Monto neto</span> <span>$100.000</span>
          </p>
          <p className="flex justify-between">
            <span>IVA 19%</span> <span>$19.000</span>
          </p>
          <p className="mt-0.5 flex justify-between border-t border-slate-800 pt-0.5 text-[9px] font-bold text-slate-900 sm:text-[10px]">
            <span>TOTAL</span> <span>$119.000</span>
          </p>
        </div>
      </div>
      <p className="mt-2.5 border-t border-dashed border-slate-200 pt-1.5 pb-6 text-center text-[6.5px] text-slate-400">
        Documento tributario electrónico · Copia cedible · Página 1 de 1
      </p>
    </div>
  );
}

const US_ITEMS = [
  ["Accounting software license (annual)", "1", "$800.00", "$800.00"],
  ["Technical support (hours)", "4", "$50.00", "$200.00"],
];

/** English visitors: a standard US invoice (EIN, Bill To, Net 30, sales tax, USD). */
function UsInvoice() {
  return (
    <div className="p-3.5 font-sans text-[7.5px] leading-snug text-slate-700 sm:text-[8.5px]">
      <div className="flex items-start justify-between gap-3">
        <div className="flex gap-2">
          <div className="grid size-7 shrink-0 place-items-center bg-gradient-to-br from-emerald-500 to-brand-600 text-[9px] font-black text-white">AS</div>
          <div>
            <p className="text-[9px] font-bold text-slate-900 sm:text-[10px]">Acme Services LLC</p>
            <p>1234 Market Street, Suite 501</p>
            <p>San Francisco, CA 94103 · EIN 12-3456789</p>
          </div>
        </div>
        <div className="shrink-0 text-right">
          <p className="text-[15px] leading-none font-black tracking-wide text-rose-600 sm:text-[17px]">INVOICE</p>
          <p className="mt-1">
            <b>Invoice #</b> INV-004512
          </p>
          <p>
            <b>Date</b> Aug 15, 2026
          </p>
          <p>
            <b>Due</b> Sep 14, 2026
          </p>
        </div>
      </div>

      <div className="mt-2.5 grid grid-cols-2 gap-x-3 border-t-2 border-rose-600 pt-1.5">
        <div>
          <p className="font-bold text-slate-900 uppercase">Bill to</p>
          <p>Andes Trading Inc.</p>
          <p>500 Main St, Austin, TX 78701</p>
        </div>
        <div>
          <p className="font-bold text-slate-900 uppercase">Terms</p>
          <p>Net 30</p>
          <p>PO # 7781</p>
        </div>
      </div>

      <table className="mt-2 w-full border-collapse">
        <thead>
          <tr className="bg-slate-800 text-left text-white">
            <th className="px-1 py-0.5 font-semibold">Description</th>
            <th className="px-1 py-0.5 text-right font-semibold">Qty</th>
            <th className="px-1 py-0.5 text-right font-semibold">Unit price</th>
            <th className="px-1 py-0.5 text-right font-semibold">Amount</th>
          </tr>
        </thead>
        <tbody>
          {US_ITEMS.map(([description, qty, price, total]) => (
            <tr key={description} className="border-b border-slate-100">
              <td className="px-1 py-0.5">{description}</td>
              <td className="px-1 py-0.5 text-right">{qty}</td>
              <td className="px-1 py-0.5 text-right">{price}</td>
              <td className="px-1 py-0.5 text-right">{total}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="mt-2 flex items-end justify-between gap-3">
        <div className="flex items-end gap-2">
          <FakeQr className="size-12 text-slate-900 sm:size-14" />
          <div className="max-w-[7.5rem] text-[6.5px] text-slate-500 sm:text-[7px]">
            <p className="font-semibold text-slate-700">Scan to pay online</p>
            <p>pay.acme-services.example</p>
            <p>Card, ACH or wire transfer</p>
          </div>
        </div>
        <div className="w-[42%] text-right">
          <p className="flex justify-between">
            <span>Subtotal</span> <span>$1,000.00</span>
          </p>
          <p className="flex justify-between">
            <span>Sales tax (8.25%)</span> <span>$82.50</span>
          </p>
          <p className="mt-0.5 flex justify-between border-t border-slate-800 pt-0.5 text-[9px] font-bold text-slate-900 sm:text-[10px]">
            <span>TOTAL DUE</span> <span>$1,082.50</span>
          </p>
        </div>
      </div>
      <p className="mt-2.5 border-t border-dashed border-slate-200 pt-1.5 pb-6 text-center text-[6.5px] text-slate-400">
        Thank you for your business · Please pay within 30 days · Page 1 of 1
      </p>
    </div>
  );
}

/** Decorative product preview: a PDF invoice on the left, the data Extracta pulls out of it on the right. */
export function HeroVisual() {
  const { m, locale } = useI18n();
  const h = m.hero;
  const spanish = locale === "es";
  // What the AI extracts from the invoice on the left, so both always match.
  const fields = spanish
    ? [
        [h.fields.type, h.invoiceValue],
        [h.fields.issuer, "Acme Servicios SpA"],
        [h.fields.taxId, "76.123.456-7"],
        [h.fields.date, "2026-08-15"],
        [h.fields.total, "CLP 119.000"],
        [h.fields.vat, "CLP 19.000"],
      ]
    : [
        [h.fields.type, h.invoiceValue],
        [h.fields.issuer, "Acme Services LLC"],
        [h.fields.taxId, "EIN 12-3456789"],
        [h.fields.date, "2026-08-15"],
        [h.fields.total, "USD 1,082.50"],
        [h.fields.vat, "USD 82.50"],
      ];

  return (
    <div className="relative mx-auto w-full max-w-md lg:max-w-none" aria-hidden>
      <div className="absolute -inset-8 -z-10 bg-gradient-to-tr from-brand-500/25 via-cyan-400/15 to-emerald-400/25 blur-3xl" />

      {/* The source PDF, with a line scanning it the way the AI reads it */}
      <div className="relative w-[84%] rotate-[-3deg] overflow-hidden border border-slate-200 bg-white shadow-2xl shadow-slate-900/15 dark:border-slate-700">
        <span
          className="animate-scan pointer-events-none absolute inset-x-0 top-12 z-10 h-px bg-emerald-400 shadow-[0_0_14px_3px_rgb(52_211_153/0.55)]"
          style={{ "--scan-distance": "230px" } as CSSProperties}
        />
        <div className="flex items-center gap-2 border-b border-slate-100 bg-slate-50 px-3 py-2">
          <div className="grid size-7 place-items-center bg-rose-100 text-rose-600">
            <FileText className="size-3.5" />
          </div>
          <div>
            <p className="text-[11px] font-semibold text-slate-800">{spanish ? "factura_004512.pdf" : "invoice_INV-004512.pdf"}</p>
            <p className="text-[9px] text-slate-500">{spanish ? "1 página · 84 KB" : "1 page · 84 KB"}</p>
          </div>
        </div>

        {/* The invoice itself: always white paper, also in dark mode */}
        {spanish ? <ChileanInvoice /> : <UsInvoice />}
      </div>

      {/* The extracted data: overlaps only the invoice's footer, so its totals stay visible */}
      <div className="glass relative -mt-9 ml-auto w-[74%] animate-float p-5 shadow-2xl shadow-brand-900/15">
        <div className="flex items-center justify-between">
          <p className="flex items-center gap-1.5 text-xs font-semibold text-brand-700 dark:text-brand-300">
            <Sparkles className="size-3.5" /> {h.extracted}
          </p>
          <span className="inline-flex items-center gap-1 bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300">
            <CheckCircle2 className="size-3" /> {h.completed}
          </span>
        </div>
        <dl className="mt-4 divide-y divide-slate-200/70 text-xs dark:divide-slate-700/70">
          {fields.map(([key, value]) => (
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
              className="inline-flex items-center gap-1 border border-slate-200 bg-white px-2 py-1 text-[10px] font-semibold dark:border-slate-700 dark:bg-slate-900"
            >
              <Icon className={`size-3 ${color}`} /> {label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
