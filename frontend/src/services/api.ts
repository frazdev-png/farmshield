import type {
  BackendHealthResponse,
  User,
  AuthResponse,
  RegisterPayload,
  LoginPayload,
  Farm,
  FarmCreatePayload,
  FarmUpdatePayload,
  FarmCrop,
  FarmCropCreatePayload,
  FarmCropUpdatePayload,
  WeatherObservation,
  WeatherForecastResponse,
  RiskAssessment,
  RiskSummary,
  AssistantChatRequest,
  AssistantChatResponse,
  ConversationDetail,
  ConversationSummary,
  FarmerPreference,
  NotificationItem,
  NotificationListResponse,
  AdminBroadcastRequest,
  AdminBroadcastPreviewResponse,
  AdminBroadcastResponse,
  AdminOverviewStats,
  AdminFarmerItem,
  AdminRiskMonitoringItem,
  AdminAgentActivityItem,
  FarmerActionResponse,
} from '../types';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const TOKEN_KEY = 'farmshield_access_token';

export const tokenStorage = {
  get: (): string | null => {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set: (token: string): void => {
    try {
      localStorage.setItem(TOKEN_KEY, token);
    } catch {
      // ignore
    }
  },
  remove: (): void => {
    try {
      localStorage.removeItem(TOKEN_KEY);
    } catch {
      // ignore
    }
  },
};

export class ApiError extends Error {
  status?: number;
  data?: unknown;

  constructor(message: string, status?: number, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

/**
 * Generic request helper with timeout and standardized error handling.
 */
async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL.replace(/\/$/, '')}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  const headers = new Headers({
    'Content-Type': 'application/json',
    Accept: 'application/json',
    ...(options.headers || {}),
  });

  // Attach Bearer token if available
  const token = tokenStorage.get();
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 6000);

  try {
    const response = await fetch(url, {
      ...options,
      headers,
      credentials: 'include', // Support HttpOnly secure cookies
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (response.status === 204) {
      return undefined as unknown as T;
    }

    if (!response.ok) {
      let errorBody: any;
      try {
        errorBody = await response.json();
      } catch {
        errorBody = await response.text();
      }

      // Extract detailed server error message if available
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      if (typeof errorBody === 'object' && errorBody !== null) {
        if (errorBody.error && typeof errorBody.error.message === 'string') {
          errorMessage = errorBody.error.message;
        } else if (typeof errorBody.detail === 'string') {
          errorMessage = errorBody.detail;
        } else if (Array.isArray(errorBody.detail) && errorBody.detail.length > 0) {
          errorMessage = errorBody.detail[0].msg || errorMessage;
        }
      } else if (typeof errorBody === 'string' && errorBody.trim().length > 0) {
        errorMessage = errorBody;
      }

      throw new ApiError(errorMessage, response.status, errorBody);
    }

    return (await response.json()) as T;
  } catch (error: unknown) {
    clearTimeout(timeoutId);
    if (error instanceof ApiError) {
      throw error;
    }
    if (error instanceof Error && error.name === 'AbortError') {
      throw new ApiError('Connection timed out after 6 seconds. Ensure backend is running.');
    }
    throw new ApiError(
      `Cannot connect to backend at ${API_BASE_URL}. Please ensure FastAPI is running.`
    );
  }
}

/**
 * Health check querying the primary API v1 health endpoint with automatic fallback to root /health.
 */
export async function fetchHealthStatus(): Promise<{ data: BackendHealthResponse; latencyMs: number }> {
  const startTime = performance.now();
  try {
    const data = await request<BackendHealthResponse>('/api/v1/health');
    const latencyMs = Math.round(performance.now() - startTime);
    return { data, latencyMs };
  } catch {
    // Attempt fallback to root /health (useful for ALB probe testing)
    const fallbackData = await request<BackendHealthResponse>('/health');
    const latencyMs = Math.round(performance.now() - startTime);
    return { data: fallbackData, latencyMs };
  }
}

export const api = {
  get: <T>(endpoint: string) => request<T>(endpoint, { method: 'GET' }),
  post: <T>(endpoint: string, body: unknown) =>
    request<T>(endpoint, { method: 'POST', body: JSON.stringify(body) }),
  checkHealth: fetchHealthStatus,

  // Authentication endpoints
  auth: {
    register: (payload: RegisterPayload) =>
      request<User>('/api/v1/auth/register', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    login: (payload: LoginPayload) =>
      request<AuthResponse>('/api/v1/auth/login', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    getMe: () => request<User>('/api/v1/auth/me', { method: 'GET' }),
    logout: () => {
      tokenStorage.remove();
    },
  },

  // Farm management endpoints
  farms: {
    list: () => request<Farm[]>('/api/v1/farms', { method: 'GET' }),
    get: (farmId: string) => request<Farm>(`/api/v1/farms/${farmId}`, { method: 'GET' }),
    create: (payload: FarmCreatePayload) =>
      request<Farm>('/api/v1/farms', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    update: (farmId: string, payload: FarmUpdatePayload) =>
      request<Farm>(`/api/v1/farms/${farmId}`, {
        method: 'PUT',
        body: JSON.stringify(payload),
      }),
    delete: (farmId: string) =>
      request<void>(`/api/v1/farms/${farmId}`, {
        method: 'DELETE',
      }),
    crops: {
      list: (farmId: string) =>
        request<FarmCrop[]>(`/api/v1/farms/${farmId}/crops`, { method: 'GET' }),
      create: (farmId: string, payload: FarmCropCreatePayload) =>
        request<FarmCrop>(`/api/v1/farms/${farmId}/crops`, {
          method: 'POST',
          body: JSON.stringify(payload),
        }),
      update: (farmId: string, cropId: string, payload: FarmCropUpdatePayload) =>
        request<FarmCrop>(`/api/v1/farms/${farmId}/crops/${cropId}`, {
          method: 'PUT',
          body: JSON.stringify(payload),
        }),
      delete: (farmId: string, cropId: string) =>
        request<void>(`/api/v1/farms/${farmId}/crops/${cropId}`, {
          method: 'DELETE',
        }),
    },
  },

  // Weather endpoints
  weather: {
    getCurrent: (farmId: string) =>
      request<WeatherObservation>(`/api/v1/farms/${farmId}/weather/current`, { method: 'GET' }),
    getForecast: (farmId: string) =>
      request<WeatherForecastResponse>(`/api/v1/farms/${farmId}/weather/forecast`, { method: 'GET' }),
    refresh: (farmId: string) =>
      request<WeatherObservation>(`/api/v1/farms/${farmId}/weather/refresh`, { method: 'POST' }),
  },

  // Deterministic Risk endpoints
  risks: {
    getRisks: (farmId: string, limit = 50, category?: string) => {
      const query = new URLSearchParams();
      query.set('limit', String(limit));
      if (category) query.set('category', category);
      return request<RiskAssessment[]>(`/api/v1/farms/${farmId}/risks?${query.toString()}`, {
        method: 'GET',
      });
    },
    getLatest: (farmId: string) =>
      request<RiskSummary>(`/api/v1/farms/${farmId}/risks/latest`, { method: 'GET' }),
    evaluate: (farmId: string) =>
      request<RiskSummary>(`/api/v1/farms/${farmId}/risks/evaluate`, { method: 'POST' }),
  },

  // Strands AI Agronomy Assistant endpoints
  assistant: {
    chat: (payload: AssistantChatRequest) =>
      request<AssistantChatResponse>('/api/v1/assistant/chat', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    listConversations: (farmId?: string) => {
      const query = farmId ? `?farm_id=${farmId}` : '';
      return request<ConversationSummary[]>(`/api/v1/assistant/conversations${query}`, {
        method: 'GET',
      });
    },
    getConversation: (conversationId: string) =>
      request<ConversationDetail>(`/api/v1/assistant/conversations/${conversationId}`, {
        method: 'GET',
      }),
  },

  // Notification & AWS SNS endpoints
  notifications: {
    list: (params?: { farmId?: string; unreadOnly?: boolean; limit?: number; offset?: number }) => {
      const query = new URLSearchParams();
      if (params?.farmId) query.set('farm_id', params.farmId);
      if (params?.unreadOnly) query.set('unread_only', 'true');
      if (params?.limit) query.set('limit', String(params.limit));
      if (params?.offset) query.set('offset', String(params.offset));
      const queryString = query.toString() ? `?${query.toString()}` : '';
      return request<NotificationListResponse>(`/api/v1/notifications${queryString}`, {
        method: 'GET',
      });
    },
    get: (id: string) =>
      request<NotificationItem>(`/api/v1/notifications/${id}`, { method: 'GET' }),
    markRead: (id: string) =>
      request<{ success: boolean; message: string; notification: NotificationItem }>(
        `/api/v1/notifications/${id}/read`,
        { method: 'POST' }
      ),
    markAllRead: () =>
      request<{ success: boolean; marked_count: number }>('/api/v1/notifications/mark-all-read', {
        method: 'POST',
      }),
    getPreferences: () =>
      request<FarmerPreference>('/api/v1/notifications/preferences', { method: 'GET' }),
    updatePreferences: (payload: { sms_consent: boolean; language_preference?: string }) =>
      request<FarmerPreference>('/api/v1/notifications/preferences', {
        method: 'PATCH',
        body: JSON.stringify(payload),
      }),
  },

  // Admin Operations endpoints
  admin: {
    getOverviewStats: () =>
      request<AdminOverviewStats>('/api/v1/admin/overview', { method: 'GET' }),
    listFarmers: (params?: { limit?: number; offset?: number }) => {
      const query = new URLSearchParams();
      if (params?.limit) query.set('limit', String(params.limit));
      if (params?.offset) query.set('offset', String(params.offset));
      const queryString = query.toString() ? `?${query.toString()}` : '';
      return request<AdminFarmerItem[]>(`/api/v1/admin/farmers${queryString}`, { method: 'GET' });
    },
    updateFarmerStatus: (farmerId: string, isActive: boolean) =>
      request<FarmerActionResponse>(`/api/v1/admin/farmers/${farmerId}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ is_active: isActive }),
      }),
    deleteFarmer: (farmerId: string) =>
      request<FarmerActionResponse>(`/api/v1/admin/farmers/${farmerId}`, {
        method: 'DELETE',
      }),
    listRisks: (params?: { severity?: string; limit?: number }) => {
      const query = new URLSearchParams();
      if (params?.severity) query.set('severity', params.severity);
      if (params?.limit) query.set('limit', String(params.limit));
      const queryString = query.toString() ? `?${query.toString()}` : '';
      return request<AdminRiskMonitoringItem[]>(`/api/v1/admin/risks${queryString}`, { method: 'GET' });
    },
    listAgentActivity: (params?: { limit?: number }) => {
      const query = new URLSearchParams();
      if (params?.limit) query.set('limit', String(params.limit));
      const queryString = query.toString() ? `?${query.toString()}` : '';
      return request<AdminAgentActivityItem[]>(`/api/v1/admin/agent-activity${queryString}`, { method: 'GET' });
    },
    notifications: {
      list: (params?: { severity?: string; status?: string; limit?: number; offset?: number }) => {
        const query = new URLSearchParams();
        if (params?.severity) query.set('severity', params.severity);
        if (params?.status) query.set('status', params.status);
        if (params?.limit) query.set('limit', String(params.limit));
        if (params?.offset) query.set('offset', String(params.offset));
        const queryString = query.toString() ? `?${query.toString()}` : '';
        return request<NotificationListResponse>(`/api/v1/admin/notifications${queryString}`, {
          method: 'GET',
        });
      },
      get: (id: string) =>
        request<NotificationItem>(`/api/v1/admin/notifications/${id}`, { method: 'GET' }),
      preview: (payload: AdminBroadcastRequest) =>
        request<AdminBroadcastPreviewResponse>('/api/v1/admin/notifications/broadcast/preview', {
          method: 'POST',
          body: JSON.stringify(payload),
        }),
      broadcast: (payload: AdminBroadcastRequest) =>
        request<AdminBroadcastResponse>('/api/v1/admin/notifications/broadcast', {
          method: 'POST',
          body: JSON.stringify({ ...payload, confirmed: true }),
        }),
      retry: (limit = 20) =>
        request<NotificationListResponse>(`/api/v1/admin/notifications/retry?limit=${limit}`, {
          method: 'POST',
        }),
    },
  },
};
