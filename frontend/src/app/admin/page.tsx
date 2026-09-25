"use client";

import clsx from "clsx";
import {
  Ban,
  BadgeCheck,
  Check,
  CircleDollarSign,
  LogOut,
  Repeat,
  RefreshCw,
  Save,
  Search,
  ShieldCheck,
  ShieldX,
  Upload,
  Users,
  X,
} from "lucide-react";
import { useCallback, useEffect, useState, type FormEvent } from "react";

import { Logo } from "@/components/logo";
import { useToast } from "@/components/toast";
import { Alert, Badge, Button, Card, Field, PageLoader } from "@/components/ui";
import { api, ApiError, type AdminPayment, type AdminStats, type AdminUser, type Plan, type PlanId, type UserStatus } from "@/lib/api";
import { formatDate } from "@/lib/documents";

const STATUSES: UserStatus[] = ["pending", "active", "rejected", "suspended"];
const STATUS_TONE = { active: "green", pending: "amber", rejected: "red", suspended: "red" } as const;
const SUBSCRIPTION_TONE = { ACTIVE: "green", APPROVED: "amber", SUSPENDED: "red" } as const;
const PAYMENT_TONE: Record<string, "green" | "red" | "amber"> = { COMPLETED: "green", REFUNDED: "red", REVERSED: "red" };
const selectClass =
  "h-10 w-full border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-900 focus:border-brand-500 focus:ring-4 focus:ring-brand-500/15 outline-none";

// ---------------------------------------------------------------- sign in

