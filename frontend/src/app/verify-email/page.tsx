"use client";

import { ArrowRight, MailCheck, MailX } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { AuthShell } from "@/components/auth-shell";
import { Alert, ButtonLink, Spinner } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { takeTokenFromHash } from "@/lib/navigation";

type State = { kind: "checking" } | { kind: "done" } | { kind: "error"; message: string };

export default function VerifyEmailPage() {
  const { user, refresh } = useAuth();
  const [state, setState] = useState<State>({ kind: "checking" });
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return; // the link works once: never post it twice
    started.current = true;
    const token = takeTokenFromHash();
    if (!token) {
      // Reading the link from the address bar is what this effect is for.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setState({ kind: "error", message: "This link is incomplete. Open it again from the email, or ask for a new one." });
      return;
    }
    api.verifyEmail(token).then(
      () => {
        setState({ kind: "done" });
        void refresh();
      },
      (err: unknown) =>
        setState({ kind: "error", message: err instanceof ApiError ? err.message : "The email could not be confirmed. Try again." }),
    );
  }, [refresh]);

  if (state.kind === "checking") {
    return (
      <AuthShell title="Confirming your email" subtitle="One moment…">
        <div className="grid h-24 place-items-center">
          <Spinner className="size-8" />
        </div>
      </AuthShell>
    );
  }

  if (state.kind === "done") {
    return (
      <AuthShell title="Email confirmed" subtitle="Thanks! Your account is ready to process documents.">
        <div className="flex flex-col items-center gap-6 text-center">
          <span className="grid size-16 place-items-center rounded-2xl bg-emerald-50 text-emerald-600 ring-1 ring-emerald-600/15 dark:bg-emerald-500/10 dark:text-emerald-300">
            <MailCheck className="size-8" />
          </span>
          <ButtonLink href={user ? "/app" : "/login"} size="lg" className="w-full" icon={<ArrowRight className="size-5" />}>
            {user ? "Go to the dashboard" : "Sign in"}
          </ButtonLink>
        </div>
      </AuthShell>
    );
  }

  return (
    <AuthShell title="This link did not work" subtitle="Links expire after 3 days and only work for the address they were sent to.">
      <div className="space-y-5">
        <Alert title="Could not confirm the email">
          <span className="flex items-center gap-2">
            <MailX className="size-4 shrink-0" /> {state.message}
          </span>
        </Alert>
        <ButtonLink href={user ? "/account" : "/login?next=/account"} variant="outline" className="w-full">
          {user ? "Send a new link from your account" : "Sign in to get a new link"}
        </ButtonLink>
      </div>
    </AuthShell>
  );
}
