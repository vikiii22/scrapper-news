/**
 * Tulotero Web API — cliente HTTP modular sin dependencias.
 *
 * Reconstruido a partir del comportamiento del frontend público de web.tulotero.es:
 * - Authorization: Bearer <JWT> (o Basic <base64> en el flujo legado).
 * - Refresco proactivo y single-flight usando `refreshTokenUrl`.
 * - Cabeceras de dispositivo, idioma, caché y geolocalización.
 * - Manejo centralizado de 401/403, 426 (verificación), FRAUD_DETECTED y reintentos.
 *
 * No es un SDK oficial. Úsalo únicamente con cuentas y datos que tengas derecho a usar.
 */

import type {
  AgendaContact,
  AllInfoResponse,
  AutoControlAnswer,
  AutoControlQuestion,
  AutoCreditRequest,
  ClubPlayRequest,
  CollectionRequest,
  CompanyClubRequest,
  ConfirmIdentityVerificationRequest,
  CreditCardRequest,
  DeviceContext,
  Draw,
  EditTicketRequest,
  EndpointConfig,
  ExternalCreditRequest,
  FacebookLoginInfo,
  FinishedDrawsResponse,
  FreeLotteryRequest,
  GameMedia,
  GeolocationContext,
  Group,
  GroupCreateRequest,
  GroupMemberInvite,
  GroupMessageRequest,
  GroupMoneyActivity,
  GroupMoneyRequest,
  GroupTransferRequest,
  GroupUpdateRequest,
  IdentityVerificationStatus,
  InstallationMetadata,
  InstallationRequest,
  JwtPayload,
  KycScannerParseRequest,
  KycScannerParseResponse,
  KycStatus,
  LocaleResponse,
  LoginRequest,
  LoginResponse,
  LotteryPlayRequest,
  LotterySearchRequest,
  LotterySearchResponse,
  LotteryStock,
  LotterySubscriptionInfo,
  MatchesResponse,
  MessageResponse,
  MoneyMovement,
  MoneyMovementsResponse,
  NativeCreditRequest,
  NewsResponse,
  PaginatedResponse,
  PaymentMethod,
  PaymentMethodLoadRequest,
  PaymentMethodWidgetRequest,
  Penya,
  PlayRequest,
  PlayResult,
  Preference,
  PreferencesResponse,
  PrizeStatus,
  RegisterRequest,
  RepeatTicketRequest,
  ResultAvailability,
  SaveAgendaRequest,
  SaveCardRequest,
  SavePreferencesRequest,
  SelfExclusionConfirmRequest,
  SendSponsorSmsRequest,
  ShareTicketRequest,
  ShipmentPrice,
  ShipmentRequest,
  SocialLoginRequest,
  SponsorInfo,
  StoredSession,
  SubscribeTicketRequest,
  SummaryResponse,
  SuggestionRequest,
  Ticket,
  TicketFiltersResponse,
  TicketProofRequest,
  TicketsPage,
  UpdateEmailRequest,
  UpdateProfileRequest,
  UserLimits,
  UserProfileResponse,
  VerifyPhoneRequest,
  WithdrawInfo,
  WithdrawRequest,
  WithdrawV2Request,
} from './types';

/* -------------------------------------------------------------------------- */
/* Errores                                                                    */
/* -------------------------------------------------------------------------- */

export class ApiError extends Error {
  readonly status: number;
  readonly statusText: string;
  readonly code: string;
  readonly body: unknown;
  readonly headers: Headers;
  readonly retryable: boolean;

  constructor(
    message: string,
    init: {
      status: number;
      statusText?: string;
      code?: string;
      body?: unknown;
      headers?: Headers;
      retryable?: boolean;
    },
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = init.status;
    this.statusText = init.statusText ?? '';
    this.code = init.code ?? `HTTP_${init.status}`;
    this.body = init.body;
    this.headers = init.headers ?? new Headers();
    this.retryable = init.retryable ?? false;
  }
}

export class VerificationRequiredError extends ApiError {
  readonly info?: string;

  constructor(error: ApiError, info?: string) {
    super(error.message, {
      status: error.status,
      statusText: error.statusText,
      code: 'VERIFICATION_REQUIRED',
      body: error.body,
      headers: error.headers,
    });
    this.name = 'VerificationRequiredError';
    this.info = info;
  }
}

export class SessionExpiredError extends ApiError {
  constructor(message = 'La sesión ha caducado') {
    super(message, { status: 401, code: 'SESSION_EXPIRED' });
    this.name = 'SessionExpiredError';
  }
}

export class FraudDetectedError extends ApiError {
  constructor(message: string, body?: unknown) {
    super(message, { status: 403, code: 'FRAUD_DETECTED', body });
    this.name = 'FraudDetectedError';
  }
}

export class NetworkError extends Error {
  readonly cause?: unknown;

  constructor(message: string, cause?: unknown) {
    super(message);
    this.name = 'NetworkError';
    this.cause = cause;
  }
}

export class TimeoutError extends Error {
  constructor(message = 'La petición ha superado el tiempo máximo') {
    super(message);
    this.name = 'TimeoutError';
  }
}

/* -------------------------------------------------------------------------- */
/* Almacenamiento de sesión                                                   */
/* -------------------------------------------------------------------------- */

export interface TokenStorage {
  get(): StoredSession | null;
  set(session: StoredSession): void;
  clear(): void;
}

export class MemoryTokenStorage implements TokenStorage {
  private session: StoredSession | null = null;

  get(): StoredSession | null {
    return this.session;
  }

  set(session: StoredSession): void {
    this.session = session;
  }

  clear(): void {
    this.session = null;
  }
}

interface WebStorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

/**
 * Compatible con localStorage y sessionStorage. Usa las mismas claves que el
 * frontend original: 0x01 (token), 0x44 (estrategia), 0x45 (refresh token),
 * 0x46 (refresh URL) y 0x47 (expiración del refresh).
 */
export class WebTokenStorage implements TokenStorage {
  private readonly local: WebStorageLike;
  private readonly session: WebStorageLike | undefined;
  private readonly keys = {
    token: '0x01',
    strategy: '0x44',
    refreshToken: '0x45',
    refreshTokenUrl: '0x46',
    refreshTokenExp: '0x47',
  };

  constructor(local: WebStorageLike, session?: WebStorageLike) {
    this.local = local;
    this.session = session;
  }

  get(): StoredSession | null {
    const storage = this.pickStorage();
    const strategy = storage.getItem(this.keys.strategy) as 'JWT' | 'BASIC' | null;
    const token = storage.getItem(this.keys.token);
    if (!strategy || !token) {
      return null;
    }
    if (strategy === 'BASIC') {
      return { strategy, basicToken: token };
    }
    const refreshToken = storage.getItem(this.keys.refreshToken) ?? undefined;
    const refreshTokenUrl = storage.getItem(this.keys.refreshTokenUrl) ?? undefined;
    const exp = Number(storage.getItem(this.keys.refreshTokenExp));
    return {
      strategy,
      accessToken: token,
      refreshToken,
      refreshTokenUrl,
      refreshTokenExpirationDate: Number.isFinite(exp) ? exp : undefined,
    };
  }

  set(session: StoredSession): void {
    const storage = this.pickStorage(session);
    storage.setItem(this.keys.strategy, session.strategy);
    storage.setItem(this.keys.token, session.accessToken ?? session.basicToken ?? '');
    if (session.refreshToken) {
      storage.setItem(this.keys.refreshToken, session.refreshToken);
    }
    if (session.refreshTokenUrl) {
      storage.setItem(this.keys.refreshTokenUrl, session.refreshTokenUrl);
    }
    if (session.refreshTokenExpirationDate) {
      storage.setItem(this.keys.refreshTokenExp, String(session.refreshTokenExpirationDate));
    }
  }

  clear(): void {
    for (const storage of [this.local, this.session]) {
      if (!storage) continue;
      Object.values(this.keys).forEach((key) => storage.removeItem(key));
    }
  }

  private pickStorage(session?: StoredSession): WebStorageLike {
    if (session?.strategy === 'JWT' && session.refreshToken) {
      return this.local;
    }
    return this.session ?? this.local;
  }
}

/* -------------------------------------------------------------------------- */
/* Opciones                                                                   */
/* -------------------------------------------------------------------------- */

