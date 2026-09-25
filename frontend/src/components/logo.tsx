"use client";

import clsx from "clsx";
import Link from "next/link";
import { useId } from "react";

const SQUIRCLE = "M16 0C24.4 0 28 0 30 2S32 7.6 32 16 32 28 30 30 24.4 32 16 32 4 32 2 30 0 24.4 0 16 0 4 2 2 7.6 0 16 0Z";

export function LogoMark({ className }: { className?: string }) {
  // Unique per instance: two logos on one page must not share a gradient id (a hidden copy
  // would otherwise "own" it and the visible one would render without colors).
  const gradient = `extracta-g-${useId().replace(/:/g, "")}`;
  return (
    <svg viewBox="0 0 32 32" className={clsx("shrink-0", className ?? "size-8")} aria-hidden>
      <defs>
        <linearGradient id={gradient} x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
          <stop stopColor="#10b981" />
          <stop offset="0.5" stopColor="#0891b2" />
          <stop offset="1" stopColor="#1f57d6" />
        </linearGradient>
      </defs>
      {/* Apple-style squircle: corners with continuous curvature, not a circular arc. */}
      <path d={SQUIRCLE} fill={`url(#${gradient})`} />
      <path d="M8.5 8.5h9.7l4.3 4.3v11.7h-14Z" fill="#fff" fillOpacity=".95" />
      <path d="M18 8.6v3.6c0 .5.4.9.9.9h3.5" fill="none" stroke="#99f6e4" strokeWidth="1.2" />
      <path d="M11.8 15.5h7.4M11.8 18.4h5.2M11.8 21.3h6.4" stroke="#1f57d6" strokeWidth="1.6" />
      <path d="M24.5 4.5l.7 1.6 1.6.7-1.6.7-.7 1.6-.7-1.6-1.6-.7 1.6-.7z" fill="#facc15" />
    </svg>
  );
}

export function Logo({ href = "/", className }: { href?: string; className?: string }) {
  return (
    <Link href={href} className={clsx("group inline-flex items-center gap-2.5", className)} aria-label="Extracta home">
      <LogoMark className="size-8 transition-transform duration-300 group-hover:rotate-90" />
      <span className="text-lg font-bold tracking-tight">Extracta</span>
    </Link>
  );
}
