"use client";

import { ArrowLeft } from "lucide-react";

import { LogoMark } from "@/components/logo";
import { ButtonLink } from "@/components/ui";
import { useI18n } from "@/lib/i18n";

export default function NotFound() {
  const { m } = useI18n();
  return (
    <main className="relative grid min-h-dvh place-items-center px-4 text-center">
      <div className="bg-dots absolute inset-0 -z-10 [mask-image:radial-gradient(ellipse_at_center,black,transparent_65%)]" />
      <div>
        <LogoMark className="mx-auto size-14" />
        <p className="text-gradient mt-6 text-7xl font-black">404</p>
        <h1 className="mt-2 text-2xl font-bold">{m.notFound.title}</h1>
        <p className="mt-2 text-slate-600 dark:text-slate-400">{m.notFound.text}</p>
        <ButtonLink href="/" className="mt-8" icon={<ArrowLeft className="size-4" />}>
          {m.notFound.back}
        </ButtonLink>
      </div>
    </main>
  );
}
