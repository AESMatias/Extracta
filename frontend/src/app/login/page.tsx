"use client";

import { LogIn } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState, type FormEvent } from "react";

import { AuthShell, Divider, GoogleButton } from "@/components/auth-shell";
import { Alert, Button, Field } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { safeNext } from "@/lib/navigation";

const GOOGLE_ERRORS: Record<string, string> = {
  google_cancelled: "Google sign-in was cancelled. Try again.",
  google_failed: "Google sign-in failed. Try again or use your email and password.",
  account_blocked: "This account cannot sign in. Contact the administrator.",
};

function LoginForm() {
  const params = useSearchParams();
  const router = useRouter();
  const { user, setUser } = useAuth();
  const [google, setGoogle] = useState(false);
  const [error, setError] = useState<string | null>(GOOGLE_ERRORS[params.get("error") ?? ""] ?? null);
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
          <GoogleButton />
          <Divider label="or with email" />
        </>
      )}
      <form onSubmit={onSubmit} className="space-y-4">
        <Field label="Email" name="email" type="email" autoComplete="email" required placeholder="you@company.com" />
        <Field label="Password" name="password" type="password" autoComplete="current-password" required placeholder="••••••••••" />
        <Button type="submit" size="lg" className="w-full" loading={loading} icon={<LogIn className="size-5" />}>
          Sign in
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-slate-600 dark:text-slate-400">
        New to Extracta?{" "}
        <Link href={`/register${next !== "/app" ? `?next=${encodeURIComponent(next)}` : ""}`} className="font-semibold text-brand-600 hover:underline dark:text-brand-400">
          Create a free account
        </Link>
      </p>
    </>
  );
}

export default function LoginPage() {
  return (
    <AuthShell title="Welcome back" subtitle="Sign in to process your PDFs.">
      <Suspense>
        <LoginForm />
      </Suspense>
    </AuthShell>
  );
}
