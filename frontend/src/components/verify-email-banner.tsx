"use client";

import { MailCheck, Send } from "lucide-react";
import { useEffect, useState } from "react";

import { api, ApiError, type User } from "@/lib/api";

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
      setError(err instanceof ApiError ? err.message : "The email could not be sent. Try again later.");
      setState("idle");
    }
  }

  return (
    <Alert
      tone={required ? "amber" : "brand"}
      title="Confirm your email address"
      action={
        state === "sent" ? (
          <span className="inline-flex items-center gap-1.5 text-sm font-semibold">
            <MailCheck className="size-4" /> Sent
          </span>
        ) : (
          <Button size="sm" variant="outline" onClick={resend} loading={state === "sending"} icon={<Send className="size-3.5" />}>
            Resend email
          </Button>
        )
      }
    >
      {state === "sent"
        ? `A new link is on its way to ${user.email}. Check your spam folder too.`
        : required
          ? `We sent a link to ${user.email}. Open it to start uploading PDFs and to buy plans.`
          : `We sent a link to ${user.email}. Confirming it helps you recover your account.`}
      {error && <span className="mt-1 block font-medium">{error}</span>}
    </Alert>
  );
}
