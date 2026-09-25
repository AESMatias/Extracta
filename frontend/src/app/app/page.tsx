"use client";

import clsx from "clsx";
import { Crown, Database, FileStack, History, Lock, Sparkles, UploadCloud, Zap } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { AppPage } from "@/components/app-header";
import { BatchCharts } from "@/components/charts";
import { DocumentDialog } from "@/components/document-dialog";
import { Dropzone, PickedList, validateFiles, type Picked } from "@/components/dropzone";
import { FormatButtons, ResultCard, type BatchEntry, type EntryStatus } from "@/components/results";
import { useToast } from "@/components/toast";
import { Alert, Button, ButtonLink, Card, PageLoader, Progress } from "@/components/ui";
import { UsageCard } from "@/components/usage-card";
import { api, ApiError, type ExportFormat, type ExtractedDocument, type SavedDocument } from "@/lib/api";
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
  const canSave = Boolean(plan?.privileges.can_save_to_db);
  const pending = user?.status === "pending";

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
            if (task.status === "not_found") return { ...entry, status: "expired", error: "The result expired or is no longer available." };
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
  }, [hasActive, loadSaved]);

  // ------------------------------------------------ actions
  function addFiles(files: File[]) {
    if (!plan) return;
    setPicked((current) => validateFiles(files, current, plan.privileges.max_file_mb));
  }

  const valid = picked.filter((p) => !p.error);
  const tooMany = plan ? valid.length > plan.privileges.max_files_per_upload : false;

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
        ...response.tasks.map((task) => ({ key: task.task_id, taskId: task.task_id, filename: task.filename, status: "pending" as const })),
        ...response.rejected.map((rejected, index) => ({
          key: `rejected-${Date.now()}-${index}`,
          filename: rejected.filename,
          status: "rejected" as const,
          error: rejected.error,
        })),
        ...current,
      ]);
      setPicked([]);
      if (response.tasks.length) toast("success", `${response.tasks.length} PDF${response.tasks.length > 1 ? "s" : ""} queued`, "Results appear below as soon as they are ready.");
      if (response.rejected.length) toast("error", `${response.rejected.length} file(s) rejected`, response.rejected[0]?.error);
      await refresh();
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "The upload failed.";
      if (error instanceof ApiError && error.upgrade) setLimitError(message);
      else toast("error", "Upload failed", message);
      await refresh();
    } finally {
      setUploading(false);
    }
  }

  async function exportDocs(fmt: ExportFormat, scope: "individual" | "unified", payload: unknown) {
    try {
      await api.download(fmt, scope, payload);
    } catch (error) {
      toast("error", "Export failed", error instanceof ApiError ? error.message : undefined);
    }
  }

  async function deleteSaved(doc: SavedDocument) {
    if (!window.confirm(`Delete "${doc.filename}" from your history?`)) return;
    try {
      await api.deleteDocument(doc.id);
      setSaved((current) => current?.filter((d) => d.id !== doc.id) ?? null);
      toast("success", "Document deleted");
    } catch (error) {
      toast("error", "Could not delete", error instanceof ApiError ? error.message : undefined);
    }
  }

  if (loading || !user || !plan) {
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
  const outOfQuota = user.usage?.remaining === 0;
  const firstName = user.name?.split(" ")[0];

  return (
    <AppPage>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">{firstName ? `Hi, ${firstName}` : "Your dashboard"}</h1>
          <p className="mt-1 text-slate-600 dark:text-slate-400">Upload PDFs and get their data in seconds.</p>
        </div>
      </div>

      <div className="mt-6 space-y-4">
        {pending && (
          <Alert tone="amber" title="Your account is waiting for approval">
            The administrator reviews new accounts manually. You will be able to upload PDFs as soon as it is approved.
          </Alert>
        )}
        {limitError && (
          <Alert tone="amber" title={limitError} action={<ButtonLink href="/pricing" size="sm">See plans</ButtonLink>}>
            {user.usage?.next_slot_at && `Your next free slot opens in ${timeUntil(user.usage.next_slot_at)}.`}
          </Alert>
        )}
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1.55fr_1fr]">
        {/* ------------------------------------------------ upload */}
        <Card className="p-5 sm:p-6">
          <h2 className="flex items-center gap-2 text-lg font-semibold">
            <UploadCloud className="size-5 text-brand-500" /> Upload documents
          </h2>
          <div className="mt-4">
            <Dropzone
              onFiles={addFiles}
              disabled={pending || uploading || outOfQuota}
              hint={
                outOfQuota
                  ? "Daily limit reached. Upgrade or wait for your next slot."
                  : `Up to ${plan.privileges.max_files_per_upload} files, ${plan.privileges.max_file_mb} MB each · digital PDFs`
              }
            />
            <PickedList items={picked} onRemove={(index) => setPicked((current) => current.filter((_, i) => i !== index))} />
          </div>

          <fieldset className="mt-5">
            <legend className="text-sm font-semibold">What should happen with the results?</legend>
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              <label
                className={clsx(
                  "flex cursor-pointer items-start gap-3 rounded-2xl border p-3.5 transition",
                  !saveToDb ? "border-brand-500 bg-brand-50/70 ring-4 ring-brand-500/10 dark:bg-brand-500/10" : "border-slate-200 dark:border-slate-800",
                )}
              >
                <input type="radio" name="mode" className="sr-only" checked={!saveToDb} onChange={() => setSaveToDb(false)} />
                <Zap className="mt-0.5 size-5 shrink-0 text-brand-500" />
                <span>
                  <span className="block text-sm font-semibold">Process only</span>
                  <span className="block text-xs text-slate-500">Nothing is stored. Results expire after 1 hour.</span>
                </span>
              </label>
              <label
                className={clsx(
                  "relative flex items-start gap-3 rounded-2xl border p-3.5 transition",
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
                {canSave ? <Database className="mt-0.5 size-5 shrink-0 text-violet-500" /> : <Lock className="mt-0.5 size-5 shrink-0 text-slate-400" />}
                <span>
                  <span className="flex items-center gap-1.5 text-sm font-semibold">
                    Save to history
                    {!canSave && (
                      <span className="inline-flex items-center gap-0.5 rounded-full bg-violet-100 px-1.5 py-0.5 text-[10px] font-bold text-violet-700 dark:bg-violet-500/20 dark:text-violet-300">
                        <Crown className="size-2.5" /> PAID
                      </span>
                    )}
                  </span>
                  <span className="block text-xs text-slate-500">Keep results in your account to export later.</span>
                </span>
              </label>
            </div>
          </fieldset>

          {tooMany && (
            <p className="mt-4 text-sm text-rose-600">
              Your {plan.name} plan allows {plan.privileges.max_files_per_upload} files per upload. Remove some or upgrade.
            </p>
          )}
          {uploading && <Progress value={progress * 100} className="mt-5" />}
          <div className="mt-5 flex flex-wrap items-center gap-3">
            <Button size="lg" onClick={upload} loading={uploading} disabled={valid.length === 0 || tooMany || pending} icon={<Sparkles className="size-5" />} className="w-full sm:w-auto">
              {uploading ? `Uploading ${Math.round(progress * 100)}%` : valid.length > 1 ? `Process ${valid.length} PDFs` : "Process PDF"}
            </Button>
            {picked.length > 0 && !uploading && (
              <Button variant="ghost" onClick={() => setPicked([])}>
                Clear
              </Button>
            )}
          </div>
        </Card>

        <div className="space-y-6">
          <UsageCard user={user} />
          <Card className="p-5">
            <h3 className="font-semibold">Tips for best results</h3>
            <ul className="mt-3 space-y-2 text-sm text-slate-600 dark:text-slate-400">
              <li>• Use digital PDFs (exported or e-invoices). Scans are not supported yet.</li>
              <li>• One document per PDF gives the cleanest data.</li>
              <li>• Always review important totals before using them.</li>
            </ul>
          </Card>
        </div>
      </div>

      {/* ------------------------------------------------ results */}
      <section className="mt-10" aria-labelledby="results-title">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 id="results-title" className="flex items-center gap-2 text-xl font-bold tracking-tight">
              <FileStack className="size-5 text-brand-500" /> This batch
            </h2>
            <p className="mt-1 text-sm text-slate-500" aria-live="polite">
              {batch.length === 0
                ? "No documents yet."
                : `${counts.done} completed · ${counts.active} in progress · ${counts.problems} with problems`}
            </p>
          </div>
          {completed.length > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm text-slate-500">Download all:</span>
              <FormatButtons
                label="Download the whole batch"
                onExport={(fmt) =>
                  exportDocs(fmt, "unified", { items: completed.slice(0, 500).map((e) => ({ filename: e.filename, document: e.document })) })
                }
              />
              <Button variant="ghost" size="sm" onClick={() => setBatch((current) => current.filter((e) => ACTIVE.has(e.status)))}>
                Clear finished
              </Button>
            </div>
          )}
        </div>

        {batch.length === 0 ? (
          <Card className="mt-4 grid place-items-center border-dashed px-6 py-14 text-center">
            <FileStack className="size-10 text-slate-300 dark:text-slate-700" />
            <p className="mt-3 font-semibold">Your processed documents will appear here</p>
            <p className="mt-1 max-w-sm text-sm text-slate-500">Upload a PDF above and watch it go from queued to completed in a few seconds.</p>
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
            Process-only results are not stored: they expire after 1 hour. Download them to keep them.
          </p>
        )}
      </section>

      {completed.length > 0 && (
        <section className="mt-10" aria-label="Charts">
          <h2 className="mb-4 text-xl font-bold tracking-tight">Charts</h2>
          <BatchCharts documents={completed.map((e) => e.document as ExtractedDocument)} />
        </section>
      )}

      {/* ------------------------------------------------ saved history */}
      {(canSave || (saved && saved.length > 0)) && (
        <section className="mt-10" aria-labelledby="history-title">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 id="history-title" className="flex items-center gap-2 text-xl font-bold tracking-tight">
              <History className="size-5 text-violet-500" /> Saved documents
            </h2>
            {saved && saved.length > 0 && (
              <FormatButtons
                label="Download all saved documents"
                onExport={(fmt) => exportDocs(fmt, "unified", { items: saved.slice(0, 500).map((d) => ({ filename: d.filename, document: d.document })) })}
              />
            )}
          </div>
          {saved === null ? (
            <div className="skeleton mt-4 h-24 w-full" />
          ) : saved.length === 0 ? (
            <p className="mt-3 text-sm text-slate-500">Choose “Save to history” when uploading to keep documents here.</p>
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
