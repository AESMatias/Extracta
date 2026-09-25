"use client";

import { UserPlus } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState, type FormEvent } from "react";

import { AuthShell, Divider, GoogleButton } from "@/components/auth-shell";
import { Alert, Button, Field } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { safeNext } from "@/lib/navigation";

function RegisterForm() {
  const params = useSearchParams();
  const router = useRouter();
  const { user, setUser } = useAuth();
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
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      {error && (
        <div className="mb-5">
          <Alert>{error}</Alert>
        </div>
      )}
      {google && (
        <>
          <GoogleButton label="Sign up with Google" />
          <Divider label="or with email" />
        </>
      )}
      <form onSubmit={onSubmit} className="space-y-4">
        <Field label="Name" name="name" autoComplete="name" placeholder="Ana Pérez" maxLength={120} />
        <Field label="Email" name="email" type="email" autoComplete="email" required placeholder="you@company.com" />
        <Field
          label="Password"
          name="password"
          type="password"
          autoComplete="new-password"
          required
          minLength={10}
          maxLength={128}
          placeholder="At least 10 characters"
          hint="Use 10 or more characters. A short phrase is easy to remember and hard to guess."
        />
        <Button type="submit" size="lg" className="w-full" loading={loading} icon={<UserPlus className="size-5" />}>
          Create free account
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-slate-600 dark:text-slate-400">
        Already have an account?{" "}
        <Link href="/login" className="font-semibold text-brand-600 hover:underline dark:text-brand-400">
          Sign in
        </Link>
      </p>
    </>
  );
}

export default function RegisterPage() {
  return (
    <AuthShell title="Create your account" subtitle="Free forever for 2 PDFs a day. No credit card.">
      <Suspense>
        <RegisterForm />
      </Suspense>
    </AuthShell>
  );
}
