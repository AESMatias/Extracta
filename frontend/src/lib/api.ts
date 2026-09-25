// Typed client for the Flask API. Every call goes to the same origin (/api/...), so the signed,
// HttpOnly session cookie travels automatically and no token is ever stored in JavaScript.

export type PlanId = "free" | "starter" | "pro" | "business" | "ultra";
export type UserStatus = "pending" | "active" | "rejected" | "suspended";
export type ExportFormat = "csv" | "xlsx" | "json";
export type DocumentType =
  | "invoice"
  | "receipt"
  | "purchase_order"
  | "quote"
  | "bank_statement"
  | "contract"
  | "payslip"
  | "resume"
  | "report"
  | "other";

export interface Privileges {
  docs_per_24h: number;
  max_file_mb: number;
  max_files_per_upload: number;
  can_save_to_db: boolean;
  export_formats: ExportFormat[];
}

export interface Plan {
  id: PlanId;
  name: string;
  price_usd: string;
  duration_days: number;
  tagline: string;
  highlight: boolean;
  privileges: Privileges;
}

export interface Usage {
  used: number;
  limit: number;
  remaining: number;
  next_slot_at: string | null;
}

export interface User {
  id: string;
  email: string;
  name: string | null;
  status: UserStatus;
  plan: Plan;
  plan_expires_at: string | null;
  has_password: boolean;
  has_google: boolean;
  daily_limit: number;
  created_at: string;
  usage?: Usage;
}

export interface Party {
  name: string;
  tax_id?: string | null;
  address?: string | null;
  role?: string | null;
}

export interface ExtractedDocument {
  document_type: DocumentType;
  language?: string | null;
  title?: string | null;
  summary: string;
  commercial?: {
    document_number?: string | null;
    issue_date?: string | null;
    due_date?: string | null;
    issuer: Party;
    recipient?: Party | null;
    currency?: string | null;
    subtotal?: number | null;
    tax_amount?: number | null;
    total_amount?: number | null;
    line_items: { description: string; quantity?: number | null; unit_price?: number | null; amount?: number | null }[];
  } | null;
  bank_statement?: {
    bank_name?: string | null;
    account_holder?: string | null;
    account_number_last4?: string | null;
    currency?: string | null;
    closing_balance?: number | null;
  } | null;
  contract?: { title?: string | null; parties: Party[]; contract_value?: number | null; currency?: string | null } | null;
  payslip?: { employee_name?: string | null; employer_name?: string | null; net_pay?: number | null; currency?: string | null } | null;
  resume?: { full_name?: string | null; current_title?: string | null } | null;
  report?: { title?: string | null; period_covered?: string | null } | null;
}

export interface TaskResult {
  task_id: string;
  filename: string;
  saved_to_db: boolean;
  page_count: number;
  truncated: boolean;
  llm_provider: string;
  llm_model: string;
  document: ExtractedDocument;
}

export type TaskState = "pending" | "processing" | "completed" | "failed" | "not_found";

export interface TaskStatus {
  task_id: string;
  status: TaskState;
  result?: TaskResult;
  error?: string;
}

export interface UploadResponse {
  save_to_db: boolean;
  tasks: { task_id: string; filename: string }[];
  rejected: { filename: string; error: string }[];
  usage: { used: number; limit: number };
}

export interface SavedDocument {
  id: string;
  filename: string;
  document_type: DocumentType;
  title: string | null;
  summary: string;
  created_at: string;
  document: ExtractedDocument;
}

export interface Payment {
  plan: PlanId;
  amount: string;
  currency: string;
  status: string;
  created_at: string;
}

export interface AdminUser extends User {
  assigned_plan: PlanId;
  raw_plan_expires_at: string | null;
  daily_limit_override: number | null;
  privileges: Privileges;
  uploads_24h: number;
  uploads_total: number;
  paid_total_usd: string;
  last_login_at: string | null;
  sign_in_methods: ("password" | "google")[];
}

export interface AdminPayment extends Payment {
  id: string;
  email: string;
  provider_order_id: string;
}

export interface AdminStats {
  users_by_status: Partial<Record<UserStatus, number>>;
  users_by_plan: Partial<Record<PlanId, number>>;
  uploads_24h: number;
  revenue_usd: string;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly data: Record<string, unknown> = {},
  ) {
    super(message);
  }

  get upgrade(): boolean {
    return this.data.upgrade === true;
  }
}

interface RequestOptions {
  method?: string;
  json?: unknown;
}

async function toError(response: Response): Promise<ApiError> {
  const data = (await response.json().catch(() => ({}))) as Record<string, unknown>;
  const message = typeof data.error === "string" ? data.error : `Request failed (HTTP ${response.status}).`;
  return new ApiError(response.status, message, data);
}

