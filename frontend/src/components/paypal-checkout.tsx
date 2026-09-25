"use client";

import { ShieldCheck } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { api, ApiError, type BillingMode, type Plan, type User } from "@/lib/api";

import { Alert, Spinner } from "./ui";

interface PayPalButtons {
  render: (container: HTMLElement) => Promise<void>;
  close?: () => Promise<void>;
}
interface ApproveData {
  orderID?: string;
  subscriptionID?: string;
}
interface PayPalNamespace {
  Buttons: (options: {
    style?: Record<string, string | number>;
    createOrder?: () => Promise<string>;
    createSubscription?: () => Promise<string>;
    onApprove: (data: ApproveData) => Promise<void>;
    onError: (error: unknown) => void;
    onCancel?: () => void;
  }) => PayPalButtons;
}

declare global {
  interface Window {
    paypalCheckout?: PayPalNamespace;
    paypalSubscriptions?: PayPalNamespace;
  }
}

// One-time payments and subscriptions need the SDK loaded with different parameters, so each gets
// its own copy under its own name (PayPal's data-namespace attribute).
const SDK = {
  once: { namespace: "paypalCheckout", params: "intent=capture" },
  monthly: { namespace: "paypalSubscriptions", params: "vault=true&intent=subscription" },
} as const;
const sdkPromises: Partial<Record<BillingMode, Promise<PayPalNamespace>>> = {};

function loadSdk(clientId: string, currency: string, mode: BillingMode): Promise<PayPalNamespace> {
  // PayPal's official JS SDK. The page's Content-Security-Policy allows paypal.com.
  const { namespace, params } = SDK[mode];
  sdkPromises[mode] ??= new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = `https://www.paypal.com/sdk/js?client-id=${encodeURIComponent(clientId)}&currency=${currency}&${params}&components=buttons`;
    script.async = true;
    script.dataset.namespace = namespace;
    script.onload = () => {
      const sdk = window[namespace];
      if (sdk) resolve(sdk);
      else reject(new Error("PayPal SDK missing"));
    };
    script.onerror = () => {
      delete sdkPromises[mode];
      reject(new Error("PayPal SDK failed to load"));
    };
    document.head.append(script);
  });
  return sdkPromises[mode];
}

/** PayPal's buttons for one plan. `onPaid` gets the updated account; `activating` means PayPal is still confirming. */
export function PayPalCheckout({
  plan,
  mode,
  onPaid,
}: {
  plan: Plan;
  mode: BillingMode;
  onPaid: (user: User, activating: boolean) => void;
}) {
  const container = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<"loading" | "ready" | "disabled" | "error">("loading");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let buttons: PayPalButtons | null = null;
    const fail = (err: unknown, fallback: string) => setError(err instanceof ApiError ? err.message : fallback);

    (async () => {
      try {
        const config = await api.billingConfig();
        if (!config.enabled || !config.client_id) {
          if (!cancelled) setState("disabled");
          return;
        }
        const paypal = await loadSdk(config.client_id, config.currency ?? "USD", mode);
        if (cancelled || !container.current) return;
        const style = { layout: "vertical", shape: "pill", color: "gold", height: 44 };
        buttons =
          mode === "monthly"
            ? paypal.Buttons({
                style: { ...style, label: "subscribe" },
                createSubscription: async () => {
                  setError(null);
                  try {
                    return (await api.createSubscription(plan.id)).subscription_id;
                  } catch (err) {
                    fail(err, "The subscription could not be started.");
                    throw err;
                  }
                },
                onApprove: async ({ subscriptionID }) => {
                  try {
                    const { user, status } = await api.activateSubscription(subscriptionID ?? "");
                    onPaid(user, status !== "ACTIVE");
                  } catch (err) {
                    fail(err, "The subscription could not be confirmed. It will activate automatically in a few minutes.");
                  }
                },
                onError: () => setError((current) => current ?? "PayPal reported an error. Nothing was charged; please try again."),
              })
            : paypal.Buttons({
                style: { ...style, label: "pay" },
                createOrder: async () => {
                  setError(null);
                  try {
                    return (await api.createOrder(plan.id)).order_id;
                  } catch (err) {
                    fail(err, "The payment could not be started.");
                    throw err;
                  }
                },
                onApprove: async ({ orderID }) => {
                  try {
                    const { user } = await api.captureOrder(orderID ?? "");
                    onPaid(user, false);
                  } catch (err) {
                    fail(err, "The payment could not be confirmed.");
                  }
                },
                onError: () => setError((current) => current ?? "PayPal reported an error. No money was taken; please try again."),
              });
        await buttons.render(container.current);
        if (!cancelled) setState("ready");
      } catch {
        if (!cancelled) setState("error");
      }
    })();

    return () => {
      cancelled = true;
      void buttons?.close?.();
    };
  }, [plan.id, mode, onPaid]);

  if (state === "disabled") {
    return (
      <Alert tone="amber" title="Payments are not enabled yet">
        The site owner has not configured PayPal. Contact them to upgrade your plan.
      </Alert>
    );
  }
  if (state === "error") {
    return <Alert title="PayPal could not be loaded">Check your connection or disable content blockers, then reload the page.</Alert>;
  }

  return (
    <div>
      {state === "loading" && (
        <div className="grid h-28 place-items-center">
          <Spinner />
        </div>
      )}
      <div ref={container} className="min-h-0" />
      {error && (
        <div className="mt-3">
          <Alert>{error}</Alert>
        </div>
      )}
      <p className="mt-3 flex items-center justify-center gap-1.5 text-xs text-slate-500">
        <ShieldCheck className="size-3.5" /> Secure payment processed by PayPal. We never see your card.
      </p>
    </div>
  );
}
