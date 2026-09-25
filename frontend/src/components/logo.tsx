"use client";

import clsx from "clsx";
import Link from "next/link";
import { useEffect, useRef, type Ref } from "react";

const MARK = 32; // px, the mark's size (size-8)
const GAP = 10; // px, gap-2.5
const TRAVEL_SHARE = 0.3; // the swap completes after scrolling 30% of the viewport height

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
 * steps' icons) and the document on top (which always stays upright). Hovering the parent
 * `group/logo` turns it, unless the caller drives the background itself through `backgroundRef`.
 */
export function LogoMark({ className, backgroundRef }: { className?: string; backgroundRef?: Ref<HTMLSpanElement> }) {
  return (
    <span className={clsx("relative inline-grid shrink-0 place-items-center", className ?? "size-8")} aria-hidden>
      <span
        ref={backgroundRef}
        className={clsx(
          "bg-signature absolute inset-0 rounded-[30%] supports-[corner-shape:squircle]:rounded-[48%] supports-[corner-shape:squircle]:[corner-shape:squircle]",
          backgroundRef
            ? "transition-[transform,border-radius] duration-150 ease-out"
            : "transition-all duration-700 ease-out group-hover/logo:rotate-90 group-hover/logo:rounded-[40%]",
        )}
      />
      <svg viewBox="0 0 32 32" className="relative size-full">
        {DOCUMENT_GLYPH}
      </svg>
    </span>
  );
}

/**
 * The logo. In a header (`travel`), the mark and the name swap places as the page scrolls: the
 * mark crosses in front of the name from left to right, turning, and the name slides left behind
 * it. The movement follows the scroll: it is complete after 30% of the viewport height, and the
 * mark shrinks only halfway through, ending at its normal size. Elsewhere, hovering turns the mark.
 */
export function Logo({ href = "/", className, travel = false }: { href?: string; className?: string; travel?: boolean }) {
  const mark = useRef<HTMLSpanElement>(null);
  const background = useRef<HTMLSpanElement>(null);
  const text = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!travel) return;
    let frame = 0;
    const update = () => {
      frame = 0;
      const width = text.current?.offsetWidth ?? 0;
      const progress = Math.min(1, Math.max(0, window.scrollY / (window.innerHeight * TRAVEL_SHARE)));
      const scale = 1 - 0.22 * Math.sin(Math.PI * progress); // smallest halfway, full size at both ends
      if (mark.current) mark.current.style.transform = `translateX(${progress * (width + GAP)}px) scale(${scale})`;
      if (text.current) text.current.style.transform = `translateX(${-progress * (MARK + GAP)}px)`;
      if (background.current) {
        background.current.style.transform = `rotate(${progress * 360}deg)`;
        background.current.style.borderRadius = `${30 + 10 * Math.sin(Math.PI * progress)}%`;
      }
    };
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(update); // at most one update per frame
    };
    update();
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
    };
  }, [travel]);

  // A very short transition smooths the steps of a mouse wheel without lagging behind the scroll.
  const follow = travel ? "transition-transform duration-150 ease-out will-change-transform" : "";
  return (
    <Link href={href} className={clsx("group/logo relative inline-flex items-center gap-2.5", className)} aria-label="Extracta home">
      <span ref={mark} className={clsx("relative z-10 inline-flex", follow)}>
        <LogoMark className="size-8" backgroundRef={travel ? background : undefined} />
      </span>
      <span ref={text} className={clsx("logo-text text-lg font-bold tracking-tight", follow)}>
        Extracta
      </span>
    </Link>
  );
}
