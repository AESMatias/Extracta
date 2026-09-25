"use client";

import clsx from "clsx";
import { useEffect, useRef, type ComponentProps, type CSSProperties, type ElementType } from "react";

type RevealProps<T extends ElementType> = {
  as?: T;
  delay?: number; // milliseconds, for staggered groups
} & Omit<ComponentProps<T>, "as">;

/** Fades and lifts its content in the first time it scrolls into view (once, then it stays). */
export function Reveal<T extends ElementType = "div">({ as, delay = 0, className, style, ...props }: RevealProps<T>) {
  const Tag = (as ?? "div") as ElementType;
  const ref = useRef<HTMLElement>(null);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        }
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.08 },
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  return <Tag ref={ref} className={clsx("reveal", className)} style={{ ...style, "--reveal-delay": `${delay}ms` } as CSSProperties} {...props} />;
}
