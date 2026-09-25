"use client";

import { ArrowLeft, MailOpen, Send } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";

import { AuthShell } from "@/components/auth-shell";
import { Alert, Button, Field } from "@/components/ui";
import { api } from "@/lib/api";
import { errorText } from "@/lib/errors";
import { useI18n } from "@/lib/i18n";

function ForgotForm() {
  const params = useSearchParams();
  const { m, locale } = useI18n();
  const f = m.auth.forgot;
  const [sentTo, setSentTo] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const email = String(new FormData(event.currentTarget).get("email")).trim();
    setLoading(true);
    setError(null);
    try {
      await api.forgotPassword(email);
      setSentTo(email);
    } catch (err) {
      setError(errorText(err, locale, m.common.somethingWrong));
    } finally {
      setLoading(false);
    }
  }

  if (sentTo) {
    return (
      <div className="space-y-6 text-center">
        <span className="mx-auto grid size-16 place-items-center bg-brand-50 text-brand-600 ring-1 ring-brand-600/15 dark:bg-brand-500/10 dark:text-brand-300">
          <MailOpen className="size-8" />
        </span>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          {f.sent.split("{email}")[0]}
          <span className="font-semibold text-slate-900 dark:text-white">{sentTo}</span>
          {f.sent.split("{email}")[1]}
        </p>
        <Button variant="outline" className="w-full" onClick={() => setSentTo(null)}>
          {f.another}
        </Button>
      </div>
    );
  }

  return (
    <>
      {error && (
        <div className="mb-5">
          <Alert>{error}</Alert>
        </div>
      )}
      <form onSubmit={onSubmit} className="space-y-4">
        <Field
          label={m.auth.email}
          name="email"
          type="email"
          autoComplete="email"
          required
          placeholder={m.auth.emailPlaceholder}
          defaultValue={params.get("email") ?? ""}
        />
        <Button type="submit" size="lg" className="w-full" loading={loading} icon={<Send className="size-5" />}>
          {f.submit}
        </Button>
      </form>
    </>
  );
}

export default function ForgotPasswordPage() {
  const { m } = useI18n();
  return (
    <AuthShell title={m.auth.forgot.title} subtitle={m.auth.forgot.subtitle}>
      <Suspense>
        <ForgotForm />
      </Suspense>
      <p className="mt-6 text-center text-sm">
        <Link href="/login" className="inline-flex items-center gap-1.5 font-semibold text-brand-600 hover:underline dark:text-brand-400">
          <ArrowLeft className="size-4" /> {m.auth.forgot.back}
        </Link>
      </p>
    </AuthShell>
  );
}
