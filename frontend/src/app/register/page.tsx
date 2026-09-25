"use client";

import { UserPlus } from "lucide-react";
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

const LINK = "font-semibold text-brand-600 hover:underline dark:text-brand-400";

function RegisterForm() {
  const params = useSearchParams();
  const router = useRouter();
  const { user, setUser } = useAuth();
  const { m, locale } = useI18n();
  const a = m.auth;
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
      const { user: created } = await api.register({
        name: String(form.get("name")),
        email: String(form.get("email")),
        password: String(form.get("password")),
      });
      setUser(created);
      router.replace(next);
    } catch (err) {
      setError(errorText(err, locale, m.common.somethingWrong));
    } finally {
      setLoading(false);
    }
  }

  const [before, afterTerms] = a.register.consent.split("{terms}");
  const [middle, after] = (afterTerms ?? "").split("{privacy}");
  return (
    <>
      {error && (
        <div className="mb-5">
          <Alert>{error}</Alert>
        </div>
      )}
      {google && (
        <>
          <GoogleButton label={a.googleSignUp} />
          <Divider label={a.orEmail} />
        </>
      )}
      <form onSubmit={onSubmit} className="space-y-4">
        <Field label={a.name} name="name" autoComplete="name" placeholder="Ana Pérez" maxLength={120} />
        <Field label={a.email} name="email" type="email" autoComplete="email" required placeholder={a.emailPlaceholder} />
        <Field
          label={a.password}
          name="password"
          type="password"
          autoComplete="new-password"
          required
          minLength={10}
          maxLength={128}
          placeholder={a.passwordPlaceholder}
          hint={a.passwordHint}
        />
        <Button type="submit" size="lg" className="w-full" loading={loading} icon={<UserPlus className="size-5" />}>
          {a.register.submit}
        </Button>
        <p className="text-center text-xs text-slate-500">
          {before}
          <Link href="/terms" className={LINK}>
            {a.register.terms}
          </Link>
          {middle}
          <Link href="/privacy" className={LINK}>
            {a.register.privacy}
          </Link>
          {after}
        </p>
      </form>
      <p className="mt-6 text-center text-sm text-slate-600 dark:text-slate-400">
        {a.register.have}{" "}
        <Link href="/login" className={LINK}>
          {m.common.signIn}
        </Link>
      </p>
    </>
  );
}

export default function RegisterPage() {
  const { m } = useI18n();
  return (
    <AuthShell title={m.auth.register.title} subtitle={m.auth.register.subtitle}>
      <Suspense>
        <RegisterForm />
      </Suspense>
    </AuthShell>
  );
}
