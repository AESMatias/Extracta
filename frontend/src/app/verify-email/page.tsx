"use client";

import { ArrowRight, MailCheck, MailX } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { AuthShell } from "@/components/auth-shell";
import { Alert, ButtonLink, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { errorText } from "@/lib/errors";
import { useI18n } from "@/lib/i18n";
import { useAuth } from "@/lib/auth";
import { takeTokenFromHash } from "@/lib/navigation";

type State = { kind: "checking" } | { kind: "done" } | { kind: "error"; message: string | null };

export default function VerifyEmailPage() {
  const { user, refresh } = useAuth();
  const { m, locale } = useI18n();
  const v = m.auth.verify;
  const [state, setState] = useState<State>({ kind: "checking" });
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return; // the link works once: never post it twice
    started.current = true;
    const token = takeTokenFromHash();
    if (!token) {
      // Reading the link from the address bar is what this effect is for.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setState({ kind: "error", message: null });
      return;
    }
    api.verifyEmail(token).then(
      () => {
        setState({ kind: "done" });
        void refresh();
      },
      (err: unknown) => setState({ kind: "error", message: errorText(err, locale, v.failAlert) }),
    );
  }, [refresh, locale, v.failAlert]);

  if (state.kind === "checking") {
    return (
      <AuthShell title={v.checking} subtitle={v.wait}>
        <div className="grid h-24 place-items-center">
          <Spinner className="size-8" />
        </div>
      </AuthShell>
    );
  }

  if (state.kind === "done") {
    return (
      <AuthShell title={v.doneTitle} subtitle={v.doneText}>
        <div className="flex flex-col items-center gap-6 text-center">
          <span className="grid size-16 place-items-center bg-emerald-50 text-emerald-600 ring-1 ring-emerald-600/15 dark:bg-emerald-500/10 dark:text-emerald-300">
            <MailCheck className="size-8" />
          </span>
          <ButtonLink href={user ? "/app" : "/login"} size="lg" className="w-full" icon={<ArrowRight className="size-5" />}>
            {user ? v.goDashboard : m.common.signIn}
          </ButtonLink>
        </div>
      </AuthShell>
    );
  }

  return (
    <AuthShell title={v.failTitle} subtitle={v.failText}>
      <div className="space-y-5">
        <Alert title={v.failAlert}>
          <span className="flex items-center gap-2">
            <MailX className="size-4 shrink-0" /> {state.message ?? v.incomplete}
          </span>
        </Alert>
        <ButtonLink href={user ? "/account" : "/login?next=/account"} variant="outline" className="w-full">
          {user ? v.newFromAccount : v.signInForNew}
        </ButtonLink>
      </div>
    </AuthShell>
  );
}
