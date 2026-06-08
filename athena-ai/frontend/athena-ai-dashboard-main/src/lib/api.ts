import type {
  AgentWorkflowResponse,
  AuthResponse,
  Event,
  EventCreate,
  EventListParams,
  EventUpdate,
  MeResponse,
  PaginatedResponse,
} from "./types";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const ACCESS_KEY = "athena_access_token";
const REFRESH_KEY = "athena_refresh_token";

export const tokenStore = {
  getAccess: () => (typeof window === "undefined" ? null : localStorage.getItem(ACCESS_KEY)),
  getRefresh: () => (typeof window === "undefined" ? null : localStorage.getItem(REFRESH_KEY)),
  set: (access: string, refresh: string) => {
    localStorage.setItem(ACCESS_KEY, access);
    localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear: () => {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

export function getApiErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

function getErrorMessage(data: unknown, fallback: string): string {
  if (typeof data === "string") return data;
  if (!data || typeof data !== "object") return fallback;

  const detail = "detail" in data ? (data as { detail?: unknown }).detail : undefined;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: unknown }).msg);
        }
        return String(item);
      })
      .join(", ");
  }
  if (detail && typeof detail === "object" && "message" in detail) {
    const message = (detail as { message?: unknown }).message;
    if (typeof message === "string") return message;
  }

  const message = "message" in data ? (data as { message?: unknown }).message : undefined;
  return typeof message === "string" ? message : fallback;
}

async function request<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(opts.headers as Record<string, string> | undefined),
  };
  const token = tokenStore.getAccess();
  if (token) headers.Authorization = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, { ...opts, headers });
  } catch (error) {
    throw new ApiError(
      error instanceof TypeError
        ? "Could not reach the Athena API. Check the backend URL and CORS settings."
        : "Network request failed",
      0,
      error,
    );
  }

  const text = await res.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }

  if (!res.ok) {
    throw new ApiError(
      getErrorMessage(data, `Request failed with ${res.status}`),
      res.status,
      data,
    );
  }

  return data as T;
}

function appendParam(q: URLSearchParams, key: string, value?: string | string[] | null) {
  if (!value) return;
  const values = Array.isArray(value) ? value : [value];
  values
    .map((item) => item.trim())
    .filter(Boolean)
    .forEach((item) => q.append(key, item));
}

export const api = {
  register: (payload: { name: string; email: string; password: string; role?: string }) =>
    request<AuthResponse>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  login: (payload: { email: string; password: string }) =>
    request<AuthResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getMe: async () => {
    const response = await request<MeResponse>("/api/auth/me");
    return response.user;
  },
  me: async () => {
    const response = await request<MeResponse>("/api/auth/me");
    return response.user;
  },
  refreshToken: (refresh_token: string) =>
    request<AuthResponse>("/api/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token }),
    }),
  refresh: (refresh_token: string) =>
    request<AuthResponse>("/api/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token }),
    }),
  logout: (refresh_token: string) =>
    request<void>("/api/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token }),
    }),

  listEvents: (params: EventListParams = {}) => {
    const q = new URLSearchParams();
    q.set("page", String(params.page ?? 1));
    q.set("page_size", String(params.page_size ?? 20));
    appendParam(q, "search", params.search);
    appendParam(q, "severity", params.severity);
    appendParam(q, "status", params.status);
    appendParam(q, "event_type", params.event_type);
    appendParam(q, "tenant_id", params.tenant_id);
    appendParam(q, "sort_by", params.sort_by);
    appendParam(q, "sort_order", params.sort_order);
    return request<PaginatedResponse<Event>>(`/api/events?${q.toString()}`);
  },
  getEvent: (id: string) => request<Event>(`/api/events/${id}`),
  createEvent: (body: EventCreate) =>
    request<Event>("/api/events", { method: "POST", body: JSON.stringify(body) }),
  updateEvent: (id: string, body: EventUpdate) =>
    request<Event>(`/api/events/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  deleteEvent: (id: string) => request<void>(`/api/events/${id}`, { method: "DELETE" }),

  runAgentWorkflow: (eventId: string) =>
    request<AgentWorkflowResponse>(`/api/agents/run/${eventId}`, { method: "POST" }),
  runWorkflow: (eventId: string) =>
    request<AgentWorkflowResponse>(`/api/agents/run/${eventId}`, { method: "POST" }),
};
