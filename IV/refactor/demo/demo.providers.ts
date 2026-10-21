import { HttpClient, HttpErrorResponse, provideHttpClient, withInterceptors } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { provideRouter } from '@angular/router';
import { Observable, of, delay } from 'rxjs';
import { AuthStrategyManager, AuthStrategyType, JwtAuthStrategy, SessionAuthStore, SessionService } from '@core/auth/auth.model';
import {
  AUTH_STRATEGY_MANAGER,
  DYNAMIC_ALLOWED_DOMAINS,
  SESSION_AUTH_STORE,
  SESSION_SERVICE,
} from '@core/auth/auth.tokens';
import { sessionAuthInterceptor } from '@core/auth/session-auth.interceptor';
import { tokenRefreshInterceptor } from '@core/auth/token-refresh.interceptor';
import { sessionExpiryInterceptor } from '@core/auth/session-expiry.interceptor';
import { APP_ENVIRONMENT, Environment } from '@core/config/environment.tokens';
import { LocaleService } from '@core/i18n/locale.service';
import { RedirectUrlService } from '@core/routing/redirect-url.service';
import { AlertsService } from '@core/ui/alerts.service';
import { DemoState } from './demo.state';
import { echoBackendInterceptor } from './echo.interceptor';

const LIVE_ENDPOINT = 'https://web-backend.es.tulotero.net/tuloteroweb/rest';
const DEMO_API_URL = `${LIVE_ENDPOINT}/demo`;

// Valores de producción tomados de chunk-HQZV36DJ.js (web.tulotero.es, build main-C3X6YJSJ).
const environment: Environment = {
  endpoint: LIVE_ENDPOINT,
  enableAuthDomains: [],
  defaultHeaders: { AvoidRedirect: 'true', Client: 'web' },
  appVersion: '1389',
  production: true,
  globalDomain: 'tulotero.es',
  noDeleteAllInfoInVersionURL: 'https://static.tulotero.net/versions-web.json',
  localStorageKeys: {
    allInfo: '0x00',
    token: '0x01',
    appVersion: '0x02',
    sponsorNew: '0x03',
    currentPlay: '0x04',
    deviceId: '0x05',
    installation: '0x06',
    popupStates: '0x07',
    contacts: '0x08',
    googleLogin: '0x09',
    messageBanner: '0x10',
    googleToken: '0x11',
    geolocationPermission: '0x12',
    fingerprint: '0x13',
    kycLaunched: '0x15',
    kycPending: '0x16',
    counterShares: '0x17',
    boothsLastDate: '0x18',
    lastAccess: '0x19',
    cameraDevideIdBack: '0x20',
    cameraDevideIdFront: '0x21',
    persistentSavePlays: '0x22',
    selectedNotificationState: '0x23',
    ticketsGameFilters: '0x24',
    winnersLastDate: '0x25',
    winners: '0x26',
    reviewsLastDate: '0x27',
    reviews: '0x28',
    ratingsLastDate: '0x29',
    ratings: '0x30',
    winnersState: '0x31',
    pushPrompted: '0x32',
    pushLastReminder: '0x33',
    userLocale: '0x34',
    media: '0x35',
    mediaLastDate: '0x36',
    mediaGame: '0x37',
    mediaLocale: '0x38',
    failedAuthKey: '0x39',
    suggestionDialogDelay: '0x40',
    lastLogin: '0x41',
    nativeLocaleSent: '0x42',
    rafflesPreventGrouped: '0x43',
    authStrategy: '0x44',
    refreshToken: '0x45',
    refreshTokenUrl: '0x46',
    refreshTokenExp: '0x47',
    transactionStatus: '0x48',
    persistentPopupStates: '0x49',
    endpoint: '0x50',
    phoneLoadAmount: '0x51',
  },
  locale: { locale: 'es-ES', routes: { promoParam: 'codigo', contactUs: 'contacto' } },
  features: { verificationDialogNewFlow: true },
  google: { clientId: '', maps: { apikey: '', defaultZoomIn: 9 } },
  apple: { clientId: 'com.tulotero.webapp.sid' },
  maintenance: { redirectUrl: (locale) => `maintenance-${locale}.html` },
  logger: { endpoint: 'https://web-backend.es.tulotero.net/kibana' },
  geolocation: { defaultAnonimousStateCode: '00' },
};

class DemoSessionAuthStore extends SessionAuthStore {
  private readonly state = inject(DemoState);

  isLoggedIn(): boolean {
    return this.state.loggedIn();
  }

  shouldRefreshAccessToken(): boolean {
    return this.state.mode() === 'expired';
  }

  getAuthorizationHeader(): string | null {
    return this.state.loggedIn() ? `Bearer ${this.state.accessToken()}` : null;
  }

  logout(): void {
    this.state.loggedIn.set(false);
  }
}

