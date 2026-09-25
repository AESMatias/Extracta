import type { Metadata } from "next";

import { Landing } from "@/components/landing";

export const metadata: Metadata = { title: { absolute: "Extracta · Turn PDFs into structured data" } };

export default function HomePage() {
  return <Landing />;
}
