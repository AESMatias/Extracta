"use client";

import { TriangleAlert, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { api, type User } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { errorText } from "@/lib/errors";
import { fill, useI18n } from "@/lib/i18n";

import { useToast } from "./toast";
import { Alert, Button, Card, Field } from "./ui";

/** The danger zone: confirm with the password (or the email, for Google-only accounts). */
export function DeleteAccountCard({ user }: { user: User }) {
  const { m, locale } = useI18n();
  const d = m.deletion;
  const { setUser } = useAuth();
  const { toast } = useToast();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = String(new FormData(event.currentTarget).get("confirm") ?? "");
    setLoading(true);
    setError(null);
    try {
      await api.deleteAccount(user.has_password ? { password: value } : { email: value });
      setUser(null);
      toast("success", d.deleted, d.deletedText);
      router.replace("/");
    } catch (err) {
      setError(errorText(err, locale, m.common.somethingWrong));
      setLoading(false);
    }
  }

  return (
    <Card className="border-rose-200 p-6 dark:border-rose-500/30">
      <h2 className="flex items-center gap-2 text-lg font-semibold text-rose-700 dark:text-rose-300">
        <TriangleAlert className="size-5" /> {d.danger}
      </h2>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{d.dangerText}</p>
      {open ? (
        <form onSubmit={onSubmit} className="mt-5 space-y-4">
          {error && <Alert>{error}</Alert>}
          <Field
            label={user.has_password ? d.confirmPassword : fill(d.confirmEmail, { email: user.email })}
            name="confirm"
            type={user.has_password ? "password" : "email"}
            autoComplete={user.has_password ? "current-password" : "off"}
            required
          />
          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
              {m.common.cancel}
            </Button>
            <Button type="submit" variant="danger" loading={loading} icon={<Trash2 className="size-4" />}>
              {d.confirm}
            </Button>
          </div>
        </form>
      ) : (
        <Button variant="outline" className="mt-5" onClick={() => setOpen(true)} icon={<Trash2 className="size-4" />}>
          {d.start}
        </Button>
      )}
    </Card>
  );
}
