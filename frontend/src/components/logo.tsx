"use client";

import clsx from "clsx";
import Link from "next/link";
import { useEffect, useRef, useState, type CSSProperties } from "react";

const MARK = 32; // px, the mark's size (size-8)
const GAP = 10; // px, gap-2.5

const DOCUMENT_GLYPH = (
  <>
    <path d="M8.5 8.5h9.7l4.3 4.3v11.7h-14Z" fill="#fff" fillOpacity=".95" />
    <path d="M18 8.6v3.6c0 .5.4.9.9.9h3.5" fill="none" stroke="#99f6e4" strokeWidth="1.2" />
    <path d="M11.8 15.5h7.4M11.8 18.4h5.2M11.8 21.3h6.4" stroke="#1f57d6" strokeWidth="1.6" />
    <path d="M24.5 4.5l.7 1.6 1.6.7-1.6.7-.7 1.6-.7-1.6-1.6-.7 1.6-.7z" fill="#facc15" />
  </>
);

/**
 * The mark in two layers: the gradient background (which turns and rounds its corners, like the
 * steps' icons) and the document on top (which always stays upright).
 * `spun` turns the background a quarter; without it, hovering the parent `group/logo` does.
 */
export function LogoMark({ className, spun, turns = 1 }: { className?: string; spun?: boolean; turns?: number }) {
  const turned = { transform: `rotate(${turns * 90}deg)` } as CSSProperties;
  return (
    <span className={clsx("relative inline-grid shrink-0 place-items-center", className ?? "size-8")} aria-hidden>
      <span
        className={clsx(
          "bg-signature absolute inset-0 rounded-[30%] transition-all duration-700 ease-out supports-[corner-shape:squircle]:rounded-[48%] supports-[corner-shape:squircle]:[corner-shape:squircle]",
          spun === undefined && "group-hover/logo:rotate-90 group-hover/logo:rounded-[40%]",
          spun && "rounded-[40%]",
        )}
        style={spun ? turned : undefined}
      />
      <svg viewBox="0 0 32 32" className="relative size-full">
        {DOCUMENT_GLYPH}
      </svg>
    </span>
  );
}

/** "Extracta", filling with gold from left to right on hover (see .logo-text in globals.css). */
function Wordmark({ textRef, style }: { textRef?: React.Ref<HTMLSpanElement>; style?: CSSProperties }) {
  return (
    <span ref={textRef} className="logo-text text-lg font-bold tracking-tight transition-transform duration-700 ease-out" style={style}>
      Extracta
    </span>
  );
}

/**
 * The logo. In a header (`travel`), scrolling down makes the mark and the name swap places: the
 * mark crosses in front of the name from left to right, spinning and shrinking a little, while
 * the name slides left behind it, so the logo keeps its width. Scrolling back to the top undoes it.
 * Elsewhere, hovering spins the mark.
 */
export function Logo({ href = "/", className, travel = false }: { href?: string; className?: string; travel?: boolean }) {
  const text = useRef<HTMLSpanElement>(null);
  const [scrolled, setScrolled] = useState(false);
  const [distance, setDistance] = useState(0);

  useEffect(() => {
    if (!travel) return;
    const measure = () => setDistance(text.current?.offsetWidth ?? 0);
    const onScroll = () => setScrolled(window.scrollY > 24);
    measure();
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", measure);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", measure);
    };
  }, [travel]);

  const moved = travel && scrolled;
  return (
    <Link href={href} className={clsx("group/logo relative inline-flex items-center gap-2.5", className)} aria-label="Extracta home">
      <span
        className="relative z-10 inline-flex transition-transform duration-700 ease-out"
        style={moved ? { transform: `translateX(${distance + GAP}px) scale(0.78)` } : undefined}
      >
        <LogoMark className="size-8" spun={travel ? moved : undefined} turns={4} />
      </span>
      <Wordmark textRef={text} style={moved ? { transform: `translateX(-${MARK + GAP}px)` } : undefined} />
    </Link>
  );
}
