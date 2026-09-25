"use client";

import clsx from "clsx";
import { LoaderCircle } from "lucide-react";
import Link from "next/link";
import type { ButtonHTMLAttributes, ComponentProps, InputHTMLAttributes, ReactNode } from "react";

// ---------------------------------------------------------------- buttons

type Variant = "primary" | "secondary" | "ghost" | "danger" | "outline";
type Size = "sm" | "md" | "lg";

const variants: Record<Variant, string> = {
  primary:
    "bg-signature animate-pan text-white shadow-lg shadow-brand-600/25 hover:shadow-xl hover:shadow-brand-600/30 hover:brightness-110",
  secondary:
    "bg-slate-900 text-white hover:bg-slate-800 dark:bg-white dark:text-slate-900 dark:hover:bg-slate-100",
  outline:
    "border border-slate-300 bg-white/70 text-slate-800 hover:border-brand-400 hover:text-brand-700 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-100 dark:hover:border-brand-400 dark:hover:text-brand-300",
  ghost: "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white",
  danger: "bg-rose-600 text-white hover:bg-rose-500",
};

const sizes: Record<Size, string> = {
  sm: "h-8 gap-1.5 px-3 text-xs",
  md: "h-10 gap-2 px-4 text-sm",
  lg: "h-12 gap-2 px-6 text-base",
};

function buttonClass(variant: Variant, size: Size, className?: string) {
  return clsx(
    "inline-flex shrink-0 cursor-pointer items-center justify-center font-semibold whitespace-nowrap transition-all duration-300 ease-out hover:-translate-y-px active:translate-y-0 active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50",
    variants[variant],
    sizes[size],
    className,
  );
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  icon?: ReactNode;
}

export function Button({ variant = "primary", size = "md", loading, icon, className, children, disabled, ...props }: ButtonProps) {
  return (
    <button className={buttonClass(variant, size, className)} disabled={disabled || loading} {...props}>
      {loading ? <LoaderCircle className="size-4 animate-spin" aria-hidden /> : icon}
      {children}
    </button>
  );
}

interface ButtonLinkProps extends ComponentProps<typeof Link> {
  variant?: Variant;
  size?: Size;
  icon?: ReactNode;
}

export function ButtonLink({ variant = "primary", size = "md", icon, className, children, ...props }: ButtonLinkProps) {
  return (
    <Link className={buttonClass(variant, size, className)} {...props}>
      {icon}
      {children}
    </Link>
  );
}

// ---------------------------------------------------------------- surfaces