export interface RetryOptions {
  /** Número máximo de reintentos. Default: 2. */
  attempts?: number;
  /** Retardo base en ms. Default: 300. */
  baseDelayMs?: number;
  /** Retardo máximo en ms. Default: 4000. */
  maxDelayMs?: number;
  /** Métodos reintentables. Default: GET, HEAD. */
  methods?: string[];
  /** Códigos HTTP reintentables. Default: 408, 425, 429, 500, 502, 503, 504. */
  statuses?: number[];
}

export interface TuloteroClientOptions {
  /** Default: https://web-backend.es.tulotero.net/tuloteroweb/rest */
  baseUrl?: string;
  fetch?: typeof fetch;
  storage?: TokenStorage;
  /** Idioma enviado en Accept-Language. Default: es-ES. */
  locale?: string;
  appVersion?: string | number;
  device?: DeviceContext | (() => DeviceContext | Promise<DeviceContext>);
  geolocation?: () => GeolocationContext | null | Promise<GeolocationContext | null>;
  defaultHeaders?: Record<string, string>;
  timeoutMs?: number;
  retry?: RetryOptions;
  /** Margen para refrescar antes de que caduque el access token. Default: 120 s. */
  refreshLeewayMs?: number;
  /** Rutas que reciben cabeceras x-geolocation. */
  geolocationPathPattern?: RegExp;
  onAuthStateChange?: (session: StoredSession | null) => void;
  onFraudDetected?: (error: FraudDetectedError) => void;
  onVerificationRequired?: (error: VerificationRequiredError) => void;
  onRequest?: (info: RequestLog) => void;
  onResponse?: (info: ResponseLog) => void;
}

export interface RequestLog {
  method: string;
  url: string;
  headers: Record<string, string>;
  attempt: number;
}

export interface ResponseLog extends RequestLog {
  status: number;
  durationMs: number;
  body?: unknown;
}

const DEFAULT_BASE_URL = 'https://web-backend.es.tulotero.net/tuloteroweb/rest';
const AUTH_PATHS = /\/rest\/(users\/|installation|userLogin|facebook\/login|google\/login|apple\/login)/;
const DEFAULT_GEOLOCATION_PATHS =
  /\/users\/(play|prereserves\/play|credit|penyas\/v1\/participacion|boleto\/.+\/subscribe|boleto\/repeat)/;

/* -------------------------------------------------------------------------- */
/* Utilidades                                                                 */
/* -------------------------------------------------------------------------- */

export function decodeJwt(token: string): JwtPayload | null {
  try {
    const payload = token.split('.')[1];
    if (!payload) return null;
    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/');
    // `atob` está disponible tanto en navegadores como en Node >= 16.
    if (typeof atob !== 'function') return null;
    const decoded = atob(normalized.padEnd(normalized.length + ((4 - (normalized.length % 4)) % 4), '='));
    const json = decodeURIComponent(
      decoded
        .split('')
        .map((char) => `%${char.charCodeAt(0).toString(16).padStart(2, '0')}`)
        .join(''),
    );
    return JSON.parse(json) as JwtPayload;
  } catch {
    return null;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function buildQuery(query?: Record<string, unknown>): string {
  if (!query) return '';
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null) continue;
    if (Array.isArray(value)) {
      value.forEach((item) => params.append(key, String(item)));
    } else {
      params.append(key, String(value));
    }
  }
  const result = params.toString();
  return result ? `?${result}` : '';
}

/* -------------------------------------------------------------------------- */
/* Autenticación                                                              */
/* -------------------------------------------------------------------------- */

export class TuloteroAuth {
  private session: StoredSession | null;
  private refreshPromise: Promise<StoredSession> | null = null;

  constructor(
    private readonly client: TuloteroClient,
    private readonly storage: TokenStorage,
    private readonly leewayMs: number,
    private readonly onStateChange?: (session: StoredSession | null) => void,
  ) {
    this.session = storage.get();
  }

  getSession(): StoredSession | null {
    return this.session;
  }

  isLoggedIn(): boolean {
    return Boolean(this.session?.accessToken || this.session?.basicToken);
  }

  setSession(session: StoredSession | null): void {
    this.session = session;
    if (session) {
      this.storage.set(session);
    } else {
      this.storage.clear();
    }
    this.onStateChange?.(session);
  }

  clear(): void {
    this.setSession(null);
  }

  /** Devuelve un access token válido, refrescándolo de forma proactiva si hace falta. */
  async getAccessToken(): Promise<string | null> {
    if (!this.session) return null;
    if (this.session.strategy === 'BASIC') {
      return this.session.basicToken ?? null;
    }
    if (!this.session.accessToken) return null;

    const payload = decodeJwt(this.session.accessToken);
    if (!payload?.exp) return this.session.accessToken;

    const remainingMs = payload.exp * 1000 - Date.now();
    if (remainingMs > this.leewayMs) {
      return this.session.accessToken;
    }
    if (!this.session.refreshToken || !this.session.refreshTokenUrl) {
      return this.session.accessToken;
    }
    const refreshed = await this.refresh();
    return refreshed.accessToken ?? null;
  }

  async login(request: LoginRequest): Promise<LoginResponse> {
    const response = await this.client.request<LoginResponse>('/userLogin', {
      method: 'POST',
      form: {
        username: request.username,
        password: request.password,
        instalacionId: request.installationId,
      },
      skipAuth: true,
      skipRefresh: true,
      retry: false,
    });
    this.applyLoginResponse(response);
    return response;
  }

  async loginFacebook(
    request: Omit<SocialLoginRequest, 'deviceType'>,
  ): Promise<LoginResponse> {
    return this.socialLogin('/facebook/login', {
      ...request,
      grantedPermissions: request.grantedPermissions ?? 'email,public_profile',
    });
  }

  async loginGoogle(
    request: Omit<SocialLoginRequest, 'deviceType'>,
  ): Promise<LoginResponse> {
    return this.socialLogin('/google/login', request);
  }

  async loginApple(
    request: Omit<SocialLoginRequest, 'deviceType'>,
  ): Promise<LoginResponse> {
    const form = {
      token: request.token,
      grantedPermissions: request.grantedPermissions ?? 'full_name, email',
      deviceType: 'WEB',
      registerDeviceId: request.registerDeviceId,
      // Typo intencional del backend original.
      instalationId: request.instalacionId,
      ...(request.userName ? { userName: request.userName } : {}),
    };
    const response = await this.client.request<LoginResponse>('/apple/login', {
      method: 'POST',
      form,
      skipAuth: true,
      skipRefresh: true,
      retry: false,
    });
    this.applyLoginResponse(response);
    return response;
  }

  /** Refresco single-flight. Todas las peticiones concurrentes comparten la misma promesa. */
  async refresh(): Promise<StoredSession> {
    if (this.refreshPromise) {
      return this.refreshPromise;
    }
    this.refreshPromise = this.doRefresh().finally(() => {
      this.refreshPromise = null;
    });
    return this.refreshPromise;
  }

  private async doRefresh(): Promise<StoredSession> {
    const current = this.session;
    if (!current || current.strategy !== 'JWT' || !current.refreshToken || !current.refreshTokenUrl) {
      this.clear();
      throw new SessionExpiredError('No hay refresh token disponible');
    }
    if (
      current.refreshTokenExpirationDate &&
      current.refreshTokenExpirationDate <= Date.now()
    ) {
      this.clear();
      throw new SessionExpiredError('El refresh token ha caducado');
    }

    const response = await this.client.request<{
      token?: string;
      accessToken?: string | { token?: string };
      refreshToken?: string;
      refreshTokenExpirationDate?: number;
    }>(current.refreshTokenUrl, {
      method: 'POST',
      form: {
        refreshToken: current.refreshToken,
        clientTimestamp: Date.now(),
      },
      skipAuth: true,
      skipRefresh: true,
      retry: false,
    });

    const accessToken =
      typeof response.token === 'string'
        ? response.token
        : typeof response.accessToken === 'string'
          ? response.accessToken
          : response.accessToken?.token;

    if (!accessToken || !response.refreshToken) {
      this.clear();
      throw new SessionExpiredError('Respuesta de refresco inválida');
    }

    const next: StoredSession = {
      strategy: 'JWT',
      accessToken,
      refreshToken: response.refreshToken,
      refreshTokenUrl: current.refreshTokenUrl,
      refreshTokenExpirationDate:
        response.refreshTokenExpirationDate ?? current.refreshTokenExpirationDate,
    };
    this.setSession(next);
    return next;
  }

