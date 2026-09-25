"use client";

import { ArrowLeft, MailOpen, Send } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";

import { AuthShell } from "@/components/auth-shell";
import { Alert, Button, Field } from "@/components/ui";
import { api, ApiError } from "@/lib/api";

function ForgotForm() {
  const params = useSearchParams();
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
      setError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
    } finally {
      setLoading(false);
    }
  }

  if (sentTo) {
    return (
      <div className="space-y-6 text-center">
        <span className="mx-auto grid size-16 place-items-center rounded-2xl bg-brand-50 text-brand-600 ring-1 ring-brand-600/15 dark:bg-brand-500/10 dark:text-brand-300">
          <MailOpen className="size-8" />
        </span>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          If an account exists for <span className="font-semibold text-slate-900 dark:text-white">{sentTo}</span>, we sent it a
          link to choose a new password. It is valid for 1 hour. Check your spam folder if it does not arrive in a few minutes.
        </p>
        <Button variant="outline" className="w-full" onClick={() => setSentTo(null)}>
          Use another email
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
          label="Email"
          name="email"
          type="email"
          autoComplete="email"
          required
          placeholder="you@company.com"
          defaultValue={params.get("email") ?? ""}
        />
        <Button type="submit" size="lg" className="w-full" loading={loading} icon={<Send className="size-5" />}>
          Send reset link
        </Button>
      </form>
    </>
  );
}

export default function ForgotPasswordPage() {
  return (
    <AuthShell title="Forgot your password?" subtitle="Enter your email and we will send you a link to choose a new one.">
      <Suspense>
        <ForgotForm />
      </Suspense>
      <p className="mt-6 text-center text-sm">
        <Link href="/login" className="inline-flex items-center gap-1.5 font-semibold text-brand-600 hover:underline dark:text-brand-400">
          <ArrowLeft className="size-4" /> Back to sign in
        </Link>
      </p>
    </AuthShell>
  );
}