export function Card({ className, children, ...props }: ComponentProps<"div">) {
  return (
    <div
      className={clsx(
        " border border-slate-200/80 bg-white shadow-sm shadow-slate-200/50 dark:border-slate-800 dark:bg-slate-900/70 dark:shadow-none",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function SectionTitle({ eyebrow, title, subtitle, center }: { eyebrow?: string; title: ReactNode; subtitle?: ReactNode; center?: boolean }) {
  return (
    <div className={clsx("max-w-2xl", center && "mx-auto text-center")}>
      {eyebrow && (
        <p className={clsx("flex items-center gap-2 text-sm font-semibold tracking-wide text-brand-600 uppercase dark:text-brand-400", center && "justify-center")}>
          <span className="size-2 bg-accent" aria-hidden /> {eyebrow}
        </p>
      )}
      <h2 className="mt-2 text-3xl font-bold tracking-tight text-balance sm:text-4xl">{title}</h2>
      {subtitle && <p className="mt-4 text-base text-pretty text-slate-600 sm:text-lg dark:text-slate-400">{subtitle}</p>}
    </div>
  );
}

// ---------------------------------------------------------------- badges

type Tone = "brand" | "green" | "amber" | "red" | "slate" | "violet";

const tones: Record<Tone, string> = {
  brand: "bg-brand-50 text-brand-700 ring-brand-600/15 dark:bg-brand-500/10 dark:text-brand-300 dark:ring-brand-400/20",
  green: "bg-emerald-50 text-emerald-700 ring-emerald-600/15 dark:bg-emerald-500/10 dark:text-emerald-300 dark:ring-emerald-400/20",
  amber: "bg-amber-50 text-amber-800 ring-amber-600/20 dark:bg-amber-500/10 dark:text-amber-300 dark:ring-amber-400/20",
  red: "bg-rose-50 text-rose-700 ring-rose-600/15 dark:bg-rose-500/10 dark:text-rose-300 dark:ring-rose-400/20",
  slate: "bg-slate-100 text-slate-700 ring-slate-500/15 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-600/30",
  violet: "bg-teal-50 text-teal-700 ring-teal-600/15 dark:bg-teal-500/10 dark:text-teal-300 dark:ring-teal-400/20",
};

export function Badge({ tone = "slate", className, children }: { tone?: Tone; className?: string; children: ReactNode }) {
  return (
    <span className={clsx("inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset", tones[tone], className)}>
      {children}
    </span>
  );
}

// ---------------------------------------------------------------- forms

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: ReactNode;
  error?: string | null;
}

export function Field({ label, hint, error, id, className, ...props }: FieldProps) {
  const inputId = id ?? props.name;
  return (
    <div className={className}>
      <label htmlFor={inputId} className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
        {label}
      </label>
      <input
        id={inputId}
        className={clsx(
          "block h-11 w-full border bg-white px-3.5 text-[15px] text-slate-900 shadow-sm transition outline-none placeholder:text-slate-400 focus:ring-4 dark:bg-slate-900 dark:text-white",
          error
            ? "border-rose-400 focus:border-rose-500 focus:ring-rose-500/15"
            : "border-slate-300 focus:border-brand-500 focus:ring-brand-500/15 dark:border-slate-700",
        )}
        aria-invalid={Boolean(error)}
        {...props}
      />
      {error ? (
        <p className="mt-1.5 text-sm text-rose-600 dark:text-rose-400">{error}</p>
      ) : (
        hint && <p className="mt-1.5 text-xs text-slate-500 dark:text-slate-400">{hint}</p>
      )}
    </div>
  );
}

export function Alert({ tone = "red", title, children, action }: { tone?: "red" | "amber" | "green" | "brand"; title?: string; children?: ReactNode; action?: ReactNode }) {
  const styles = {
    red: "border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-200",
    amber: "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200",
    green: "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-200",
    brand: "border-brand-200 bg-brand-50 text-brand-900 dark:border-brand-500/30 dark:bg-brand-500/10 dark:text-brand-100",
  }[tone];
  return (
    <div role={tone === "red" ? "alert" : "status"} className={clsx("flex flex-col gap-3 border px-4 py-3 text-sm sm:flex-row sm:items-center", styles)}>
      <div className="flex-1">
        {title && <p className="font-semibold">{title}</p>}
        {children && <div className={clsx(title && "mt-0.5", "opacity-90")}>{children}</div>}
      </div>
      {action}
    </div>
  );
}

export function Spinner({ className }: { className?: string }) {
  return <LoaderCircle className={clsx("animate-spin text-brand-500", className ?? "size-6")} aria-label="Loading" />;
}

export function Progress({ value, className, tone = "brand" }: { value: number; className?: string; tone?: "brand" | "amber" | "red" }) {
  const bar = { brand: "from-emerald-500 to-brand-600", amber: "from-amber-400 to-orange-500", red: "from-rose-500 to-red-600" }[tone];
  return (
    <div className={clsx("h-2 w-full overflow-hidden bg-slate-200/80 dark:bg-slate-800", className)}>
      <div
        className={clsx("h-full bg-gradient-to-r transition-[width] duration-500 ease-out", bar)}
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  );
}

export function PageLoader() {
  return (
    <div className="grid min-h-[60dvh] place-items-center">
      <Spinner className="size-8" />
    </div>
  );
}
