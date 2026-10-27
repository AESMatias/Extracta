import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import { ToastProvider } from "@/components/toast";
import { VisitBeacon } from "@/components/visit-beacon";
import { AuthProvider } from "@/lib/auth";
import { I18nProvider } from "@/lib/i18n";
import { PREFERENCES_SCRIPT } from "@/lib/preferences";

import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

// Full URL for the preview image shown by LinkedIn and WhatsApp
const SITE_URL = process.env.SITE_URL ?? "https://pdf.rapidmov.online";
const SHARE_TITLE = "Extracta · Turn documents into structured data";
const SHARE_DESCRIPTION =
  "Upload invoices, receipts, contracts, bank statements and more, as PDFs, images or XML e-invoices. Extracta reads them with AI and gives you clean data, charts and Excel, CSV or JSON exports.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: "Extracta · Turn documents into structured data", template: "%s · Extracta" },
  description: SHARE_DESCRIPTION,
  applicationName: "Extracta",
  icons: { icon: "/icon.svg" },
  openGraph: {
    type: "website",
    siteName: "Extracta",
    title: SHARE_TITLE,
    description: SHARE_DESCRIPTION,
    images: [{ url: "/og-image.png", width: 1200, height: 627, alt: "Extracta turns PDFs, images and XML e-invoices into structured data" }],
  },
  twitter: { card: "summary_large_image", title: SHARE_TITLE, description: SHARE_DESCRIPTION, images: ["/og-image.png"] },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#ffffff",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    // The head script changes the class and lang before React loads, hence suppressHydrationWarning.
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`} suppressHydrationWarning>
      <head>
        {/* Theme and language before the first paint: no flash of the wrong ones. */}
        <script dangerouslySetInnerHTML={{ __html: PREFERENCES_SCRIPT }} />
      </head>
      <body>
        <I18nProvider>
          <AuthProvider>
            <ToastProvider>{children}</ToastProvider>
            <VisitBeacon />
          </AuthProvider>
        </I18nProvider>
      </body>
    </html>
  );
}
