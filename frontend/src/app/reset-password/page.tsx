"use client";

import { KeyRound } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent } from "react";

import { AuthShell } from "@/components/auth-shell";
import { useToast } from "@/components/toast";
import { Alert, Button, ButtonLink, Field, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { errorText } from "@/lib/errors";
import { useI18n } from "@/lib/i18n";
import { useAuth } from "@/lib/auth";
import { takeTokenFromHash } from "@/lib/navigation";

export default function ResetPasswordPage() {
  const router = useRouter();
  const { setUser } = useAuth();
  const { toast } = useToast();
  const { m, locale } = useI18n();
  const r = m.auth.reset;
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
      toast("success", r.done, r.doneText);
      router.replace("/app");
    } catch (err) {
      setError(errorText(err, locale, m.common.somethingWrong));
      setLoading(false);
    }
  }

  if (ready === null) {
    return (
      <AuthShell title={r.title} subtitle={r.wait}>
        <div className="grid h-24 place-items-center">
          <Spinner className="size-8" />
        </div>
      </AuthShell>
    );
  }

  if (!ready) {
    return (
      <AuthShell title={r.incompleteTitle} subtitle={r.incompleteText}>
        <ButtonLink href="/forgot-password" size="lg" className="w-full">
          {r.newLink}
        </ButtonLink>
      </AuthShell>
    );
  }

  return (
    <AuthShell title={r.title} subtitle={r.subtitle}>
      {error && (
        <div className="mb-5 space-y-3">
          <Alert>{error}</Alert>
          <ButtonLink href="/forgot-password" variant="outline" size="sm" className="w-full">
            {r.askNew}
          </ButtonLink>
        </div>
      )}
      <form onSubmit={onSubmit} className="space-y-4">
        <Field
          label={r.newPassword}
          name="password"
          type="password"
          autoComplete="new-password"
          required
          minLength={10}
          maxLength={128}
          placeholder={m.auth.passwordPlaceholder}
          hint={m.auth.passwordHint}
        />
        <Field
          label={r.repeat}
          name="confirm"
          type="password"
          autoComplete="new-password"
          required
          minLength={10}
          maxLength={128}
          error={mismatch ? r.mismatch : null}
        />
        <Button type="submit" size="lg" className="w-full" loading={loading} icon={<KeyRound className="size-5" />}>
          {r.submit}
        </Button>
      </form>
    </AuthShell>
  );
}
