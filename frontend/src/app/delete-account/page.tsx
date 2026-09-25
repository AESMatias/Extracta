"use client";

import { ArrowRight, Mail, MailOpen, Send, Trash2, UserRound } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";

import { AuthShell } from "@/components/auth-shell";
import { useToast } from "@/components/toast";
import { Alert, Button, ButtonLink, Field } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { errorText } from "@/lib/errors";
import { fill, useI18n } from "@/lib/i18n";
import { CONTACT_EMAIL } from "@/lib/legal";
import { takeTokenFromHash } from "@/lib/navigation";

/**
 * Three ways to delete an account: from the account page (signed in), with a link sent to the
 * account's email (this form), or by writing to the contact address (done by hand within 48 h).
 * Opening the emailed link lands here with #token=... and asks for a last confirmation.
 */
export default function DeleteAccountPage() {
  const { m, locale } = useI18n();
  const d = m.deletion;
  const { user, setUser } = useAuth();
  const { toast } = useToast();
  const token = useRef<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [sentTo, setSentTo] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    token.current ??= takeTokenFromHash();
    if (token.current) setConfirming(true); // the emailed link: ask for a last confirmation
  }, []);

  async function request(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const email = String(new FormData(event.currentTarget).get("email")).trim();
    setLoading(true);
    setError(null);
    try {
      await api.requestAccountDeletion(email);
      setSentTo(email);
    } catch (err) {
      setError(errorText(err, locale, m.common.somethingWrong));
    } finally {
      setLoading(false);
    }
  }

  async function confirm() {
    setLoading(true);
    setError(null);
    try {
      await api.confirmAccountDeletion(token.current ?? "");
      setUser(null);
      setDone(true);
      toast("success", d.deleted, d.deletedText);
    } catch {
      setConfirming(false);
      setError(d.linkFailed);
    } finally {
      setLoading(false);
    }
  }

  if (done) {
    return (
      <AuthShell title={d.deleted} subtitle={d.deletedText}>
        <ButtonLink href="/" size="lg" className="w-full" icon={<ArrowRight className="size-5" />}>
          {m.notFound.back}
        </ButtonLink>
      </AuthShell>
    );
  }

  if (confirming) {
    return (
      <AuthShell title={d.confirmTitle} subtitle={d.confirmText}>
        <Button variant="danger" size="lg" className="w-full" loading={loading} onClick={confirm} icon={<Trash2 className="size-5" />}>
          {d.confirmButton}
        </Button>
      </AuthShell>
    );
  }

  const [before, after] = d.manual.split("{contact}");
  return (
    <AuthShell title={d.pageTitle} subtitle={d.pageSubtitle}>
      <div className="space-y-8">
        {error && <Alert>{error}</Alert>}

        {user && (
          <Alert
            tone="brand"
            title={d.signedIn}
            action={
              <ButtonLink href="/account" size="sm" variant="outline" icon={<UserRound className="size-4" />}>
                {d.goAccount}
              </ButtonLink>
            }
          />
        )}

        <section>
          <h2 className="font-semibold">{d.formTitle}</h2>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{d.formText}</p>
          {sentTo ? (
            <p className="mt-4 flex gap-2 text-sm text-slate-700 dark:text-slate-300">
              <MailOpen className="mt-0.5 size-4 shrink-0 text-brand-500" /> {fill(d.sent, { email: sentTo })}
            </p>
          ) : (
            <form onSubmit={request} className="mt-4 space-y-3">
              <Field label={m.auth.email} name="email" type="email" autoComplete="email" required placeholder={m.auth.emailPlaceholder} />
              <Button type="submit" variant="outline" className="w-full" loading={loading} icon={<Send className="size-4" />}>
                {d.send}
              </Button>
            </form>
          )}
        </section>

        <section className="border-t border-slate-200 pt-6 dark:border-slate-800">
          <h2 className="font-semibold">{d.manualTitle}</h2>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            {before}
            <a href={`mailto:${CONTACT_EMAIL}?subject=Delete%20my%20Extracta%20account`} className="inline-flex items-center gap-1 font-semibold text-brand-600 hover:underline dark:text-brand-400">
              <Mail className="size-3.5" /> {CONTACT_EMAIL}
            </a>
            {after}
          </p>
        </section>
      </div>
    </AuthShell>
  );
}
