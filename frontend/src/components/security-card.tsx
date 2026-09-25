"use client";

import { KeyRound, ShieldCheck } from "lucide-react";
import { useState, type FormEvent } from "react";

import { api, ApiError, type User } from "@/lib/api";
import { useAuth } from "@/lib/auth";

import { useToast } from "./toast";
import { Alert, Button, Card, Field } from "./ui";

/** Change the password, or add one to an account that only signs in with Google. */
export function SecurityCard({ user }: { user: User }) {
  const { setUser } = useAuth();
  const { toast } = useToast();
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mismatch, setMismatch] = useState(false);
  const [loading, setLoading] = useState(false);
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
      toast("success", adding ? "Password added" : "Password changed", "Other devices were signed out.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className="p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="flex items-center gap-2 text-lg font-semibold">
          <ShieldCheck className="size-5 text-emerald-500" /> Security
        </h2>
        {!open && (
          <Button size="sm" variant="outline" onClick={() => setOpen(true)} icon={<KeyRound className="size-3.5" />}>
            {adding ? "Add a password" : "Change password"}
          </Button>
        )}
      </div>
      <p className="mt-1 text-sm text-slate-500">
        {adding
          ? "You sign in with Google. Add a password to also sign in with your email."
          : "Changing your password signs you out on every other device."}
      </p>

      {open && (
        <form onSubmit={onSubmit} className="mt-5 space-y-4">
          {error && <Alert>{error}</Alert>}
          {!adding && (
            <Field label="Current password" name="current_password" type="password" autoComplete="current-password" required />
          )}
          <Field
            label="New password"
            name="new_password"
            type="password"
            autoComplete="new-password"
            required
            minLength={10}
            maxLength={128}
            hint="10 or more characters."
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
          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={loading}>
              {adding ? "Add password" : "Save new password"}
            </Button>
          </div>
        </form>
      )}
    </Card>
  );
}
