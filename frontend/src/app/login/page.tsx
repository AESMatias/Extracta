"use client";

import { LogIn } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState, type FormEvent } from "react";

import { AuthShell, Divider, GoogleButton } from "@/components/auth-shell";
import { Alert, Button, Field } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { errorText } from "@/lib/errors";
import { useI18n } from "@/lib/i18n";
import { safeNext } from "@/lib/navigation";

function LoginForm() {
  const params = useSearchParams();
  const router = useRouter();
  const { user, setUser } = useAuth();
  const { m, locale } = useI18n();
  const a = m.auth;
  const googleError = params.get("error") as keyof typeof a.login.errors | null;
  const [google, setGoogle] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const next = safeNext(params.get("next"));

  useEffect(() => {
    api.providers().then((p) => setGoogle(p.google), () => undefined);
  }, []);

  useEffect(() => {
    if (user) router.replace(next);
  }, [user, next, router]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setLoading(true);
    setError(null);
    try {
      const { user: signedIn } = await api.login({ email: String(form.get("email")), password: String(form.get("password")) });
      setUser(signedIn);
      router.replace(next);
    } catch (err) {
      setError(errorText(err, locale, m.common.somethingWrong));
    } finally {
      setLoading(false);
    }
  }

  const shownError = error ?? (googleError ? (a.login.errors[googleError] ?? null) : null);
  return (
    <>
      {shownError && (
        <div className="mb-5">
          <Alert>{shownError}</Alert>
        </div>
      )}
      {google && (
        <>
          <GoogleButton label={a.google} />
          <Divider label={a.orEmail} />
        </>
      )}
      <form onSubmit={onSubmit} className="space-y-4">
        <Field label={a.email} name="email" type="email" autoComplete="email" required placeholder={a.emailPlaceholder} />
        <div>
          <Field label={a.password} name="password" type="password" autoComplete="current-password" required placeholder="••••••••••" />
          <p className="mt-3 text-center text-sm">
            <Link href="/forgot-password" className="font-medium text-brand-600 hover:underline dark:text-brand-400">
              {a.login.forgot}
            </Link>
          </p>
        </div>
        <Button type="submit" size="lg" className="w-full" loading={loading} icon={<LogIn className="size-5" />}>
          {a.login.submit}
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-slate-600 dark:text-slate-400">
        {a.login.newHere}{" "}
        <Link href={`/register${next !== "/app" ? `?next=${encodeURIComponent(next)}` : ""}`} className="font-semibold text-brand-600 hover:underline dark:text-brand-400">
          {a.login.create}
        </Link>
      </p>
    </>
  );
}

export default function LoginPage() {
  const { m } = useI18n();
  return (
    <AuthShell title={m.auth.login.title} subtitle={m.auth.login.subtitle}>
      <Suspense>
        <LoginForm />
      </Suspense>
    </AuthShell>
  );
}
