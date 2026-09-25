"use client";

import clsx from "clsx";
import { Crown, Database, FileStack, History, Lock, Sparkles, UploadCloud, Zap } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { AppPage } from "@/components/app-header";
import { BatchCharts } from "@/components/charts";
import { DocumentDialog } from "@/components/document-dialog";
import { Dropzone, PickedList, validateFiles, type Picked } from "@/components/dropzone";
import { useVerificationRequired, VerifyEmailBanner } from "@/components/verify-email-banner";
import { FormatButtons, ResultCard, type BatchEntry, type EntryStatus } from "@/components/results";
import { useToast } from "@/components/toast";
import { Alert, Button, ButtonLink, Card, PageLoader, Progress } from "@/components/ui";
import { UsageCard } from "@/components/usage-card";
import { api, ApiError, type ExportFormat, type ExtractedDocument, type SavedDocument } from "@/lib/api";
import { errorText, localizeError } from "@/lib/errors";
import { fill, useI18n } from "@/lib/i18n";
import { formatPages } from "@/lib/plans";
import { useAuth, useRequireUser } from "@/lib/auth";
import { formatDate, timeUntil } from "@/lib/documents";

const POLL_MS = 2000;
const ACTIVE = new Set<EntryStatus>(["pending", "processing"]);

function storageKey(userId: string) {
  return `extracta:batch:${userId}`;
}

function loadBatch(userId: string): BatchEntry[] {
  try {
    return JSON.parse(localStorage.getItem(storageKey(userId)) ?? "[]") as BatchEntry[];
  } catch {
    return [];
  }
}

