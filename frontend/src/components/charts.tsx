"use client";

import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useI18n } from "@/lib/i18n";

import type { ExtractedDocument } from "@/lib/api";
import { DOCUMENT_TYPES } from "@/lib/documents";

import { Card } from "./ui";

const tooltipStyle = {
  borderRadius: 12,
  border: "1px solid rgb(148 163 184 / 0.3)",
  background: "rgb(15 23 42 / 0.92)",
  color: "#fff",
  fontSize: 12,
};

export function BatchCharts({ documents }: { documents: ExtractedDocument[] }) {
  const { m } = useI18n();
  const byType = Object.entries(
    documents.reduce<Record<string, number>>((acc, doc) => {
      acc[doc.document_type] = (acc[doc.document_type] ?? 0) + 1;
      return acc;
    }, {}),
  ).map(([type, count]) => ({ type, name: m.documentTypes.types[type as keyof typeof DOCUMENT_TYPES]?.label ?? type, count }));

  const byCurrency = Object.entries(
    documents.reduce<Record<string, number>>((acc, doc) => {
      const c = doc.commercial;
      if (c && typeof c.total_amount === "number") acc[c.currency || "N/A"] = (acc[c.currency || "N/A"] ?? 0) + c.total_amount;
      return acc;
    }, {}),
  ).map(([currency, total]) => ({ currency, total }));

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card className="p-5">
        <h3 className="font-semibold">{m.charts.byType}</h3>
        <div className="mt-2 flex flex-col items-center gap-4 sm:flex-row">
          <div className="h-52 w-full sm:w-1/2">
            <ResponsiveContainer>
              <PieChart>
                <Pie data={byType} dataKey="count" nameKey="name" innerRadius="58%" outerRadius="92%" paddingAngle={3} strokeWidth={0}>
                  {byType.map((entry) => (
                    <Cell key={entry.type} fill={DOCUMENT_TYPES[entry.type as keyof typeof DOCUMENT_TYPES].color} />
                  ))}
                </Pie>
                <Tooltip contentStyle={tooltipStyle} itemStyle={{ color: "#fff" }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <ul className="w-full space-y-2 sm:w-1/2">
            {byType.map((entry) => (
              <li key={entry.type} className="flex items-center justify-between gap-2 text-sm">
                <span className="flex items-center gap-2">
                  <span className="size-2.5 " style={{ background: DOCUMENT_TYPES[entry.type as keyof typeof DOCUMENT_TYPES].color }} />
                  {entry.name}
                </span>
                <span className="font-semibold">{entry.count}</span>
              </li>
            ))}
          </ul>
        </div>
      </Card>
      <Card className="p-5">
        <h3 className="font-semibold">
          {m.charts.byCurrency} <span className="text-sm font-normal text-slate-500">{m.charts.byCurrencyHint}</span>
        </h3>
        {byCurrency.length === 0 ? (
          <p className="grid h-52 place-items-center text-sm text-slate-500">{m.charts.noAmounts}</p>
        ) : (
          <div className="mt-4 h-52">
            <ResponsiveContainer>
              <BarChart data={byCurrency} margin={{ left: 8, right: 8 }}>
                <defs>
                  <linearGradient id="bar-gradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#10b981" />
                    <stop offset="100%" stopColor="#2f6fed" />
                  </linearGradient>
                </defs>
                <CartesianGrid vertical={false} stroke="rgb(148 163 184 / 0.2)" />
                <XAxis dataKey="currency" tickLine={false} axisLine={false} tick={{ fill: "#94a3b8", fontSize: 12 }} />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  width={64}
                  tick={{ fill: "#94a3b8", fontSize: 12 }}
                  tickFormatter={(value: number) => Intl.NumberFormat(undefined, { notation: "compact" }).format(value)}
                />
                <Tooltip
                  cursor={{ fill: "rgb(47 111 237 / 0.08)" }}
                  contentStyle={tooltipStyle}
                  itemStyle={{ color: "#fff" }}
                  formatter={(value) => Intl.NumberFormat().format(Number(value))}
                />
                <Bar dataKey="total" name={m.charts.total} fill="url(#bar-gradient)" radius={0} maxBarSize={72} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>
    </div>
  );
}
