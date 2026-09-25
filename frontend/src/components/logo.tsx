"use client";

import clsx from "clsx";
import Link from "next/link";
import { useId } from "react";

export function LogoMark({ className }: { className?: string }) {
  // Unique per instance: two logos on one page must not share a gradient id (a hidden copy
  // would otherwise "own" it and the visible one would render without colors).
  const gradient = `extracta-g-${useId().replace(/:/g, "")}`;
  return (
    <svg viewBox="0 0 32 32" className={clsx("shrink-0", className ?? "size-8")} aria-hidden>
      <defs>
        <linearGradient id={gradient} x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
          <stop stopColor="#6366f1" />
          <stop offset="0.55" stopColor="#a855f7" />
          <stop offset="1" stopColor="#ec4899" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="9" fill={`url(#${gradient})`} />
      <path d="M10 8.5h8.2l4.3 4.3V23a1.5 1.5 0 0 1-1.5 1.5H10A1.5 1.5 0 0 1 8.5 23V10A1.5 1.5 0 0 1 10 8.5Z" fill="#fff" fillOpacity=".95" />
      <path d="M18 8.6v3.6c0 .5.4.9.9.9h3.5" fill="none" stroke="#c4b5fd" strokeWidth="1.2" />
      <path d="M11.8 15.5h7.4M11.8 18.4h5.2M11.8 21.3h6.4" stroke="#6366f1" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M24.5 4.5l.7 1.6 1.6.7-1.6.7-.7 1.6-.7-1.6-1.6-.7 1.6-.7z" fill="#fff" />
    </svg>
  );
}

export function Logo({ href = "/", className }: { href?: string; className?: string }) {
  return (
    <Link href={href} className={clsx("group inline-flex items-center gap-2.5", className)} aria-label="Extracta home">
      <LogoMark className="size-8 transition-transform duration-300 group-hover:rotate-[-6deg] group-hover:scale-105" />
      <span className="text-lg font-bold tracking-tight">Extracta</span>
    </Link>
  );
}
