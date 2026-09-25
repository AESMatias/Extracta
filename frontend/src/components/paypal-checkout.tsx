"use client";

import { ShieldCheck } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { api, ApiError, type Plan, type User } from "@/lib/api";

import { Alert, Spinner } from "./ui";

interface PayPalButtons {
  render: (container: HTMLElement) => Promise<void>;
  close?: () => Promise<void>;
}
interface PayPalNamespace {
  Buttons: (options: {
    style?: Record<string, string | number>;
    createOrder: () => Promise<string>;
    onApprove: (data: { orderID: string }) => Promise<void>;
    onError: (error: unknown) => void;
    onCancel?: () => void;
  }) => PayPalButtons;
}

declare global {
  interface Window {
    paypal?: PayPalNamespace;
  }
}

let sdkPromise: Promise<PayPalNamespace> | null = null;

function loadSdk(clientId: string, currency: string): Promise<PayPalNamespace> {
  // PayPal's official JS SDK, loaded once. The page's Content-Security-Policy allows paypal.com.
  sdkPromise ??= new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = `https://www.paypal.com/sdk/js?client-id=${encodeURIComponent(clientId)}&currency=${currency}&intent=capture&components=buttons`;
    script.async = true;
    script.onload = () => (window.paypal ? resolve(window.paypal) : reject(new Error("PayPal SDK missing")));
    script.onerror = () => {
      sdkPromise = null;
      reject(new Error("PayPal SDK failed to load"));
    };
    document.head.append(script);
  });
  return sdkPromise;
}

export function PayPalCheckout({ plan, onPaid }: { plan: Plan; onPaid: (user: User) => void }) {
  const container = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<"loading" | "ready" | "disabled" | "error">("loading");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let buttons: PayPalButtons | null = null;

    (async () => {
      try {
        const config = await api.billingConfig();
        if (!config.enabled || !config.client_id) {
          if (!cancelled) setState("disabled");
          return;
        }
        const paypal = await loadSdk(config.client_id, config.currency ?? "USD");
        if (cancelled || !container.current) return;
        buttons = paypal.Buttons({
          style: { layout: "vertical", shape: "pill", color: "gold", label: "pay", height: 44 },
          createOrder: async () => (await api.createOrder(plan.id)).order_id,
          onApprove: async ({ orderID }) => {
            try {
              const { user } = await api.captureOrder(orderID);
              onPaid(user);
            } catch (err) {
              setError(err instanceof ApiError ? err.message : "The payment could not be confirmed.");
            }
          },
          onError: () => setError("PayPal reported an error. No money was taken; please try again."),
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
  }, [plan.id, onPaid]);

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
