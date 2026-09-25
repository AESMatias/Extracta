import type { Metadata } from "next";

import { LegalPage } from "@/components/legal-page";

export const metadata: Metadata = { title: "Terms and Conditions" };

export default function TermsPage() {
  return <LegalPage kind="terms" />;
}