  private async socialLogin(
    path: string,
    request: Omit<SocialLoginRequest, 'deviceType'>,
  ): Promise<LoginResponse> {
    const response = await this.client.request<LoginResponse>(path, {
      method: 'POST',
      form: {
        ...request,
        deviceType: 'WEB',
      },
      skipAuth: true,
      skipRefresh: true,
      retry: false,
    });
    this.applyLoginResponse(response);
    return response;
  }

  private applyLoginResponse(response: LoginResponse): void {
    if (!response?.token || !response?.refreshToken) {
      throw new SessionExpiredError('Respuesta de login inválida');
    }
    this.setSession({
      strategy: 'JWT',
      accessToken: response.token,
      refreshToken: response.refreshToken,
      refreshTokenUrl: response.refreshTokenUrl,
      refreshTokenExpirationDate: response.refreshTokenExpirationDate,
    });
  }
}

/* -------------------------------------------------------------------------- */
/* Cliente base                                                               */
/* -------------------------------------------------------------------------- */

export class TuloteroClient {
  readonly baseUrl: string;
  readonly auth: TuloteroAuth;
  readonly session: SessionModule;

  private readonly fetchImpl: typeof fetch;
  private readonly locale: string;
  private readonly appVersion: string;
  private readonly device?: TuloteroClientOptions['device'];
  private readonly geolocation?: TuloteroClientOptions['geolocation'];
  private readonly defaultHeaders: Record<string, string>;
  private readonly timeoutMs: number;
  private readonly retry: Required<RetryOptions>;
  private readonly geolocationPathPattern: RegExp;
  private readonly onFraudDetected?: (error: FraudDetectedError) => void;
  private readonly onVerificationRequired?: (error: VerificationRequiredError) => void;
  private readonly onRequest?: (info: RequestLog) => void;
  private readonly onResponse?: (info: ResponseLog) => void;

  readonly users: UsersModule;
  readonly draws: DrawsModule;
  readonly play: PlayModule;
  readonly tickets: TicketsModule;
  readonly wallet: WalletModule;
  readonly groups: GroupsModule;
  readonly clubs: ClubsModule;
  readonly kyc: KycModule;
  readonly news: NewsModule;
  readonly platform: PlatformModule;
  readonly support: SupportModule;

  constructor(options: TuloteroClientOptions = {}) {
    this.baseUrl = (options.baseUrl ?? DEFAULT_BASE_URL).replace(/\/+$/, '');
    this.fetchImpl = options.fetch ?? fetch.bind(globalThis);
    this.locale = options.locale ?? 'es-ES';
    this.appVersion = String(options.appVersion ?? '1389');
    this.device = options.device;
    this.geolocation = options.geolocation;
    this.defaultHeaders = {
      Accept: 'application/json',
      AvoidRedirect: 'true',
      Client: 'web',
      ...options.defaultHeaders,
    };
    this.timeoutMs = options.timeoutMs ?? 20_000;
    this.retry = {
      attempts: options.retry?.attempts ?? 2,
      baseDelayMs: options.retry?.baseDelayMs ?? 300,
      maxDelayMs: options.retry?.maxDelayMs ?? 4_000,
      methods: options.retry?.methods ?? ['GET', 'HEAD'],
      statuses: options.retry?.statuses ?? [408, 425, 429, 500, 502, 503, 504],
    };
    this.geolocationPathPattern =
      options.geolocationPathPattern ?? DEFAULT_GEOLOCATION_PATHS;
    this.onFraudDetected = options.onFraudDetected;
    this.onVerificationRequired = options.onVerificationRequired;
    this.onRequest = options.onRequest;
    this.onResponse = options.onResponse;

    const storage = options.storage ?? new MemoryTokenStorage();
    this.auth = new TuloteroAuth(
      this,
      storage,
      options.refreshLeewayMs ?? 120_000,
      options.onAuthStateChange,
    );

    this.users = new UsersModule(this);
    this.session = new SessionModule(this);
    this.draws = new DrawsModule(this);
    this.play = new PlayModule(this);
    this.tickets = new TicketsModule(this);
    this.wallet = new WalletModule(this);
    this.groups = new GroupsModule(this);
    this.clubs = new ClubsModule(this);
    this.kyc = new KycModule(this);
    this.news = new NewsModule(this);
    this.platform = new PlatformModule(this);
    this.support = new SupportModule(this);
  }

  /**
   * Punto único de salida HTTP. Normaliza URL, cabeceras, auth, errores, timeout y reintentos.
   */
  async request<T>(
    path: string,
    options: {
      method?: string;
      query?: Record<string, unknown>;
      headers?: Record<string, string>;
      body?: unknown;
      form?: Record<string, string | number | boolean | undefined>;
      multipart?: FormData;
      signal?: AbortSignal;
      timeoutMs?: number;
      retry?: boolean | number;
      skipAuth?: boolean;
      skipRefresh?: boolean;
      responseType?: 'json' | 'text' | 'blob' | 'arrayBuffer';
    } = {},
  ): Promise<T> {
    const method = (options.method ?? 'GET').toUpperCase();
    const url = path.startsWith('http')
      ? `${path}${buildQuery(options.query)}`
      : `${this.baseUrl}${path}${buildQuery(options.query)}`;

    const maxAttempts =
      typeof options.retry === 'number'
        ? options.retry + 1
        : options.retry === false
          ? 1
          : this.retry.methods.includes(method)
            ? this.retry.attempts + 1
            : 1;

    let didRefresh = false;
    let attempt = 0;

    while (true) {
      attempt += 1;
      try {
        return await this.execute<T>(
          url,
          method,
          options,
          attempt,
          didRefresh,
          () => {
            didRefresh = true;
          },
        );
      } catch (error) {
        if (this.shouldRetry(error, method, attempt, maxAttempts)) {
          const delay = this.retryDelay(error, attempt);
          await sleep(delay);
          continue;
        }
        throw error;
      }
    }
  }

