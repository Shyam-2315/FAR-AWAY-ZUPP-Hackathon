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
  url?: string;

  constructor(message: string, status: number, data?: unknown, url?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
    this.url = url;
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

function describeHttpError(statusCode: number, data: unknown, url: string): string {
  if (statusCode === 404) {
    return `Athena API endpoint was not found: ${url}. Verify the backend route and API base URL.`;
  }
  if (statusCode === 422) {
    return `Athena API validation error: ${getErrorMessage(data, "Check the submitted fields.")}`;
  }
  if (statusCode >= 500) {
    return `Athena API backend error (${statusCode}). Check the FastAPI logs. ${getErrorMessage(
      data,
      "No error details were returned.",
    )}`;
  }
  return getErrorMessage(data, `Athena API request failed with status ${statusCode}.`);
}

async function diagnoseFetchFailure(url: string, error: unknown): Promise<ApiError> {
  if (typeof window !== "undefined" && !window.navigator.onLine) {
    return new ApiError("The browser is offline. Connect to the network and retry.", 0, error, url);
  }

  try {
    await fetch(url, { method: "GET", mode: "no-cors", cache: "no-store" });
    const origin = typeof window === "undefined" ? "the frontend origin" : window.location.origin;
    return new ApiError(
      `CORS blocked the Athena API response from ${url}. Ensure FRONTEND_ORIGINS includes ${origin}.`,
      0,
      error,
      url,
    );
  } catch {
    return new ApiError(
      `Could not reach the Athena API at ${API_BASE_URL}. Confirm the backend is running on http://localhost:8000 and the port is not stale.`,
      0,
      error,
      url,
    );
  }
}

function redirectToLogin() {
  if (typeof window !== "undefined" && window.location.pathname !== "/login") {
    window.location.assign("/login");
  }
}

async function request<T>(
  path: string,
  opts: RequestInit = {},
  retryOnUnauthorized = true,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(opts.headers as Record<string, string> | undefined),
  };
  const token = tokenStore.getAccess();
  if (token) headers.Authorization = `Bearer ${token}`;

  const url = `${API_BASE_URL}${path}`;
  const requestPayload = typeof opts.body === "string" ? opts.body : (opts.body ?? null);
  console.log("[Athena API] request", {
    url,
    payload: requestPayload,
  });

  let res: Response;
  try {
    res = await fetch(url, { ...opts, headers });
  } catch (error) {
    throw await diagnoseFetchFailure(url, error);
  }

  const text = await res.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }

  console.log("[Athena API] response", {
    url,
    status: res.status,
    body: data,
  });

  if (res.status === 401 && retryOnUnauthorized && path !== "/api/auth/refresh") {
    const refresh = tokenStore.getRefresh();
    if (refresh) {
      try {
        const refreshed = await request<AuthResponse>(
          "/api/auth/refresh",
          {
            method: "POST",
            body: JSON.stringify({ refresh_token: refresh }),
          },
          false,
        );
        tokenStore.set(refreshed.access_token, refreshed.refresh_token);
        return request<T>(path, opts, false);
      } catch {
        tokenStore.clear();
        redirectToLogin();
      }
    } else {
      tokenStore.clear();
      redirectToLogin();
    }
  }

  if (!res.ok) {
    throw new ApiError(describeHttpError(res.status, data, url), res.status, data, url);
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
  healthCheck: () => request<{ status: string; service: string }>("/healthz", {}, false),
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
