import axios from 'axios';
import type { AnalysisResult, CachedAnalysisResult } from '@/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const SUPABASE_URL = (process.env.NEXT_PUBLIC_SUPABASE_URL || '').replace(/\/$/, '');
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';
const SUPABASE_AUTH_ENABLED = Boolean(SUPABASE_URL && SUPABASE_ANON_KEY);

const ACCESS_TOKEN_KEY = 'ari_supabase_access_token';
const REFRESH_TOKEN_KEY = 'ari_supabase_refresh_token';
const RECOVERY_SESSION_TOKEN = '__supabase_recovery_session__';

export interface AuthUser {
  id: number | string;
  email: string;
  role: 'user' | 'admin' | string;
  is_active: boolean;
  email_verified: boolean;
  email_verified_at?: string | null;
}

interface CachedResultsResponse {
  success: boolean;
  count: number;
  cache_enabled: boolean;
  results: CachedAnalysisResult[];
}

interface SupabaseSessionResponse {
  access_token?: string;
  refresh_token?: string;
  user?: Record<string, any>;
  expires_in?: number;
}

export interface AuthBootstrapResult {
  user: AuthUser | null;
  resetToken: string | null;
  handled: boolean;
}

function isBrowser(): boolean {
  return typeof window !== 'undefined';
}

function readStorage(key: string): string {
  if (!isBrowser()) return '';
  return window.localStorage.getItem(key) || '';
}

function writeStorage(key: string, value: string): void {
  if (!isBrowser()) return;
  window.localStorage.setItem(key, value);
}

function clearStorage(key: string): void {
  if (!isBrowser()) return;
  window.localStorage.removeItem(key);
}

function getSupabaseAccessToken(): string {
  return readStorage(ACCESS_TOKEN_KEY);
}

function getSupabaseRefreshToken(): string {
  return readStorage(REFRESH_TOKEN_KEY);
}

function storeSupabaseSession(session: SupabaseSessionResponse): void {
  if (session.access_token) {
    writeStorage(ACCESS_TOKEN_KEY, session.access_token);
  }
  if (session.refresh_token) {
    writeStorage(REFRESH_TOKEN_KEY, session.refresh_token);
  }
}

function clearSupabaseSession(): void {
  clearStorage(ACCESS_TOKEN_KEY);
  clearStorage(REFRESH_TOKEN_KEY);
}

function browserOrigin(): string | undefined {
  if (!isBrowser()) return undefined;
  return window.location.origin;
}

function readHashParams(): URLSearchParams {
  if (!isBrowser()) {
    return new URLSearchParams();
  }
  const hash = window.location.hash.startsWith('#')
    ? window.location.hash.slice(1)
    : window.location.hash;
  return new URLSearchParams(hash);
}

function stripAuthParamsFromUrl(): void {
  if (!isBrowser()) return;

  const searchParams = new URLSearchParams(window.location.search);
  const hashParams = readHashParams();
  const keys = [
    'verify_token',
    'reset_token',
    'token_hash',
    'type',
    'access_token',
    'refresh_token',
    'expires_in',
    'expires_at',
    'error',
    'error_code',
    'error_description',
  ];

  keys.forEach((key) => {
    searchParams.delete(key);
    hashParams.delete(key);
  });

  const search = searchParams.toString();
  const hash = hashParams.toString();
  const nextUrl = `${window.location.pathname}${search ? `?${search}` : ''}${hash ? `#${hash}` : ''}`;
  window.history.replaceState({}, '', nextUrl);
}

function mapSupabaseUser(user: Record<string, any>): AuthUser {
  const appMetadata = user?.app_metadata || {};
  const userMetadata = user?.user_metadata || {};
  const role = appMetadata.role || userMetadata.role || 'user';
  const emailVerifiedAt = user?.email_confirmed_at || user?.confirmed_at || null;

  return {
    id: String(user?.id || ''),
    email: String(user?.email || ''),
    role: String(role),
    is_active: true,
    email_verified: Boolean(emailVerifiedAt),
    email_verified_at: emailVerifiedAt,
  };
}

function ensureSupabaseAuthConfigured(): void {
  if (!SUPABASE_AUTH_ENABLED) {
    throw new Error(
      'Supabase auth is not configured. Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY.',
    );
  }
}