export default function DashboardPage() {
  const { user, loading } = useRequireUser();
  const { refresh } = useAuth();
  const { toast } = useToast();
  const { m, locale } = useI18n();
  const d = m.app;

  const [picked, setPicked] = useState<Picked[]>([]);
  const [saveToDb, setSaveToDb] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [batch, setBatch] = useState<BatchEntry[]>([]);
  const [restored, setRestored] = useState(false);
  const [saved, setSaved] = useState<SavedDocument[] | null>(null);
  const [viewing, setViewing] = useState<{ filename: string; document: ExtractedDocument } | null>(null);
  const [limitError, setLimitError] = useState<string | null>(null);

  const plan = user?.plan;
  const privileges = user?.privileges; // the plan's, widened by prepaid pages
  const canSave = Boolean(privileges?.can_save_to_db);
  const verificationRequired = useVerificationRequired();
  const pending = user?.status === "pending";
  const unverified = Boolean(user && !user.email_verified && verificationRequired);
  const blocked = pending || unverified;

  // ------------------------------------------------ batch persistence (survives a reload)
  useEffect(() => {
    if (!user || restored) return;
    // Restoring this browser's batch from localStorage once the account is known.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setBatch(loadBatch(user.id));
    setRestored(true);
  }, [user, restored]);

  useEffect(() => {
    if (!user || !restored) return;
    try {
      const keep = batch.filter((entry) => entry.status !== "rejected").slice(-200);
      localStorage.setItem(storageKey(user.id), JSON.stringify(keep));
    } catch {
      // Private mode or full storage: the batch still works for this page view.
    }
  }, [batch, user, restored]);

  // ------------------------------------------------ saved documents (paid plans)
  const loadSaved = useCallback(async () => {
    try {
      setSaved((await api.documents()).documents);
    } catch {
      setSaved([]);
    }
  }, []);

  useEffect(() => {
    // Loading the saved history is the purpose of this effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (user) void loadSaved();
  }, [user, loadSaved]);

  // ------------------------------------------------ polling
  const batchRef = useRef(batch);
  useEffect(() => {
    batchRef.current = batch;
  }, [batch]);
  const hasActive = batch.some((entry) => entry.taskId && ACTIVE.has(entry.status));

  useEffect(() => {
    if (!hasActive) return;
    let inFlight = false; // never overlap two status requests

    const timer = setInterval(async () => {
      const ids = batchRef.current.filter((e) => e.taskId && ACTIVE.has(e.status)).map((e) => e.taskId as string);
      if (inFlight || ids.length === 0) return;
      inFlight = true;
      try {
        const { tasks } = await api.taskStatuses(ids.slice(0, 100));
        const byId = new Map(tasks.map((task) => [task.task_id, task]));
        let newlySaved = false;
        setBatch((current) =>
          current.map((entry): BatchEntry => {
            const task = entry.taskId ? byId.get(entry.taskId) : undefined;
            if (!task || !ACTIVE.has(entry.status)) return entry;
            if (task.status === "not_found") return { ...entry, status: "expired", error: d.expired };
            if (task.status === "completed" && task.result) {
              newlySaved ||= task.result.saved_to_db;
              return { ...entry, status: "completed", document: task.result.document, savedToDb: task.result.saved_to_db, truncated: task.result.truncated };
            }
            return { ...entry, status: task.status, error: task.error };
          }),
        );
        if (newlySaved) void loadSaved();
      } catch {
        // Temporary network or server problem: try again on the next tick.
      } finally {
        inFlight = false;
      }
    }, POLL_MS);

    return () => clearInterval(timer);
  }, [hasActive, loadSaved, d.expired]);

  // ------------------------------------------------ actions
  function addFiles(files: File[]) {
    if (!privileges) return;
    setPicked((current) => validateFiles(files, current, privileges.max_file_mb, m.dropzone));
  }

  const valid = picked.filter((p) => !p.error);
  const tooMany = privileges ? valid.length > privileges.max_files_per_upload : false;

  async function upload() {
    if (!user || valid.length === 0 || tooMany) return;
    setUploading(true);
    setProgress(0);
    setLimitError(null);
    try {
      const response = await api.upload(
        valid.map((p) => p.file),
        saveToDb && canSave,
        setProgress,
      );
      setBatch((current) => [
        ...response.tasks.map((task) => ({ key: task.task_id, taskId: task.task_id, filename: task.filename, status: "pending" as const, pages: task.pages })),
        ...response.rejected.map((rejected, index) => ({
          key: `rejected-${Date.now()}-${index}`,
          filename: rejected.filename,
          status: "rejected" as const,
          error: rejected.error,
        })),
        ...current,
      ]);
      setPicked([]);
      if (response.tasks.length)
        toast("success", fill(d.queued, { count: response.tasks.length }), fill(d.queuedPages, { pages: formatPages(response.usage.pages, locale) }));
      if (response.rejected.length) toast("error", fill(d.rejected, { count: response.rejected.length }), localizeError(response.rejected[0]?.error, locale));
      await refresh();
    } catch (error) {
      const message = errorText(error, locale, d.uploadFailed);
      if (error instanceof ApiError && error.upgrade) setLimitError(message);
      else toast("error", d.uploadFailed, message);
      await refresh();
    } finally {
      setUploading(false);
    }
  }

  async function exportDocs(fmt: ExportFormat, scope: "individual" | "unified", payload: unknown) {
    try {
      await api.download(fmt, scope, payload);
    } catch (error) {
      toast("error", d.exportFailed, errorText(error, locale, ""));
    }
  }

  async function deleteSaved(doc: SavedDocument) {
    if (!window.confirm(fill(d.deleteConfirm, { name: doc.filename }))) return;
    try {
      await api.deleteDocument(doc.id);
      setSaved((current) => current?.filter((d) => d.id !== doc.id) ?? null);
      toast("success", d.deleted);
    } catch (error) {
      toast("error", d.deleteFailed, errorText(error, locale, ""));
    }
  }

  if (loading || !user || !plan || !privileges) {
    return (
      <AppPage>
        <PageLoader />
      </AppPage>
    );
  }

  const completed = batch.filter((e) => e.status === "completed" && e.document);
  const counts = {
    done: completed.length,
    active: batch.filter((e) => ACTIVE.has(e.status)).length,
    problems: batch.filter((e) => ["failed", "rejected", "expired"].includes(e.status)).length,
  };
  const outOfQuota = user.usage?.available === 0;
  const firstName = user.name?.split(" ")[0];

  return (
    <AppPage>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">{firstName ? fill(d.hi, { name: firstName }) : d.title}</h1>
          <p className="mt-1 text-slate-600 dark:text-slate-400">{d.subtitle}</p>
        </div>
      </div>

      <div className="mt-6 space-y-4">
        <VerifyEmailBanner user={user} />
        {pending && (
          <Alert tone="amber" title={d.pendingTitle}>
            {d.pendingText}
          </Alert>
        )}
        {limitError && (
          <Alert tone="amber" title={limitError} action={<ButtonLink href="/pricing" size="sm">{d.seePlans}</ButtonLink>}>
            {user.usage?.next_slot_at && fill(d.nextSlot, { time: timeUntil(user.usage.next_slot_at) })}
          </Alert>
        )}
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1.55fr_1fr]">
        {/* ------------------------------------------------ upload */}
        <Card className="p-5 sm:p-6">
          <h2 className="flex items-center gap-2 text-lg font-semibold">
            <UploadCloud className="size-5 text-brand-500" /> {d.upload}
          </h2>
          <div className="mt-4">
            <Dropzone
              onFiles={addFiles}
              disabled={blocked || uploading || outOfQuota}
              hint={
                unverified
                  ? d.hintVerify
                  : outOfQuota
                    ? d.hintEmpty
                    : fill(d.hint, { files: privileges.max_files_per_upload, mb: privileges.max_file_mb, pages: privileges.max_pages_per_pdf })
              }
            />
            <PickedList items={picked} onRemove={(index) => setPicked((current) => current.filter((_, i) => i !== index))} />
          </div>

          <fieldset className="mt-5">
            <legend className="text-sm font-semibold">{d.modeTitle}</legend>
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              <label
                className={clsx(
                  "flex cursor-pointer items-start gap-3 border p-3.5 transition",
                  !saveToDb ? "border-brand-500 bg-brand-50/70 ring-4 ring-brand-500/10 dark:bg-brand-500/10" : "border-slate-200 dark:border-slate-800",
                )}
              >
                <input type="radio" name="mode" className="sr-only" checked={!saveToDb} onChange={() => setSaveToDb(false)} />
                <Zap className="mt-0.5 size-5 shrink-0 text-brand-500" />
                <span>
                  <span className="block text-sm font-semibold">{d.processOnly}</span>
                  <span className="block text-xs text-slate-500">{d.processOnlyText}</span>
                </span>
              </label>
              <label
                className={clsx(
                  "relative flex items-start gap-3 border p-3.5 transition",
                  canSave ? "cursor-pointer" : "cursor-not-allowed opacity-70",
                  saveToDb ? "border-brand-500 bg-brand-50/70 ring-4 ring-brand-500/10 dark:bg-brand-500/10" : "border-slate-200 dark:border-slate-800",
                )}
              >
                <input
                  type="radio"
                  name="mode"
                  className="sr-only"
                  checked={saveToDb}
                  disabled={!canSave}
                  onChange={() => setSaveToDb(true)}
                />
                {canSave ? <Database className="mt-0.5 size-5 shrink-0 text-teal-500" /> : <Lock className="mt-0.5 size-5 shrink-0 text-slate-400" />}
                <span>
                  <span className="flex items-center gap-1.5 text-sm font-semibold">
                    {d.save}
                    {!canSave && (
                      <span className="inline-flex items-center gap-0.5 bg-teal-100 px-1.5 py-0.5 text-[10px] font-bold text-teal-700 dark:bg-teal-500/20 dark:text-teal-300">
                        <Crown className="size-2.5" /> {d.paid}
                      </span>
                    )}
                  </span>
                  <span className="block text-xs text-slate-500">{d.saveText}</span>
                </span>
              </label>
            </div>
          </fieldset>

          {tooMany && (
            <p className="mt-4 text-sm text-rose-600">
              {fill(d.tooMany, { files: privileges.max_files_per_upload })}
            </p>
          )}
          {uploading && <Progress value={progress * 100} className="mt-5" />}
          <div className="mt-5 flex flex-wrap items-center gap-3">
            <Button size="lg" onClick={upload} loading={uploading} disabled={valid.length === 0 || tooMany || blocked} icon={<Sparkles className="size-5" />} className="w-full sm:w-auto">
              {uploading
                ? fill(d.uploading, { percent: Math.round(progress * 100) })
                : valid.length > 1
                  ? fill(d.processMany, { count: valid.length })
                  : d.processOne}
            </Button>
            {picked.length > 0 && !uploading && (
              <Button variant="ghost" onClick={() => setPicked([])}>
                {d.clear}
              </Button>
            )}
          </div>
        </Card>

        <div className="space-y-6">
          <UsageCard user={user} />
          <Card className="p-5">
            <h3 className="font-semibold">{d.tipsTitle}</h3>
            <ul className="mt-3 space-y-2 text-sm text-slate-600 dark:text-slate-400">
              {d.tips.map((tip) => (
                <li key={tip} className="flex gap-2">
                  <span className="mt-1.5 size-1.5 shrink-0 bg-accent" aria-hidden /> {tip}
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>

      {/* ------------------------------------------------ results */}
      <section className="mt-10" aria-labelledby="results-title">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 id="results-title" className="flex items-center gap-2 text-xl font-bold tracking-tight">
              <FileStack className="size-5 text-brand-500" /> {d.batch}
            </h2>
            <p className="mt-1 text-sm text-slate-500" aria-live="polite">
              {batch.length === 0 ? d.noDocs : fill(d.counts, counts)}
            </p>
          </div>
          {completed.length > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm text-slate-500">{d.downloadAll}</span>
              <FormatButtons
                label={d.downloadBatch}
                onExport={(fmt) =>
                  exportDocs(fmt, "unified", { items: completed.slice(0, 500).map((e) => ({ filename: e.filename, document: e.document })) })
                }
              />
              <Button variant="ghost" size="sm" onClick={() => setBatch((current) => current.filter((e) => ACTIVE.has(e.status)))}>
                {d.clearFinished}
              </Button>
            </div>
          )}
        </div>

        {batch.length === 0 ? (
          <Card className="mt-4 grid place-items-center border-dashed px-6 py-14 text-center">
            <FileStack className="size-10 text-slate-300 dark:text-slate-700" />
            <p className="mt-3 font-semibold">{d.emptyTitle}</p>
            <p className="mt-1 max-w-sm text-sm text-slate-500">{d.emptyText}</p>
          </Card>
        ) : (
          <ul className="mt-4 grid gap-3 md:grid-cols-2">
            {batch.map((entry) => (
              <ResultCard
                key={entry.key}
                entry={entry}
                onView={() => entry.document && setViewing({ filename: entry.filename, document: entry.document })}
                onExport={(fmt) => exportDocs(fmt, "individual", { filename: entry.filename, document: entry.document })}
              />
            ))}
          </ul>
        )}

        {completed.length > 0 && batch.some((e) => e.status === "completed" && !e.savedToDb) && (
          <p className="mt-4 text-sm text-amber-700 dark:text-amber-400">
            {d.ephemeral}
          </p>
        )}
      </section>

      {completed.length > 0 && (
        <section className="mt-10" aria-label={d.charts}>
          <h2 className="mb-4 text-xl font-bold tracking-tight">{d.charts}</h2>
          <BatchCharts documents={completed.map((e) => e.document as ExtractedDocument)} />
        </section>
      )}

      {/* ------------------------------------------------ saved history */}
      {(canSave || (saved && saved.length > 0)) && (
        <section className="mt-10" aria-labelledby="history-title">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 id="history-title" className="flex items-center gap-2 text-xl font-bold tracking-tight">
              <History className="size-5 text-teal-500" /> {d.saved}
            </h2>
            {saved && saved.length > 0 && (
              <FormatButtons
                label={d.downloadSaved}
                onExport={(fmt) => exportDocs(fmt, "unified", { items: saved.slice(0, 500).map((d) => ({ filename: d.filename, document: d.document })) })}
              />
            )}
          </div>
          {saved === null ? (
            <div className="skeleton mt-4 h-24 w-full" />
          ) : saved.length === 0 ? (
            <p className="mt-3 text-sm text-slate-500">{d.savedEmpty}</p>
          ) : (
            <ul className="mt-4 grid gap-3 md:grid-cols-2">
              {saved.map((doc) => (
                <ResultCard
                  key={doc.id}
                  entry={{ key: doc.id, filename: `${doc.filename} · ${formatDate(doc.created_at)}`, status: "completed", document: doc.document, savedToDb: true }}
                  onView={() => setViewing({ filename: doc.filename, document: doc.document })}
                  onExport={(fmt) => exportDocs(fmt, "individual", { filename: doc.filename, document: doc.document })}
                  onDelete={() => deleteSaved(doc)}
                />
              ))}
            </ul>
          )}
        </section>
      )}

      {viewing && <DocumentDialog filename={viewing.filename} document={viewing.document} onClose={() => setViewing(null)} />}
    </AppPage>
  );
}
