"use client";

import { KeyRound } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent } from "react";

import { AuthShell } from "@/components/auth-shell";
import { useToast } from "@/components/toast";
import { Alert, Button, ButtonLink, Field, Spinner } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { takeTokenFromHash } from "@/lib/navigation";

export default function ResetPasswordPage() {
  const router = useRouter();
  const { setUser } = useAuth();
  const { toast } = useToast();
  const token = useRef<string | null>(null);
  const [ready, setReady] = useState<boolean | null>(null); // null: still reading the link
  const [error, setError] = useState<string | null>(null);
  const [mismatch, setMismatch] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    token.current ??= takeTokenFromHash(); // read once: the link is removed from the address bar
    setReady(Boolean(token.current));
  }, []);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const password = String(form.get("password"));
    if (password !== String(form.get("confirm"))) {
      setMismatch(true);
      return;
    }
    setMismatch(false);
    setLoading(true);
    setError(null);
    try {
      const { user } = await api.resetPassword(token.current ?? "", password);
      setUser(user);
      toast("success", "Password changed", "You are signed in. Other devices were signed out.");
      router.replace("/app");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
      setLoading(false);
    }
  }

  if (ready === null) {
    return (
      <AuthShell title="Choose a new password" subtitle="One moment…">
        <div className="grid h-24 place-items-center">
          <Spinner className="size-8" />
        </div>
      </AuthShell>
    );
  }

  if (!ready) {
    return (
      <AuthShell title="This link is incomplete" subtitle="Open the link from the email again, or ask for a new one.">
        <ButtonLink href="/forgot-password" size="lg" className="w-full">
          Send me a new link
        </ButtonLink>
      </AuthShell>
    );
  }

  return (
    <AuthShell title="Choose a new password" subtitle="You will be signed in right after, and signed out everywhere else.">
      {error && (
        <div className="mb-5 space-y-3">
          <Alert>{error}</Alert>
          <ButtonLink href="/forgot-password" variant="outline" size="sm" className="w-full">
            Ask for a new link
          </ButtonLink>
        </div>
      )}
      <form onSubmit={onSubmit} className="space-y-4">
        <Field
          label="New password"
          name="password"
          type="password"
          autoComplete="new-password"
          required
          minLength={10}
          maxLength={128}
          placeholder="At least 10 characters"
          hint="Use 10 or more characters. A short phrase is easy to remember and hard to guess."
        />
        <Field
          label="Repeat the new password"
          name="confirm"
          type="password"
          autoComplete="new-password"
          required
          minLength={10}
          maxLength={128}
          error={mismatch ? "The two passwords are different." : null}
        />
        <Button type="submit" size="lg" className="w-full" loading={loading} icon={<KeyRound className="size-5" />}>
          Save new password
        </Button>
      </form>
    </AuthShell>
  );
}