async function request<T>(path: string, { method = "GET", json }: RequestOptions = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      method,
      credentials: "same-origin",
      headers: json === undefined ? undefined : { "Content-Type": "application/json" },
      body: json === undefined ? undefined : JSON.stringify(json),
    });
  } catch {
    throw new ApiError(0, "Network error: check your connection and try again.");
  }
  if (!response.ok) throw await toError(response);
  return (await response.json()) as T;
}

function uploadWithProgress(files: File[], saveToDb: boolean, onProgress: (fraction: number) => void): Promise<UploadResponse> {
  // XMLHttpRequest instead of fetch: it reports upload progress for the progress bar.
  return new Promise((resolve, reject) => {
    const form = new FormData();
    for (const file of files) form.append("files", file, file.name);
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `/api/upload?save_to_db=${saveToDb}`);
    xhr.responseType = "json";
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(event.loaded / event.total);
    };
    xhr.onload = () => {
      const data = (xhr.response ?? {}) as Record<string, unknown>;
      if (xhr.status >= 200 && xhr.status < 300) resolve(data as unknown as UploadResponse);
      else if (xhr.status === 400 && Array.isArray(data.tasks)) resolve(data as unknown as UploadResponse);
      else reject(new ApiError(xhr.status, typeof data.error === "string" ? data.error : `Upload failed (HTTP ${xhr.status}).`, data));
    };
    xhr.onerror = () => reject(new ApiError(0, "Network error: the upload did not reach the server."));
    xhr.send(form);
  });
}

function filenameFrom(response: Response, fallback: string): string {
  const header = response.headers.get("Content-Disposition") ?? "";
  const utf8 = /filename\*=UTF-8''([^;]+)/i.exec(header);
  if (utf8?.[1]) return decodeURIComponent(utf8[1]);
  const plain = /filename="([^"]+)"/i.exec(header);
  return plain?.[1] ?? fallback;
}

async function download(fmt: ExportFormat, scope: "individual" | "unified", payload: unknown): Promise<void> {
  const response = await fetch(`/api/export/${fmt}/${scope}`, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw await toError(response);
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = filenameFrom(response, `export.${fmt}`);
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export const api = {
  me: () => request<{ user: User | null }>("/api/auth/me"),
  providers: () => request<{ google: boolean; manual_approval: boolean }>("/api/auth/providers"),
  register: (body: { email: string; password: string; name: string }) =>
    request<{ user: User }>("/api/auth/register", { method: "POST", json: body }),
  login: (body: { email: string; password: string }) => request<{ user: User }>("/api/auth/login", { method: "POST", json: body }),
  logout: () => request<{ ok: boolean }>("/api/auth/logout", { method: "POST" }),

  plans: () => request<{ plans: Plan[] }>("/api/plans"),
  upload: uploadWithProgress,
  taskStatuses: (taskIds: string[]) => request<{ tasks: TaskStatus[] }>("/api/tasks/status", { method: "POST", json: { task_ids: taskIds } }),
  documents: () => request<{ documents: SavedDocument[] }>("/api/documents"),
  deleteDocument: (id: string) => request<{ deleted: string }>(`/api/documents/${id}`, { method: "DELETE" }),
  download,

  billingConfig: () => request<{ enabled: boolean; client_id?: string; currency?: string; env?: string }>("/api/billing/config"),
  createOrder: (plan: PlanId) => request<{ order_id: string }>("/api/billing/orders", { method: "POST", json: { plan } }),
  captureOrder: (orderId: string) => request<{ user: User }>(`/api/billing/orders/${orderId}/capture`, { method: "POST" }),
  payments: () => request<{ payments: Payment[] }>("/api/billing/payments"),

  admin: {
    session: () => request<{ enabled: boolean; authenticated: boolean }>("/api/admin/session"),
    login: (password: string) => request<{ authenticated: boolean }>("/api/admin/login", { method: "POST", json: { password } }),
    logout: () => request<{ authenticated: boolean }>("/api/admin/logout", { method: "POST" }),
    users: (params: { status?: string; q?: string }) => {
      const query = new URLSearchParams(Object.entries(params).filter(([, v]) => v) as [string, string][]);
      return request<{ users: AdminUser[]; plans: Plan[] }>(`/api/admin/users?${query}`);
    },
    updateUser: (id: string, changes: Partial<Pick<AdminUser, "status" | "daily_limit_override">> & { plan?: PlanId; plan_expires_at?: string | null }) =>
      request<{ user: AdminUser }>(`/api/admin/users/${id}`, { method: "PATCH", json: changes }),
    payments: () => request<{ payments: AdminPayment[] }>("/api/admin/payments"),
    stats: () => request<AdminStats>("/api/admin/stats"),
  },
};