function AdminLogin({ onDone }: { onDone: () => void }) {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await api.admin.login(String(new FormData(event.currentTarget).get("password")));
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not sign in.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid min-h-dvh place-items-center bg-slate-950 px-4">
      <div className="bg-dots absolute inset-0 opacity-30" />
      <Card className="relative w-full max-w-sm p-8">
        <div className="flex justify-center">
          <Logo />
        </div>
        <h1 className="mt-6 text-center text-xl font-bold">Administration</h1>
        <p className="mt-1 text-center text-sm text-slate-500">Enter the ADMIN_PASSWORD from the server&apos;s .env</p>
        <form onSubmit={submit} className="mt-6 space-y-4">
          {error && <Alert>{error}</Alert>}
          <Field label="Admin password" name="password" type="password" autoComplete="current-password" required />
          <Button type="submit" className="w-full" loading={loading} icon={<ShieldCheck className="size-4" />}>
            Enter
          </Button>
        </form>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------- one account

function toDateInput(iso: string | null): string {
  return iso ? iso.slice(0, 10) : "";
}

function UserCard({ user, plans, onSaved }: { user: AdminUser; plans: Plan[]; onSaved: (user: AdminUser) => void }) {
  const { toast } = useToast();
  const [status, setStatus] = useState<UserStatus>(user.status);
  const [plan, setPlan] = useState<PlanId>(user.assigned_plan);
  const [expires, setExpires] = useState(toDateInput(user.raw_plan_expires_at));
  const [limit, setLimit] = useState(user.daily_limit_override?.toString() ?? "");
  const [saving, setSaving] = useState(false);

  const dirty =
    status !== user.status ||
    plan !== user.assigned_plan ||
    expires !== toDateInput(user.raw_plan_expires_at) ||
    limit !== (user.daily_limit_override?.toString() ?? "");

  async function save(changes?: { status?: UserStatus; email_verified?: boolean }) {
    setSaving(true);
    try {
      const body = changes ?? {
        status,
        plan,
        plan_expires_at: plan === "free" || !expires ? null : new Date(`${expires}T23:59:59Z`).toISOString(),
        daily_limit_override: limit === "" ? null : Number(limit),
      };
      const { user: updated } = await api.admin.updateUser(user.id, body);
      setStatus(updated.status);
      onSaved(updated);
      toast("success", "Account updated", updated.email);
    } catch (err) {
      toast("error", "Could not update", err instanceof ApiError ? `${err.message} ${String(err.data.details ?? "")}` : undefined);
    } finally {
      setSaving(false);
    }
  }

  const p = user.privileges;
  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate font-semibold">{user.email}</p>
          <p className="text-sm text-slate-500">
            {user.name ?? "No name"} · joined {formatDate(user.created_at)} · last sign-in {formatDate(user.last_login_at, true)}
          </p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            <Badge tone={STATUS_TONE[user.status]}>{user.status}</Badge>
            <Badge tone={user.plan.id === "free" ? "slate" : "violet"}>{user.plan.name}</Badge>
            {user.email_verified ? (
              <Badge tone="green">
                <BadgeCheck className="size-3" /> email verified
              </Badge>
            ) : (
              <Badge tone="amber">email not verified</Badge>
            )}
            {user.subscription && (
              <Badge tone={SUBSCRIPTION_TONE[user.subscription.status as keyof typeof SUBSCRIPTION_TONE] ?? "slate"}>
                <Repeat className="size-3" /> monthly {user.subscription.plan} · {user.subscription.status.toLowerCase()}
              </Badge>
            )}
            {user.sign_in_methods.map((m) => (
              <Badge key={m} tone="slate">
                {m}
              </Badge>
            ))}
          </div>
        </div>
        {!user.email_verified && user.status !== "pending" && (
          <Button size="sm" variant="outline" onClick={() => save({ email_verified: true })} loading={saving} icon={<BadgeCheck className="size-4" />}>
            Mark email verified
          </Button>
        )}
        {user.status === "pending" && (
          <div className="flex gap-2">
            <Button size="sm" onClick={() => save({ status: "active" })} loading={saving} icon={<Check className="size-4" />}>
              Approve
            </Button>
            <Button size="sm" variant="danger" onClick={() => save({ status: "rejected" })} disabled={saving} icon={<X className="size-4" />}>
              Reject
            </Button>
          </div>
        )}
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
        {[
          ["PDFs / 24 h", `${p.docs_per_24h}${user.daily_limit_override !== null ? " (custom)" : ""}`],
          ["MB per file", p.max_file_mb],
          ["Files / upload", p.max_files_per_upload],
          ["Save to DB", p.can_save_to_db ? "Yes" : "No"],
          ["Used (24 h)", user.uploads_24h],
          ["Total uploads", user.uploads_total],
          ["Paid", `$${user.paid_total_usd}`],
          ["Plan until", user.raw_plan_expires_at ? formatDate(user.raw_plan_expires_at) : user.assigned_plan === "free" ? "—" : "No expiry"],
          ...(user.subscription?.next_billing_at && user.subscription.status === "ACTIVE"
            ? [["Next charge", formatDate(user.subscription.next_billing_at)]]
            : []),
        ].map(([label, value]) => (
          <div key={label as string} className="bg-slate-50 px-3 py-2 dark:bg-slate-800/60">
            <p className="text-[11px] font-medium text-slate-500 uppercase">{label}</p>
            <p className="text-sm font-semibold">{value}</p>
          </div>
        ))}
      </div>

      <details className="group mt-4">
        <summary className="cursor-pointer text-sm font-semibold text-brand-600 dark:text-brand-400">Edit status, plan and privileges</summary>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <label className="text-sm">
            <span className="mb-1 block font-medium">Status</span>
            <select className={selectClass} value={status} onChange={(e) => setStatus(e.target.value as UserStatus)}>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            <span className="mb-1 block font-medium">Plan</span>
            <select className={selectClass} value={plan} onChange={(e) => setPlan(e.target.value as PlanId)}>
              {plans.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.name} — {option.privileges.docs_per_24h}/24 h
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            <span className="mb-1 block font-medium">Plan expires</span>
            <input
              type="date"
              className={selectClass}
              value={expires}
              disabled={plan === "free"}
              onChange={(e) => setExpires(e.target.value)}
            />
            <span className="mt-1 block text-xs text-slate-500">Empty = no expiry</span>
          </label>
          <label className="text-sm">
            <span className="mb-1 block font-medium">Custom PDFs / 24 h</span>
            <input
              type="number"
              min={0}
              className={selectClass}
              value={limit}
              placeholder="Plan default"
              onChange={(e) => setLimit(e.target.value)}
            />
            <span className="mt-1 block text-xs text-slate-500">Empty = use the plan&apos;s limit</span>
          </label>
        </div>
        <div className="mt-4 flex justify-end">
          <Button onClick={() => save()} loading={saving} disabled={!dirty} icon={<Save className="size-4" />}>
            Save changes
          </Button>
        </div>
      </details>
    </Card>
  );
}

