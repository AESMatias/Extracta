"use client";

import { KeyRound, ShieldCheck } from "lucide-react";
import { useState, type FormEvent } from "react";

import { api, type User } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { errorText } from "@/lib/errors";
import { useI18n } from "@/lib/i18n";

import { PasswordStrength } from "./password-strength";

import { useToast } from "./toast";
import { Alert, Button, Card, Field } from "./ui";

/** Change the password, or add one to an account that only signs in with Google. */
export function SecurityCard({ user }: { user: User }) {
  const { setUser } = useAuth();
  const { toast } = useToast();
  const { m, locale } = useI18n();
  const s = m.securityCard;
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mismatch, setMismatch] = useState(false);
  const [loading, setLoading] = useState(false);
  const [password, setPassword] = useState("");
  const adding = !user.has_password;

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const password = String(form.get("new_password"));
    if (password !== String(form.get("confirm"))) {
      setMismatch(true);
      return;
    }
    setMismatch(false);
    setLoading(true);
    setError(null);
    try {
      const { user: updated } = await api.changePassword({
        current_password: adding ? undefined : String(form.get("current_password")),
        new_password: password,
      });
      setUser(updated);
      setOpen(false);
      toast("success", adding ? s.added : s.changed, s.othersOut);
    } catch (err) {
      setError(errorText(err, locale, m.common.somethingWrong));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className="p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="flex items-center gap-2 text-lg font-semibold">
          <ShieldCheck className="size-5 text-emerald-500" /> {s.title}
        </h2>
        {!open && (
          <Button size="sm" variant="outline" onClick={() => setOpen(true)} icon={<KeyRound className="size-3.5" />}>
            {adding ? s.add : s.change}
          </Button>
        )}
      </div>
      <p className="mt-1 text-sm text-slate-500">
        {adding ? s.googleOnly : s.signsOut}
      </p>

      {open && (
        <form onSubmit={onSubmit} className="mt-5 space-y-4">
          {error && <Alert>{error}</Alert>}
          {!adding && (
            <Field label={s.current} name="current_password" type="password" autoComplete="current-password" required />
          )}
          <div>
            <Field
              label={s.newPassword}
              name="new_password"
              type="password"
              autoComplete="new-password"
              required
              minLength={10}
              maxLength={128}
              onChange={(e) => setPassword(e.target.value)}
            />
            <PasswordStrength password={password} email={user.email} name={user.name ?? ""} />
          </div>
          <Field
            label={s.repeat}
            name="confirm"
            type="password"
            autoComplete="new-password"
            required
            minLength={10}
            maxLength={128}
            error={mismatch ? s.mismatch : null}
          />
          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
              {m.common.cancel}
            </Button>
            <Button type="submit" loading={loading}>
              {adding ? s.submitAdd : s.submitChange}
            </Button>
          </div>
        </form>
      )}
    </Card>
  );
}
