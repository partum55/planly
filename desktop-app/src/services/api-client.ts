import axios, { AxiosInstance } from 'axios';
import { execFile } from 'child_process';
import { AuthStore } from './auth';

// ─── Widget Protocol (Agent 2 defines, Agent 1 implements) ──

export type ResponseBlock =
  | { type: 'text'; content: string }
  | { type: 'action_cards'; actions: ProposedAction[] }
  | { type: 'calendar_picker'; prompt: string }
  | { type: 'time_picker'; prompt: string }
  | { type: 'error'; message: string };

export interface ProposedAction {
  action_id: string;
  tool: string;
  description: string;
  parameters: Record<string, unknown>;
}

export interface AgentProcessResponse {
  conversation_id: string;
  blocks: ResponseBlock[];
}

export interface ConfirmActionsResponse {
  results: {
    action_id: string;
    tool: string;
    success: boolean;
    result: Record<string, unknown>;
  }[];
  formatted_response?: string;
}

export interface LoginResponse {
  user_id: string;
  access_token: string;
  refresh_token: string;
}

export interface RegisterResponse {
  user_id: string;
  access_token: string;
  refresh_token: string;
}

// ─── API Client ─────────────────────────────────────────────

export class ApiClient {
  private client: AxiosInstance;
  private authStore: AuthStore;
  private baseURL: string;

  constructor(baseURL: string, authStore: AuthStore) {
    this.authStore = authStore;
    this.baseURL = baseURL;

    this.client = axios.create({
      baseURL,
      timeout: 30_000,
      headers: { 'Content-Type': 'application/json' },
    });

    // Attach auth token to every request
    this.client.interceptors.request.use((config) => {
      const token = this.authStore.getAccessToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Auto-refresh on 401
    this.client.interceptors.response.use(
      (res) => res,
      async (error) => {
        const original = error.config;
        if (error.response?.status === 401 && !original._retried) {
          original._retried = true;
          const refreshed = await this.refreshToken();
          if (refreshed) {
            return this.client.request(original);
          }
        }
        return Promise.reject(error);
      }
    );
  }

  // ─── Health ────────────────────────────────────────────

  async healthCheck(): Promise<boolean> {
    const url = `${this.baseURL}/health`;
    return new Promise((resolve) => {
      execFile('curl', ['-s', '--connect-timeout', '5', url], (err, stdout) => {
        if (err) { resolve(false); return; }
        try {
          const data = JSON.parse(stdout);
          resolve(data.status === 'ok');
        } catch {
          resolve(false);
        }
      });
    });
  }

  // ─── Auth ───────────────────────────────────────────────

  async login(email: string, password: string): Promise<LoginResponse> {
    const { data } = await this.client.post<LoginResponse>('/auth/login', {
      email,
      password,
    });
    this.authStore.setTokens(data.access_token, data.refresh_token);
    return data;
  }

  async register(
    email: string,
    password: string,
    fullName: string
  ): Promise<RegisterResponse> {
    const { data } = await this.client.post<RegisterResponse>(
      '/auth/register',
      { email, password, full_name: fullName }
    );
    this.authStore.setTokens(data.access_token, data.refresh_token);
    return data;
  }

  async getMe(): Promise<{ full_name?: string; email?: string } | null> {
    try {
      const { data } = await this.client.get<{ full_name?: string; email?: string }>('/auth/me');
      return data;
    } catch {
      return null;
    }
  }

  async refreshToken(): Promise<boolean> {
    const refreshToken = this.authStore.getRefreshToken();
    if (!refreshToken) return false;

    try {
      const { data } = await this.client.post<{
        access_token: string;
        refresh_token: string;
      }>('/auth/refresh', { refresh_token: refreshToken });

      this.authStore.setTokens(data.access_token, data.refresh_token);
      return true;
    } catch {
      this.authStore.clear();
      return false;
    }
  }

  // ─── Agent ──────────────────────────────────────────────

  async processConversation(params: {
    conversation_id?: string;
    user_prompt: string;
    messages: { username: string; text: string; timestamp: string }[];
    screenshot_metadata: {
      ocr_confidence: number;
      raw_text?: string;
    };
  }): Promise<AgentProcessResponse> {
    const { data } = await this.client.post<AgentProcessResponse>(
      '/agent/process',
      {
        source: 'desktop_screenshot',
        conversation_id: params.conversation_id,
        user_prompt: params.user_prompt,
        context: {
          messages: params.messages,
          screenshot_metadata: params.screenshot_metadata,
        },
      }
    );
    return data;
  }

  async logout(): Promise<void> {
    try {
      await this.client.post('/auth/logout');
    } catch {
      // Best-effort — clear local tokens regardless
    }
    this.authStore.clear();
  }

  async deleteUser(): Promise<void> {
    await this.client.delete('/auth/me');
    this.authStore.clear();
  }

  async confirmActions(
    conversationId: string,
    actionIds: string[]
  ): Promise<ConfirmActionsResponse> {
    const { data } = await this.client.post<ConfirmActionsResponse>(
      '/agent/confirm-actions',
      {
        conversation_id: conversationId,
        action_ids: actionIds,
      }
    );
    return data;
  }
}