// ---------------------------------------------------------------- panel

export default function AdminPage() {
  const [session, setSession] = useState<{ enabled: boolean; authenticated: boolean } | null>(null);
  const [tab, setTab] = useState<"users" | "payments">("users");
  const [status, setStatus] = useState<string>("");
  const [query, setQuery] = useState("");
  const [users, setUsers] = useState<AdminUser[] | null>(null);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [payments, setPayments] = useState<AdminPayment[] | null>(null);
  const [stats, setStats] = useState<AdminStats | null>(null);

  const checkSession = useCallback(() => {
    api.admin.session().then(setSession, () => setSession({ enabled: false, authenticated: false }));
  }, []);

  const load = useCallback(async () => {
    try {
      const [list, summary] = await Promise.all([api.admin.users({ status, q: query }), api.admin.stats()]);
      setUsers(list.users);
      setPlans(list.plans);
      setStats(summary);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) checkSession();
    }
  }, [status, query, checkSession]);

  useEffect(checkSession, [checkSession]);

  useEffect(() => {
    if (!session?.authenticated) return;
    const timer = setTimeout(load, 250); // debounce the search box
    return () => clearTimeout(timer);
  }, [session, load]);

  useEffect(() => {
    if (session?.authenticated && tab === "payments") api.admin.payments().then((r) => setPayments(r.payments), () => setPayments([]));
  }, [session, tab]);

  if (!session) return <PageLoader />;
  if (!session.enabled) {
    return (
      <div className="grid min-h-dvh place-items-center px-4">
        <Alert tone="amber" title="Administration is disabled">
          Set ADMIN_PASSWORD (at least 12 characters) in the server&apos;s .env and restart it.
        </Alert>
      </div>
    );
  }
  if (!session.authenticated) return <AdminLogin onDone={checkSession} />;

  const pendingCount = stats?.users_by_status.pending ?? 0;

  return (
    <div className="min-h-dvh bg-slate-50/70 dark:bg-slate-950">
      <header className="sticky top-0 z-40 border-b border-slate-200/70 bg-white/80 backdrop-blur-xl dark:border-slate-800/70 dark:bg-slate-950/75">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-3 px-4 sm:px-6">
          <div className="flex items-center gap-3">
            <Logo href="/admin" />
            <Badge tone="red">Admin</Badge>
          </div>
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" onClick={load} icon={<RefreshCw className="size-4" />} aria-label="Refresh" />
            <Button variant="ghost" size="sm" onClick={() => api.admin.logout().then(checkSession)} icon={<LogOut className="size-4" />}>
              <span className="hidden sm:inline">Sign out</span>
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {[
            { icon: Users, label: "Accounts", value: Object.values(stats?.users_by_status ?? {}).reduce((a, b) => a + (b ?? 0), 0) },
            { icon: ShieldX, label: "Pending approval", value: pendingCount, highlight: pendingCount > 0 },
            { icon: Upload, label: "PDFs last 24 h", value: stats?.uploads_24h ?? 0 },
            { icon: Repeat, label: "Active subscriptions", value: stats?.active_subscriptions ?? 0 },
            { icon: CircleDollarSign, label: "Revenue (USD)", value: `$${stats?.revenue_usd ?? "0.00"}` },
          ].map(({ icon: Icon, label, value, highlight }) => (
            <Card key={label} className={clsx("p-4", highlight && "ring-2 ring-amber-400")}>
              <Icon className="size-5 text-brand-500" />
              <p className="mt-3 text-2xl font-bold">{value}</p>
              <p className="text-xs text-slate-500">{label}</p>
            </Card>
          ))}
        </div>

        <div className="mt-8 flex gap-2 border-b border-slate-200 dark:border-slate-800">
          {(["users", "payments"] as const).map((name) => (
            <button
              key={name}
              onClick={() => setTab(name)}
              className={clsx(
                "-mb-px border-b-2 px-4 py-2 text-sm font-semibold capitalize transition",
                tab === name ? "border-brand-500 text-brand-600 dark:text-brand-400" : "border-transparent text-slate-500 hover:text-slate-800",
              )}
            >
              {name}
            </button>
          ))}
        </div>

        {tab === "users" ? (
          <>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center">
              <div className="relative flex-1">
                <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-slate-400" />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search by email or name"
                  className="h-10 w-full border border-slate-300 bg-white pr-3 pl-9 text-sm outline-none focus:border-brand-500 focus:ring-4 focus:ring-brand-500/15 dark:border-slate-700 dark:bg-slate-900"
                />
              </div>
              <div className="flex gap-1.5 overflow-x-auto">
                {["", ...STATUSES].map((s) => (
                  <button
                    key={s || "all"}
                    onClick={() => setStatus(s)}
                    className={clsx(
                      " px-3 py-1.5 text-xs font-semibold whitespace-nowrap capitalize transition",
                      status === s ? "bg-slate-900 text-white dark:bg-white dark:text-slate-900" : "bg-white text-slate-600 ring-1 ring-slate-200 dark:bg-slate-900 dark:text-slate-300 dark:ring-slate-700",
                    )}
                  >
                    {s || "all"}
                    {s === "pending" && pendingCount > 0 && ` (${pendingCount})`}
                  </button>
                ))}
              </div>
            </div>
            <div className="mt-6 space-y-4">
              {users === null ? (
                <PageLoader />
              ) : users.length === 0 ? (
                <p className="py-10 text-center text-sm text-slate-500">No accounts match.</p>
              ) : (
                users.map((user) => (
                  <UserCard key={user.id} user={user} plans={plans} onSaved={(updated) => setUsers((current) => current?.map((u) => (u.id === updated.id ? { ...u, ...updated } : u)) ?? null)} />
                ))
              )}
            </div>
          </>
        ) : (
          <Card className="mt-6 overflow-x-auto">
            {payments === null ? (
              <PageLoader />
            ) : payments.length === 0 ? (
              <p className="p-10 text-center text-sm text-slate-500">No payments yet.</p>
            ) : (
              <table className="w-full text-left text-sm">
                <thead className="border-b border-slate-200 text-xs text-slate-500 uppercase dark:border-slate-800">
                  <tr>
                    <th className="px-4 py-3">Date</th>
                    <th className="px-4 py-3">Account</th>
                    <th className="px-4 py-3">Plan</th>
                    <th className="px-4 py-3">Type</th>
                    <th className="px-4 py-3">Amount</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">PayPal reference</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {payments.map((p) => (
                    <tr key={p.id}>
                      <td className="px-4 py-3 whitespace-nowrap">{formatDate(p.created_at, true)}</td>
                      <td className="px-4 py-3">{p.email}</td>
                      <td className="px-4 py-3 capitalize">{p.plan}</td>
                      <td className="px-4 py-3 whitespace-nowrap">{p.kind === "subscription" ? "Monthly" : "30-day pass"}</td>
                      <td className="px-4 py-3 font-semibold whitespace-nowrap">
                        ${p.amount} {p.currency}
                      </td>
                      <td className="px-4 py-3">
                        <Badge tone={PAYMENT_TONE[p.status] ?? "amber"}>{p.status.toLowerCase()}</Badge>
                      </td>
                      <td className="px-4 py-3 font-mono text-xs">{p.provider_order_id}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        )}
        <p className="mt-10 flex items-center justify-center gap-2 text-xs text-slate-500">
          <Ban className="size-3.5" /> Rejected and suspended accounts are signed out immediately and cannot sign in.
        </p>
      </main>
    </div>
  );
}
