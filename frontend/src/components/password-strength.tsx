"use client";

import clsx from "clsx";
import { Check, X } from "lucide-react";

import { useI18n } from "@/lib/i18n";

// Mirrors app/passwords.py (the server is the authority; this only gives live feedback).
const COMMON = new Set([
  "1234567890", "0123456789", "0987654321", "1111111111", "0000000000", "1q2w3e4r5t", "qwertyuiop",
  "qwerty1234", "qwerty12345", "password12", "password123", "password1234", "passw0rd123", "iloveyou12",
  "iloveyou123", "abcdefghij", "abcd123456", "abc1234567", "a123456789", "letmein123", "welcome123",
  "admin12345", "administrator", "changeme123", "contraseña", "contrasena", "contraseña123", "contrasena123",
  "teamo12345", "extracta123", "qwertyqwerty", "passwordpassword",
]);
const SEQUENCES = ["0123456789", "abcdefghijklmnopqrstuvwxyz", "qwertyuiopasdfghjklzxcvbnm"];

function isSequence(value: string): boolean {
  const steps = [...value].slice(1).map((char, index) => [value[index] ?? "", char] as const);
  if (steps.length === 0) return false;
  return SEQUENCES.some((sequence) => {
    let forward = 0;
    let backward = 0;
    for (const [a, b] of steps) {
      const i = sequence.indexOf(a);
      const j = sequence.indexOf(b);
      if (i < 0 || j < 0) continue;
      if ((j - i + sequence.length) % sequence.length === 1) forward += 1;
      if ((i - j + sequence.length) % sequence.length === 1) backward += 1;
    }
    return Math.max(forward, backward) >= 0.8 * steps.length;
  });
}

function basedOn(password: string, word: string): boolean {
  return word.length >= 4 && password.includes(word) && password.length - word.length < 6;
}

export function passwordChecks(password: string, email = "", name = "") {
  const lowered = password.trim().toLowerCase();
  const compact = lowered.replace(/[\s._-]/g, "");
  const length = password.length >= 10 && password.length <= 128;
  const notCommon = compact.length > 0 && !COMMON.has(lowered) && !COMMON.has(compact) && new Set(compact).size > 2 && !isSequence(compact);
  const local = email.split("@")[0]?.toLowerCase() ?? "";
  const notPersonal =
    compact.length > 0 && lowered !== email.toLowerCase() && !basedOn(lowered, local) && !name.toLowerCase().split(/\s+/).some((w) => basedOn(lowered, w));
  // 0-4: nothing until the rules pass, then length and variety add strength.
  const variety = [/[a-z]/, /[A-Z]/, /\d/, /[^A-Za-z\d]/].filter((r) => r.test(password)).length;
  let score = 0;
  if (length && notCommon && notPersonal) score = 1 + Number(password.length >= 14) + Number(password.length >= 18 || variety >= 3) + Number(password.length >= 22);
  return { length, notCommon, notPersonal, score: Math.min(score, 4) };
}

/** A strength bar plus the three rules the server enforces, updated as the user types. */
export function PasswordStrength({ password, email, name }: { password: string; email?: string; name?: string }) {
  const { m } = useI18n();
  if (!password) return <p className="mt-1.5 text-xs text-slate-500 dark:text-slate-400">{m.password.tip}</p>;
  const checks = passwordChecks(password, email, name);
  const colors = ["bg-rose-500", "bg-rose-500", "bg-amber-400", "bg-emerald-500", "bg-emerald-500"];
  return (
    <div className="mt-2 space-y-2" aria-live="polite">
      <div className="flex items-center gap-2">
        <div className="grid flex-1 grid-cols-4 gap-1">
          {[1, 2, 3, 4].map((level) => (
            <span
              key={level}
              className={clsx("h-1 transition-colors duration-300 ease-out", checks.score >= level ? colors[checks.score] : "bg-slate-200 dark:bg-slate-700")}
            />
          ))}
        </div>
        <span className="w-20 text-right text-xs font-semibold text-slate-600 dark:text-slate-300">{m.password.strength[checks.score]}</span>
      </div>
      <ul className="space-y-0.5 text-xs">
        {(
          [
            [checks.length, m.password.length],
            [checks.notCommon, m.password.notCommon],
            [checks.notPersonal, m.password.notPersonal],
          ] as const
        ).map(([ok, label]) => (
          <li key={label} className={clsx("flex items-center gap-1.5", ok ? "text-emerald-600 dark:text-emerald-400" : "text-slate-500")}>
            {ok ? <Check className="size-3.5" /> : <X className="size-3.5" />} {label}
          </li>
        ))}
      </ul>
    </div>
  );
}