  private async execute<T>(
    url: string,
    method: string,
    options: {
      headers?: Record<string, string>;
      body?: unknown;
      form?: Record<string, string | number | boolean | undefined>;
      multipart?: FormData;
      signal?: AbortSignal;
      timeoutMs?: number;
      skipAuth?: boolean;
      skipRefresh?: boolean;
      responseType?: 'json' | 'text' | 'blob' | 'arrayBuffer';
    },
    attempt: number,
    didRefresh: boolean,
    markRefreshed: () => void,
  ): Promise<T> {
    const headers = new Headers(this.defaultHeaders);
    headers.set('Accept-Language', this.locale);
    headers.set('ngTime', String(Date.now()));
    for (const [key, value] of Object.entries(options.headers ?? {})) {
      headers.set(key, value);
    }

    if (AUTH_PATHS.test(url)) {
      await this.applyDeviceHeaders(headers);
    }

    if (this.geolocation && this.geolocationPathPattern.test(url)) {
      const location = await this.geolocation();
      if (location) {
        headers.set(
          'x-geolocation',
          `${location.coords.latitude}:${location.coords.longitude}:${location.coords.accuracy}`,
        );
        headers.set('x-geolocation-timestamp', String(location.timestamp));
      }
    }

    let body: BodyInit | undefined;
    if (options.multipart) {
      body = options.multipart;
    } else if (options.form) {
      const params = new URLSearchParams();
      for (const [key, value] of Object.entries(options.form)) {
        if (value !== undefined) params.append(key, String(value));
      }
      body = params;
      if (!headers.has('Content-Type')) {
        headers.set('Content-Type', 'application/x-www-form-urlencoded');
      }
    } else if (options.body !== undefined) {
      body = JSON.stringify(options.body);
      if (!headers.has('Content-Type')) {
        headers.set('Content-Type', 'application/json');
      }
    }

    if (!options.skipAuth && this.auth.isLoggedIn()) {
      const accessToken = await this.auth.getAccessToken();
      const session = this.auth.getSession();
      if (accessToken && session) {
        headers.set(
          'Authorization',
          session.strategy === 'BASIC' ? `Basic ${accessToken}` : `Bearer ${accessToken}`,
        );
      }
    }

    const controller = new AbortController();
    const timeoutMs = options.timeoutMs ?? this.timeoutMs;
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    const onAbort = () => controller.abort();
    options.signal?.addEventListener('abort', onAbort, { once: true });

    const log: RequestLog = {
      method,
      url,
      headers: this.sanitizeHeaders(headers),
      attempt,
    };
    this.onRequest?.(log);
    const started = Date.now();

    let response: Response;
    try {
      response = await this.fetchImpl(url, {
        method,
        headers,
        body,
        signal: controller.signal,
      });
    } catch (error) {
      if (options.signal?.aborted) {
        throw error;
      }
      if (controller.signal.aborted) {
        throw new TimeoutError(`Timeout de ${timeoutMs} ms en ${method} ${url}`);
      }
      throw new NetworkError(`No se pudo conectar con ${url}`, error);
    } finally {
      clearTimeout(timer);
      options.signal?.removeEventListener('abort', onAbort);
    }

    const durationMs = Date.now() - started;
    const parsed = await this.parseBody(response, options.responseType);
    this.onResponse?.({ ...log, status: response.status, durationMs, body: parsed });

    if (response.ok) {
      if (isRecord(parsed) && parsed.status === 'FRAUD_DETECTED') {
        const fraud = new FraudDetectedError(
          String(parsed.message ?? 'Operación bloqueada por el sistema antifraude'),
          parsed,
        );
        this.auth.clear();
        this.onFraudDetected?.(fraud);
        throw fraud;
      }
      return parsed as T;
    }

    const error = this.toApiError(response, parsed);
    if (isRecord(parsed) && parsed.status === 'FRAUD_DETECTED') {
      const fraud = new FraudDetectedError(
        String(parsed.message ?? 'Operación bloqueada por el sistema antifraude'),
        parsed,
      );
      this.auth.clear();
      this.onFraudDetected?.(fraud);
      throw fraud;
    }

    if (response.status === 426) {
      const verification = new VerificationRequiredError(
        error,
        isRecord(parsed) ? String(parsed.info ?? '') : undefined,
      );
      this.onVerificationRequired?.(verification);
      throw verification;
    }

    const isAuthFailure =
      (response.status === 401 || response.status === 403) &&
      !options.skipAuth &&
      this.auth.isLoggedIn();

    if (isAuthFailure && !options.skipRefresh && !didRefresh) {
      try {
        markRefreshed();
        await this.auth.refresh();
      } catch {
        this.auth.clear();
        throw new SessionExpiredError();
      }
      return this.execute<T>(url, method, options, attempt, true, markRefreshed);
    }

    if (isAuthFailure) {
      this.auth.clear();
      throw new SessionExpiredError(error.message);
    }

    throw error;
  }

  private async applyDeviceHeaders(headers: Headers): Promise<void> {
    if (!this.device) return;
    const device = typeof this.device === 'function' ? await this.device() : this.device;
    if (device.androidRegistrationId) {
      headers.set('androidRegistrationId', device.androidRegistrationId);
    }
    if (device.deviceId) {
      headers.set('deviceId', device.deviceId);
    }
    headers.set('deviceType', device.deviceType ?? 'WEB');
    headers.set(
      'deviceDesc',
      device.deviceDesc ?? 'Chrome(120.0.0.0)',
    );
    headers.set('osVersion', device.osVersion ?? 'Windows(10)');
    headers.set('versionCode', String(device.versionCode ?? this.appVersion));
    headers.set('mode', device.mode ?? 'desktop');
  }

  private async parseBody(
    response: Response,
    responseType?: 'json' | 'text' | 'blob' | 'arrayBuffer',
  ): Promise<unknown> {
    if (response.status === 204) return undefined;
    if (responseType === 'blob') return response.blob();
    if (responseType === 'arrayBuffer') return response.arrayBuffer();
    if (responseType === 'text') return response.text();
    const contentType = response.headers.get('content-type') ?? '';
    if (contentType.includes('json')) {
      const text = await response.text();
      if (!text) return undefined;
      try {
        return JSON.parse(text);
      } catch {
        return text;
      }
    }
    const text = await response.text();
    return text || undefined;
  }

  private toApiError(response: Response, body: unknown): ApiError {
    const record = isRecord(body) ? body : undefined;
    const message =
      (record?.message as string | undefined) ??
      (record?.info as string | undefined) ??
      response.statusText ??
      'Error HTTP';
    return new ApiError(message, {
      status: response.status,
      statusText: response.statusText,
      code:
        (record?.status as string | undefined) ??
        (record?.code as string | undefined) ??
        `HTTP_${response.status}`,
      body,
      headers: response.headers,
      retryable: this.retry.statuses.includes(response.status),
    });
  }

  private shouldRetry(
    error: unknown,
    method: string,
    attempt: number,
    maxAttempts: number,
  ): boolean {
    if (attempt >= maxAttempts) return false;
    if (!this.retry.methods.includes(method)) return false;
    if (error instanceof ApiError) {
      return error.retryable || this.retry.statuses.includes(error.status);
    }
    if (error instanceof NetworkError || error instanceof TimeoutError) {
      return true;
    }
    return false;
  }

  private retryDelay(error: unknown, attempt: number): number {
    if (error instanceof ApiError) {
      const retryAfter = error.headers.get('retry-after');
      if (retryAfter) {
        const seconds = Number(retryAfter);
        if (Number.isFinite(seconds)) {
          return Math.min(seconds * 1000, this.retry.maxDelayMs);
        }
      }
    }
    const exponential = this.retry.baseDelayMs * 2 ** (attempt - 1);
    return Math.min(exponential + Math.random() * 100, this.retry.maxDelayMs);
  }

  private sanitizeHeaders(headers: Headers): Record<string, string> {
    const result: Record<string, string> = {};
    headers.forEach((value, key) => {
      result[key] =
        key.toLowerCase() === 'authorization' ? 'Bearer [redacted]' : value;
    });
    return result;
  }
}

/* -------------------------------------------------------------------------- */
/* Módulos                                                                    */
/* -------------------------------------------------------------------------- */

type Client = TuloteroClient;

export class SessionModule {
  constructor(private readonly client: Client) {}

  /**
   * Alta de cuenta. El frontend hace login automático justo después del alta,
   * por lo que este método devuelve ya la sesión iniciada.
   */
  async register(
    request: RegisterRequest,
    disableGlobalMessages = false,
  ): Promise<LoginResponse> {
    await this.client.request<MessageResponse>('/registration', {
      method: 'POST',
      query: { disableGlobalMessages },
      body: request,
      skipAuth: true,
      skipRefresh: true,
      retry: false,
    });
    return this.client.auth.login({
      username: request.mail,
      password: request.password,
      installationId: request.instalationId,
    });
  }

  startPasswordReset(mail: string): Promise<MessageResponse> {
    return this.client.request('/beginForgotPassword/', {
      query: { mail },
      skipAuth: true,
      retry: false,
    });
  }

  createInstallation(request: InstallationRequest): Promise<{ id: number }> {
    return this.client.request('/installation', {
      method: 'POST',
      body: request,
      skipAuth: true,
      skipRefresh: true,
      retry: false,
    });
  }

  unregister(registrationId: string): Promise<string> {
    return this.client.request('/users/unregister', {
      method: 'POST',
      form: { registrationId },
      responseType: 'text',
      retry: false,
    });
  }

  updateDeviceLocale(registrationId: string, locale: string): Promise<MessageResponse> {
    return this.client.request(`/device/${encodeURIComponent(registrationId)}/locale`, {
      method: 'PUT',
      body: { locale },
    });
  }
}

export class UsersModule {
  constructor(private readonly client: Client) {}

  getProfile(): Promise<UserProfileResponse> {
    return this.client.request('/users/me');
  }

  updateProfile(request: UpdateProfileRequest): Promise<UserProfileResponse> {
    return this.client.request('/users/me', { method: 'PUT', body: request });
  }

  deleteProfile(): Promise<void> {
    return this.client.request('/users/me', { method: 'DELETE' });
  }

  verifyEmail(): Promise<MessageResponse> {
    return this.client.request('/users/verificarMail');
  }

