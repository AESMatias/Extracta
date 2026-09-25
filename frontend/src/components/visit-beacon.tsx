"use client";

import { usePathname } from "next/navigation";
import { useEffect } from "react";

/**
 * Counts a page view for the visitor totals in /admin: no cookie, no identifier in the browser
 * (the server keeps only daily counts, see app/web/visits.py). The admin panel is not counted.
 */
export function VisitBeacon() {
  const pathname = usePathname();

  useEffect(() => {
    if (pathname.startsWith("/admin")) return;
    fetch("/api/visit", { method: "POST", credentials: "same-origin", keepalive: true }).catch(() => {});
  }, [pathname]);

  return null;
}