class DemoSessionService extends SessionService {
  private readonly state = inject(DemoState);

  isLoggedIn(): Observable<boolean> {
    return of(this.state.loggedIn());
  }

  logout(): void {
    this.state.loggedIn.set(false);
  }

  logoutNoUnregister(): void {
    this.state.loggedIn.set(false);
  }
}

class DemoJwtStrategy implements JwtAuthStrategy {
  readonly type = AuthStrategyType.JWT;

  constructor(private readonly state: DemoState) {}

  getAuthorizationHeader(): string | null {
    return this.state.loggedIn() ? `Bearer ${this.state.accessToken()}` : null;
  }

  isAccessTokenExpired(): boolean {
    return this.state.mode() === 'expired';
  }

  isRefreshTokenExpired(): boolean {
    return this.state.mode() === 'unauthorized';
  }

  markRefreshAttempt(): void {}

  updateTokens(accessToken: string): void {
    this.state.accessToken.set(accessToken);
  }
}

class DemoAuthStrategyManager implements AuthStrategyManager {
  private readonly state = inject(DemoState);
  private readonly strategy = new DemoJwtStrategy(this.state);

  getActiveStrategy(): JwtAuthStrategy {
    return this.strategy;
  }

  refreshAccessToken$(): Observable<{
    accessToken: string;
    refreshToken: string;
    refreshTokenExpirationDate: number;
  }> {
    this.state.refreshCalls.update((calls) => calls + 1);

    return of({
      accessToken: `access-token-v${this.state.refreshCalls() + 1}`,
      refreshToken: 'refresh-token',
      refreshTokenExpirationDate: Date.now() + 3_600_000,
    }).pipe(delay(10));
  }

  clear(): void {
    this.state.loggedIn.set(false);
  }
}

class DemoAlertsService extends AlertsService {
  notifyError(message: string): void {
    console.warn('[alerts]', message);
  }

  notifySuccess(message: string): void {
    console.info('[alerts]', message);
  }
}

class DemoLocaleService extends LocaleService {
  getLocale(): string {
    return 'es-ES';
  }

  getLocaleAbbr(): string {
    return 'es';
  }
}

@Component({
  selector: 'app-demo',
  standalone: true,
  template: `
    <main style="font-family: system-ui; padding: 24px; max-width: 860px">
      <h1>Tulotero auth interceptors</h1>
      <p>Token actual: <code>{{ state.accessToken() }}</code> · refrescos: {{ state.refreshCalls() }}</p>
      <p>Modo: <strong>{{ state.mode() }}</strong> · sesión: {{ state.loggedIn() ? 'activa' : 'cerrada' }}</p>

      <button (click)="request('ok')">Petición normal</button>
      <button (click)="request('expired')">Token a punto de caducar</button>
      <button (click)="request('unauthorized')">Respuesta 401</button>
      <button (click)="reset()">Reiniciar</button>

      <pre style="background:#0f172a;color:#e2e8f0;padding:16px;border-radius:8px;overflow:auto">{{ output() }}</pre>
    </main>
  `,
})
export class DemoComponent {
  private readonly http = inject(HttpClient);
  readonly state = inject(DemoState);
  readonly output = signal('Pulsa un botón para ejecutar la petición.');

  request(mode: 'ok' | 'expired' | 'unauthorized'): void {
    this.state.setMode(mode);

    this.http.get<unknown>(DEMO_API_URL).subscribe({
      next: (body) => this.output.set(JSON.stringify(body, null, 2)),
      error: (error: HttpErrorResponse) =>
        this.output.set(JSON.stringify({ status: error.status, statusText: error.statusText }, null, 2)),
    });
  }

  reset(): void {
    this.state.setMode('ok');
    this.state.loggedIn.set(true);
    this.state.accessToken.set('access-token-v1');
    this.state.refreshCalls.set(0);
    this.output.set('Estado reiniciado.');
  }
}

export const demoProviders = [
  provideRouter([]),
  provideHttpClient(
    withInterceptors([
      sessionAuthInterceptor,
      tokenRefreshInterceptor,
      sessionExpiryInterceptor,
      echoBackendInterceptor,
    ]),
  ),
  { provide: APP_ENVIRONMENT, useValue: environment },
  { provide: SESSION_AUTH_STORE, useClass: DemoSessionAuthStore },
  { provide: SESSION_SERVICE, useClass: DemoSessionService },
  { provide: AUTH_STRATEGY_MANAGER, useClass: DemoAuthStrategyManager },
  { provide: DYNAMIC_ALLOWED_DOMAINS, useValue: { isAllowed: () => true } },
  { provide: AlertsService, useClass: DemoAlertsService },
  { provide: LocaleService, useClass: DemoLocaleService },
  RedirectUrlService,
];