  updateEmail(email: string): Promise<MessageResponse> {
    return this.client.request('/users/mail', {
      method: 'PUT',
      body: { mail: email } satisfies UpdateEmailRequest,
    });
  }

  getLocale(): Promise<LocaleResponse> {
    return this.client.request('/users/locale');
  }

  updateLocale(locale: string): Promise<MessageResponse> {
    return this.client.request('/users/locale', {
      method: 'PUT',
      body: { locale },
    });
  }

  startPhoneVerification(number: string): Promise<MessageResponse> {
    return this.client.request('/users/inicioVerificarNumero', {
      method: 'POST',
      form: { numero: number },
    });
  }

  verifyPhone(
    token: string,
    number: string,
    disableGlobalMessages = false,
  ): Promise<MessageResponse> {
    return this.client.request('/users/verifyPhoneNumber', {
      method: 'POST',
      query: { disableGlobalMessages },
      form: { numero: number, token } satisfies VerifyPhoneRequest,
    });
  }

  isRegistered(email: string): Promise<boolean> {
    return this.client
      .request<ResultAvailability>(`/shouldShowPrivacyModalOnRegister/${encodeURIComponent(email)}`, {
        skipAuth: true,
      })
      .then((response) => response.result === false);
  }

  addExtraField(name: string, value: string): Promise<MessageResponse> {
    return this.client.request('/users/extras/add', {
      method: 'PUT',
      body: { name, value },
    });
  }

  replaceExtraFields(extras: Record<string, string>): Promise<MessageResponse> {
    return this.client.request('/users/extras/replace', {
      method: 'PUT',
      body: { extras },
    });
  }

  getPreferences(): Promise<PreferencesResponse> {
    return this.client.request('/users/preferences');
  }

  savePreferences(preferences: Preference[]): Promise<PreferencesResponse> {
    return this.client.request('/users/preferences', {
      method: 'PUT',
      body: { preferences } satisfies SavePreferencesRequest,
    });
  }

  getLimits(): Promise<UserLimits> {
    return this.client.request('/users/limits');
  }

  saveLimits(limits: UserLimits): Promise<MessageResponse> {
    return this.client.request('/users/limits', { method: 'PUT', body: limits });
  }

  requestSelfExclusionToken(selfExclusionTypeCode: string): Promise<MessageResponse> {
    return this.client.request('/users/selfexclusion/generatetoken', {
      method: 'POST',
      query: { selfexclusiontypecode: selfExclusionTypeCode },
      body: {},
    });
  }

  confirmSelfExclusion(request: SelfExclusionConfirmRequest): Promise<MessageResponse> {
    return this.client.request('/users/selfexclusion/confirm', {
      method: 'PUT',
      body: request,
    });
  }

  getAutoControlQuestions(): Promise<{ object: AutoControlQuestion[] }> {
    return this.client.request('/users/autocontroltest/questions');
  }

  saveAutoControlAnswers(answers: AutoControlAnswer[]): Promise<MessageResponse> {
    return this.client.request('/users/autocontroltest/testResult', {
      method: 'POST',
      body: answers,
    });
  }

  getAutoControlNextAttempt(): Promise<{ object: number }> {
    return this.client.request('/users/autocontroltest/nextAttemptTimestamp');
  }

  getAgenda(): Promise<{ agenda: AgendaContact[]; relations: AgendaContact[] }> {
    return this.client.request('/users/agenda');
  }

  saveAgenda(contacts: AgendaContact[], deviceId: string): Promise<unknown> {
    return this.client.request('/users/agenda', {
      method: 'POST',
      body: { contactos: contacts, deviceId } satisfies SaveAgendaRequest,
    });
  }

  getSponsor(): Promise<SponsorInfo> {
    return this.client.request('/users/sponsor');
  }

  sendSponsorSms(request: SendSponsorSmsRequest): Promise<MessageResponse> {
    return this.client.request('/users/sponsor/sms', {
      method: 'POST',
      body: request,
    });
  }

  getIdentityVerificationStatus(): Promise<IdentityVerificationStatus> {
    return this.client.request('/users/identity-verification');
  }

  requestIdentityVerificationCode(): Promise<MessageResponse> {
    return this.client.request('/users/identity-verification/resend-sms');
  }

  confirmIdentityVerification(
    request: ConfirmIdentityVerificationRequest,
  ): Promise<MessageResponse> {
    return this.client.request('/users/identity-verification', {
      method: 'POST',
      body: request,
    });
  }

  getLastShipmentAddress(): Promise<ShipmentRequest> {
    return this.client.request('/users/lastEnvioAddress');
  }

  saveLastShipmentAddress(address: ShipmentRequest): Promise<ShipmentRequest> {
    return this.client.request('/users/lastEnvioAddress', {
      method: 'POST',
      body: address,
    });
  }

  uploadPhoto(file: Blob, filename = 'photo.jpg'): Promise<MessageResponse> {
    const form = new FormData();
    form.append('img', file, filename);
    return this.client.request('/users/photo', {
      method: 'POST',
      multipart: form,
    });
  }

  deletePhoto(): Promise<void> {
    return this.client.request('/users/photo', { method: 'DELETE' });
  }
}

export class DrawsModule {
  constructor(private readonly client: Client) {}

  getDraw(raffleId: number | string): Promise<Draw> {
    return this.client.request(`/sorteos/${raffleId}`);
  }

  getMatches(raffleId: number | string, imgSize = 20): Promise<MatchesResponse> {
    return this.client.request(`/sorteos/${raffleId}/partidos`, {
      query: { imgSize },
    });
  }

  getFinishedDraws(
    firstResult = 0,
    gameTypes: string[] = [],
    stateCode?: string,
  ): Promise<FinishedDrawsResponse> {
    const suffix = gameTypes.length
      ? `/${gameTypes.map((game) => game.toLowerCase()).join('+')}`
      : '';
    return this.client.request(`/sorteos/finished${suffix}`, {
      query: { firstResult, filters: stateCode ? `state:${stateCode}` : undefined },
    });
  }

  /** Alias antiguo observado en algunos chunks del frontend. */
  getMatchesLegacy(raffleId: number | string, imgSize = 20): Promise<MatchesResponse> {
    return this.client.request(`/matches/sorteos/${raffleId}`, {
      query: { imgSize },
    });
  }

  getGameMedia(gameId: string | number, query: Record<string, unknown> = {}): Promise<{ object: GameMedia }> {
    return this.client.request(`/game/${gameId}/media`, { query });
  }
}

export class PlayModule {
  constructor(private readonly client: Client) {}

