"use client";

import { MailCheck, Send } from "lucide-react";
import { useEffect, useState } from "react";

import { api, type User } from "@/lib/api";
import { errorText } from "@/lib/errors";
import { fill, useI18n } from "@/lib/i18n";

import { Alert, Button } from "./ui";

let requiredPromise: Promise<boolean> | null = null;

/** Whether the server requires a verified email to upload and pay (asked once per page load). */
export function useVerificationRequired(): boolean {
  const [required, setRequired] = useState(true); // assume yes until the server answers
  useEffect(() => {
    requiredPromise ??= api.providers().then(
      (p) => p.email_verification,
      () => true,
    );
    let active = true;
    void requiredPromise.then((value) => active && setRequired(value));
    return () => {
      active = false;
    };
  }, []);
  return required;
}

export function VerifyEmailBanner({ user }: { user: User }) {
  const required = useVerificationRequired();
  const { m, locale } = useI18n();
  const b = m.auth.banner;
  const [state, setState] = useState<"idle" | "sending" | "sent">("idle");
  const [error, setError] = useState<string | null>(null);

  if (user.email_verified) return null;

  async function resend() {
    setState("sending");
    setError(null);
    try {
      await api.resendVerification();
      setState("sent");
    } catch (err) {
      setError(errorText(err, locale, b.sendFailed));
      setState("idle");
    }
  }

  return (
    <Alert
      tone={required ? "amber" : "brand"}
      title={b.title}
      action={
        state === "sent" ? (
          <span className="inline-flex items-center gap-1.5 text-sm font-semibold">
            <MailCheck className="size-4" /> {b.sent}
          </span>
        ) : (
          <Button size="sm" variant="outline" onClick={resend} loading={state === "sending"} icon={<Send className="size-3.5" />}>
            {b.resend}
          </Button>
        )
      }
    >
      {state === "sent"
        ? fill(b.sentText, { email: user.email })
        : fill(required ? b.required : b.optional, { email: user.email })}
      {error && <span className="mt-1 block font-medium">{error}</span>}
    </Alert>
  );
}