async function supabaseFetch(path: string, init: RequestInit = {}): Promise<Response> {
  ensureSupabaseAuthConfigured();

  const headers = new Headers(init.headers || {});
  headers.set('apikey', SUPABASE_ANON_KEY);
  if (!headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(`${SUPABASE_URL}${path}`, {
    ...init,
    headers,
  });
  return response;
}

async function parseSupabaseError(response: Response): Promise<string> {
  try {
    const payload = await response.json();
    return payload?.msg || payload?.error_description || payload?.error || `Supabase error: ${response.status}`;
  } catch {
    return `Supabase error: ${response.status}`;
  }
}

async function refreshSupabaseAccessToken(): Promise<string> {
  const refreshToken = getSupabaseRefreshToken();
  if (!refreshToken) {
    clearSupabaseSession();
    return '';
  }

  const response = await supabaseFetch('/auth/v1/token?grant_type=refresh_token', {
    method: 'POST',
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok) {
    clearSupabaseSession();
    return '';
  }

  const session = (await response.json()) as SupabaseSessionResponse;
  storeSupabaseSession(session);
  return getSupabaseAccessToken();
}

export async function bootstrapAuthFromUrl(): Promise<AuthBootstrapResult> {
  if (!isBrowser()) {
    return { user: null, resetToken: null, handled: false };
  }

  const searchParams = new URLSearchParams(window.location.search);
  const hashParams = readHashParams();
  let handled = false;
  let user: AuthUser | null = null;
  let resetToken: string | null = null;

  const rawError =
    searchParams.get('error_description') ||
    hashParams.get('error_description') ||
    searchParams.get('error') ||
    hashParams.get('error');
  if (rawError) {
    stripAuthParamsFromUrl();
    let decodedError = rawError;
    try {
      decodedError = decodeURIComponent(rawError);
    } catch {
      decodedError = rawError;
    }
    throw new Error(decodedError);
  }

  if (SUPABASE_AUTH_ENABLED) {
    const accessToken = searchParams.get('access_token') || hashParams.get('access_token');
    const refreshToken = searchParams.get('refresh_token') || hashParams.get('refresh_token');
    const type = String(searchParams.get('type') || hashParams.get('type') || '').toLowerCase();
    if (accessToken) {
      storeSupabaseSession({
        access_token: accessToken,
        refresh_token: refreshToken || undefined,
      });
      handled = true;
    }

    const tokenHash = searchParams.get('token_hash');
    if (tokenHash && ['signup', 'email', 'invite'].includes(type)) {
      user = await confirmEmailVerification(tokenHash);
      handled = true;
    } else if (tokenHash && type === 'recovery') {
      resetToken = tokenHash;
      handled = true;
    } else if (type === 'recovery' && accessToken) {
      // Supabase recovery links may return a recovery session without token_hash.
      resetToken = RECOVERY_SESSION_TOKEN;
      handled = true;
    }
  }

  const verifyToken = searchParams.get('verify_token');
  const resetTokenParam = searchParams.get('reset_token');
  if (verifyToken) {
    user = await confirmEmailVerification(verifyToken);
    handled = true;
  }
  if (resetTokenParam) {
    resetToken = resetTokenParam;
    handled = true;
  }

  if (handled) {
    stripAuthParamsFromUrl();
  }

  return { user, resetToken, handled };
}

export const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 90000,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use(
  async (config) => {
    const accessToken = SUPABASE_AUTH_ENABLED ? getSupabaseAccessToken() : '';

    config.headers = config.headers || {};

    if (accessToken) {
      (config.headers as Record<string, string>).Authorization = `Bearer ${accessToken}`;
    }

    console.log(`📤 API Request: ${config.method?.toUpperCase()} ${config.url}`, config.data);
    return config;
  },
  (error) => {
    console.error('🔴 Request error:', error);
    return Promise.reject(error);
  }
);

apiClient.interceptors.response.use(
  (response) => {
    const url = response.config.url || '';
    const payload = response.data || {};

    if (url.includes('/api/v1/cache/results')) {
      console.log('📥 Cache API Response:', {
        url,
        status: response.status,
        success: payload.success,
        count: payload.count,
        cache_backend: payload.cache_backend,
      });
      return response;
    }

    console.log('📥 API Response:', {
      url,
      status: response.status,
      success: payload.success,
      total_reviews: payload.total_reviews,
      from_cache: payload.from_cache,
      data_source: payload.data_source,
    });
    return response;
  },
  async (error) => {
    const status = error?.response?.status;
    const originalConfig = error?.config || {};

    if (
      SUPABASE_AUTH_ENABLED &&
      status === 401 &&
      !originalConfig.__retried_with_refresh &&
      getSupabaseRefreshToken()
    ) {
      const refreshedToken = await refreshSupabaseAccessToken();
      if (refreshedToken) {
        originalConfig.__retried_with_refresh = true;
        originalConfig.headers = originalConfig.headers || {};
        originalConfig.headers.Authorization = `Bearer ${refreshedToken}`;
        return apiClient.request(originalConfig);
      }
    }

    console.error('🔴 Response error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export async function analyzeReviews(params: {
  asin: string;
  max_reviews?: number;
  enable_ai?: boolean;
  country?: string;
}): Promise<AnalysisResult> {
  try {
    const requestData = {
      asin: params.asin,
      max_reviews: Math.min(params.max_reviews || 50, 100),
      enable_ai: params.enable_ai ?? true,
      country: params.country || 'IN',
    };

    const response = await apiClient.post<AnalysisResult>('/api/v1/analyze', requestData);
    const analysisData = response.data;

    if (!analysisData.success) {
      throw new Error(analysisData.error || 'Analysis failed');
    }

    if (typeof analysisData.total_reviews !== 'number') {
      analysisData.total_reviews = 0;
    }

    if (typeof analysisData.average_rating !== 'number') {
      analysisData.average_rating = 0;
    }

    analysisData.reviews = analysisData.reviews || [];
    analysisData.top_keywords = analysisData.top_keywords || [];
    analysisData.themes = analysisData.themes || [];
    analysisData.rating_distribution = analysisData.rating_distribution || {};
    analysisData.sentiment_distribution = analysisData.sentiment_distribution || null;

    return analysisData;
  } catch (error: any) {
    if (error.response) {
      const errorData = error.response.data;
      throw new Error(errorData?.detail || errorData?.error || `Server error: ${error.response.status}`);
    } else if (error.request) {
      throw new Error('No response from server. Check if backend is running.');
    }
    throw new Error(error.message || 'Analysis failed');
  }
}

export async function healthCheck(): Promise<any> {
  try {
    const response = await apiClient.get('/health');
    return response.data;
  } catch (error) {
    return { status: 'unhealthy', error };
  }
}

export async function signup(email: string, password: string): Promise<AuthUser> {
  ensureSupabaseAuthConfigured();

  const response = await supabaseFetch('/auth/v1/signup', {
    method: 'POST',
    body: JSON.stringify({
      email,
      password,
      options: {
        emailRedirectTo: browserOrigin(),
      },
    }),
  });

  if (!response.ok) {
    throw new Error(await parseSupabaseError(response));
  }

  const payload = (await response.json()) as { user?: Record<string, any>; session?: SupabaseSessionResponse };
  if (payload.session) {
    storeSupabaseSession(payload.session);
  }
  if (!payload.user) {
    throw new Error('Signup completed but user payload was empty');
  }
  return mapSupabaseUser(payload.user);
}

export async function login(email: string, password: string): Promise<AuthUser> {
  ensureSupabaseAuthConfigured();

  const response = await supabaseFetch('/auth/v1/token?grant_type=password', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    throw new Error(await parseSupabaseError(response));
  }

  const payload = (await response.json()) as SupabaseSessionResponse;
  storeSupabaseSession(payload);
  if (!payload.user) {
    throw new Error('Login failed: user payload missing');
  }
  return mapSupabaseUser(payload.user);
}

export async function logout(): Promise<void> {
  ensureSupabaseAuthConfigured();

  const accessToken = getSupabaseAccessToken();
  if (accessToken) {
    await supabaseFetch('/auth/v1/logout', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    }).catch(() => undefined);
  }
  clearSupabaseSession();
}

export async function logoutAll(): Promise<void> {
  ensureSupabaseAuthConfigured();
  await logout();
}

export async function getCurrentUser(): Promise<AuthUser | null> {
  ensureSupabaseAuthConfigured();

  let accessToken = getSupabaseAccessToken();
  if (!accessToken && getSupabaseRefreshToken()) {
    accessToken = await refreshSupabaseAccessToken();
  }
  if (!accessToken) {
    return null;
  }

  const response = await supabaseFetch('/auth/v1/user', {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (response.status === 401) {
    const refreshed = await refreshSupabaseAccessToken();
    if (!refreshed) {
      return null;
    }

    const retry = await supabaseFetch('/auth/v1/user', {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${refreshed}`,
      },
    });

    if (!retry.ok) {
      return null;
    }
    const user = (await retry.json()) as Record<string, any>;
    return mapSupabaseUser(user);
  }

  if (!response.ok) {
    return null;
  }

  const user = (await response.json()) as Record<string, any>;
  return mapSupabaseUser(user);
}

export async function requestEmailVerification(email?: string): Promise<void> {
  ensureSupabaseAuthConfigured();

  if (!email) {
    const current = await getCurrentUser();
    email = current?.email;
  }
  if (!email) {
    throw new Error('Email is required to request verification');
  }

  const response = await supabaseFetch('/auth/v1/resend', {
    method: 'POST',
    body: JSON.stringify({
      type: 'signup',
      email,
      options: {
        emailRedirectTo: browserOrigin(),
      },
    }),
  });

  if (!response.ok) {
    throw new Error(await parseSupabaseError(response));
  }
}

export async function confirmEmailVerification(token: string): Promise<AuthUser> {
  ensureSupabaseAuthConfigured();

  const response = await supabaseFetch('/auth/v1/verify', {
    method: 'POST',
    body: JSON.stringify({
      type: 'signup',
      token_hash: token,
    }),
  });

  if (!response.ok) {
    throw new Error(await parseSupabaseError(response));
  }

  const payload = (await response.json()) as { user?: Record<string, any>; session?: SupabaseSessionResponse };
  if (payload.session) {
    storeSupabaseSession(payload.session);
  }

  if (payload.user) {
    return mapSupabaseUser(payload.user);
  }

  const current = await getCurrentUser();
  if (!current) {
    throw new Error('Email verification succeeded but user is not available');
  }
  return current;
}

export async function requestPasswordReset(email: string): Promise<void> {
  ensureSupabaseAuthConfigured();

  const response = await supabaseFetch('/auth/v1/recover', {
    method: 'POST',
    body: JSON.stringify({
      email,
      options: {
        emailRedirectTo: browserOrigin(),
      },
    }),
  });

  if (!response.ok) {
    throw new Error(await parseSupabaseError(response));
  }
}

export async function confirmPasswordReset(token: string, newPassword: string): Promise<AuthUser> {
  ensureSupabaseAuthConfigured();

  const normalizedToken = String(token || '').trim();
  const usesRecoverySession = normalizedToken === RECOVERY_SESSION_TOKEN;

  if (!usesRecoverySession) {
    const verifyResponse = await supabaseFetch('/auth/v1/verify', {
      method: 'POST',
      body: JSON.stringify({
        type: 'recovery',
        token_hash: normalizedToken,
      }),
    });

    if (!verifyResponse.ok) {
      throw new Error(await parseSupabaseError(verifyResponse));
    }

    const verifyPayload = (await verifyResponse.json()) as { session?: SupabaseSessionResponse; user?: Record<string, any> };
    if (verifyPayload.session) {
      storeSupabaseSession(verifyPayload.session);
    }
  }

  const accessToken = getSupabaseAccessToken();
  if (!accessToken) {
    throw new Error('Recovery session missing. Please request password reset again.');
  }

  const updateResponse = await supabaseFetch('/auth/v1/user', {
    method: 'PUT',
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({ password: newPassword }),
  });

  if (!updateResponse.ok) {
    throw new Error(await parseSupabaseError(updateResponse));
  }

  const user = (await updateResponse.json()) as Record<string, any>;
  return mapSupabaseUser(user);
}

export async function getCachedResults(limit: number = 20): Promise<CachedAnalysisResult[]> {
  const response = await apiClient.get<CachedResultsResponse>('/api/v1/cache/results', {
    params: { limit, include_payload: true },
  });
  if (!response.data.success) {
    throw new Error('Unable to load cached results');
  }
  const rawResults = response.data.results || [];
  return rawResults.map((item) => ({
    ...item,
    product_title:
      item.product_title ||
      item.analysis?.product_info?.title ||
      `Product ${item.asin}`,
  }));
}

export function formatErrorMessage(error: any): string {
  if (typeof error === 'string') return error;
  if (error?.message) return error.message;
  if (error?.error) return error.error;
  return 'An unexpected error occurred';
}

export const MAX_REVIEWS_LIMIT = 100;