  play(request: PlayRequest): Promise<PlayResult> {
    return this.client.request('/users/play', {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  playLottery(request: LotteryPlayRequest): Promise<PlayResult> {
    return this.client.request('/users/play/loteria', {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  playDescriptor(request: PlayRequest): Promise<PlayResult> {
    return this.client.request('/users/play/descriptor', {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  validate(request: PlayRequest): Promise<{ status: string }> {
    return this.client.request('/users/play/descriptor/validate', {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  playScanned(code: string): Promise<PlayResult> {
    return this.client.request('/users/play/scannercode', {
      method: 'POST',
      body: { code },
      retry: false,
    });
  }

  saveUnfinished(request: PlayRequest): Promise<void> {
    return this.client.request('/users/unfinish/play', {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  saveUnfinishedDescriptor(request: PlayRequest): Promise<void> {
    return this.client.request('/users/unfinish/play/descriptor', {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  saveUnfinishedLottery(request: LotteryPlayRequest): Promise<void> {
    return this.client.request('/users/unfinish/jugar/loteria', {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  playPromo(request: PlayRequest): Promise<PlayResult> {
    return this.client.request('/users/prereserves/play', {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  playPromoDescriptor(request: PlayRequest): Promise<PlayResult> {
    return this.client.request('/users/prereserves/play/descriptor', {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  searchLottery(request: LotterySearchRequest): Promise<LotterySearchResponse> {
    return this.client.request('/users/lottery/search', {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  searchPublicLottery(request: LotterySearchRequest): Promise<LotterySearchResponse> {
    return this.client.request('/lottery/search', {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  freeLottery(request: FreeLotteryRequest): Promise<unknown> {
    return this.client.request('/users/lottery/free/search', {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  freePublicLottery(request: FreeLotteryRequest): Promise<unknown> {
    return this.client.request('/lottery/free/search', {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  getStock(raffleId: number | string): Promise<LotteryStock> {
    return this.client.request(`/lottery/info/${raffleId}`);
  }

  getUserStock(raffleId: number | string): Promise<LotteryStock> {
    return this.client.request(`/users/lottery/info/${raffleId}`);
  }

  getLotteryTickets(
    raffleId: number | string,
    query: Record<string, unknown> = {},
  ): Promise<LotterySearchResponse> {
    return this.client.request(`/users/lottery/decimos/${raffleId}`, { query });
  }

  getPublicLotteryTickets(
    raffleId: number | string,
    query: Record<string, unknown> = {},
  ): Promise<LotterySearchResponse> {
    return this.client.request(`/lottery/decimos/${raffleId}`, { query });
  }

  getSubscriptionInfo(): Promise<LotterySubscriptionInfo[]> {
    return this.client.request('/lottery/infoSubscribe');
  }

  redeemShares(payload: Record<string, unknown>): Promise<PlayResult> {
    return this.client.request('/users/papeletas', {
      method: 'POST',
      body: payload,
      retry: false,
    });
  }
}

export class TicketsModule {
  constructor(private readonly client: Client) {}

  list(firstResult = 0, gameIds: string[] = []): Promise<TicketsPage> {
    const suffix = gameIds.length
      ? `/${gameIds.join('+').toLowerCase()}`
      : '';
    return this.client.request(`/users/boletos/me${suffix}`, {
      query: { firstResult },
    });
  }

  getFilters(): Promise<TicketFiltersResponse> {
    return this.client.request('/users/boletos/me/filters');
  }

  get(ticketId: number | string): Promise<Ticket> {
    return this.client.request(`/users/boletos/${ticketId}`);
  }

  getHtml(ticketId: number | string): Promise<string> {
    return this.client.request(`/users/boletos/html/${ticketId}`, {
      responseType: 'text',
    });
  }

  edit(request: EditTicketRequest): Promise<MessageResponse> {
    return this.client.request('/users/boletos/', {
      method: 'PUT',
      body: request,
    });
  }

  archive(ticketId: number | string): Promise<void> {
    return this.client.request(`/users/boletos/${ticketId}/archive`, {
      method: 'PUT',
      body: {},
    });
  }

  unarchive(ticketId: number | string): Promise<void> {
    return this.client.request(`/users/boletos/${ticketId}/unarchive`, {
      method: 'PUT',
      body: {},
    });
  }

  cancel(ticketId: number | string): Promise<void> {
    return this.client.request(`/users/boletos/${ticketId}/cancel`, {
      method: 'PUT',
    });
  }

  delete(ticketId: number | string): Promise<void> {
    return this.client.request(`/users/boletos/${ticketId}`, {
      method: 'DELETE',
    });
  }

  deleteAllArchived(): Promise<void> {
    return this.client.request('/users/boletos/archivedAll', {
      method: 'DELETE',
    });
  }

  share(request: ShareTicketRequest): Promise<MessageResponse> {
    return this.client.request('/users/compartir', {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  returnPrize(ticketId: number | string): Promise<MessageResponse> {
    return this.client.request('/users/compartir/prizeReturn', {
      method: 'POST',
      body: { idBoleto: ticketId },
      retry: false,
    });
  }

  subscribe(
    ticketId: number | string,
    request: SubscribeTicketRequest,
  ): Promise<MessageResponse> {
    return this.client.request(`/users/boleto/${ticketId}/subscribe`, {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  getSubscribeInfo(ticketId: number | string): Promise<unknown[]> {
    return this.client.request(`/users/lottery/boleto/${ticketId}/subscribe`);
  }

  unsubscribe(subscriptionId: number | string): Promise<void> {
    return this.client.request(`/users/abonos/${subscriptionId}/subscription`, {
      method: 'DELETE',
    });
  }

  repeat(
    request: RepeatTicketRequest,
    query: Record<string, unknown> = {},
  ): Promise<PlayResult> {
    return this.client.request('/users/boleto/repeat', {
      method: 'POST',
      body: request,
      query,
      retry: false,
    });
  }

  getProof(ticketId: number | string): Promise<Blob> {
    return this.client.request(`/users/boleto/${ticketId}/proof`, {
      responseType: 'blob',
    });
  }

  sendProofToEmail(ticketId: number | string): Promise<MessageResponse> {
    return this.client.request(`/users/boleto/${ticketId}/notifproof`);
  }

  getConstancia(
    ticketId: number | string,
    request: TicketProofRequest = {},
  ): Promise<MessageResponse> {
    return this.client.request(`/users/lotenal/boleto/${ticketId}/constancia`, {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  saveUnfinishedRepeat(request: RepeatTicketRequest): Promise<void> {
    return this.client.request('/users/unfinish/boleto/repetir', {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  requestShipment(request: ShipmentRequest): Promise<MessageResponse> {
    return this.client.request('/users/enviocasa/v2/', {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  requestCollection(request: CollectionRequest): Promise<MessageResponse> {
    return this.client.request('/users/recogida/', {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  cancelCollection(ticketId: number | string): Promise<void> {
    return this.client.request(`/users/recogida/${ticketId}`, {
      method: 'DELETE',
    });
  }

  getShipmentPrice(ticketId: number | string, province: string): Promise<ShipmentPrice> {
    return this.client.request(`/users/envioCasa/${ticketId}`, {
      query: { provinciaEnvio: province },
    });
  }

  getPublicShipmentPrice(
    ticketId: number | string,
    province: string,
  ): Promise<ShipmentPrice> {
    return this.client.request(`/envioCasa/${ticketId}`, {
      query: { provinciaEnvio: province },
      skipAuth: true,
    });
  }

  checkZipCode(zipCode: string, province: string): Promise<{ valid?: boolean }> {
    return this.client.request('/delivery/checkCp', {
      query: { cp: zipCode, province },
      skipAuth: true,
    });
  }

  getPrizeStatus(ticketId: number | string): Promise<PrizeStatus> {
    return this.client.request(`/users/premios/status/${ticketId}`);
  }

  cancelPrizePickup(ticketId: number | string): Promise<void> {
    return this.client.request(`/users/premios/cancelPickup/${ticketId}`, {
      method: 'POST',
      body: {},
      retry: false,
    });
  }

  requestPrizeDelivery(
    ticketId: number | string,
    request: Record<string, unknown>,
  ): Promise<void> {
    return this.client.request(`/users/premios/requestDelivery/${ticketId}`, {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  signPrizePickup(signature: string): Promise<MessageResponse> {
    return this.client.request('/users/premios/signPickup/', {
      method: 'POST',
      body: { signature },
      retry: false,
    });
  }
}

export class WalletModule {
  constructor(private readonly client: Client) {}

  getMovements(query: Record<string, unknown> = {}): Promise<MoneyMovementsResponse> {
    return this.client.request('/users/movimientos/me', { query });
  }

  getMovementStatus(movementId: string | number): Promise<MoneyMovement> {
    return this.client.request(`/users/movimientos/status/${movementId}`);
  }

  getPspRedsys(params: {
    amount: number;
    useSavedCreditCard?: boolean;
    creditCardAlias?: string;
    autoCreditMultiple?: number;
  }): Promise<string> {
    return this.client.request('/users/psp/redsys', {
      query: {
        amount: params.amount,
        redirectUrlAfter: 'https://web.tulotero.es/tpv.html',
        useSavedCreditCard: params.useSavedCreditCard ? 'true' : undefined,
        creditCardAlias: params.creditCardAlias,
        autoCreditMultiple: params.autoCreditMultiple,
      },
      responseType: 'text',
      retry: false,
    });
  }

  getPspResponse(query: Record<string, unknown>): Promise<unknown> {
    return this.client.request('/users/movimientos/pspResponse', { query });
  }

  withdraw(request: WithdrawRequest): Promise<MessageResponse> {
    return this.client.request('/users/withdraw', {
      method: 'POST',
      query: { enhanced: true },
      form: {
        cuenta: request.cuenta,
        cantidad: request.cantidad,
        persist: request.persist,
        useOtp: request.useOtp,
      },
      retry: false,
    });
  }

  getWithdrawInfo(): Promise<WithdrawInfo> {
    return this.client.request('/users/withdrawInfo').then((response) => {
      const record = isRecord(response) ? response : {};
      return (record.object as WithdrawInfo | undefined) ?? record;
    });
  }

  withdrawV2(request: WithdrawV2Request): Promise<MessageResponse> {
    return this.client.request('/users/withdraw/v2', {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  sendWithdrawOtp(): Promise<MessageResponse> {
    return this.client.request('/users/withdrawal/send-otp', {
      method: 'POST',
      body: {},
      retry: false,
    });
  }

  verifyWithdrawOtp(code: string): Promise<MessageResponse> {
    return this.client.request('/users/withdrawal/verify-otp', {
      method: 'POST',
      query: { code },
      retry: false,
    });
  }

  getBankTransferInfo(): Promise<unknown> {
    return this.client.request('/users/credit/bankTransferRedirectInfo');
  }

  bankTransfer(request: ExternalCreditRequest): Promise<MessageResponse> {
    return this.client.request('/users/credit/external', {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  removeCreditCard(): Promise<void> {
    return this.client.request('/users/creditCard', { method: 'DELETE' });
  }

  setAutoCredit(request: AutoCreditRequest): Promise<MessageResponse> {
    return this.client.request('/users/autoCredit', {
      method: 'POST',
      form: { autoCreditMultiple: request.autoCreditMultiple },
    });
  }

  removeAutoCredit(): Promise<void> {
    return this.client.request('/users/autoCredit', { method: 'DELETE' });
  }

  removeBankAccount(): Promise<void> {
    return this.client.request('/users/bankaccount', { method: 'DELETE' });
  }

  nativeCredit(request: NativeCreditRequest): Promise<MessageResponse> {
    return this.client.request('/users/credit/native', {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  markWithdrawalDisplayed(requestId: number | string): Promise<void> {
    return this.client.request(`/users/withdrawalrequest/markAsDisplayed/${requestId}`, {
      method: 'PUT',
      body: {},
    });
  }

  getSummary(year: number): Promise<SummaryResponse> {
    return this.client.request('/users/movimientos/summary', {
      query: { year },
    });
  }

  downloadSummaryPdf(year: number): Promise<Blob> {
    return this.client.request('/users/movimientos/summary/pdf', {
      query: { year },
      responseType: 'blob',
    });
  }

  pciCredit(request: CreditCardRequest): Promise<MessageResponse> {
    return this.client.request('/users/credit/pci', {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  pciSavedCard(request: CreditCardRequest): Promise<MessageResponse> {
    return this.client.request('/users/credit/pci/savedCard', {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  saveCard(request: SaveCardRequest): Promise<MessageResponse> {
    return this.client.request('/users/credit/pci/saveCardWithoutCredit', {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  getPaymentMethods(): Promise<PaymentMethod[]> {
    return this.client.request('/users/paymentmethod').then((response) => {
      const record = isRecord(response) ? response : {};
      return (record.object as PaymentMethod[] | undefined) ?? [];
    });
  }

  addPaymentMethod(request: PaymentMethodLoadRequest): Promise<MessageResponse> {
    return this.client.request('/users/paymentmethod/direct', {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  addPaymentWidget(request: PaymentMethodWidgetRequest): Promise<{ html?: string }> {
    return this.client
      .request<{ object?: { html?: string } }>(
        '/users/paymentmethod/external/create-widget',
        { method: 'POST', body: request, retry: false },
      )
      .then((response) => response.object ?? {});
  }

  loadPaymentMethod(request: PaymentMethodLoadRequest): Promise<MessageResponse> {
    return this.client.request('/users/paymentmethod/load', {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  withdrawToPaymentMethod(request: PaymentMethodLoadRequest): Promise<MessageResponse> {
    return this.client.request('/users/paymentmethod/withdraw', {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  deletePaymentMethod(id: number | string): Promise<void> {
    return this.client.request(`/users/paymentmethod/${id}`, {
      method: 'DELETE',
    });
  }

  favoritePaymentMethod(id: number | string): Promise<MessageResponse> {
    return this.client.request(`/users/paymentmethod/favorite/${id}`, {
      method: 'POST',
      body: {},
    });
  }

  getAndroidSubscription(): Promise<unknown> {
    return this.client.request('/users/android/subscription');
  }

  subscribeAndroid(request: Record<string, unknown>): Promise<MessageResponse> {
    return this.client.request('/users/android/subscription', {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  unsubscribeAndroid(): Promise<void> {
    return this.client.request('/users/android/subscription', {
      method: 'DELETE',
    });
  }
}

export class GroupsModule {
  constructor(private readonly client: Client) {}

  get(groupId: number | string, lastUpdate?: number): Promise<Group> {
    return this.client.request(`/users/groups/${groupId}`, {
      query: { lastUpdate },
    });
  }

  create(request: GroupCreateRequest): Promise<{ id: number | string }> {
    return this.client.request('/users/groups', {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  join(code: string): Promise<Group> {
    return this.client.request('/users/groups/join', {
      method: 'POST',
      body: { code },
      retry: false,
    });
  }

  update(groupId: number | string, request: GroupUpdateRequest): Promise<Group> {
    return this.client.request(`/users/groups/${groupId}`, {
      method: 'PUT',
      body: request,
    });
  }

  updatePreferences(groupId: number | string, request: GroupUpdateRequest): Promise<Group> {
    return this.client.request(`/users/groups/${groupId}/members/me/profile`, {
      method: 'PUT',
      body: request,
    });
  }

  leave(groupId: number | string): Promise<void> {
    return this.client.request(`/users/groups/${groupId}/members/me`, {
      method: 'DELETE',
    });
  }

  invite(groupId: number | string, request: GroupMemberInvite): Promise<MessageResponse> {
    return this.client.request(`/users/groups/${groupId}/members`, {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  kick(groupId: number | string, userId: number | string): Promise<void> {
    return this.client.request(`/users/groups/${groupId}/members/${userId}`, {
      method: 'DELETE',
    });
  }

  requestMoney(groupId: number | string, request: GroupMoneyRequest): Promise<Group> {
    return this.client.request(`/users/groups/${groupId}/balance/request`, {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  distribute(groupId: number | string, request: GroupMoneyRequest): Promise<Group> {
    return this.client.request(`/users/groups/${groupId}/balance/withdraw`, {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  distributeParticipants(groupId: number | string, request: GroupMoneyRequest): Promise<Group> {
    return this.client.request(`/users/groups/${groupId}/balance/withdrawParticipants`, {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  transfer(groupId: number | string, request: GroupTransferRequest): Promise<Group> {
    return this.client.request(`/users/groups/${groupId}/balance/transfer`, {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  transferPending(groupId: number | string, userIds: Array<number | string>): Promise<Group> {
    return this.client.request(`/users/groups/${groupId}/balance/transferPending`, {
      method: 'POST',
      body: { userIds },
      retry: false,
    });
  }

  transferCycle(groupId: number | string, amount: number): Promise<Group> {
    return this.client.request(`/users/groups/${groupId}/balance/transferCycle`, {
      method: 'POST',
      body: { amount },
      retry: false,
    });
  }

  distributeBlocked(groupId: number | string, request: GroupMoneyRequest): Promise<Group> {
    return this.client.request(`/users/groups/${groupId}/balanceBlocked/withdraw`, {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  distributeAllBlocked(groupId: number | string, amount: number): Promise<Group> {
    return this.client.request(`/users/groups/${groupId}/balanceBlocked/withdrawAll`, {
      method: 'POST',
      body: { amount },
      retry: false,
    });
  }

  transferBlocked(groupId: number | string, amount: number): Promise<Group> {
    return this.client.request(`/users/groups/${groupId}/balanceBlocked/transfer`, {
      method: 'POST',
      body: { amount },
      retry: false,
    });
  }

  sendMessage(groupId: number | string, request: GroupMessageRequest): Promise<Group> {
    return this.client.request(`/users/groups/${groupId}/message`, {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  uploadPhoto(groupId: number | string, file: Blob, filename = 'group.jpg'): Promise<unknown> {
    const form = new FormData();
    form.append('img', file, filename);
    return this.client.request(`/users/groups/${groupId}/photo`, {
      method: 'POST',
      multipart: form,
    });
  }

  checkCode(code: string): Promise<boolean> {
    return this.client
      .request(`/users/codes/${encodeURIComponent(code)}/availability`)
      .then(() => true)
      .catch((error) => {
        if (error instanceof ApiError && error.status === 400) return false;
        throw error;
      });
  }

  getByCode(code: string): Promise<Group> {
    return this.client.request(`/groups/${encodeURIComponent(code)}`);
  }

  getBalanceHistory(
    groupId: number | string,
    query: { idLessThan?: number; types?: string[] } = {},
  ): Promise<PaginatedResponse<GroupMoneyActivity>> {
    return this.client.request(`/users/groups/${groupId}/history/balance`, {
      query: {
        idLessThan: query.idLessThan,
        types: query.types?.join(','),
      },
    });
  }

  getHistory(
    groupId: number | string,
    cursor: number,
    direction: 'older' | 'newer' = 'older',
    numResults = 10,
  ): Promise<PaginatedResponse<GroupMoneyActivity>> {
    return this.client.request(`/users/groups/${groupId}/history`, {
      query: {
        numResults,
        [direction === 'older' ? 'idLessThan' : 'idGreaterThan']: cursor,
      },
    });
  }

  getMemberHistory(
    groupId: number | string,
    userId: number | string,
    query: Record<string, unknown> = {},
  ): Promise<PaginatedResponse<GroupMoneyActivity>> {
    return this.client.request(`/users/groups/${groupId}/members/${userId}/history`, {
      query,
    });
  }
}

export class ClubsModule {
  constructor(private readonly client: Client) {}

  getClubs(gameId: string | number, asUser = false): Promise<{ penyas: Penya[] }> {
    const path = asUser ? `/users/penyas/${gameId}` : `/penyas/${gameId}`;
    return this.client.request(path);
  }

  playMultiple(request: ClubPlayRequest): Promise<PlayResult> {
    return this.client.request('/users/penyas/v1/participacion/multiple', {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  joinPrivate(promo: string): Promise<MessageResponse> {
    return this.client.request('/users/penyas/private/join', {
      method: 'POST',
      body: { promo },
      retry: false,
    });
  }

  getByCode(code: string): Promise<{ penyas: Penya[] }> {
    return this.client.request(`/loteriaEmpresas/${code}`);
  }

  getByCodeAsUser(code: string): Promise<{ penyas: Penya[] }> {
    return this.client.request(`/users/penyas/promo/${code}`);
  }

  isCodeAvailable(code: string, parentCode: string): Promise<boolean> {
    return this.client
      .request(`/loteriaEmpresas/isChildAvailable/${code}`, {
        query: { parentCode },
      })
      .then(() => true);
  }

  isCodeAvailableAsUser(code: string, parentCode: string): Promise<boolean> {
    return this.client
      .request(`/users/loteriaEmpresas/isChildAvailable/${code}`, {
        query: { parentCode },
      })
      .then(() => true);
  }

  saveUnfinished(request: ClubPlayRequest): Promise<void> {
    return this.client.request('/users/unfinish/penyas/participacion/multiple', {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  hide(clubId: number | string): Promise<void> {
    return this.client.request(`/users/penyas/hide/${clubId}`, {
      method: 'PUT',
      body: {},
    });
  }

  mute(clubId: number | string): Promise<void> {
    return this.client.request(`/users/penyas/mute/${clubId}`, {
      method: 'PUT',
      body: {},
    });
  }

  createCompany(request: CompanyClubRequest): Promise<MessageResponse> {
    return this.client.request('/users/loteriaEmpresas', {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  updateCompany(request: CompanyClubRequest): Promise<MessageResponse> {
    return this.client.request('/users/loteriaEmpresas', {
      method: 'PUT',
      body: request,
    });
  }

  deleteCompany(id: number | string): Promise<void> {
    return this.client.request(`/users/loteriaEmpresas/${id}`, {
      method: 'DELETE',
    });
  }

  getCompany(id: number | string): Promise<Penya> {
    return this.client.request(`/users/loteriaEmpresas/${id}`);
  }

  uploadCompanyImage(penyaId: number | string, file: Blob, filename = 'club.jpg'): Promise<unknown> {
    const form = new FormData();
    form.append('penyaId', String(penyaId));
    form.append('img', file, filename);
    return this.client.request('/users/loteriaEmpresas/image', {
      method: 'POST',
      multipart: form,
    });
  }

  isPromoCodeFree(code: string): Promise<boolean> {
    return this.client.request(`/users/loteriaEmpresas/isPromoCodeFree/${code}`);
  }

  getCreationInfo(code: string): Promise<unknown> {
    return this.client.request(`/users/loteriaEmpresas/penyasCreationInfo/${code}`);
  }

  getPenyaTickets(penyaId: number | string): Promise<{ object: Ticket[] }> {
    return this.client.request(`/users/penyas/boletos/${penyaId}`);
  }
}

export class KycModule {
  constructor(private readonly client: Client) {}

  openProcess(processId: string | number, id: string | number, body: unknown): Promise<KycStatus> {
    return this.client.request(`/users/kyc/servlet/${processId}`, {
      method: 'POST',
      query: { id },
      body,
      retry: false,
    });
  }

  parseDocument(request: KycScannerParseRequest): Promise<KycScannerParseResponse> {
    return this.client.request('/users/kyc/scanner/parse', {
      method: 'POST',
      body: request,
      retry: false,
    });
  }
}

export class NewsModule {
  constructor(private readonly client: Client) {}

  getPublicNews(firstResult = 0, region?: string): Promise<NewsResponse> {
    return this.client.request(`/newsflash`, {
      query: { firstResult },
      headers: region ? { region } : undefined,
      skipAuth: true,
    });
  }

  getUserNews(firstResult = 0, region?: string): Promise<NewsResponse> {
    return this.client.request(`/users/news`, {
      query: { firstResult },
      headers: region ? { region } : undefined,
    });
  }

  visitPublicNews(id: number | string): Promise<unknown> {
    return this.client.request(`/guestnews/${id}`, { skipAuth: true });
  }

  visitUserNews(id: number | string): Promise<unknown> {
    return this.client.request(`/users/news/${id}`);
  }

  markAsRead(): Promise<void> {
    return this.client.request('/users/news/touch', {
      method: 'POST',
      body: {},
    });
  }
}

export class PlatformModule {
  constructor(private readonly client: Client) {}

  getEndpointConfig(): Promise<EndpointConfig> {
    return this.client.request('/endpoint', { skipAuth: true });
  }

  getAllInfo(lastUpdate?: number): Promise<AllInfoResponse> {
    return this.client.request('/users/allinfo/v2', {
      query: { lastUpdate },
    });
  }

  shouldShowPrivacyModal(email: string): Promise<ResultAvailability> {
    return this.client.request(
      `/shouldShowPrivacyModalOnRegister/${encodeURIComponent(email)}`,
      { skipAuth: true },
    );
  }

  getVersionFile(url: string): Promise<unknown> {
    return this.client.request(url, {
      query: { 'ngsw-bypass': 1, 'cache-bust': Date.now() },
      skipAuth: true,
    });
  }
}

export class SupportModule {
  constructor(private readonly client: Client) {}

  sendSuggestion(request: SuggestionRequest): Promise<MessageResponse> {
    return this.client.request('/users/suggestion', {
      method: 'POST',
      body: request,
      retry: false,
    });
  }

  sendAnonymousSuggestion(request: Omit<SuggestionRequest, 'versionCode' | 'deviceType'>): Promise<MessageResponse> {
    return this.client.request('/suggestion', {
      method: 'POST',
      body: {
        ...request,
        versionCode: 1389,
        deviceType: 'WEB',
      },
      skipAuth: true,
      retry: false,
    });
  }
}

/* -------------------------------------------------------------------------- */
/* Helpers de composición                                                     */
/* -------------------------------------------------------------------------- */

export function createClient(options: TuloteroClientOptions = {}): TuloteroClient {
  return new TuloteroClient(options);
}

export {
  MemoryTokenStorage as InMemoryTokenStorage,
};

/** Crea un cliente apuntando al mirror local (IV/mirror, puerto 4300). */
export function createMirrorClient(options: Omit<TuloteroClientOptions, 'baseUrl'> = {}): TuloteroClient {
  return new TuloteroClient({
    ...options,
    baseUrl: 'http://127.0.0.1:4300/backend-proxy-es/tuloteroweb/rest',
  });
}
