import type {
  Analysis,
  BillingConfig,
  BillingStatus,
  CheckoutPayload,
  CheckoutResponse,
  OutputFile,
  ParseResult,
  ProjectMetadata,
  ProjectPlan,
  ProjectSnapshot
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";
const BILLING_EMAIL_KEY = "ali-pmo-billing-email";

export function getBillingEmail() {
  return localStorage.getItem(BILLING_EMAIL_KEY) ?? "";
}

export function setBillingEmail(email: string) {
  localStorage.setItem(BILLING_EMAIL_KEY, email.trim().toLowerCase());
}

async function requestJson<T>(path: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers);
  if (!(options?.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const email = getBillingEmail();
  if (email) {
    headers.set("X-Ali-User-Email", email);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function uploadDocument(file: File, onProgress: (progress: number) => void): Promise<{ file_id: string; metadata: ProjectMetadata }> {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append("file", file);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/api/upload`);
    const email = getBillingEmail();
    if (email) {
      xhr.setRequestHeader("X-Ali-User-Email", email);
    }
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        reject(new Error(xhr.responseText || `Upload failed: ${xhr.status}`));
      }
    };
    xhr.onerror = () => reject(new Error("Upload failed"));
    xhr.send(formData);
  });
}

export const api = {
  billingConfig: () => requestJson<BillingConfig>("/api/billing/config"),
  billingStatus: (email?: string) => requestJson<BillingStatus>(`/api/billing/status${email ? `?email=${encodeURIComponent(email)}` : ""}`),
  createCheckout: (payload: CheckoutPayload) => requestJson<CheckoutResponse>("/api/billing/checkout", { method: "POST", body: JSON.stringify(payload) }),
  confirmBilling: (tapId: string, email: string) =>
    requestJson<BillingStatus & { subscription: NonNullable<BillingStatus["subscription"]> }>(
      `/api/billing/confirm?tap_id=${encodeURIComponent(tapId)}&email=${encodeURIComponent(email)}`
    ),
  projects: () => requestJson<{ projects: ProjectMetadata[] }>("/api/projects"),
  snapshot: (fileId: string) => requestJson<ProjectSnapshot>(`/api/project/${fileId}`),
  parse: (fileId: string) => requestJson<ParseResult>(`/api/parse/${fileId}`, { method: "POST" }),
  analyze: (fileId: string) => requestJson<Analysis>(`/api/analyze/${fileId}`, { method: "POST" }),
  generatePlan: (fileId: string) => requestJson<ProjectPlan>(`/api/generate-plan/${fileId}`, { method: "POST" }),
  generateOutputs: (fileId: string) => requestJson<{ file_id: string; outputs: OutputFile[] }>(`/api/generate-outputs/${fileId}`, { method: "POST" }),
  downloadUrl: (fileId: string, outputName: string) => {
    const email = getBillingEmail();
    return `${API_BASE}/api/download/${fileId}/${outputName}${email ? `?email=${encodeURIComponent(email)}` : ""}`;
  }
};
